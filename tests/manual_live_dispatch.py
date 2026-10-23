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
from check_intake import BASE_DECISIONS, intake_sha256
from research_dispatch import run_dispatch, target_config
from strict_json import read as read_json

SOURCE = 'https://docs.python.org/3/library/json.html'


def source_probe_passed(role, result):
    if role == 'validate':
        return (result.get('verdict') == 'approved' and result.get('checked_claim_ids') == ['P1']
                and not result.get('issues') and bool(result.get('checks'))
                and all(check.get('claim_id') == 'P1' and check.get('verdict') == 'confirmed'
                        and check.get('source_url', '').split('#', 1)[0] == SOURCE
                        for check in result['checks']))
    return (result.get('verdict') == 'completed' and not result.get('unresolved')
            and bool(result.get('changes')) and all(change.get('gap_id') == 'G1'
                and SOURCE in [url.split('#', 1)[0] for url in change.get('source_urls', [])]
                for change in result['changes']))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--role", choices=["validate", "gap_fill"], default="validate")
    parser.add_argument("--prepare-only", action="store_true",
                        help="Write synthetic probe inputs without dispatching")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    config = read_json(args.config)
    choice = target_config(config, args.target)
    if choice.get("transport") == "docker":
        parent = Path(choice["docker"]["host_mount"]) / "probe"
        parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix='source-check-', dir=parent))
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
    # Synthetic probe bookkeeping is never evidence of a real user's approval.
    evidence = {"message_ref": "synthetic-source-probe",
                "quote": "Synthetic probe only: use this target to check the public documentation claim."}
    for entry in record["decisions"].values():
        entry["user_evidence"] = evidence.copy()
    record["confirmation"]["user_evidence"] = evidence.copy()
    record["confirmation"]["intake_sha256"] = intake_sha256(record)
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
    result = read_json(path)
    print(json.dumps(result, indent=2))
    if not source_probe_passed(args.role, result):
        print('Probe did not establish successful source checking; inspect retained evidence.', file=sys.stderr)
        return 3
    print('Structured source probe passed; inspect tool logs to establish actual source access.')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
