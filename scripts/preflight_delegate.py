"""Check configured external CLI routing before research starts.

This checks executable, container state, and version command only. A harmless
source-reading run is still required to prove authentication and source access.
"""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

from check_intake import checked_files
from research_dispatch import confirmed_target, target_config


def version_probe(command: list[str]) -> str:
    result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True,
                            text=True, timeout=30, shell=False)
    if result.returncode:
        raise RuntimeError(f"{' '.join(command[:2])} exited {result.returncode}: {result.stderr.strip()[-500:]}")
    lines = (result.stdout or result.stderr).strip().splitlines()
    if not lines:
        raise RuntimeError("version command returned no output")
    return lines[0][:200]


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
    args = parser.parse_args()
    try:
        record, _ = checked_files(args.record, args.brief)
        if record["decisions"]["validation_mode"]["answer"] != "external_cli":
            raise ValueError("confirmed brief did not select external CLI validation")
        config = json.loads(args.config.read_text(encoding="utf-8"))
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
