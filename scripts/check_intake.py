"""Reject an incomplete or unconfirmed research brief before a pipeline phase."""

import argparse
import hashlib
import json
from pathlib import Path
from strict_json import read as read_json, read_text


BASE_DECISIONS = {
    "research_type", "research_questions", "targets", "geography", "time_scope",
    "depth", "report_format", "source_leads", "review_granularity",
    "validation_mode",
}
STATES = {"pending", "unclear", "answered", "not_applicable"}
ROUTING_DECISIONS = {
    "validation_mode", "validator_cli", "gap_filler_cli", "validator_transport",
    "gap_filler_transport", "validator_model", "gap_filler_model",
}


def nonempty_text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def recorded_user_evidence(value) -> bool:
    """Check audit fields only; this cannot authenticate a conversation or consent."""
    return (isinstance(value, dict)
            and nonempty_text(value.get("message_ref"))
            and nonempty_text(value.get("quote")))


def intake_sha256(record: dict) -> str:
    """Bind confirmation to decisions and branch inventory, excluding confirmation."""
    if not isinstance(record, dict):
        raise ValueError("intake record must be an object")
    scope = {key: record.get(key, []) if key != "decisions" else record.get(key, {})
             for key in ("decisions", "required_branches", "open_branches")}
    canonical = json.dumps(scope, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def check(record: dict, brief: bytes) -> list[str]:
    if not isinstance(record, dict):
        return ["intake record must be an object"]
    errors = []
    decisions = record.get("decisions")
    if not isinstance(decisions, dict):
        return ["decisions must be an object"]
    branches = record.get("required_branches", [])
    if not isinstance(branches, list) or any(not nonempty_text(x) for x in branches):
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
            if not isinstance(transport, str) or transport not in {"direct", "docker"}:
                errors.append(f"{role}_transport must be direct or docker")
    elif not isinstance(mode, str) or mode not in {"same_session", "external_cli"}:
        errors.append("validation_mode must be same_session or external_cli")
    if not isinstance(research_type, str) or research_type not in {"market", "technical"}:
        errors.append("research_type must be market or technical")
    for key in sorted(required):
        entry = decisions.get(key)
        if not isinstance(entry, dict):
            errors.append(f"{key}: missing decision")
            continue
        state = entry.get("state")
        if not isinstance(state, str) or state not in STATES:
            errors.append(f"{key}: invalid state")
        elif state in {"pending", "unclear"}:
            errors.append(f"{key}: {state}")
        elif state == "answered" and not nonempty_text(entry.get("answer")):
            errors.append(f"{key}: answer must be a nonempty string")
        elif state == "not_applicable" and not nonempty_text(entry.get("reason")):
            errors.append(f"{key}: not_applicable requires a nonempty string reason")
        if (state == "not_applicable" and key in ROUTING_DECISIONS
                and not key.endswith("_model")):
            errors.append(f"{key}: must be answered when this routing choice is required")
    for key, entry in decisions.items():
        if not isinstance(entry, dict) or not isinstance(entry.get("state"), str) or entry["state"] not in STATES:
            errors.append(f"{key}: invalid state")
        elif entry.get("state") in {"pending", "unclear"}:
            errors.append(f"{key}: unresolved branch")
        elif entry.get("state") == "answered" and not nonempty_text(entry.get("answer")):
            errors.append(f"{key}: answer must be a nonempty string")
        elif entry.get("state") == "not_applicable" and not nonempty_text(entry.get("reason")):
            errors.append(f"{key}: not_applicable requires a nonempty string reason")
        if (key in ROUTING_DECISIONS and isinstance(entry, dict)
                and entry.get("state") == "answered"
                and not recorded_user_evidence(entry.get("user_evidence"))):
            errors.append(f"{key}: user_evidence requires a nonempty message_ref and quote")
    if record.get("open_branches") != []:
        errors.append("open_branches must be an empty list")
    confirmation = record.get("confirmation", {})
    if not isinstance(confirmation, dict):
        confirmation = {}
    if not recorded_user_evidence(confirmation.get("user_evidence")):
        errors.append("confirmation: user_evidence requires a nonempty message_ref and quote")
    digest = hashlib.sha256(brief).hexdigest()
    if confirmation.get("confirmed") is not True or confirmation.get("brief_sha256") != digest:
        errors.append("user confirmation must match the current brief SHA-256")
    try:
        decision_digest = intake_sha256(record)
    except (TypeError, ValueError):
        decision_digest = None
        errors.append("intake decisions must contain JSON-serializable finite values")
    if decision_digest is None or confirmation.get("intake_sha256") != decision_digest:
        errors.append("user confirmation must match the current intake SHA-256; reconfirm decisions and brief")
    if not brief.strip():
        errors.append("brief is empty")
    return sorted(set(errors))


def checked_files(record_path: Path, brief_path: Path) -> tuple[dict, bytes]:
    record = read_json(record_path)
    brief = read_text(brief_path).encode('utf-8')
    errors = check(record, brief)
    if errors:
        raise ValueError("Intake gate failed:\n- " + "\n- ".join(errors))
    return record, brief


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--brief", type=Path, required=True)
    parser.add_argument("--confirmation-hashes", action="store_true",
                        help="Print hashes for review; does not confirm or modify the intake")
    args = parser.parse_args()
    try:
        if args.confirmation_hashes:
            record = read_json(args.record)
            print(json.dumps({"brief_sha256": hashlib.sha256(read_text(args.brief).encode('utf-8')).hexdigest(),
                              "intake_sha256": intake_sha256(record)}, indent=2))
            return 0
        checked_files(args.record, args.brief)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(2, f"{exc}\n")
    print("Intake gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
