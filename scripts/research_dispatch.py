"""Run a research validator or gap filler in a fresh external CLI process.

Configuration is JSON data, never shell code. See README.md for the contract.
"""

import argparse
from datetime import datetime
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import time
import uuid

from check_intake import checked_files


CLIS = {"agy", "opencode", "codex"}
ROLES = {"validate", "gap_fill"}


def inside(path: Path, root: Path) -> bool:
    return path.resolve().is_relative_to(root.resolve())


def target_config(config: dict, target: str) -> dict:
    targets = config.get("targets", {})
    choice = targets.get(target)
    if not isinstance(choice, dict) or choice.get("cli") not in CLIS:
        raise ValueError(f"target {target!r} must configure one of {sorted(CLIS)}")
    if choice.get("transport", "direct") not in {"direct", "docker"}:
        raise ValueError("transport must be direct or docker")
    if choice["cli"] == "opencode" and not choice.get("model"):
        raise ValueError("OpenCode requires an explicitly selected provider/model")
    return choice


def confirmed_target(record: dict, role: str, target: str, choice: dict) -> None:
    prefix = "validator" if role == "validate" else "gap_filler"
    decisions = record["decisions"]
    if decisions[f"{prefix}_cli"].get("answer") != target:
        raise ValueError(f"target differs from confirmed {prefix}_cli")
    if decisions[f"{prefix}_transport"].get("answer") != choice.get("transport", "direct"):
        raise ValueError(f"transport differs from confirmed {prefix}_transport")
    model_decision = decisions[f"{prefix}_model"]
    model = choice.get("model")
    if model and model_decision.get("answer") != model:
        raise ValueError(f"model differs from confirmed {prefix}_model")
    if not model and model_decision.get("state") == "answered" and model_decision.get("answer") != "default":
        raise ValueError(f"configured model is missing for {prefix}")


def cli_args(choice: dict, prompt: str, stage: Path, container_stage: str | None) -> list[str]:
    cli = choice["cli"]
    executable = choice.get("executable", cli)
    model = choice.get("model")
    if cli == "agy":
        args = [executable, "--input-format", "stream-json", "--output-format", "stream-json"]
        if model:
            args += ["--model", model]
        return args
    if cli == "opencode":
        return [executable, "run", "--model", model, prompt]
    result_path = f"{container_stage}/last_message.txt" if container_stage else str(stage / "last_message.txt")
    args = [executable, "exec", "--sandbox", "read-only", "--skip-git-repo-check",
            "--ephemeral", "--output-last-message", result_path]
    if model:
        args += ["--model", model]
    return args + [prompt]


def command_for(choice: dict, prompt: str, stage: Path) -> tuple[list[str], Path | None]:
    if choice.get("transport", "direct") == "direct":
        return cli_args(choice, prompt, stage, None), stage
    docker = choice.get("docker", {})
    if not docker.get("host_mount"):
        raise ValueError("Docker target requires host_mount")
    host_root = Path(docker.get("host_mount", "")).resolve()
    container_root = docker.get("container_mount", "")
    container = docker.get("container", "")
    if not container or not container_root or not inside(stage, host_root):
        raise ValueError("Docker stage must be inside the configured shared host_mount")
    relative = stage.resolve().relative_to(host_root)
    container_stage = str(PurePosixPath(container_root, *relative.parts))
    docker_bin = docker.get("executable", "docker")
    args = [docker_bin, "exec"]
    if choice["cli"] == "agy":
        args.append("-i")
    args += ["--workdir", container_stage, container]
    return args + cli_args(choice, prompt, stage, container_stage), None


def stop_docker_stage(choice: dict, stage: Path) -> str:
    """Stop only processes whose container cwd is this unique dispatch stage."""
    docker = choice["docker"]
    host_root = Path(docker["host_mount"]).resolve()
    if not inside(stage, host_root):
        raise ValueError("Docker timeout stage is outside the configured shared mount")
    relative = stage.resolve().relative_to(host_root)
    container_stage = str(PurePosixPath(docker["container_mount"], *relative.parts))
    script = (
        'target=$1; found=0; '
        'for link in /proc/[0-9]*/cwd; do '
        'if [ "$(readlink "$link" 2>/dev/null)" = "$target" ]; then '
        'pid=${link#/proc/}; pid=${pid%/cwd}; '
        'if [ "$pid" != "$$" ]; then kill -TERM "$pid" 2>/dev/null || true; found=1; fi; '
        'fi; done; '
        'if [ "$found" = 1 ]; then sleep 2; fi; '
        'for link in /proc/[0-9]*/cwd; do '
        'if [ "$(readlink "$link" 2>/dev/null)" = "$target" ]; then '
        'pid=${link#/proc/}; pid=${pid%/cwd}; '
        'if [ "$pid" != "$$" ]; then kill -KILL "$pid" 2>/dev/null || true; fi; '
        'fi; done; '
        'printf "matched=%s\\n" "$found"'
    )
    command = [docker.get("executable", "docker"), "exec", docker["container"],
               "sh", "-c", script, "research-timeout", container_stage]
    cleanup = subprocess.run(command, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=15, check=False)
    if cleanup.returncode:
        raise RuntimeError(f"Docker timeout cleanup failed: {cleanup.stderr.strip()[-500:]}")
    return cleanup.stdout.strip()


def stop_dispatch_process(choice: dict, stage: Path, process: subprocess.Popen,
                          metadata: dict, reason: str) -> None:
    """Stop the selected run; stdout and stderr are already captured on disk."""
    if choice.get("transport", "direct") == "docker":
        try:
            metadata[f"{reason}_cleanup"] = stop_docker_stage(choice, stage)
        except Exception as cleanup_error:
            metadata[f"{reason}_cleanup_error"] = str(cleanup_error)
    try:
        process.kill()
    except OSError as cleanup_error:
        metadata[f"{reason}_process_cleanup_error"] = str(cleanup_error)
    try:
        process.communicate(timeout=10)
    except (OSError, subprocess.TimeoutExpired) as cleanup_error:
        metadata[f"{reason}_process_cleanup_error"] = str(cleanup_error)
    metadata["exit_code"] = process.returncode


def parse_role_object(content: str) -> dict:
    """Accept CLI narration around one complete role result, but not partial JSON."""
    try:
        result = json.loads(content.strip())
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    results = []
    position = content.find("{")
    while position != -1:
        try:
            value, end = decoder.raw_decode(content, position)
        except json.JSONDecodeError:
            position = content.find("{", position + 1)
            continue
        if isinstance(value, dict) and value.get("role") in {"validate", "gap_fill"}:
            results.append(value)
        position = content.find("{", end)
    if len(results) != 1:
        raise ValueError("external CLI must return exactly one complete role JSON object")
    return results[0]


def parse_result(cli: str, process: subprocess.CompletedProcess, stage: Path) -> dict:
    if process.returncode:
        raise RuntimeError(f"external CLI exited {process.returncode}: {process.stderr.strip()[-1000:]}")
    if cli == "agy":
        events = [json.loads(line) for line in process.stdout.splitlines() if line.strip()]
        results = [event.get("result") for event in events if event.get("event") == "result"]
        if len(results) != 1 or not isinstance(results[0], dict):
            raise ValueError("Antigravity did not return exactly one result event")
        envelope = results[0]
        if envelope.get("status") != "SUCCESS":
            raise RuntimeError(f"Antigravity status: {envelope.get('status')}: {envelope.get('error', '')}")
        content = envelope.get("response", "")
        if not content.strip() and envelope.get("denied_actions"):
            raise RuntimeError(f"Antigravity denied tool actions: {envelope['denied_actions']}")
    elif cli == "codex":
        result_file = stage / "last_message.txt"
        content = result_file.read_text(encoding="utf-8") if result_file.exists() else ""
    else:
        content = process.stdout
    if not content.strip():
        raise ValueError("external CLI returned an empty result")
    result = parse_role_object(content)
    if not isinstance(result, dict):
        raise ValueError("external CLI result must be an object")
    return result


def validate_result(role: str, result: dict) -> None:
    if result.get("role") != role:
        raise ValueError("result role does not match the requested role")
    if role == "validate":
        if result.get("verdict") not in {"approved", "approved_with_limits", "gaps_found", "blocked"}:
            raise ValueError("validation verdict is missing or invalid")
        issues = result.get("issues")
        if not isinstance(issues, list):
            raise ValueError("validation issues must be a list")
        if result["verdict"] == "approved" and issues:
            raise ValueError("approved validation cannot contain open issues")
        if result["verdict"] == "approved_with_limits" and issues:
            raise ValueError("approved_with_limits cannot contain open issues")
        if result["verdict"] == "gaps_found" and not issues:
            raise ValueError("gaps_found requires issues")
        if not isinstance(result.get("checked_claim_ids"), list) or not result["checked_claim_ids"]:
            raise ValueError("validation must list checked_claim_ids")
        if any(not isinstance(x, str) or not x.strip() for x in result["checked_claim_ids"]):
            raise ValueError("checked_claim_ids must be nonempty strings")
        checks = result.get("checks")
        if not isinstance(checks, list) or not checks:
            raise ValueError("validation must include source checks")
        for check in checks:
            if not isinstance(check, dict) or not all(isinstance(check.get(k), str) and check[k].strip() for k in
                ("claim_id", "source_url", "evidence", "verdict")):
                raise ValueError("each source check needs claim_id, source_url, evidence, and verdict")
            if check["verdict"] not in {"confirmed", "partial", "mismatch", "unverifiable"}:
                raise ValueError("invalid source-check verdict")
        if set(result["checked_claim_ids"]) != {x["claim_id"] for x in checks}:
            raise ValueError("checked_claim_ids must match source checks")
        if result["verdict"] == "approved" and any(x["verdict"] != "confirmed" for x in checks):
            raise ValueError("approved validation cannot contain unconfirmed source checks")
        if result["verdict"] == "approved_with_limits":
            limits = result.get("limitations")
            if not isinstance(limits, list) or not limits:
                raise ValueError("approved_with_limits requires stated limitations")
            if any(not isinstance(limit, dict) or not all(
                isinstance(limit.get(k), str) and limit[k].strip() for k in ("claim_id", "reason"))
                for limit in limits):
                raise ValueError("each limitation needs claim_id and reason")
            limited_ids = {limit["claim_id"] for limit in limits}
            if not limited_ids <= set(result["checked_claim_ids"]):
                raise ValueError("limitations must refer to checked claims")
            if any(check["verdict"] == "mismatch" for check in checks):
                raise ValueError("approved_with_limits cannot contain mismatches")
            if any(check["claim_id"] not in limited_ids for check in checks
                   if check["verdict"] != "confirmed"):
                raise ValueError("unconfirmed checks must have stated limitations")
        if any(not isinstance(issue, dict) or not all(issue.get(k) for k in ("id", "problem"))
               for issue in issues):
            raise ValueError("each validation issue needs an id and problem")
    else:
        if result.get("verdict") not in {"completed", "blocked"}:
            raise ValueError("gap-fill verdict is missing or invalid")
        if not isinstance(result.get("changes"), list) or not isinstance(result.get("unresolved"), list):
            raise ValueError("gap-fill changes and unresolved must be lists")
        if result["verdict"] == "completed" and not result["changes"] and not result["unresolved"]:
            raise ValueError("completed gap fill must report changes or unresolved items")
        if any(not isinstance(change, dict) or not all(change.get(k) for k in
               ("gap_id", "corrected_finding", "source_urls")) for change in result["changes"]):
            raise ValueError("each gap-fill change needs gap_id, corrected_finding, and source_urls")
    if not str(result.get("summary", "")).strip():
        raise ValueError("result summary is required")


def prompt_for(role: str, inline_brief: str | None = None, inline_input: str | None = None) -> str:
    validation_date = datetime.now().astimezone().date().isoformat()
    common = ("Use only the confirmed brief and role input supplied here, plus the cited sources. "
              "Check sources directly where access permits. Never assume a source supports a claim. "
              "Return exactly one complete JSON object, no Markdown fences, drafts, or repeated objects. "
              f"The host validation date is {validation_date}; do not claim a later run checked sources on "
              "an earlier date. State inaccessible evidence as unresolved. "
              "The research as-of date is a cutoff for the claims; "
              "checking a dated eligible source later does not change that cutoff. Preserve the actual source "
              "retrieval or validation date and never claim a check occurred on the as-of date unless it did. ")
    if inline_brief is None:
        common += "The brief is in brief.md and the role input is in this directory. "
    else:
        common += "The supplied text is complete. Use URL or browser tools for cited sources and answer directly. "
        common += f"\n<confirmed_brief>\n{inline_brief}\n</confirmed_brief>\n"
        common += f"<role_input>\n{inline_input}\n</role_input>\n"
    if role == "validate":
        source_instruction = "Check the role input above." if inline_brief is not None else "Read findings.md."
        return common + (f"You are an independent research validator. {source_instruction} Check link access, "
                         "claim accuracy, recency, completeness, and source quality. Return keys: "
                         "role='validate', verdict='approved'|'approved_with_limits'|'gaps_found'|'blocked', summary, "
                         "issues=[{id,claim_id,problem,evidence_urls}], checked_claim_ids=[...], "
                         "checks=[{claim_id,source_url,evidence,verdict}], "
                         "limitations=[{claim_id,reason}] when verdict is approved_with_limits. For evidence, give a "
                         "short source-grounded paraphrase or explain why it could not be accessed. "
                         "Each check verdict is confirmed, partial, mismatch, or unverifiable. "
                         "Approve only if every material claim has support and no material issue remains. "
                         "Use approved_with_limits only for nonmaterial uncertainty that is explicitly "
                         "mapped to partial or unverifiable checks, and set issues=[] for that verdict. "
                         "If any issue remains open, use gaps_found. Never use approved_with_limits for a "
                         "mismatch or a material gap. Do not list claims absent from the role input as checked.")
    source_instruction = "Use the role input above" if inline_brief is not None else "Read gaps.md"
    return common + (f"You are a research gap filler. {source_instruction}, resolve each identified issue "
                     "with evidence, and do not conduct the originating agent's general research. Return keys: "
                     "role='gap_fill', verdict='completed'|'blocked', summary, "
                     "changes=[{gap_id,corrected_finding,source_urls}], "
                     "unresolved=[{gap_id,reason}].")


def run_dispatch(args: argparse.Namespace) -> Path:
    record, brief = checked_files(args.record, args.brief)
    mode = record["decisions"]["validation_mode"].get("answer")
    if mode != "external_cli":
        raise ValueError("confirmed intake did not select external CLI validation")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    choice = target_config(config, args.target)
    confirmed_target(record, args.role, args.target, choice)
    stage = (args.run_dir / "dispatch" / uuid.uuid4().hex).resolve()
    stage.mkdir(parents=True, exist_ok=False)
    (stage / "brief.md").write_bytes(brief)
    input_name = "findings.md" if args.role == "validate" else "gaps.md"
    shutil.copyfile(args.input, stage / input_name)
    if choice["cli"] == "agy":
        prompt = prompt_for(args.role, brief.decode("utf-8"), args.input.read_text(encoding="utf-8"))
    else:
        prompt = prompt_for(args.role)
    (stage / "prompt.txt").write_text(prompt, encoding="utf-8")
    record_path = stage / "dispatch.json"
    started_clock = time.monotonic()
    metadata = {"role": args.role, "target": args.target, "cli": choice["cli"],
                "transport": choice.get("transport", "direct"),
                "status": "started", "run_id": stage.name,
                "started_at": datetime.now().astimezone().isoformat(timespec="seconds")}
    record_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    process = None
    try:
        command, cwd = command_for(choice, prompt, stage)
        metadata["command"] = command
        # Capture streams as they arrive, including output before an interruption.
        # This also preserves output if stopping the external process fails.
        with (stage / "stdout.txt").open("w", encoding="utf-8") as stdout_file, \
             (stage / "stderr.txt").open("w", encoding="utf-8") as stderr_file:
            process = subprocess.Popen(command, cwd=cwd,
                                       stdin=subprocess.PIPE if choice["cli"] == "agy" else subprocess.DEVNULL,
                                       stdout=stdout_file, stderr=stderr_file,
                                       text=True, encoding="utf-8", errors="replace", shell=False)
            metadata["process_id"] = process.pid
            try:
                payload = json.dumps({"event": "user", "message": {"content": prompt}}) + "\n" if choice["cli"] == "agy" else None
                process.communicate(input=payload, timeout=args.timeout)
            except subprocess.TimeoutExpired:
                stop_dispatch_process(choice, stage, process, metadata, "timeout")
                raise TimeoutError(f"external CLI exceeded {args.timeout} seconds")
            except KeyboardInterrupt:
                stop_dispatch_process(choice, stage, process, metadata, "cancel")
                raise
        stdout = (stage / "stdout.txt").read_text(encoding="utf-8", errors="replace")
        stderr = (stage / "stderr.txt").read_text(encoding="utf-8", errors="replace")
        metadata["exit_code"] = process.returncode
        completed = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
        result = parse_result(choice["cli"], completed, stage)
        validate_result(args.role, result)
        (stage / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        metadata["status"] = "completed"
    except KeyboardInterrupt:
        metadata["status"] = "cancelled"
        metadata["cancellation_reason"] = "User interrupted the run"
        raise
    except Exception as exc:
        metadata["status"] = "failed"
        metadata["error"] = str(exc)
        raise
    finally:
        metadata["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        metadata["elapsed_seconds"] = round(time.monotonic() - started_clock, 3)
        record_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return stage / "result.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--brief", type=Path, required=True)
    parser.add_argument("--role", choices=sorted(ROLES), required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    try:
        result = run_dispatch(args)
    except KeyboardInterrupt:
        print("Dispatch cancelled; captured output is saved in the run directory.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Dispatch failed: {exc}", file=sys.stderr)
        return 2
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
