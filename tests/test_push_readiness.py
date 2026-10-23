"""Readiness regressions: ambiguous results, acceptance and caller feedback."""
import argparse
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import test_workflow as workflow
import test_regressions as fixtures
import manual_live_dispatch as probe
import research_dispatch as dispatch
import research_mailbox as mailbox


class ReadinessTests(unittest.TestCase):
    def test_duplicate_keys_rejected_at_every_result_level(self):
        payload = json.dumps(fixtures.validation())
        candidates = [
            payload.replace('"verdict": "approved"', '"verdict":"blocked","verdict":"approved"', 1),
            payload.replace('"claim_id": "C1"', '"claim_id":"ABSENT","claim_id":"C1"'),
        ]
        for content in candidates:
            for prefix in ('', 'Checked sources.\n'):
                with self.subTest(content=content, prefix=prefix), self.assertRaisesRegex(ValueError, 'duplicate'):
                    dispatch.parse_role_object(prefix + content)

    def test_duplicate_transport_envelope_cannot_override_failure(self):
        envelope = '{"event":"result","result":{"status":"DENIED","status":"SUCCESS","response":' + json.dumps(json.dumps(fixtures.validation())) + '}}'
        process = subprocess.CompletedProcess([], 0, envelope, '')
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(ValueError, 'duplicate'):
            dispatch.parse_result('agy', process, Path(directory))

    def test_nonfinite_json_is_rejected_even_in_extra_fields(self):
        for token in ('NaN', 'Infinity', '-Infinity'):
            payload = json.dumps(fixtures.validation())[:-1] + ',"extra":' + token + '}'
            with self.subTest(token=token), self.assertRaises(ValueError):
                dispatch.parse_role_object(payload)

    def test_blocked_dispatch_is_retained_but_cli_requires_attention(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = fixtures.validation(())
            result.update(verdict='blocked', summary='Source access unavailable')
            path = fixtures.CoverageRegressions().dispatch(root, result)
            out, error = StringIO(), StringIO()
            with patch('research_dispatch.argparse.ArgumentParser.parse_args', return_value=argparse.Namespace()), \
                 patch('research_dispatch.run_dispatch', return_value=path), redirect_stdout(out), redirect_stderr(error):
                self.assertEqual(dispatch.main(), 3)
            self.assertIn(str(path), out.getvalue())
            self.assertIn('blocked', error.getvalue())
            self.assertIn('Source access unavailable', error.getvalue())
            self.assertIn('C1', error.getvalue())
            self.assertIn('C2', error.getvalue())
            metadata = json.loads((path.parent / 'dispatch.json').read_text())
            self.assertEqual(metadata['status'], 'completed')
            self.assertEqual(metadata['role_verdict'], 'blocked')
            self.assertTrue(metadata['requires_attention'])

    def test_source_probe_does_not_accept_nonapproval_or_unresolved_gap(self):
        for role, result in (
            ('validate', {**fixtures.validation(()), 'verdict': 'blocked'}),
            ('validate', {**fixtures.validation(('P1',)), 'verdict': 'gaps_found'}),
            ('validate', fixtures.validation(('P1',))),  # unrelated source
            ('gap_fill', {'role':'gap_fill', 'verdict':'completed', 'changes':[],
                          'unresolved':[{'gap_id':'G1','reason':'No source access'}]}),
        ):
            with self.subTest(role=role, result=result), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                workflow.DispatchTests().setup_files(root)
                result_path = root / 'result.json'
                result_path.write_text(json.dumps(result), encoding='utf-8')
                prepared = root / 'prepared'; prepared.mkdir()
                args = argparse.Namespace(config=root/'config.json', target='validator', role=role,
                                          timeout=10, prepare_only=False)
                with patch('manual_live_dispatch.argparse.ArgumentParser.parse_args', return_value=args), \
                     patch('manual_live_dispatch.tempfile.mkdtemp', return_value=str(prepared)), \
                     patch('manual_live_dispatch.run_dispatch', return_value=result_path), \
                     redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    self.assertNotEqual(probe.main(), 0)

    def test_docker_probe_preparations_have_different_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            choice = {'cli':'opencode', 'model':'provider/model', 'transport':'docker',
                      'docker':{'host_mount':str(root), 'container_mount':'/shared', 'container':'test'}}
            config = root/'config.json'; config.write_text(json.dumps({'targets':{'validator':choice}}))
            args = argparse.Namespace(config=config, target='validator', role='validate', timeout=10, prepare_only=True)
            outputs = []
            for _ in range(2):
                output = StringIO()
                with patch('manual_live_dispatch.argparse.ArgumentParser.parse_args', return_value=args), redirect_stdout(output):
                    self.assertEqual(probe.main(), 0)
                outputs.append(output.getvalue())
            self.assertNotEqual(*outputs)

    def test_mailbox_blockage_is_visible_to_waiting_client(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflow.DispatchTests().setup_files(root)
            args = argparse.Namespace(shared_root=root, record=root/'intake.json', brief=root/'brief.md',
                                      input=root/'findings.md', role='validate', target='validator', timeout=10, wait=True)
            result = fixtures.validation(())
            result.update(verdict='blocked', summary='Authentication unavailable')
            workflow.FakeProcess.output = json.dumps({'event':'result','result':{
                'status':'SUCCESS','response':json.dumps(result)}})

            def handle_request():
                request = next((root/'requests').glob('*.json'))
                with patch('research_dispatch.subprocess.Popen', workflow.FakeProcess):
                    mailbox.process_one(root, root/'config.json', request)

            # First response poll waits; the sleep hook lets the worker handle it.
            with patch('research_mailbox.time.sleep', side_effect=lambda _: handle_request()), redirect_stdout(StringIO()) as out:
                self.assertEqual(mailbox.submit(args), 3)
            response = json.loads(next((root/'responses').glob('*.json')).read_text())
            self.assertEqual(response['status'], 'completed')
            self.assertEqual(response['role_verdict'], 'blocked')
            self.assertTrue(response['requires_attention'])
            self.assertIn('Authentication unavailable', out.getvalue())
