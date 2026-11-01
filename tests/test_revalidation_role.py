"""Revalidation role contract/routing and ledger telemetry; no model or network calls."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_workflow as fixtures
from check_intake import intake_sha256
from research_dispatch import extract_tokens_reported, ledger_launches, run_dispatch


def approved_revalidation():
    return {"role": "revalidate", "verdict": "approved", "summary": "Corrections check out",
            "issues": [], "checked_claim_ids": ["F1"],
            "checks": [{"claim_id": "F1", "source_url": "https://example.org",
                        "evidence": "Correction is supported", "verdict": "confirmed"}]}


def agy_envelope(result):
    return json.dumps({"event": "result", "result": {"status": "SUCCESS",
                                                     "response": json.dumps(result)}})


def options_for(root: Path, role="revalidate", target="validator"):
    helper = fixtures.DispatchTests()
    helper.setup_files(root)
    options = helper.options(root)
    options.role = role
    options.target = target
    options.ledger = root / "run_ledger.jsonl"
    return options


def set_decision(root: Path, key: str, answer):
    record = json.loads((root / "intake.json").read_text(encoding="utf-8"))
    record["decisions"][key] = {
        "state": "answered", "answer": answer,
        "user_evidence": {"message_ref": "synthetic-test-user-turn",
                          "quote": "Routing choice for this research effort."}}
    record["confirmation"]["intake_sha256"] = intake_sha256(record)
    (root / "intake.json").write_text(json.dumps(record), encoding="utf-8")


class RevalidationRoleTests(unittest.TestCase):
    def test_revalidation_defaults_to_validator_routing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            options = options_for(root)
            fixtures.FakeProcess.output = agy_envelope(approved_revalidation())
            with patch("research_dispatch.subprocess.Popen", fixtures.FakeProcess):
                result = run_dispatch(options)
            self.assertEqual(json.loads(result.read_text())["role"], "revalidate")
            metadata = json.loads((result.parent / "dispatch.json").read_text())
            self.assertEqual(metadata["role_verdict"], "approved")
            ledger = root / "run_ledger.jsonl"
            self.assertEqual(ledger_launches(ledger, "revalidate"), 1)
            self.assertEqual(ledger_launches(ledger, "validate"), 0)

    def test_result_role_must_match_revalidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            options = options_for(root)
            wrong = approved_revalidation()
            wrong["role"] = "validate"
            fixtures.FakeProcess.output = agy_envelope(wrong)
            with patch("research_dispatch.subprocess.Popen", fixtures.FakeProcess):
                with self.assertRaises(ValueError):
                    run_dispatch(options)

    def test_revalidation_gaps_found_requires_attention(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            options = options_for(root)
            result = approved_revalidation()
            result["verdict"] = "gaps_found"
            result["issues"] = [{"id": "G1", "claim_id": "F1", "problem": "Correction unsupported",
                                 "evidence_urls": [], "severity": "material"}]
            result["checks"][0]["verdict"] = "partial"
            result["checks"][0]["evidence"] = "Source reached but does not support the correction"
            fixtures.FakeProcess.output = agy_envelope(result)
            with patch("research_dispatch.subprocess.Popen", fixtures.FakeProcess):
                saved = run_dispatch(options)
            metadata = json.loads((saved.parent / "dispatch.json").read_text())
            self.assertTrue(metadata["requires_attention"])

    def test_revalidator_cli_override_uses_that_clis_routing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            options = options_for(root, target="gap_filler")
            set_decision(root, "revalidator_cli", "gap_filler")
            fixtures.FakeProcess.output = json.dumps(approved_revalidation())
            with patch("research_dispatch.subprocess.Popen", fixtures.FakeProcess):
                result = run_dispatch(options)
            self.assertEqual(json.loads(result.read_text())["role"], "revalidate")

    def test_revalidator_override_mismatch_refuses(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            options = options_for(root, target="validator")
            set_decision(root, "revalidator_cli", "gap_filler")
            fixtures.FakeProcess.output = agy_envelope(approved_revalidation())
            with patch("research_dispatch.subprocess.Popen", fixtures.FakeProcess):
                with self.assertRaises(ValueError) as raised:
                    run_dispatch(options)
            self.assertIn("confirmed revalidator_cli", str(raised.exception))

    def test_revalidate_limit_counts_separately(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            options = options_for(root)
            set_decision(root, "approved_run_counts", {"revalidate": 1})
            fixtures.FakeProcess.output = agy_envelope(approved_revalidation())
            with patch("research_dispatch.subprocess.Popen", fixtures.FakeProcess):
                run_dispatch(options)
                with self.assertRaises(ValueError) as raised:
                    run_dispatch(options)
            self.assertIn("approved run limit reached for role revalidate", str(raised.exception))


class TokenTelemetryTests(unittest.TestCase):
    def test_codex_counter_extracts_last_occurrence(self):
        stdout = "tokens used 100\nworking\ntokens used 2,345\ndone"
        self.assertEqual(extract_tokens_reported("codex", stdout), 2345)

    def test_unknown_patterns_and_absence_stay_null(self):
        self.assertIsNone(extract_tokens_reported("agy", "tokens used 555"))
        self.assertIsNone(extract_tokens_reported("opencode", "tokens used 555"))
        self.assertIsNone(extract_tokens_reported("codex", "no counter here"))
        self.assertIsNone(extract_tokens_reported("codex", ""))

    def test_codex_dispatch_records_printed_counter_in_ledger(self):
        class CodexProcess(fixtures.FakeProcess):
            def communicate(self, input=None, timeout=None):
                Path(self.streams["cwd"], "last_message.txt").write_text(
                    json.dumps(approved_revalidation()), encoding="utf-8")
                self.streams["stdout"].write("tokens used 1,234\n")
                self.streams["stdout"].flush()
                return None, None

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            options = options_for(root)
            # A native executable with no launcher suffix; the process is
            # faked, so only native_program's validation sees this path.
            (root / "config.json").write_text(json.dumps({"targets": {
                "validator": {"cli": "codex", "transport": "direct",
                              "executable": sys.executable}}}), encoding="utf-8")
            with patch("research_dispatch.subprocess.Popen", CodexProcess):
                result = run_dispatch(options)
            self.assertEqual(json.loads(result.read_text())["role"], "revalidate")
            complete = json.loads((root / "run_ledger.jsonl").read_text(encoding="utf-8").splitlines()[1])
            self.assertEqual(complete["tokens_reported"], 1234)
            self.assertEqual(complete["verdict"], "approved")


if __name__ == "__main__":
    unittest.main()
