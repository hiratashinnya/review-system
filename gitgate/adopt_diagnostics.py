"""Actionable local-ref conflict descriptions independent of permission checks."""
from .adopt_holders import HOLDER_PRIMARY, HOLDER_AGENT, HOLDER_LINKED, HOLDER_UNKNOWN
def describe_local_ref_conflict(
    branch_name: str,
    *,
    holder_kind: str | None,
    holder_path: str | None = None,
    entry=None,
    local_tip: str | None = None,
    remote_tip: str | None = None,
) -> str:
    """``BRANCH_ADOPT_LOCAL_EXISTS`` の detail を組み立てる（純関数・Issue #502）。

    「何が起きたか」だけでなく「**誰が掴んでいるか**」と「次に何を実行するか」を必ず含める。
    """
    detail = _holder_detail(branch_name, holder_kind, holder_path, entry, local_tip, remote_tip)
    return detail + _FOLLOWUP_AUTHOR_NOTE


# 後続作者の失敗は掴んでいる側を片付けても同branchで継続できない（#685 F-685-23）。
_FOLLOWUP_AUTHOR_NOTE = (
    "。後続作者（change-planner／test-writer／issue-implementer）の失敗なら、上の処置をしても失敗作者の"
    "台帳 entry が最新 owner として残るので同じブランチでは継続できない。STOP してオーナーへ報告する"
    "（.ai/troubleshooting/issue-pipeline.md「`adopt-branch` が `BRANCH_ADOPT_LOCAL_EXISTS` で失敗したとき」）"
)


def _holder_detail(branch_name, holder_kind, holder_path, entry, local_tip, remote_tip) -> str:
    if holder_kind == HOLDER_PRIMARY:
        return (
            f"{branch_name}（**メインワークツリー（primary checkout）** "
            f"{holder_path or '<path unknown>'} が同じブランチを checkout したままになっている。"
            "agent worktree ではないので gitgate の worktree verb では解消しない。"
            "解消: そのワークツリーで `git switch <既定ブランチ>` を実行して戻す"
            "（レビュー担当がブランチを切り替えたまま戻していない場合がある＝Issue #502 観測2））"
        )
    if holder_kind in (HOLDER_AGENT, HOLDER_LINKED):
        if entry is not None:
            attribution = (
                f"台帳 entry={entry.get('entry_id')}[{entry.get('status')}]"
            )
            remedy = (
                "解消: python3 -m gitgate collect-worktree --entry "
                f"{entry.get('entry_id')}"
                "（回収不能なら python3 -m gitgate worktree-forget --entry "
                f"{entry.get('entry_id')} --reason <text> のあと "
                "python3 -m gitgate worktree-release <path> --force-uncollected --reason <text>）"
            )
        elif holder_kind == HOLDER_AGENT:
            attribution = "台帳に対応するエントリが無い"
            remedy = (
                "解消: python3 -m gitgate worktree-release <path> --force-uncollected "
                "--reason <text>（主文脈が実行する）"
            )
        else:
            attribution = "台帳に対応するエントリが無い"
            remedy = (
                "解消: そのワークツリーで `git switch --detach` を実行して外す（主文脈が行う。"
                "worktree-release は .claude/worktrees/agent-<id> 形しか受理しないので使えない）"
            )
        label = "agent worktree" if holder_kind == HOLDER_AGENT else "linked worktree"
        return (
            f"{branch_name}（{label} {holder_path or '<path unknown>'} が同じブランチを"
            f"掴んでいる。{attribution}。{remedy}）"
        )
    if holder_kind == HOLDER_UNKNOWN:
        return (
            f"{branch_name}（ローカル ref が残っているが `git worktree list` を実行できず、"
            "どのワークツリーが掴んでいるか判定できない。判定不能は衝突側に倒す＝fail-close）"
        )
    return (
        f"{branch_name}（ローカル ref が origin と別のコミットを指す: "
        f"local={local_tip or '<unknown>'} / origin={remote_tip or '<unknown>'}。"
        "未 push のローカル作業がありうるため自動回収しない。内容を確認したうえで手当てする）"
    )
