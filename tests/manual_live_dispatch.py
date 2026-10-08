"""Opt-in live source-check probe for one configured external CLI target.

This creates synthetic intake and a harmless claim. It never substitutes for a
real user's confirmation of a real research brief.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_intake import BASE_DECISIONS
from research_dispatch import run_dispatch, target_config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--role", choices=["validate", "gap_fill"], default="validate")
    parser.add_argument("--prepare-only", action="store_true",
                        help="Write synthetic probe inputs without dispatching")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    choice = target_config(config, args.target)
    if choice.get("transport") == "docker":
        root = Path(choice["docker"]["host_mount"]) / "probe"
        root.mkdir(parents=True, exist_ok=True)
    else:
        root = Path(tempfile.mkdtemp(prefix="research-delegate-probe-"))
    brief = b"Probe one harmless documentation claim for CLI source access."
    (root / "brief.md").write_bytes(brief)
    answers = {name: "specified" for name in BASE_DECISIONS}
    answers.update(research_type="technical", validation_mode="external_cli",
                   validator_cli=args.target, gap_filler_cli=args.target,
                   validator_transport=choice.get("transport", "direct"),
                   gap_filler_transport=choice.get("transport", "direct"),
                   validator_model=choice.get("model", "default"),
                   gap_filler_model=choice.get("model", "default"))
    record = {"required_branches": [], "open_branches": [],
              "decisions": {key: {"state": "answered", "answer": value}
                            for key, value in answers.items()},
              "confirmation": {"confirmed": True,
                               "brief_sha256": hashlib.sha256(brief).hexdigest()}}
    (root / "intake.json").write_text(json.dumps(record), encoding="utf-8")
    if args.role == "validate":
        input_path = root / "findings.md"
        input_path.write_text(
            "P1: Python's json.dumps serializes an object to a JSON-formatted string. "
            "Source: https://docs.python.org/3/library/json.html\n", encoding="utf-8")
    else:
        input_path = root / "gaps.md"
        input_path.write_text(
            "G1: Check whether Python's json.dumps returns a string, using "
            "https://docs.python.org/3/library/json.html, and state the corrected finding.\n",
            encoding="utf-8")
    options = argparse.Namespace(config=args.config.resolve(), record=root / "intake.json",
                                 brief=root / "brief.md", role=args.role, target=args.target,
                                 input=input_path, run_dir=root, timeout=args.timeout)
    if args.prepare_only:
        print(f"Probe inputs: {root}")
        return 0
    try:
        path = run_dispatch(options)
    except Exception as exc:
        print(f"Probe failed: {exc}\nArtifacts: {root}", file=sys.stderr)
        return 2
    print(f"Result: {path}")
    print(path.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
