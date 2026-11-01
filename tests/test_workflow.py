import argparse
from contextlib import redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_intake import BASE_DECISIONS, check, intake_sha256
from research_dispatch import command_for, parse_role_object, run_dispatch, stop_docker_stage, validate_result
from research_mailbox import process_one, submit
from preflight_delegate import check_target


class FakeProcess:
    pid = 12345
    returncode = 0
    output = ""
    last_input = None
    last_kwargs = None

    def __init__(self, *args, **kwargs):
        self.command = args[0]
        self.streams = kwargs
        FakeProcess.last_kwargs = kwargs

    def communicate(self, input=None, timeout=None):
        FakeProcess.last_input = input
        self.streams["stdout"].write(self.output)
        self.streams["stdout"].flush()
        return None, None


def intake(brief: bytes, external=True):
    answers = {name: "specified" for name in BASE_DECISIONS}
    answers["research_type"] = "technical"
    answers["validation_mode"] = "external_cli" if external else "same_session"
    if external:
        answers.update(validator_cli="validator", gap_filler_cli="gap_filler",
                       validator_transport="direct", gap_filler_transport="direct",
                       validator_model="default", gap_filler_model="provider/model")
    record = {"required_branches": [], "open_branches": [],
            "decisions": {name: {"state": "answered", "answer": answer,
                                  "user_evidence": {
                                      "message_ref": "synthetic-test-user-turn",
                                      "quote": "Use the scope and validation arrangement in this test fixture."}}
                          for name, answer in answers.items()},
            "confirmation": {"confirmed": True,
                             "user_evidence": {
                                 "message_ref": "synthetic-test-user-turn",
                                 "quote": "I approve this test fixture brief and its recorded decisions."},
                             "brief_sha256": hashlib.sha256(brief).hexdigest()}}
    record["confirmation"]["intake_sha256"] = intake_sha256(record)
    return record


class IntakeTests(unittest.TestCase):
    def test_changed_brief_and_open_branch_block_pipeline(self):
        brief = b"Research these specified topics."
        record = intake(brief)
        self.assertEqual(check(record, brief), [])
        self.assertTrue(any("confirmation" in e for e in check(record, brief + b" changed")))
        record["required_branches"] = ["comparison_denominator"]
        self.assertTrue(any("comparison_denominator" in e for e in check(record, brief)))
        record["decisions"]["comparison_denominator"] = {"state": "unclear"}
        self.assertTrue(any("unclear" in e for e in check(record, brief)))

    def test_market_and_delegate_branches_are_required(self):
        brief = b"Market comparison."
        record = intake(brief)
        record["decisions"]["research_type"]["answer"] = "market"
        del record["decisions"]["gap_filler_cli"]
        errors = check(record, brief)
        self.assertTrue(any("market_subtype" in e for e in errors))
        self.assertTrue(any("gap_filler_cli" in e for e in errors))


class DispatchTests(unittest.TestCase):
    def test_cancellation_preserves_output_from_real_child(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_files(root)
            real_popen = subprocess.Popen
            launched = []
            child_code = ("import sys, time; "
                          "sys.stdout.buffer.write(b'partial finding without newline'); sys.stdout.flush(); "
                          "sys.stderr.buffer.write(b'source check in progress'); sys.stderr.flush(); "
                          "time.sleep(30)")

            def launch(command, **kwargs):
                process = real_popen([sys.executable, "-u", "-c", child_code], **kwargs)
                launched.append(process)
                real_communicate = process.communicate
                interrupted = False

                def communicate(input=None, timeout=None):
                    nonlocal interrupted
                    if interrupted:
                        return real_communicate(timeout=timeout)
                    interrupted = True
                    stage = Path(kwargs["cwd"])
                    deadline = time.monotonic() + 5
                    while time.monotonic() < deadline:
                        if ((stage / "stdout.txt").read_bytes() == b"partial finding without newline"
                                and (stage / "stderr.txt").read_bytes() == b"source check in progress"):
                            raise KeyboardInterrupt
                        time.sleep(0.01)
                    raise AssertionError("Child output was not captured while the run was active")

                process.communicate = communicate
                return process

            try:
                with patch("research_dispatch.subprocess.Popen", side_effect=launch):
                    with self.assertRaises(KeyboardInterrupt):
                        run_dispatch(self.options(root))
                stage = next((root / "dispatch").iterdir())
                self.assertEqual(json.loads((stage / "dispatch.json").read_text())["status"], "cancelled")
                self.assertEqual((stage / "stdout.txt").read_bytes(), b"partial finding without newline")
                self.assertEqual((stage / "stderr.txt").read_bytes(), b"source check in progress")
                self.assertIsNotNone(launched[0].poll())
            finally:
                for process in launched:
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=5)

    def test_cancellation_preserves_output_when_docker_cleanup_fails(self):
        class InterruptedProcess(FakeProcess):
            def communicate(self, input=None, timeout=None):
                self.streams["stdout"].write("Already captured evidence\n")
                self.streams["stdout"].flush()
                raise KeyboardInterrupt

            def kill(self):
                self.returncode = -1
                self.communicate = lambda **kwargs: (None, None)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_files(root)
            record = json.loads((root / "intake.json").read_text())
            record["decisions"]["validator_transport"]["answer"] = "docker"
            record["confirmation"]["intake_sha256"] = intake_sha256(record)
            (root / "intake.json").write_text(json.dumps(record))
            config = json.loads((root / "config.json").read_text())
            config["targets"]["validator"].update(transport="docker", docker={
                "host_mount": str(root), "container_mount": "/shared", "container": "test-validator"})
            (root / "config.json").write_text(json.dumps(config))
            with patch("research_dispatch.subprocess.Popen", InterruptedProcess), \
                 patch("research_dispatch.stop_docker_stage", side_effect=RuntimeError("cleanup unavailable")):
                with self.assertRaises(KeyboardInterrupt):
                    run_dispatch(self.options(root))
            stage = next((root / "dispatch").iterdir())
            metadata = json.loads((stage / "dispatch.json").read_text())
            self.assertEqual(metadata["status"], "cancelled")
            self.assertEqual(metadata["cancel_cleanup_error"], "cleanup unavailable")
            self.assertEqual(metadata["exit_code"], -1)
            self.assertEqual((stage / "stdout.txt").read_text(), "Already captured evidence\n")

    def test_cancellation_records_status_and_preserves_output(self):
        class InterruptedProcess(FakeProcess):
            returncode = None
            killed = False

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.streams = kwargs

            def communicate(self, input=None, timeout=None):
                if not self.killed:
                    for name, value in (("stdout", "Partial finding before cancellation\n"),
                                        ("stderr", "Source check in progress\n")):
                        stream = self.streams[name]
                        if hasattr(stream, "write"):
                            stream.write(value)
                            stream.flush()
                    raise KeyboardInterrupt
                return "Partial finding before cancellation\n", "Source check in progress\n"

            def kill(self):
                self.killed = True
                self.returncode = -1

        for transport in ("direct", "docker"):
            with self.subTest(transport=transport), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.setup_files(root)
                record = json.loads((root / "intake.json").read_text())
                record["decisions"]["validator_transport"]["answer"] = transport
                record["confirmation"]["intake_sha256"] = intake_sha256(record)
                (root / "intake.json").write_text(json.dumps(record))
                config = json.loads((root / "config.json").read_text())
                choice = config["targets"]["validator"]
                choice["transport"] = transport
                if transport == "docker":
                    choice["docker"] = {"host_mount": str(root), "container_mount": "/shared",
                                        "container": "test-validator"}
                (root / "config.json").write_text(json.dumps(config))
                launched = []

                def launch(*args, **kwargs):
                    process = InterruptedProcess(*args, **kwargs)
                    launched.append(process)
                    return process

                with patch("research_dispatch.subprocess.Popen", side_effect=launch), \
                     patch("research_dispatch.stop_docker_stage", return_value="matched=1") as cleanup:
                    with self.assertRaises(KeyboardInterrupt):
                        run_dispatch(self.options(root))
                stage = next((root / "dispatch").iterdir())
                metadata = json.loads((stage / "dispatch.json").read_text())
                self.assertEqual(metadata["status"], "cancelled")
                self.assertEqual(metadata["cancellation_reason"], "User interrupted the run")
                self.assertIn("finished_at", metadata)
                self.assertGreaterEqual(metadata["elapsed_seconds"], 0)
                self.assertTrue(launched[0].killed)
                self.assertEqual((stage / "stdout.txt").read_text(),
                                 "Partial finding before cancellation\n")
                self.assertEqual((stage / "stderr.txt").read_text(), "Source check in progress\n")
                self.assertFalse((stage / "result.json").exists())
                if transport == "docker":
                    cleanup.assert_called_once_with(choice, stage)
                    self.assertEqual(metadata["cancel_cleanup"], "matched=1")
                else:
                    cleanup.assert_not_called()

    def test_docker_timeout_cleanup_targets_only_the_dispatch_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / "dispatch" / "unique-run"
            stage.mkdir(parents=True)
            choice = {"docker": {"host_mount": str(root), "container_mount": "/shared",
                                 "container": "opencode", "executable": "docker"}}
            completed = subprocess.CompletedProcess([], 0, "matched=1\n", "")
            with patch("research_dispatch.subprocess.run", return_value=completed) as run:
                self.assertEqual(stop_docker_stage(choice, stage), "matched=1")
            command = run.call_args.args[0]
            self.assertEqual(Path(command[0]).stem.lower(), 'docker')
            self.assertEqual(command[1:4], ["exec", "opencode", "sh"])
            self.assertEqual(command[-1], "/shared/dispatch/unique-run")

    def test_approved_with_limits_requires_mapped_nonmaterial_uncertainty(self):
        result = {"role": "validate", "verdict": "approved_with_limits", "summary": "Supported with a stated limit",
                  "issues": [], "checked_claim_ids": ["F1"],
                  "checks": [{"claim_id": "F1", "source_url": "https://example.org",
                              "evidence": "The source cannot establish the minor qualifier", "verdict": "partial"}],
                  "limitations": [{"claim_id": "F1", "reason": "Minor qualifier remains uncertain"}]}
        validate_result("validate", result, {"F1"})
        result["limitations"] = []
        with self.assertRaises(ValueError):
            validate_result("validate", result, {"F1"})
        result["limitations"] = [{"claim_id": "F1", "reason": "Minor qualifier remains uncertain"}]
        result["checks"][0]["verdict"] = "mismatch"
        with self.assertRaises(ValueError):
            validate_result("validate", result, {"F1"})

    def test_narrated_role_result_is_accepted_but_partial_or_duplicate_is_not(self):
        payload = {"role": "validate", "verdict": "approved"}
        encoded = json.dumps(payload)
        self.assertEqual(parse_role_object("Checked sources.\n" + encoded), payload)
        with self.assertRaises(ValueError):
            parse_role_object("Checked sources.\n" + encoded[:-2])
        with self.assertRaises(ValueError):
            parse_role_object(encoded + "\n" + encoded)

    def setup_files(self, root: Path):
        brief = b"Check documented capabilities."
        (root / "brief.md").write_bytes(brief)
        (root / "intake.json").write_text(json.dumps(intake(brief)), encoding="utf-8")
        (root / "findings.md").write_text("F1: documented claim; https://example.org", encoding="utf-8")
        (root / "config.json").write_text(json.dumps({"targets": {
            "validator": {"cli": "agy", "transport": "direct", "executable": "agy"},
            "gap_filler": {"cli": "opencode", "transport": "direct", "model": "provider/model"}}}), encoding="utf-8")

    def options(self, root: Path):
        return argparse.Namespace(config=root / "config.json", record=root / "intake.json",
                                  brief=root / "brief.md", role="validate", target="validator",
                                  input=root / "findings.md", run_dir=root, timeout=10)

    def test_fresh_external_result_and_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_files(root)
            result = {"role": "validate", "verdict": "approved", "summary": "All checked",
                      "issues": [], "checked_claim_ids": ["F1"],
                      "checks": [{"claim_id": "F1", "source_url": "https://example.org",
                                  "evidence": "Source supports claim", "verdict": "confirmed"}]}
            FakeProcess.output = json.dumps({"event": "result", "result":
                                             {"status": "SUCCESS", "response": json.dumps(result)}})
            with patch("research_dispatch.subprocess.Popen", FakeProcess):
                first = run_dispatch(self.options(root))
                second = run_dispatch(self.options(root))
            self.assertNotEqual(first.parent, second.parent)
            self.assertEqual(json.loads(first.read_text())["verdict"], "approved")
            dispatch = json.loads((first.parent / "dispatch.json").read_text())
            self.assertEqual(dispatch["process_id"], 12345)
            self.assertIn("started_at", dispatch)
            self.assertIn("finished_at", dispatch)
            self.assertGreaterEqual(dispatch["elapsed_seconds"], 0)
            self.assertEqual(dispatch["status"], "completed")
            self.assertFalse((first.parent / "search_plan.md").exists())
            self.assertIn("F1: documented claim", json.loads(FakeProcess.last_input)["message"]["content"])
            self.assertEqual(FakeProcess.last_kwargs["encoding"], "utf-8")

    def test_malformed_output_fails_without_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_files(root)
            FakeProcess.output = json.dumps({"event": "result", "result":
                                             {"status": "SUCCESS", "response": "not JSON"}})
            with patch("research_dispatch.subprocess.Popen", FakeProcess):
                with self.assertRaises(ValueError):
                    run_dispatch(self.options(root))
            stage = next((root / "dispatch").iterdir())
            self.assertEqual(json.loads((stage / "dispatch.json").read_text())["status"], "failed")

    def test_gap_fill_uses_selected_cli_and_requires_cited_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_files(root)
            (root / "gaps.md").write_text("G1: Verify claim F1", encoding="utf-8")
            options = self.options(root)
            options.role = "gap_fill"
            options.target = "gap_filler"
            options.input = root / "gaps.md"
            FakeProcess.output = json.dumps({"role": "gap_fill", "verdict": "completed",
                "summary": "Corrected F1", "changes": [{"gap_id": "G1",
                "corrected_finding": "Corrected claim", "source_urls": ["https://example.org"]}],
                "unresolved": []})
            with patch("research_dispatch.subprocess.Popen", FakeProcess):
                path = run_dispatch(options)
            self.assertEqual(json.loads(path.read_text())["changes"][0]["gap_id"], "G1")
            self.assertIn("opencode", json.loads((path.parent / "dispatch.json").read_text())["command"])

    def test_changed_transport_is_rejected_before_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_files(root)
            config = json.loads((root / "config.json").read_text())
            config["targets"]["validator"]["transport"] = "docker"
            (root / "config.json").write_text(json.dumps(config))
            with patch("research_dispatch.subprocess.Popen", side_effect=AssertionError("launched")):
                with self.assertRaises(ValueError):
                    run_dispatch(self.options(root))

    def test_preflight_reports_missing_executable(self):
        with self.assertRaises(FileNotFoundError):
            check_target({"targets": {"missing": {"cli": "agy", "transport": "direct",
                       "executable": "this-command-does-not-exist-48291"}}}, "missing")

    def test_docker_command_maps_only_shared_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / "runs" / "example"
            stage.mkdir(parents=True)
            choice = {"cli": "agy", "transport": "docker", "docker": {
                "container": "test-container", "host_mount": str(root),
                "container_mount": "/research-shared"}}
            command, cwd = command_for(choice, "Check sources", stage)
            self.assertEqual(Path(command[0]).stem.lower(), 'docker')
            self.assertEqual(command[1:8], ["exec", "-i", "--env", "RESEARCH_DISPATCH_ID=example", "--workdir",
                                           "/research-shared/runs/example", "test-container"])
            self.assertIsNone(cwd)
            with self.assertRaises(ValueError):
                command_for(choice, "Check sources", root.parent)

    def test_host_mailbox_accepts_fixed_job_and_returns_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_files(root)
            options = argparse.Namespace(shared_root=root, record=root / "intake.json",
                                         brief=root / "brief.md", input=root / "findings.md",
                                         role="validate", target="validator", timeout=10, wait=False)
            with redirect_stdout(StringIO()):
                self.assertEqual(submit(options), 0)
            request = next((root / "requests").glob("*.json"))
            job_id = request.stem
            result = {"role": "validate", "verdict": "approved", "summary": "Checked",
                      "issues": [], "checked_claim_ids": ["F1"],
                      "checks": [{"claim_id": "F1", "source_url": "https://example.org",
                                  "evidence": "Source supports claim", "verdict": "confirmed"}]}
            FakeProcess.output = json.dumps({"event": "result", "result":
                                             {"status": "SUCCESS", "response": json.dumps(result)}})
            with patch("research_dispatch.subprocess.Popen", FakeProcess):
                process_one(root, root / "config.json", request)
            response = json.loads((root / "responses" / f"{job_id}.json").read_text())
            self.assertEqual(response["status"], "completed")
            self.assertTrue((root / response["result"]).is_file())

    def test_host_mailbox_rejects_path_outside_shared_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.setup_files(root)
            requests = root / "requests"
            requests.mkdir()
            request = requests / "badjob.json"
            request.write_text(json.dumps({"id": "badjob", "role": "validate",
                "target": "validator", "record": "../outside.json", "brief": "brief.md",
                "input": "findings.md", "timeout": 10, "expires_at": time.time() + 40}), encoding="utf-8")
            with patch("research_dispatch.subprocess.Popen", side_effect=AssertionError("launched")):
                process_one(root, root / "config.json", request)
            response = json.loads((root / "responses" / "badjob.json").read_text())
            self.assertEqual(response["status"], "failed")
            self.assertIn("outside shared root", response["error"])


if __name__ == "__main__":
    unittest.main()
