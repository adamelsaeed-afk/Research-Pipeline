"""Local process and mailbox lifecycle checks; no model or network calls."""
import argparse
from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import test_workflow as fixtures
from research_dispatch import run_dispatch, stop_docker_stage
from research_mailbox import process_one, submit, worker, worker_lock


class LifecycleTests(unittest.TestCase):
    def test_tree_cleanup_error_preserves_cancellation_and_logs(self):
        class Interrupted(fixtures.FakeProcess):
            def communicate(self, input=None, timeout=None):
                self.streams['stdout'].write('Evidence before interruption')
                self.streams['stdout'].flush()
                raise KeyboardInterrupt

            def kill(self):
                self.returncode = -1
                self.communicate = lambda **kwargs: (None, None)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            helper = fixtures.DispatchTests()
            helper.setup_files(root)
            with patch('research_dispatch.subprocess.Popen', Interrupted), \
                 patch('process_tree.ProcessTree.stop', side_effect=RuntimeError('tree cleanup failed')):
                with self.assertRaises(KeyboardInterrupt):
                    run_dispatch(helper.options(root))
            stage = next((root / 'dispatch').iterdir())
            metadata = json.loads((stage / 'dispatch.json').read_text())
            self.assertEqual(metadata['status'], 'cancelled')
            self.assertEqual(metadata['process_tree_cleanup_error'], 'tree cleanup failed')
            self.assertEqual((stage / 'stdout.txt').read_text(), 'Evidence before interruption')
            self.assertFalse((stage / 'result.json').exists())

    def test_tree_cleanup_error_prevents_accepting_a_successful_response(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            helper = fixtures.DispatchTests()
            helper.setup_files(root)
            result = {'role': 'validate', 'verdict': 'approved', 'summary': 'Supported',
                      'issues': [], 'checked_claim_ids': ['F1'],
                      'checks': [{'claim_id': 'F1', 'source_url': 'https://example.org',
                                  'evidence': 'Supports claim', 'verdict': 'confirmed'}]}
            fixtures.FakeProcess.output = json.dumps({'event': 'result', 'result': {
                'status': 'SUCCESS', 'response': json.dumps(result)}})
            with patch('research_dispatch.subprocess.Popen', fixtures.FakeProcess), \
                 patch('process_tree.ProcessTree.stop', side_effect=RuntimeError('tree cleanup failed')):
                with self.assertRaisesRegex(RuntimeError, 'tree cleanup failed'):
                    run_dispatch(helper.options(root))
            stage = next((root / 'dispatch').iterdir())
            metadata = json.loads((stage / 'dispatch.json').read_text())
            self.assertEqual(metadata['status'], 'failed')
            self.assertEqual(metadata['process_tree_cleanup_error'], 'tree cleanup failed')
            self.assertFalse((stage / 'result.json').exists())

    @unittest.skipIf(os.name == 'nt', 'Requires Linux /proc and sh')
    def test_linux_cleanup_finds_reparented_descendant_by_run_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / 'dispatch' / root.name
            stage.mkdir(parents=True)
            marker = root / 'child.pid'
            child_code = f"import os,time; from pathlib import Path; os.chdir('/'); Path({str(marker)!r}).write_text(str(os.getpid())); time.sleep(30)"
            parent_code = f"import subprocess,sys; subprocess.Popen([sys.executable,'-c',{child_code!r}],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)"
            unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], cwd=root)
            parent = subprocess.Popen([sys.executable, '-c', parent_code], cwd=stage,
                                      env={**os.environ, 'RESEARCH_DISPATCH_ID': stage.name})
            try:
                parent.wait(timeout=5)
                deadline = time.monotonic() + 5
                while not marker.exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(marker.exists())
                real_run = subprocess.run

                def local_shell(command, **kwargs):
                    return real_run(command[3:], **kwargs)

                choice = {'docker': {'host_mount': str(root), 'container_mount': str(root), 'container': 'test'}}
                with patch('research_dispatch.subprocess.run', side_effect=local_shell):
                    self.assertEqual(stop_docker_stage(choice, stage), 'matched=1')
                self.assertIsNone(unrelated.poll(), 'Cleanup affected an unrelated process')
                status = Path('/proc') / marker.read_text() / 'stat'
                if status.exists():
                    self.assertEqual(status.read_text().split(') ', 1)[1][0], 'Z')
            finally:
                unrelated.kill()
                unrelated.wait(timeout=5)
                if marker.exists():
                    try:
                        os.kill(int(marker.read_text()), signal.SIGKILL)
                    except ProcessLookupError:
                        pass

    def test_cancellation_stops_descendant_after_chdir_and_parent_exit(self):
        real_popen = subprocess.Popen
        for parent_exits, reason in ((False, 'cancel'), (True, 'cancel'), (False, 'timeout'), (True, 'timeout')):
            with self.subTest(parent_exits=parent_exits, reason=reason), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                helper = fixtures.DispatchTests()
                helper.setup_files(root)
                heartbeat = root / 'heartbeat'
                child_id = root / 'child.pid'
                child_code = ("import os,time; from pathlib import Path; "
                              f"os.chdir({str(root)!r}); p=Path({str(heartbeat)!r}); "
                              "exec('while True:\\n p.write_text(str(time.time_ns()))\\n time.sleep(0.02)')")
                parent_code = ("import subprocess,sys,time; from pathlib import Path; "
                               f"p=subprocess.Popen([sys.executable,'-u','-c',{child_code!r}]); "
                               f"Path({str(child_id)!r}).write_text(str(p.pid)); "
                               + ("sys.exit(0)" if parent_exits else "time.sleep(30)"))
                launched = []

                def launch(command, **kwargs):
                    process = real_popen([sys.executable, '-u', '-c', parent_code], **kwargs)
                    launched.append(process)
                    real_communicate = process.communicate
                    interrupted = False

                    def communicate(input=None, timeout=None):
                        nonlocal interrupted
                        if interrupted:
                            return real_communicate(timeout=timeout)
                        interrupted = True
                        deadline = time.monotonic() + 5
                        while time.monotonic() < deadline:
                            if heartbeat.exists() and (not parent_exits or process.poll() is not None):
                                if reason == 'timeout':
                                    raise subprocess.TimeoutExpired(command, timeout)
                                raise KeyboardInterrupt
                            time.sleep(0.01)
                        raise AssertionError('Test child did not start')

                    process.communicate = communicate
                    return process

                try:
                    with patch('research_dispatch.subprocess.Popen', side_effect=launch):
                        with self.assertRaises(KeyboardInterrupt if reason == 'cancel' else TimeoutError):
                            run_dispatch(helper.options(root))
                    time.sleep(0.05)
                    before = heartbeat.read_text()
                    time.sleep(0.15)
                    self.assertEqual(heartbeat.read_text(), before, 'Descendant survived cancellation')
                finally:
                    if child_id.exists():
                        pid = int(child_id.read_text())
                        if os.name == 'nt':
                            subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'],
                                           capture_output=True, timeout=5)
                        else:
                            try:
                                os.kill(pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                    for process in launched:
                        if process.poll() is None:
                            process.kill()
                        process.wait(timeout=5)


class MailboxLifecycleTests(unittest.TestCase):
    @unittest.skipIf(os.name == 'nt', 'Requires a POSIX shell')
    def test_shell_client_preserves_argument_forms_and_attaches_expiry(self):
        script = Path(__file__).resolve().parents[1] / 'scripts' / 'submit_research_job.sh'
        for optional in ([], ['10'], ['10', 'ids.json']):
            with self.subTest(optional=optional), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                fixtures.DispatchTests().setup_files(root)
                (root / 'ids.json').write_text('["F1"]')
                before = time.time()
                process = subprocess.Popen(['sh', str(script), str(root), 'intake.json',
                                            'brief.md', 'validate', 'validator', 'findings.md', *optional],
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                           start_new_session=True)
                try:
                    deadline = time.monotonic() + 5
                    requests = []
                    while time.monotonic() < deadline:
                        requests = list((root / 'requests').glob('*.json'))
                        if requests:
                            break
                        time.sleep(0.01)
                    self.assertEqual(len(requests), 1)
                    job = json.loads(requests[0].read_text())
                    self.assertGreater(job['expires_at'], before)
                    self.assertLessEqual(job['expires_at'], time.time() + job['timeout'] + 30)
                    self.assertEqual(job.get('input_ids'), 'ids.json' if len(optional) == 2 else None)
                    (root / 'responses' / requests[0].name).write_text(json.dumps({'status': 'completed'}))
                    output, error = process.communicate(timeout=5)
                    self.assertEqual(process.returncode, 0, error)
                    self.assertIn('completed', output)
                finally:
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGKILL)
                    process.communicate(timeout=5)

    def setup_job(self, root, **extra):
        fixtures.DispatchTests().setup_files(root)
        (root / 'requests').mkdir()
        job = {'id': 'job', 'role': 'validate', 'target': 'validator',
               'record': 'intake.json', 'brief': 'brief.md', 'input': 'findings.md',
               'timeout': 10, 'expires_at': time.time() + 40, **extra}
        request = root / 'requests' / 'job.json'
        request.write_text(json.dumps(job))
        return request

    def test_expired_queued_request_never_launches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.setup_job(root, expires_at=time.time() - 1)
            with patch('research_mailbox.run_dispatch', side_effect=AssertionError('Late launch')):
                process_one(root, root / 'config.json', request)
            response = json.loads((root / 'responses' / 'job.json').read_text())
            self.assertEqual(response['status'], 'expired')

    def test_worker_restart_reports_abandoned_processing_without_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.setup_job(root)
            processing = request.with_suffix('.processing')
            scripts = Path(__file__).resolve().parents[1] / 'scripts'
            crash_code = (f"import sys,os,argparse; sys.path.insert(0,{str(scripts)!r}); "
                          "import research_mailbox as m; m.run_dispatch=lambda options:os._exit(17); "
                          f"m.worker(argparse.Namespace(shared_root=m.Path({str(root)!r}), config=m.Path({str(root / 'config.json')!r}), once=True))")
            crashed = subprocess.run([sys.executable, '-B', '-c', crash_code],
                                     capture_output=True, text=True, timeout=5)
            self.assertEqual(crashed.returncode, 17, crashed.stderr)
            self.assertTrue(processing.exists())
            with patch('research_mailbox.run_dispatch', side_effect=AssertionError('Replayed job')):
                worker(argparse.Namespace(shared_root=root, config=root / 'config.json', once=True))
            response = json.loads((root / 'responses' / 'job.json').read_text())
            self.assertEqual(response['status'], 'interrupted')
            self.assertFalse(processing.exists())
            self.assertTrue(processing.with_suffix('.interrupted').exists())

    def test_active_worker_lock_prevents_another_worker_recovering_its_job(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.setup_job(root)
            processing = request.with_suffix('.processing')
            request.rename(processing)
            with worker_lock(root):
                with self.assertRaisesRegex(RuntimeError, 'another mailbox worker'):
                    worker(argparse.Namespace(shared_root=root, config=root / 'config.json', once=True))
                self.assertTrue(processing.exists())
                self.assertFalse((root / 'responses' / 'job.json').exists())

    def test_recovery_preserves_an_already_written_response(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request = self.setup_job(root)
            request.rename(request.with_suffix('.processing'))
            (root / 'responses').mkdir()
            response = root / 'responses' / 'job.json'
            original = json.dumps({'id': 'job', 'status': 'completed', 'result': 'runs/retained/result.json'})
            response.write_text(original)
            worker(argparse.Namespace(shared_root=root, config=root / 'config.json', once=True))
            self.assertEqual(response.read_text(), original)

    def test_missing_or_malformed_expiry_fails_without_launch(self):
        for expiry in (None, False, 'tomorrow', float('nan'), float('inf')):
            with self.subTest(expiry=expiry), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                request = self.setup_job(root, expires_at=expiry)
                with patch('research_mailbox.run_dispatch', side_effect=AssertionError('Invalid launch')):
                    process_one(root, root / 'config.json', request)
                self.assertEqual(json.loads((root / 'responses' / 'job.json').read_text())['status'], 'failed')

    def test_expiry_during_staging_prevents_cli_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            helper = fixtures.DispatchTests()
            helper.setup_files(root)
            options = helper.options(root)
            import shutil
            original_copy = shutil.copyfile
            now = [1000.0]
            options.queue_deadline = 1005.0

            def staging_crosses_deadline(source, destination):
                self.assertLess(now[0], options.queue_deadline)
                original_copy(source, destination)
                now[0] = 1006.0

            with patch('research_dispatch.shutil.copyfile', side_effect=staging_crosses_deadline), \
                 patch('research_dispatch.time.time', side_effect=lambda: now[0]), \
                 patch('research_dispatch.subprocess.Popen', side_effect=AssertionError('Late launch')):
                with self.assertRaisesRegex(TimeoutError, 'expired before CLI launch'):
                    run_dispatch(options)
            stage = next((root / 'dispatch').iterdir())
            self.assertFalse((stage / 'result.json').exists())
            self.assertEqual(json.loads((stage / 'dispatch.json').read_text())['status'], 'failed')

    def test_waiting_submission_expires_at_its_wait_deadline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixtures.DispatchTests().setup_files(root)
            args = argparse.Namespace(shared_root=root, record=root / 'intake.json',
                                      brief=root / 'brief.md', input=root / 'findings.md',
                                      role='validate', target='validator', timeout=10, wait=True)
            with patch('research_mailbox.time.time', return_value=1000), \
                 patch('research_mailbox.time.monotonic', side_effect=[0, 41]), \
                 redirect_stdout(StringIO()):
                with self.assertRaises(TimeoutError):
                    submit(args)
            job = json.loads(next((root / 'requests').glob('*.json')).read_text())
            self.assertEqual(job['expires_at'], 1040)
            request = next((root / 'requests').glob('*.json'))
            with patch('research_mailbox.time.time', return_value=1041), \
                 patch('research_mailbox.run_dispatch', side_effect=AssertionError('Late launch')):
                process_one(root, root / 'config.json', request)
            self.assertEqual(json.loads(next((root / 'responses').glob('*.json')).read_text())['status'], 'expired')
