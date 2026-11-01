"""レビューア本人の取り込み（``ingest-reviewer``）だけに課す追加規則。

レビューアが書けるのは自分の申告（scope）まで。処置方針（disposition 系）はオーナー専権なので、
レポートに書かれていたら拒否し、台帳にある値は上書きせず保持する。
"""

from . import scope_ledger

OWNER_ONLY_KEYS = ("disposition", "deferred_to", "waived_by", "waived_reason")


class ReviewerIngestPolicy:
    def __init__(self, repo_root, issue, round_no):
        self.repo_root = repo_root
        self.issue = issue
        self.round_no = round_no
        self.owner_scopes = scope_ledger.owner_scopes(issue, repo_root)
        self.declared_now = {}
        self.kept_owner_scope = []  # オーナー確定の scope を保持した finding ID（申告と食い違うもの）

    def check(self, review) -> list:
        """オーナー専権キーを含むブロックを全件列挙する（1 件ずつ往復させない）。"""
        return [
            f"{item.lineno} 行目: レビューアはオーナー専権の {key} を書けない"
            "（処置方針の記録は主文脈が `decide` で行う）"
            for item in review
            for key in OWNER_ONLY_KEYS
            if getattr(item, key)
        ]

    def apply(self, finding, item, is_new) -> None:
        """scope だけをレポート値で更新する。disposition 系は触らない。

        オーナーが ``decide --scope`` で確定した印のある finding は台帳の scope を保持する
        （レビューアの申告は原本として記録するだけ）。印が無ければ、台帳の値がどこから来たかに
        よらずレビューアの申告を正当な訂正として反映する。
        """
        self.declared_now[finding.id] = item.scope
        if finding.id in self.owner_scopes:
            if finding.scope != item.scope:
                self.kept_owner_scope.append(finding.id)
            return
        finding.scope = item.scope

    def persist(self, round_no) -> None:
        scope_ledger.record_declared(self.issue, self.repo_root, round_no, self.declared_now)
