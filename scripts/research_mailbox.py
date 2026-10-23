"""Shared-folder bridge for container-originated research delegation.

The host worker can run only the fixed validator/gap-fill jobs accepted by
research_dispatch.py. It never accepts a shell command from the container.
"""

import argparse
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import sys
import time
import uuid

from research_dispatch import inside, run_dispatch, result_feedback
from strict_json import read as read_json


def relative_file(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    if not inside(path, root) or not path.is_file():
        raise ValueError(f"file is outside shared root or missing: {value}")
    return path


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def submit(args: argparse.Namespace) -> int:
    root = args.shared_root.resolve()
    if type(args.timeout) is not int or not 1 <= args.timeout <= 3600:
        raise ValueError("timeout must be 1–3600 seconds")
    input_ids = getattr(args, "input_ids", None)
    for source in (args.record, args.brief, args.input, *([input_ids] if input_ids is not None else [])):
        if not inside(source, root) or not source.is_file():
            raise ValueError(f"input must be an existing file under {root}: {source}")
    job_id = uuid.uuid4().hex
    requests = root / "requests"
    responses = root / "responses"
    requests.mkdir(parents=True, exist_ok=True)
    responses.mkdir(parents=True, exist_ok=True)
    job = {"id": job_id, "role": args.role, "target": args.target,
           "record": str(args.record.resolve().relative_to(root)),
           "brief": str(args.brief.resolve().relative_to(root)),
           "input": str(args.input.resolve().relative_to(root)),
           "timeout": args.timeout, "expires_at": time.time() + args.timeout + 30}
    if input_ids is not None:
        job["input_ids"] = str(input_ids.resolve().relative_to(root))
    atomic_json(requests / f"{job_id}.json", job)
    print(f"Submitted {job_id}", flush=True)
    if not args.wait:
        return 0
    response_path = responses / f"{job_id}.json"
    deadline = time.monotonic() + args.timeout + 30
    while time.monotonic() < deadline:
        if response_path.exists():
            response = read_json(response_path)
            if not isinstance(response, dict) or response.get('id') != job_id:
                raise ValueError('mailbox response identity does not match the submitted job')
            print(json.dumps(response, indent=2))
            if response.get('status') != 'completed':
                return 2
            return 3 if response.get('requires_attention') else 0
        time.sleep(1)
    raise TimeoutError(f"no host-worker response for {job_id}")


def process_one(root: Path, config: Path, request_path: Path) -> None:
    processing = request_path.with_suffix(".processing")
    os.replace(request_path, processing)
    job_id = request_path.stem
    response = {"id": job_id, "status": "failed"}
    try:
        job = read_json(processing)
        if not isinstance(job, dict):
            raise ValueError('mailbox request must be an object')
        if job.get("id") != job_id or job.get("role") not in {"validate", "gap_fill"}:
            raise ValueError("invalid request identity or role")
        timeout = job.get("timeout", 600)
        if type(timeout) is not int or not 1 <= timeout <= 3600:
            raise ValueError("timeout must be 1–3600 seconds")
        expiry = job.get("expires_at")
        if type(expiry) not in (int, float) or not math.isfinite(expiry):
            raise ValueError("request needs a finite expires_at deadline; resubmit with the updated client")
        if time.time() >= expiry:
            response.update(status="expired", error="request expired in the queue; no CLI launched")
            return
        options = argparse.Namespace(config=config, record=relative_file(root, job["record"]),
                                     brief=relative_file(root, job["brief"]),
                                     input=relative_file(root, job["input"]),
                                     input_ids=relative_file(root, job["input_ids"]) if "input_ids" in job else None,
                                     role=job["role"], target=job["target"],
                                     run_dir=root / "runs", timeout=timeout, queue_deadline=expiry)
        result_path = run_dispatch(options)
        response = {"id": job_id, "status": "completed",
                    "result": str(result_path.relative_to(root))}
        response.update(result_feedback(result_path))
    except KeyboardInterrupt:
        response.update(status="interrupted", error="worker interrupted; request was not replayed")
        raise
    except Exception as exc:
        response["error"] = str(exc)
    finally:
        (root / "responses").mkdir(parents=True, exist_ok=True)
        atomic_json(root / "responses" / f"{job_id}.json", response)
        processing.unlink(missing_ok=True)


@contextmanager
def worker_lock(root: Path):
    """Only one worker may claim/recover requests in this shared root."""
    with (root / "worker.lock").open("a+b") as lock:
        # Reading byte zero can itself fail while a Windows worker owns it.
        if lock.seek(0, os.SEEK_END) == 0:
            lock.write(b'0')
            lock.flush()
        lock.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("another mailbox worker already owns this shared root") from exc
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == 'nt':
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock, fcntl.LOCK_UN)


def recover_interrupted(root: Path) -> None:
    """Surface abandoned claims without automatically repeating external work."""
    for processing in sorted((root / "requests").glob("*.processing")):
        response = root / "responses" / f"{processing.stem}.json"
        if not response.exists():
            atomic_json(response, {"id": processing.stem, "status": "interrupted",
                                  "error": "previous worker stopped before returning a result; inspect logs and resubmit explicitly"})
        os.replace(processing, processing.with_suffix(".interrupted"))


def worker(args: argparse.Namespace) -> int:
    root = args.shared_root.resolve()
    requests = root / "requests"
    requests.mkdir(parents=True, exist_ok=True)
    (root / "responses").mkdir(parents=True, exist_ok=True)
    with worker_lock(root):
        recover_interrupted(root)
        while True:
            for request in sorted(requests.glob("*.json")):
                process_one(root, args.config, request)
            if args.once:
                return 0
            time.sleep(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    request = subs.add_parser("submit")
    request.add_argument("--shared-root", type=Path, required=True)
    request.add_argument("--record", type=Path, required=True)
    request.add_argument("--brief", type=Path, required=True)
    request.add_argument("--input", type=Path, required=True)
    request.add_argument("--input-ids", type=Path)
    request.add_argument("--role", choices=["validate", "gap_fill"], required=True)
    request.add_argument("--target", required=True)
    request.add_argument("--timeout", type=int, default=600)
    request.add_argument("--wait", action="store_true")
    host = subs.add_parser("worker")
    host.add_argument("--shared-root", type=Path, required=True)
    host.add_argument("--config", type=Path, required=True)
    host.add_argument("--once", action="store_true")
    args = parser.parse_args()
    try:
        return submit(args) if args.command == "submit" else worker(args)
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        print(f"Mailbox error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
