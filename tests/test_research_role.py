"""Delegated research role and research_mode gating; no model or network calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import test_workflow as fixtures
from check_intake import check, intake_sha256
from research_dispatch import ledger_launches, run_dispatch


def research_result():
    return {"role": "research", "verdict": "completed", "summary": "Documented systems found",
            "findings": [{"id": "F1", "question_ids": ["Q1"],
                          "claim": "System X operated in country Y from 2020.",
                          "source_urls": ["https://example.org/system-x"],
                          "retrieved": "2026-10-31", "source_date": "2024-06-01"}],
            "unanswered": [{"question_id": "Q2", "reason": "No documented cost for drone pilots"}]}


def agy_envelope(result):
    return json.dumps({"event": "result", "result": {"status": "SUCCESS",
                                                     "response": json.dumps(result)}})


def research_options(root: Path, target="researcher"):
    helper = fixtures.DispatchTests()
    helper.setup_files(root)
    (root / "questions.md").write_text(
        "Q1: Which integrated emergency systems are documented?\n"
        "Q2: What did documented drone pilots cost?\n", encoding="utf-8")
    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    config["targets"]["researcher"] = {"cli": "agy", "transport": "direct", "executable": "agy"}
    (root / "config.json").write_text(json.dumps(config), encoding="utf-8")
    options = helper.options(root)
    options.role = "research"
    options.target = target
    options.input = root / "questions.md"
    options.ledger = root / "run_ledger.jsonl"
    return options


def enable_delegated(root: Path, model="default"):
    record = json.loads((root / "intake.json").read_text(encoding="utf-8"))
    evidence = {"message_ref": "synthetic-test-user-turn",
                "quote": "Delegate research to the researcher CLI with these limits."}
    record["decisions"]["research_mode"] = {"state": "answered", "answer": "delegated",
                                            "user_evidence": dict(evidence)}
    record["decisions"]["researcher_cli"] = {"state": "answered", "answer": "researcher",
                                             "user_evidence": dict(evidence)}
    record["decisions"]["researcher_transport"] = {"state": "answered", "answer": "direct",
                                                   "user_evidence": dict(evidence)}
    record["decisions"]["researcher_model"] = {"state": "answered", "answer": model,
                                               "user_evidence": dict(evidence)}
    record["confirmation"]["intake_sha256"] = intake_sha256(record)
    (root / "intake.json").write_text(json.dumps(record), encoding="utf-8")


class ResearchRoleTests(unittest.TestCase):
    def test_delegated_research_dispatch_and_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            options = research_options(root)
            enable_delegated(root)
            fixtures.FakeProcess.output = agy_envelope(research_result())
            with patch("research_dispatch.subprocess.Popen", fixtures.FakeProcess):
                result = run_dispatch(options)
            self.assertEqual(json.loads(result.read_text())["role"], "research")
            metadata = json.loads((result.parent / "dispatch.json").read_text())
            self.assertEqual(metadata["role_verdict"], "completed")
            self.assertTrue(metadata["requires_attention"])
            self.assertIn("Unanswered questions: Q2", metadata["user_notice"])
            self.assertIn("Findings require validation before use", metadata["user_notice"])
            self.assertEqual(ledger_launches(root / "run_ledger.jsonl", "research"), 1)

    def test_completed_research_must_cover_every_question(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            options = research_options(root)
            enable_delegated(root)
            result = research_result()
            result["unanswered"] = []
            fixtures.FakeProcess.output = agy_envelope(result)
            with patch("research_dispatch.subprocess.Popen", fixtures.FakeProcess):
                with self.assertRaises(ValueError) as raised:
                    run_dispatch(options)
            self.assertIn("missing input question IDs: ['Q2']", str(raised.exception))

    def test_duplicate_finding_ids_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            options = research_options(root)
            enable_delegated(root)
            result = research_result()
            result["findings"].append(dict(result["findings"][0], question_ids=["Q2"]))
            result["unanswered"] = []
            fixtures.FakeProcess.output = agy_envelope(result)
            with patch("research_dispatch.subprocess.Popen", fixtures.FakeProcess):
                with self.assertRaises(ValueError) as raised:
                    run_dispatch(options)
            self.assertIn("duplicate IDs", str(raised.exception))

    def test_unknown_question_id_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            options = research_options(root)
            enable_delegated(root)
            result = research_result()
            result["findings"][0]["question_ids"] = ["Q9"]
            fixtures.FakeProcess.output = agy_envelope(result)
            with patch("research_dispatch.subprocess.Popen", fixtures.FakeProcess):
                with self.assertRaises(ValueError):
                    run_dispatch(options)

    def test_blocked_research_needs_no_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            options = research_options(root)
            enable_delegated(root)
            result = research_result()
            result.update({"verdict": "blocked", "summary": "Source access denied",
                           "findings": [], "unanswered": []})
            fixtures.FakeProcess.output = agy_envelope(result)
            with patch("research_dispatch.subprocess.Popen", fixtures.FakeProcess):
                result = run_dispatch(options)
            metadata = json.loads((result.parent / "dispatch.json").read_text())
            self.assertTrue(metadata["requires_attention"])

    def test_research_role_requires_delegated_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            options = research_options(root)
            fixtures.FakeProcess.output = agy_envelope(research_result())
            with patch("research_dispatch.subprocess.Popen", fixtures.FakeProcess):
                with self.assertRaises(ValueError) as raised:
                    run_dispatch(options)
            self.assertIn("research_mode 'delegated'", str(raised.exception))

    def test_research_limit_counts_separately(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            options = research_options(root)
            enable_delegated(root)
            record = json.loads((root / "intake.json").read_text(encoding="utf-8"))
            record["decisions"]["approved_run_counts"] = {
                "state": "answered", "answer": {"research": 1},
                "user_evidence": {"message_ref": "synthetic-test-user-turn",
                                  "quote": "Approved run counts for this research effort."}}
            record["confirmation"]["intake_sha256"] = intake_sha256(record)
            (root / "intake.json").write_text(json.dumps(record), encoding="utf-8")
            fixtures.FakeProcess.output = agy_envelope(research_result())
            with patch("research_dispatch.subprocess.Popen", fixtures.FakeProcess):
                run_dispatch(options)
                with self.assertRaises(ValueError) as raised:
                    run_dispatch(options)
            self.assertIn("approved run limit reached for role research", str(raised.exception))


class ResearchModeCheckerTests(unittest.TestCase):
    def checker_errors(self, research_mode=None, include_researcher=False):
        brief = b"Research-mode checker fixture."
        record = fixtures.intake(brief)
        evidence = {"message_ref": "synthetic-test-user-turn", "quote": "Delegate research."}
        if research_mode is not None:
            record["decisions"]["research_mode"] = {"state": "answered", "answer": research_mode,
                                                    "user_evidence": dict(evidence)}
        if include_researcher:
            for key, answer in (("researcher_cli", "researcher"), ("researcher_transport", "direct"),
                                ("researcher_model", "default")):
                record["decisions"][key] = {"state": "answered", "answer": answer,
                                            "user_evidence": dict(evidence)}
        record["confirmation"]["intake_sha256"] = intake_sha256(record)
        return check(record, brief)

    def test_valid_delegated_record_passes(self):
        self.assertEqual(self.checker_errors("delegated", include_researcher=True), [])

    def test_delegated_requires_researcher_routing(self):
        self.assertTrue(any("researcher_cli" in error
                            for error in self.checker_errors("delegated")))

    def test_invalid_mode_value_rejected(self):
        self.assertTrue(any("research_mode must be coordinator or delegated" in error
                            for error in self.checker_errors("external")))

    def test_coordinator_mode_needs_no_researcher_routing(self):
        self.assertEqual(self.checker_errors("coordinator"), [])


if __name__ == "__main__":
    unittest.main()
