"""Shared-folder bridge for container-originated research delegation.

The host worker can run only the fixed validator/gap-fill jobs accepted by
research_dispatch.py. It never accepts a shell command from the container.
"""

import argparse
import json
import os
from pathlib import Path
import sys
import time
import uuid

from research_dispatch import inside, run_dispatch


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
    for source in (args.record, args.brief, args.input):
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
           "timeout": args.timeout}
    atomic_json(requests / f"{job_id}.json", job)
    print(f"Submitted {job_id}", flush=True)
    if not args.wait:
        return 0
    response_path = responses / f"{job_id}.json"
    deadline = time.monotonic() + args.timeout + 30
    while time.monotonic() < deadline:
        if response_path.exists():
            response = json.loads(response_path.read_text(encoding="utf-8"))
            print(json.dumps(response, indent=2))
            return 0 if response.get("status") == "completed" else 2
        time.sleep(1)
    raise TimeoutError(f"no host-worker response for {job_id}")


def process_one(root: Path, config: Path, request_path: Path) -> None:
    processing = request_path.with_suffix(".processing")
    os.replace(request_path, processing)
    job_id = request_path.stem
    response = {"id": job_id, "status": "failed"}
    try:
        job = json.loads(processing.read_text(encoding="utf-8"))
        if job.get("id") != job_id or job.get("role") not in {"validate", "gap_fill"}:
            raise ValueError("invalid request identity or role")
        timeout = job.get("timeout", 600)
        if not isinstance(timeout, int) or not 1 <= timeout <= 3600:
            raise ValueError("timeout must be 1–3600 seconds")
        options = argparse.Namespace(config=config, record=relative_file(root, job["record"]),
                                     brief=relative_file(root, job["brief"]),
                                     input=relative_file(root, job["input"]),
                                     role=job["role"], target=job["target"],
                                     run_dir=root / "runs", timeout=timeout)
        result_path = run_dispatch(options)
        response = {"id": job_id, "status": "completed",
                    "result": str(result_path.relative_to(root))}
    except Exception as exc:
        response["error"] = str(exc)
    finally:
        (root / "responses").mkdir(parents=True, exist_ok=True)
        atomic_json(root / "responses" / f"{job_id}.json", response)
        processing.unlink(missing_ok=True)


def worker(args: argparse.Namespace) -> int:
    root = args.shared_root.resolve()
    requests = root / "requests"
    requests.mkdir(parents=True, exist_ok=True)
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
    except (OSError, ValueError, TimeoutError) as exc:
        print(f"Mailbox error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
