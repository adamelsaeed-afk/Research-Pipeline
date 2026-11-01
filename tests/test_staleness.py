"""Staleness detection: dated run records outrank older status fields."""
import json
import os
from pathlib import Path
import tempfile
import time
import unittest

import test_workflow as fixtures
from preflight_delegate import staleness_warnings


def write_ledger(ledger: Path, entries):
    ledger.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8")


def aged_record(root: Path, seconds_ago=3600):
    """A valid intake record whose file was last written in the past."""
    helper = fixtures.DispatchTests()
    helper.setup_files(root)
    record_path = root / "intake.json"
    past = time.time() - seconds_ago
    os.utime(record_path, (past, past))
    return record_path


class StalenessWarningTests(unittest.TestCase):
    def test_no_ledger_means_no_warnings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record_path = aged_record(root)
            record = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(staleness_warnings(record_path, record, root / "run_ledger.jsonl"), [])

    def test_older_run_records_do_not_warn(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record_path = aged_record(root)
            record = json.loads(record_path.read_text(encoding="utf-8"))
            ledger = root / "run_ledger.jsonl"
            write_ledger(ledger, [
                {"ts": "2020-01-01T00:00:00+00:00", "run_id": "old", "event": "launch",
                 "role": "validate", "target": "validator"}])
            self.assertEqual(staleness_warnings(record_path, record, ledger), [])

    def test_newer_run_record_warns_with_precedence_rule(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record_path = aged_record(root)
            record = json.loads(record_path.read_text(encoding="utf-8"))
            ledger = root / "run_ledger.jsonl"
            write_ledger(ledger, [
                {"ts": "2099-01-01T00:00:00+00:00", "run_id": "fresh", "event": "launch",
                 "role": "validate", "target": "validator"}])
            warnings = staleness_warnings(record_path, record, ledger)
            self.assertEqual(len(warnings), 1)
            self.assertIn("run record fresh", warnings[0])
            self.assertIn("later dated run records outrank them", warnings[0])

    def test_newer_contradicting_target_warns_by_name(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record_path = aged_record(root)
            record = json.loads(record_path.read_text(encoding="utf-8"))
            ledger = root / "run_ledger.jsonl"
            write_ledger(ledger, [
                {"ts": "2099-01-01T00:00:00+00:00", "run_id": "moved", "event": "launch",
                 "role": "validate", "target": "other_validator"}])
            warnings = staleness_warnings(record_path, record, ledger)
            self.assertTrue(any("dispatched role validate to target 'other_validator'"
                                in warning and "confirms 'validator'" in warning
                                for warning in warnings), warnings)

    def test_older_contradicting_target_does_not_warn(self):
        """The record was legitimately reconfirmed after those runs: the
        record's mtime outranks them."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record_path = aged_record(root)
            record = json.loads(record_path.read_text(encoding="utf-8"))
            ledger = root / "run_ledger.jsonl"
            write_ledger(ledger, [
                {"ts": "2020-01-01T00:00:00+00:00", "run_id": "historic", "event": "launch",
                 "role": "validate", "target": "other_validator"}])
            self.assertEqual(staleness_warnings(record_path, record, ledger), [])

    def test_corrupt_ledger_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record_path = aged_record(root)
            record = json.loads(record_path.read_text(encoding="utf-8"))
            ledger = root / "run_ledger.jsonl"
            ledger.write_text("garbage\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                staleness_warnings(record_path, record, ledger)


if __name__ == "__main__":
    unittest.main()
