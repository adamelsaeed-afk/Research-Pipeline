"""Run ledger and approved-run-count checks; no model or network calls."""
import argparse
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import test_workflow as fixtures
from check_intake import check, intake_sha256
from research_dispatch import ledger_launches, run_dispatch


def success_output():
    result = {"role": "validate", "verdict": "approved", "summary": "All checked",
              "issues": [], "checked_claim_ids": ["F1"],
              "checks": [{"claim_id": "F1", "source_url": "https://example.org",
                          "evidence": "Source supports claim", "verdict": "confirmed"}]}
    return json.dumps({"event": "result", "result":
                       {"status": "SUCCESS", "response": json.dumps(result)}})


def prepared_options(root: Path, ledger=None):
    helper = fixtures.DispatchTests()
    helper.setup_files(root)
    options = helper.options(root)
    options.ledger = ledger if ledger is not None else root / "run_ledger.jsonl"
    return options


def set_limit(root: Path, limits: dict):
    """Record the decision in the canonical object form and rebind the
    confirmation digest to the changed decisions."""
    record = json.loads((root / "intake.json").read_text(encoding="utf-8"))
    record["decisions"]["approved_run_counts"] = {
        "state": "answered",
        "answer": limits,
        "user_evidence": {"message_ref": "synthetic-test-user-turn",
                          "quote": "Approved run counts for this research effort."}}
    record["confirmation"]["intake_sha256"] = intake_sha256(record)
    (root / "intake.json").write_text(json.dumps(record), encoding="utf-8")


class RunLedgerTests(unittest.TestCase):
    def test_success_appends_launch_and_complete_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            options = prepared_options(root)
            fixtures.FakeProcess.output = success_output()
            with patch("research_dispatch.subprocess.Popen", fixtures.FakeProcess):
                first = run_dispatch(options)
                second = run_dispatch(options)
            ledger = root / "run_ledger.jsonl"
            entries = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual([entry["event"] for entry in entries],
                             ["launch", "complete", "launch", "complete"])
            launch, complete = entries[0], entries[1]
            self.assertEqual(launch["run_id"], first.parent.name)
            self.assertEqual(launch["role"], "validate")
            self.assertEqual(launch["cli"], "agy")
            self.assertIsNone(launch["model"])
            self.assertGreater(launch["staged_input_bytes"], 0)
            self.assertEqual(launch["brief_bytes"], len((root / "brief.md").read_bytes()))
            self.assertEqual(launch["timeout_s"], 10)
            self.assertEqual(complete["run_id"], first.parent.name)
            self.assertEqual(complete["exit_code"], 0)
            self.assertEqual(complete["verdict"], "approved")
            self.assertGreaterEqual(complete["duration_s"], 0)
            self.assertIsNone(complete["tokens_reported"])
            self.assertEqual(entries[2]["run_id"], second.parent.name)
            self.assertEqual(ledger_launches(ledger, "validate"), 2)
            self.assertEqual(ledger_launches(ledger, "gap_fill"), 0)

    def test_default_ledger_lives_in_run_directory_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            options = prepared_options(root, ledger=root / "runs" / "ignored")
            del options.ledger
            options.run_dir = root / "run1"
            fixtures.FakeProcess.output = success_output()
            with patch("research_dispatch.subprocess.Popen", fixtures.FakeProcess):
                run_dispatch(options)
            self.assertTrue((root / "run_ledger.jsonl").exists())
            self.assertFalse((root / "run1" / "run_ledger.jsonl").exists())

    def test_limit_refuses_before_stage_and_counts_launches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            options = prepared_options(root)
            set_limit(root, {"validate": 1})
            fixtures.FakeProcess.output = success_output()
            with patch("research_dispatch.subprocess.Popen", fixtures.FakeProcess):
                run_dispatch(options)
                with self.assertRaises(ValueError) as raised:
                    run_dispatch(options)
            self.assertIn("approved run limit reached for role validate", str(raised.exception))
            self.assertIn("recorded user evidence", str(raised.exception))
            self.assertEqual(len(list((root / "dispatch").iterdir())), 1)
            ledger = root / "run_ledger.jsonl"
            self.assertEqual(ledger_launches(ledger, "validate"), 1)

    def test_failed_runs_count_toward_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            options = prepared_options(root)
            set_limit(root, {"validate": 1})
            fixtures.FakeProcess.output = json.dumps(
                {"event": "result", "result": {"status": "SUCCESS", "response": "not JSON"}})
            with patch("research_dispatch.subprocess.Popen", fixtures.FakeProcess):
                with self.assertRaises(ValueError):
                    run_dispatch(options)
            ledger = root / "run_ledger.jsonl"
            complete = json.loads(ledger.read_text(encoding="utf-8").splitlines()[1])
            self.assertIsNone(complete["verdict"])
            with patch("research_dispatch.subprocess.Popen", fixtures.FakeProcess):
                with self.assertRaises(ValueError) as raised:
                    run_dispatch(options)
            self.assertIn("approved run limit reached", str(raised.exception))

    def test_unset_limit_enforces_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            options = prepared_options(root)
            fixtures.FakeProcess.output = success_output()
            with patch("research_dispatch.subprocess.Popen", fixtures.FakeProcess):
                for _ in range(3):
                    run_dispatch(options)
            self.assertEqual(ledger_launches(root / "run_ledger.jsonl", "validate"), 3)

    def test_corrupt_ledger_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            options = prepared_options(root)
            (root / "run_ledger.jsonl").write_text("not a ledger line\n", encoding="utf-8")
            fixtures.FakeProcess.output = success_output()
            with patch("research_dispatch.subprocess.Popen", fixtures.FakeProcess):
                with self.assertRaises(ValueError) as raised:
                    run_dispatch(options)
            self.assertIn("corrupt at line 1", str(raised.exception))
            self.assertFalse((root / "dispatch").exists())

    def test_unreadable_ledger_refuses_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            options = prepared_options(root, ledger=root / "ledgerdir")
            (root / "ledgerdir").mkdir()
            fixtures.FakeProcess.output = success_output()
            with patch("research_dispatch.subprocess.Popen", fixtures.FakeProcess):
                with self.assertRaises(OSError):
                    run_dispatch(options)

    def test_unwritable_ledger_location_refuses_dispatch(self):
        """The in-flight registry lives beside the ledger, so an unwritable
        ledger location is a fail-closed refusal, not a tolerated write gap."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "blocked").write_text("a file, not a directory", encoding="utf-8")
            options = prepared_options(root, ledger=root / "blocked" / "run_ledger.jsonl")
            fixtures.FakeProcess.output = success_output()
            with patch("research_dispatch.subprocess.Popen", fixtures.FakeProcess):
                with self.assertRaises(OSError):
                    run_dispatch(options)
            self.assertFalse((root / "dispatch").exists())


class RunCountCheckerTests(unittest.TestCase):
    """The one decision whose answer is a table gets structural validation;
    the generic string rule is unchanged for every other decision."""

    def checker_errors(self, decision, answer):
        brief = b"Run limit checker fixture."
        record = fixtures.intake(brief)
        record["decisions"][decision] = {
            "state": "answered", "answer": answer,
            "user_evidence": {"message_ref": "synthetic-test-user-turn",
                              "quote": "Approved run counts for this research effort."}}
        record["confirmation"]["intake_sha256"] = intake_sha256(record)
        return [error for error in check(record, brief) if decision in error]

    def test_object_answer_passes(self):
        self.assertEqual(self.checker_errors("approved_run_counts", {"validate": 2, "gap_fill": 3}), [])

    def test_unknown_role_name_rejected(self):
        self.assertTrue(self.checker_errors("approved_run_counts", {"revalidat": 2}))

    def test_negative_count_rejected(self):
        self.assertTrue(self.checker_errors("approved_run_counts", {"validate": -1}))

    def test_boolean_count_rejected(self):
        self.assertTrue(self.checker_errors("approved_run_counts", {"validate": True}))

    def test_empty_table_rejected(self):
        self.assertTrue(self.checker_errors("approved_run_counts", {}))

    def test_string_answer_rejected(self):
        self.assertTrue(self.checker_errors("approved_run_counts", json.dumps({"validate": 2})))

    def test_generic_string_rule_unchanged(self):
        brief = b"Run limit checker fixture."
        record = fixtures.intake(brief)
        record["decisions"]["geography"]["answer"] = {"scope": "worldwide"}
        record["confirmation"]["intake_sha256"] = intake_sha256(record)
        self.assertTrue(any("geography" in error and "nonempty string" in error
                            for error in check(record, brief)))


if __name__ == "__main__":
    unittest.main()
