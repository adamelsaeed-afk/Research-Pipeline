"""Run-state derivation from the ledger and live registry; no model or network calls."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from research_dispatch import in_flight_path, run_states


def write_ledger(ledger: Path, entries):
    ledger.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8")


class RunStatesTests(unittest.TestCase):
    def test_completed_failed_running_orphaned(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "run_ledger.jsonl"
            write_ledger(ledger, [
                {"ts": "T", "run_id": "done", "event": "launch", "role": "validate"},
                {"ts": "T", "run_id": "done", "event": "complete", "exit_code": 0,
                 "verdict": "approved", "duration_s": 1.0, "tokens_reported": None},
                {"ts": "T", "run_id": "broke", "event": "launch", "role": "validate"},
                {"ts": "T", "run_id": "broke", "event": "complete", "exit_code": 2,
                 "verdict": None, "duration_s": 0.5, "tokens_reported": None},
                {"ts": "T", "run_id": "live", "event": "launch", "role": "validate"},
                {"ts": "T", "run_id": "gone", "event": "launch", "role": "gap_fill"},
            ])
            registry = in_flight_path(ledger)
            registry.write_text(json.dumps({"runs": [
                {"run_id": "live", "role": "validate", "pid": os.getpid(),
                 "ts": "2026-10-31T00:00:00+03:00"}]}), encoding="utf-8")
            result = run_states(ledger)
            self.assertEqual(result["runs"]["done"]["state"], "completed")
            self.assertEqual(result["runs"]["done"]["verdict"], "approved")
            self.assertEqual(result["runs"]["broke"]["state"], "failed")
            self.assertIsNone(result["runs"]["broke"]["verdict"])
            self.assertEqual(result["runs"]["live"]["state"], "running")
            self.assertEqual(result["runs"]["gone"]["state"], "orphaned")
            self.assertEqual(result["states"], {"completed": 1, "failed": 1,
                                                "running": 1, "orphaned": 1})

    def test_missing_registry_makes_running_launch_orphaned(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "run_ledger.jsonl"
            write_ledger(ledger, [{"ts": "T", "run_id": "r1", "event": "launch",
                                   "role": "validate"}])
            result = run_states(ledger)
            self.assertEqual(result["runs"]["r1"]["state"], "orphaned")
            self.assertEqual(result["states"], {"orphaned": 1})

    def test_corrupt_ledger_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "run_ledger.jsonl"
            ledger.write_text("garbage line\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                run_states(ledger)


if __name__ == "__main__":
    unittest.main()
