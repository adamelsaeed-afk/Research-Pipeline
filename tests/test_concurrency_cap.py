"""Parallel-launch cap: atomic reservation, parallel within cap, refusal beyond."""
import json
from contextlib import contextmanager
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import unittest
from unittest.mock import patch

import test_workflow as fixtures
from check_intake import intake_sha256
from research_dispatch import (enforce_concurrency_cap, in_flight_path, load_in_flight,
                               release_in_flight, run_dispatch)


def approved_validate():
    return {"role": "validate", "verdict": "approved", "summary": "All checked",
            "issues": [], "checked_claim_ids": ["F1"],
            "checks": [{"claim_id": "F1", "source_url": "https://example.org",
                        "evidence": "Source supports claim", "verdict": "confirmed"}]}


def agy_envelope(result):
    return json.dumps({"event": "result", "result": {"status": "SUCCESS",
                                                     "response": json.dumps(result)}})


def set_decision(root: Path, key: str, answer):
    record = json.loads((root / "intake.json").read_text(encoding="utf-8"))
    record["decisions"][key] = {
        "state": "answered", "answer": answer,
        "user_evidence": {"message_ref": "synthetic-test-user-turn",
                          "quote": "Parallel-launch choice for this research effort."}}
    record["confirmation"]["intake_sha256"] = intake_sha256(record)
    (root / "intake.json").write_text(json.dumps(record), encoding="utf-8")


def prepared_options(root: Path, cap=None):
    helper = fixtures.DispatchTests()
    helper.setup_files(root)
    options = helper.options(root)
    options.ledger = root / "run_ledger.jsonl"
    if cap is not None:
        set_decision(root, "approved_concurrency", cap)
    return options


def wait_for(condition, timeout=10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.02)
    return condition()


class ConcurrencyRegistryTests(unittest.TestCase):
    def record(self):
        return {"decisions": {}}

    def test_default_cap_is_serial(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "run_ledger.jsonl"
            enforce_concurrency_cap(self.record(), "validate", ledger, "run-a")
            with self.assertRaises(ValueError) as raised:
                enforce_concurrency_cap(self.record(), "validate", ledger, "run-b")
            self.assertIn("concurrency cap reached for role validate", str(raised.exception))
            release_in_flight(ledger, "run-a")
            enforce_concurrency_cap(self.record(), "validate", ledger, "run-c")
            self.assertEqual(len(load_in_flight(in_flight_path(ledger))), 1)

    def test_cap_from_decision_allows_parallel(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "run_ledger.jsonl"
            record = {"decisions": {"approved_concurrency": {
                "state": "answered", "answer": {"validate": 2},
                "user_evidence": {"message_ref": "t", "quote": "Two in parallel."}}}}
            enforce_concurrency_cap(record, "validate", ledger, "run-a")
            enforce_concurrency_cap(record, "validate", ledger, "run-b")
            with self.assertRaises(ValueError):
                enforce_concurrency_cap(record, "validate", ledger, "run-c")
            self.assertEqual(len(load_in_flight(in_flight_path(ledger))), 2)

    def test_stale_dead_pid_entry_is_reclaimed(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "run_ledger.jsonl"
            registry = in_flight_path(ledger)
            gone = subprocess.Popen([sys.executable, "-c", "pass"])
            gone.wait()
            save_registry = {"runs": [{"run_id": "dead", "role": "validate",
                                       "pid": gone.pid, "ts": "2026-10-31T00:00:00+03:00"}]}
            registry.write_text(json.dumps(save_registry), encoding="utf-8")
            enforce_concurrency_cap(self.record(), "validate", ledger, "live")
            runs = load_in_flight(registry)
            self.assertEqual([entry["run_id"] for entry in runs], ["live"])

    def test_release_removes_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "run_ledger.jsonl"
            enforce_concurrency_cap(self.record(), "validate", ledger, "run-a")
            release_in_flight(ledger, "run-a")
            self.assertEqual(load_in_flight(in_flight_path(ledger)), [])

    def test_corrupt_registry_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "run_ledger.jsonl"
            in_flight_path(ledger).write_text("not a registry", encoding="utf-8")
            with self.assertRaises(ValueError):
                enforce_concurrency_cap(self.record(), "validate", ledger, "run-a")

    def test_zero_cap_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "run_ledger.jsonl"
            record = {"decisions": {"approved_concurrency": {
                "state": "answered", "answer": {"validate": 0},
                "user_evidence": {"message_ref": "t", "quote": "Zero."}}}}
            with self.assertRaises(ValueError):
                enforce_concurrency_cap(record, "validate", ledger, "run-a")


@contextmanager
def parallel_dispatches(cap, workers=2):
    """Start `workers` simultaneous dispatches held inside communicate() so
    their reservations genuinely overlap. Joins happen INSIDE the patch
    block: a reservation precedes its launch, so joining outside could let a
    late launch hit the real Popen. Cleanup always unblocks the workers."""
    results = {}
    errors = {}
    held = threading.Event()

    class HeldProcess:
        output = agy_envelope(approved_validate())
        pid = 12345
        returncode = 0

        def __init__(self, *args, **kwargs):
            self.streams = kwargs

        def communicate(self, input=None, timeout=None):
            if not held.wait(timeout=30):
                raise AssertionError("hold event not set in time")
            self.streams["stdout"].write(HeldProcess.output)
            self.streams["stdout"].flush()
            return None, None

    def worker(index, options):
        try:
            results[index] = run_dispatch(options)
        except Exception as exc:  # tests assert on the type
            results[index] = exc
            errors[index] = traceback.format_exc()

    temp = tempfile.TemporaryDirectory()
    try:
        root = Path(temp.name)
        options = prepared_options(root, cap=cap)
        threads = [threading.Thread(target=worker, args=(index, options))
                   for index in range(workers)]
        with patch("research_dispatch.subprocess.Popen", HeldProcess):
            for thread in threads:
                thread.start()
            yield root, results, errors, held, threads
            held.set()
            for thread in threads:
                thread.join(timeout=30)
    finally:
        held.set()
        for thread in threads:
            thread.join(timeout=30)
        temp.cleanup()


class ParallelDispatchTests(unittest.TestCase):
    def test_parallel_within_cap_runs_together(self):
        with parallel_dispatches(cap={"validate": 2}) as (root, results, errors, held, threads):
            ledger = root / "run_ledger.jsonl"
            self.assertTrue(wait_for(
                lambda: len(load_in_flight(in_flight_path(ledger))) == 2))
            held.set()
            for thread in threads:
                thread.join(timeout=30)
            self.assertEqual(len(results), 2)
            for result in results.values():
                self.assertIsInstance(result, Path, errors)
            self.assertEqual(load_in_flight(in_flight_path(ledger)), [])
            self.assertEqual(len(ledger.read_text(encoding="utf-8").splitlines()), 4)

    def test_cap_refuses_second_parallel_launch(self):
        with parallel_dispatches(cap={"validate": 1}) as (root, results, errors, held, threads):
            ledger = root / "run_ledger.jsonl"
            # The winner blocks inside communicate until the hold releases,
            # so exactly one result (the loser's refusal) exists before it.
            self.assertTrue(wait_for(lambda: len(results) >= 1))
            held.set()
            for thread in threads:
                thread.join(timeout=30)
            self.assertEqual(len(results), 2)
            refusal = next(result for result in results.values() if isinstance(result, ValueError))
            self.assertIn("concurrency cap reached", str(refusal))
            winner = next(result for result in results.values() if isinstance(result, Path))
            self.assertEqual(len(ledger.read_text(encoding="utf-8").splitlines()), 2)
            self.assertEqual(load_in_flight(in_flight_path(ledger)), [])


if __name__ == "__main__":
    unittest.main()
