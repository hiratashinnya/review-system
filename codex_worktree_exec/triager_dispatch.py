"""Standalone trusted dispatch of an independent finding triager."""
import hashlib
import hmac
import json
import subprocess
import uuid
from pathlib import Path

from finding_triager.adapter import prepare, propose
from finding_triager.inputs import BINDINGS
from finding_triager.assessment import FIELDS
from .errors import CodexExecError
from .invocation import build_codex_argv
from .launcher import run_codex
from .prompt_files import resolve_output_target
from .source_snapshot import verify_source_snapshot
from .triage_binding_verify import EXTRA, verify_binding_capture


def validate_binding(request, cwd, worktree, environ):
    if request.binding_file is None:
        raise ValueError("trusted triager binding required")
    source = cwd / request.binding_file
    if any(part.is_symlink() for part in (source, *source.parents)):
        raise ValueError("symlink in triager binding path")
    path = source.resolve(strict=True)
    if not path.is_relative_to(worktree / "tmp") or not path.is_file():
        raise ValueError("binding must be in worktree tmp")
    binding = json.loads(path.read_bytes())
    fields = {"review", "review_signature", "expected", "context", "context_digest", "reviewer_worktree"} | EXTRA
    if not isinstance(binding, dict) or set(binding) != fields:
        raise ValueError("invalid triager binding fields")
    reviewer = Path(binding["reviewer_worktree"]).resolve(strict=True)
    listing = subprocess.run(["git", "-C", str(worktree), "worktree", "list", "--porcelain"],
                             check=True, capture_output=True, text=True).stdout.splitlines()
    registered = {Path(line[9:]).resolve() for line in listing if line.startswith("worktree ")}
    if reviewer == worktree.resolve() or reviewer not in registered:
        raise ValueError("reviewer must be a distinct registered worktree")
    expected = binding["expected"]
    if subprocess.run(["git", "-C", str(worktree), "rev-parse", "HEAD"], check=True,
                      capture_output=True, text=True).stdout.strip() != expected["review_oid"]:
        raise ValueError("triager snapshot mismatch")
    keys = [bytes.fromhex(environ[name]) for name in ("TRIAGER_REVIEW_KEY", "TRIAGER_CAPTURE_KEY")]
    receipt = verify_binding_capture(binding, keys[0])
    verify_source_snapshot(worktree, expected["snapshot_oid"], expected["issue"],
                           receipt["approval"]["source_changes"])
    raw, context = binding["review"].encode(), binding["context"].encode()
    prompt, review = prepare(raw, binding["review_signature"], keys[0], expected,
                             context, binding["context_digest"])
    if reviewer != Path(review["reviewer_worktree"]).resolve(strict=True):
        raise ValueError("reviewer origin mismatch")
    if len(keys[1]) < 32 or hmac.compare_digest(*keys):
        raise ValueError("distinct trusted capture key required")
    return binding, keys, raw, context, prompt, review


def capture(review, raw, context_digest, assessments, key):
    payload = {**{k: review[k] for k in BINDINGS}, "producer": "finding-triager",
               "review_sha256": hashlib.sha256(raw).hexdigest(),
               "context_sha256": context_digest, "assessments": assessments}
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
    signature = hmac.new(key, b"finding-triage-capture/v1\0" + data, hashlib.sha256).hexdigest()
    return data, signature


def dispatch(request, cwd, worktree, environ, codex):
    try:
        binding, keys, raw, context, prompt, review = validate_binding(request, cwd, worktree, environ)
        target = resolve_output_target(request.output_file, cwd, worktree)
        if target.exists():
            raise ValueError("triager output must be new")
        intermediate = target.with_name(".triager-" + uuid.uuid4().hex + ".json")
        if intermediate.exists():
            raise ValueError("triager output collision")
        instructions = ("\nReturn only a JSON array. Each item has finding_id, harm, scope, "
                        "evidence (nonempty ac, vd_cp, design, change strings), and facts "
                        "(booleans for every key: " + ", ".join(sorted(FIELDS)) + ").\n")
        result = run_codex(build_codex_argv(request, worktree, intermediate, codex),
                           prompt + instructions, cwd=worktree, timeout_seconds=request.timeout_seconds,
                           environ=environ, quiet=True)
        if result:
            raise ValueError("triager process failed")
        assessments = json.loads(intermediate.read_bytes())
        capture_raw, signature = capture(review, raw, binding["context_digest"], assessments, keys[1])
        artifact = propose(raw, binding["review_signature"], keys[0], binding["expected"], context,
                           binding["context_digest"], capture_raw, signature, keys[1])
        output = {"capture": capture_raw.decode(), "signature": signature, "artifact": artifact}
        with target.open("x", encoding="utf-8") as stream:
            json.dump(output, stream, ensure_ascii=False)
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        raise CodexExecError("CODEX_EXEC_TRIAGER_INVALID", str(error)) from None
    finally:
        if "intermediate" in locals():
            intermediate.unlink(missing_ok=True)
