"""P5 適用（🤖 自動修正を内部 git に finding 単位コミット）。design/02・S4。

🤖 の確定 fix を workspace に書き込み finding 単位でコミット。1件でも失敗したら実行ぶんを
基準点へ戻す（all-or-nothing＝S4：半端を残さない）。MVP は SuggestedFix.diff を「新しい
ファイル内容」として適用する（unified diff 適用は post-MVP）。
"""
from __future__ import annotations

from ..domain.ids import ExecutionId
from ..domain.report import AppliedCommit
from ..domain.review import TriagedFinding, finding_key
from ..domain.result import StageOutcome, FailureStage, ok, fail


def apply_auto(
    exec_id: ExecutionId,
    auto: tuple[TriagedFinding, ...],
    targets: dict[str, str],
    workspace,
    now: str,
) -> StageOutcome[tuple[AppliedCommit, ...]]:
    """🤖 区分を内部 git に適用。失敗時は基準点へ全戻し（書込ゼロ）。

    open() も含めて try 内で受ける（open 失敗も fail-close）。rollback は best-effort で、
    二次例外が原因例外を潰さないようにする（S4 の「書込ゼロ」を例外漏れ無しで保つ）。
    """
    commits: list[AppliedCommit] = []
    try:
        workspace.open(exec_id, targets)
        for tf in auto:
            fix = tf.finding.suggested_fix
            if fix is None:                      # 修正案が無い 🤖 はスキップ（適用対象外）
                continue
            rel = str(tf.finding.location.file)
            key = finding_key(tf.finding)
            ref = workspace.commit_fix(exec_id, key, rel, fix.diff)
            commits.append(AppliedCommit(exec_id, key, ref, now))
        return ok(tuple(commits))
    except Exception as e:                        # S4：途中失敗→実行ぶんを巻き戻す
        try:
            workspace.rollback_execution(exec_id)
        except Exception:                         # 二次例外で原因を潰さない
            pass
        return fail(FailureStage.APPLY, f"自動適用に失敗: {e}", None,
                    "実行ぶんは基準点へ戻したので（書込ゼロ）、原因を確認のうえ手動で修正・適用してください。")
