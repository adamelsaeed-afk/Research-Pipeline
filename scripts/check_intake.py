"""Reject an incomplete or unconfirmed research brief before a pipeline phase."""

import argparse
import hashlib
import json
from pathlib import Path


BASE_DECISIONS = {
    "research_type", "research_questions", "targets", "geography", "time_scope",
    "depth", "report_format", "source_leads", "review_granularity",
    "validation_mode",
}
STATES = {"pending", "unclear", "answered", "not_applicable"}


def check(record: dict, brief: bytes) -> list[str]:
    if not isinstance(record, dict):
        return ["intake record must be an object"]
    errors = []
    decisions = record.get("decisions")
    if not isinstance(decisions, dict):
        return ["decisions must be an object"]
    branches = record.get("required_branches", [])
    if not isinstance(branches, list) or any(not isinstance(x, str) or not x for x in branches):
        return ["required_branches must be a list of nonempty decision names"]
    required = BASE_DECISIONS | set(branches)
    research_entry = decisions.get("research_type")
    research_type = research_entry.get("answer") if isinstance(research_entry, dict) else None
    if research_type == "market":
        required.add("market_subtype")
    mode_entry = decisions.get("validation_mode")
    mode = mode_entry.get("answer") if isinstance(mode_entry, dict) else None
    if mode == "external_cli":
        required |= {"validator_cli", "gap_filler_cli", "validator_transport",
                     "gap_filler_transport", "validator_model", "gap_filler_model"}
        for key in ("validator_cli", "gap_filler_cli"):
            entry = decisions.get(key)
            if not isinstance(entry, dict) or not isinstance(entry.get("answer"), str):
                errors.append(f"{key} must be a target name")
        for role in ("validator", "gap_filler"):
            transport_entry = decisions.get(f"{role}_transport")
            transport = transport_entry.get("answer") if isinstance(transport_entry, dict) else None
            if transport not in {"direct", "docker"}:
                errors.append(f"{role}_transport must be direct or docker")
    elif mode not in {"same_session", "external_cli"}:
        errors.append("validation_mode must be same_session or external_cli")
    if research_type not in {"market", "technical"}:
        errors.append("research_type must be market or technical")
    for key in sorted(required):
        entry = decisions.get(key)
        if not isinstance(entry, dict):
            errors.append(f"{key}: missing decision")
            continue
        state = entry.get("state")
        if state not in STATES:
            errors.append(f"{key}: invalid state")
        elif state in {"pending", "unclear"}:
            errors.append(f"{key}: {state}")
        elif state == "answered" and not str(entry.get("answer", "")).strip():
            errors.append(f"{key}: empty answer")
        elif state == "not_applicable" and not str(entry.get("reason", "")).strip():
            errors.append(f"{key}: not_applicable requires a reason")
    for key, entry in decisions.items():
        if not isinstance(entry, dict) or entry.get("state") not in STATES:
            errors.append(f"{key}: invalid state")
        elif entry.get("state") in {"pending", "unclear"}:
            errors.append(f"{key}: unresolved branch")
        elif entry.get("state") == "answered" and not str(entry.get("answer", "")).strip():
            errors.append(f"{key}: empty answer")
        elif entry.get("state") == "not_applicable" and not str(entry.get("reason", "")).strip():
            errors.append(f"{key}: not_applicable requires a reason")
    if record.get("open_branches") != []:
        errors.append("open_branches must be an empty list")
    confirmation = record.get("confirmation", {})
    if not isinstance(confirmation, dict):
        confirmation = {}
    digest = hashlib.sha256(brief).hexdigest()
    if confirmation.get("confirmed") is not True or confirmation.get("brief_sha256") != digest:
        errors.append("user confirmation must match the current brief SHA-256")
    if not brief.strip():
        errors.append("brief is empty")
    return sorted(set(errors))


def checked_files(record_path: Path, brief_path: Path) -> tuple[dict, bytes]:
    record = json.loads(record_path.read_text(encoding="utf-8"))
    brief = brief_path.read_bytes()
    errors = check(record, brief)
    if errors:
        raise ValueError("Intake gate failed:\n- " + "\n- ".join(errors))
    return record, brief


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--brief", type=Path, required=True)
    args = parser.parse_args()
    try:
        checked_files(args.record, args.brief)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(2, f"{exc}\n")
    print("Intake gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
