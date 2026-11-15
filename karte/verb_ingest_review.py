"""verb_ingest_review の責務。詳細は .ai/rationale/karte-module-split.md。"""
from . import ingest_review, pointer_completion, report_source
from .verb_boundary import fail_close

def prepare_ingest(args, repo_root) -> str:
    """ロック前に入力を検証する。"""
    pointer_completion.ingest_target(args, repo_root)
    return report_source.read_report(args, repo_root)


@fail_close(locked=True, prepare=prepare_ingest)
def cmd_ingest_review(args, repo_root, report_text) -> int:
    """レビューレポートを台帳へ取り込む。"""
    issue, round_no = pointer_completion.ingest_target(args, repo_root)
    return ingest_review.ingest_locked(repo_root, issue, round_no, report_text)
