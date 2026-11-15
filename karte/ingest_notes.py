"""保護モードの取り込み結果に添える注記（標準出力）と、未完了（再掲漏れ）の判定。"""

import sys

from .exit_codes import EXIT_INCOMPLETE, EXIT_OK


def print_policy_notes(policy) -> None:
    """オーナー確定 scope の保持と、申告原本のない scope の置換を出す。"""
    if policy and policy.kept_owner_scope:
        kept = ", ".join(policy.kept_owner_scope)
        print(f"  オーナーが確定した scope を保持（レビューア申告と台帳が不一致）: {kept}")
    if policy and policy.replaced_unattested:
        replaced = ", ".join(policy.replaced_unattested)
        print(f"  申告原本のない scope をレビューア申告で置換（台帳の旧値は主文脈の取り込み等で原本なし）: {replaced}")


def exit_code_for(policy, karte, absent) -> int:
    """レビューアが申告した是正対象の finding の再掲漏れがあれば ``EXIT_INCOMPLETE``（台帳は書き込み済み）。

    引き継ぎで取り込み自体は成功させるが、reviewer の出力欠落（切り詰め等）を終了コード 0 の
    「完了」にしない（F-375-05）。対象は**レビューアが過去に申告した**（原本がある）、かつ
    当該 PR で是正が求められている（``needs_remediation``）未解消 finding に限る。主文脈が足した
    finding・オーナーが申し送り／処置不要と決めた finding はレビューアが知らない・再掲不要なので対象外。
    主文脈専用の追記専用モードも再掲しないのが通常なので対象外。
    """
    if not (policy and policy.record_declarations):
        return EXIT_OK
    missing = [
        fid for fid in absent
        if fid in policy.declared_ids and (item := karte.finding(fid)) is not None and item.needs_remediation
    ]
    if not missing:
        return EXIT_OK
    print(
        "  未完了（取り込み済み）: レビューアが申告した未解消 finding が今回の出力に再掲されていない: "
        + ", ".join(missing) + "（解消ではない。次のレビューで `status: open|resolved` を明示して再掲させる）"
    )
    print("未完了: 再掲漏れ " + ", ".join(missing), file=sys.stderr)
    return EXIT_INCOMPLETE
