"""Check configured external CLI routing before research starts.

This checks executable, container state, and version command only. A harmless
source-reading run is still required to prove authentication and source access.
"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys

from check_intake import checked_files
from research_dispatch import (confirmed_target, ledger_entries, routing_prefix,
                               target_config, child_environment, native_program)
from strict_json import read as read_json


def version_probe(command: list[str]) -> str:
    command = [native_program(command[0]), *command[1:]]
    result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True,
                            text=True, encoding='utf-8', errors='replace', timeout=30, shell=False,
                            env=child_environment({}))
    if result.returncode:
        raise RuntimeError(f"{' '.join(command[:2])} exited {result.returncode}: {result.stderr.strip()[-500:]}")
    lines = (result.stdout or result.stderr).strip().splitlines()
    if not lines:
        raise RuntimeError("version command returned no output")
    return lines[0][:200]


def record_mtime(record_path: Path) -> datetime | None:
    try:
        return datetime.fromtimestamp(record_path.stat().st_mtime).astimezone()
    except OSError:
        return None


def entry_time(entry: dict) -> datetime | None:
    value = entry.get("ts")
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def staleness_warnings(record_path: Path, record: dict, ledger: Path) -> list[str]:
    """Encode the precedence rule: later dated run records outrank status
    fields. Warn when the intake record's last write predates dated run
    activity, and when runs newer than the record contradict its confirmed
    routing. Warnings name the newer record; they never silently trust."""
    warnings: list[str] = []
    written = record_mtime(record_path)
    entries = [entry for entry in ledger_entries(ledger) if isinstance(entry, dict)]
    if written is not None:
        newer = [(entry, entry_time(entry)) for entry in entries]
        newer = [(entry, when) for entry, when in newer if when is not None and when > written]
        if newer:
            newest, when = max(newer, key=lambda pair: pair[1])
            warnings.append(
                f"the intake record was last written {written.isoformat(timespec='seconds')} and "
                f"predates run record {newest.get('run_id')} dated {when.isoformat(timespec='seconds')}; "
                "operational notes in the record may be stale — later dated run records outrank them")
            if ledger.exists():
                decisions = record.get("decisions", {})
                for entry, _ in newer:
                    role, target = entry.get("role"), entry.get("target")
                    if role not in ("validate", "gap_fill", "revalidate", "research"):
                        continue
                    prefix = routing_prefix(record, role, "cli")
                    confirmed = decisions.get(f"{prefix}_cli", {}).get("answer")
                    if confirmed is not None and target != confirmed:
                        warnings.append(
                            f"run record {entry.get('run_id')} dated "
                            f"{entry_time(entry).isoformat(timespec='seconds')} dispatched role "
                            f"{role} to target {target!r} while the record confirms {confirmed!r}; "
                            "reconfirm the affected routing decisions")
    return warnings


def check_target(config: dict, name: str) -> str:
    choice = target_config(config, name)
    executable = choice.get("executable", choice["cli"])
    if choice.get("transport", "direct") == "direct":
        if not shutil.which(executable):
            raise FileNotFoundError(f"{name}: executable not found: {executable}")
        return version_probe([executable, "--version"])
    docker = choice.get("docker", {})
    docker_bin = docker.get("executable", "docker")
    container = docker.get("container")
    if not container or not docker.get("host_mount") or not docker.get("container_mount"):
        raise ValueError(f"{name}: container, host_mount, and container_mount are required")
    if not Path(docker["host_mount"]).is_dir():
        raise FileNotFoundError(f"{name}: shared host_mount does not exist")
    if not shutil.which(docker_bin):
        raise FileNotFoundError(f"{name}: Docker executable not found: {docker_bin}")
    running = version_probe([docker_bin, "container", "inspect", "--format",
                             "{{.State.Running}}", container])
    if running.lower() != "true":
        raise RuntimeError(f"{name}: container is not running; use its configured startup command")
    return version_probe([docker_bin, "exec", container, executable, "--version"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--brief", type=Path, required=True)
    parser.add_argument("--ledger", type=Path,
                        help="run ledger for staleness checks; default is run_ledger.jsonl "
                             "beside the intake record")
    args = parser.parse_args()
    try:
        record, _ = checked_files(args.record, args.brief)
        if record["decisions"]["validation_mode"]["answer"] != "external_cli":
            raise ValueError("confirmed brief did not select external CLI validation")
        ledger = args.ledger if args.ledger is not None else args.record.parent / "run_ledger.jsonl"
        for warning in staleness_warnings(args.record, record, ledger):
            print(f"Staleness warning: {warning}", file=sys.stderr)
        config = read_json(args.config)
        names = {record["decisions"][key]["answer"]
                 for key in ("validator_cli", "gap_filler_cli")}
        for role, key in (("validate", "validator_cli"), ("gap_fill", "gap_filler_cli")):
            name = record["decisions"][key]["answer"]
            confirmed_target(record, role, name, target_config(config, name))
        for name in sorted(names):
            print(f"{name}: {check_target(config, name)}")
        print("Routing passed. Test authentication, source access, and result output with a harmless headless run.")
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"Preflight failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
