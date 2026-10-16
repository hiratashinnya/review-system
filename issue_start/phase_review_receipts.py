"""trusted dispatcher からの独立レビュー証跡を対象artifactへ束縛する。"""
import hashlib
import tomllib
from pathlib import Path
from issue_envelope.model import normalize
from issue_envelope.placement import validate_placement
from codex_worktree_exec.committed_artifact import read_committed_artifact
from codex_worktree_exec.source_snapshot import verify_source_snapshot

RECEIPT_FIELDS = {"phase", "reviewer", "producer_context", "review_context", "artifact",
                  "artifact_digest", "status"}


def validate_review_receipts(reviews, approval, root: Path):
    if not isinstance(reviews, list):
        raise ValueError("review receipts must be an array")
    seen, contexts, producers = {}, set(), set()
    for review in reviews:
        if not isinstance(review, dict) or set(review) != RECEIPT_FIELDS:
            raise ValueError("review receipt fields mismatch")
        reviewer = "pr-reviewer" if review["phase"] == "test_design" else "plan-reviewer"
        producer, context = review["producer_context"], review["review_context"]
        if (review["status"] != "clean" or review["reviewer"] != reviewer
                or not isinstance(context, str) or not context.strip()
                or not isinstance(producer, str) or not producer.strip() or producer == context
                or context == approval["context_id"] or producer == approval["context_id"]
                or context in contexts or producer in producers
                or review["phase"] in seen):
            raise ValueError("separate clean review context required")
        path = root / review["artifact"]
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("review artifact outside worktree")
        content = read_committed_artifact(path, root)
        if hashlib.sha256(content).hexdigest() != review["artifact_digest"]:
            raise ValueError("reviewed artifact digest mismatch")
        data = normalize(tomllib.loads(content.decode("utf-8")))
        validate_placement(path, data, root)
        if (data["phase"] != review["phase"] or data["issue"] != approval["issue"]
                or any(data[key] != approval[key] for key in ("run_id", "target_key", "snapshot_oid"))
                or data["status"] != "ready"
                or data["unresolved_findings"] or data["unresolved_owner_decisions"]):
            raise ValueError("reviewed artifact mismatch/STOP")
        verify_source_snapshot(root, data["snapshot_oid"], data["issue"])
        seen[review["phase"]] = review
        contexts.add(context)
        producers.add(producer)
    if contexts & producers:
        raise ValueError("author and review contexts must be separate")
    return seen
