"""保護モードの取り込みでオーナー決定を保持する規則。

レビューアが書けるのは自分の申告（scope）まで。処置方針（disposition 系）はオーナー専権なので、
レポートに書かれていたら無視し、台帳にある値は上書きせず保持する。
"""

from . import model, scope_ledger, scope_records

OWNER_ONLY_KEYS = ("disposition", "deferred_to", "waived_by", "waived_reason")


def ignore_owner_keys(report_text):
    """finding 中の専権キーを除き、元の行番号を保持して警告を返す。"""
    lines, warnings = [], []
    in_block = False
    for lineno, raw in enumerate(report_text.splitlines(keepends=True), start=1):
        line = raw.strip()
        if line.startswith("### "):
            in_block = True
        elif line.startswith("## ") or line.startswith("# "):
            in_block = False
        matched = model.KEY_RE.match(line) if in_block else None
        if matched and matched.group(1) in OWNER_ONLY_KEYS:
            warnings.append(f"{lineno} 行目: オーナー専権の {matched.group(1)} を無視")
            lines.append("\n")
        else:
            lines.append(raw)
    return "".join(lines), warnings


class ReviewerIngestPolicy:
    def __init__(self, repo_root, issue, round_no, *, record_declarations=True):
        self.repo_root = repo_root
        self.issue = issue
        self.round_no = round_no
        self.record_declarations = record_declarations
        self.records = scope_records.read_records(issue, repo_root)
        self.owner_scopes = scope_ledger.owner_scopes(issue, repo_root, records=self.records)
        self.declared_now = {}
        self.kept_owner_scope = []  # オーナー確定の scope を保持した finding ID（申告と食い違うもの）
        # レビューアの申告原本が無い台帳の scope（主文脈の取り込み由来）を、申告で置換した記録（検出用）
        self.replaced_unattested = []
        self.declared_ids = {finding_id for _line, (_round, finding_id, _scope, by) in self.records if not by}

    def apply(self, finding, item, is_new) -> None:
        """scope だけをレポート値で更新する。disposition 系は触らない。

        オーナーが ``decide --scope`` で確定した印のある finding は台帳の scope を保持する
        （レビューアの申告は原本として記録するだけ）。印が無ければ、台帳の値がどこから来たかに
        よらずレビューアの申告を正当な訂正として反映する。
        """
        if self.record_declarations:
            self.declared_now[finding.id] = item.scope
        if finding.id in self.owner_scopes:
            owner_scope = self.owner_scopes[finding.id]
            if owner_scope != item.scope:
                self.kept_owner_scope.append(finding.id)
            finding.scope = owner_scope
            return
        if self.record_declarations and not is_new and finding.id not in self.declared_ids and finding.scope != item.scope:
            self.replaced_unattested.append(f"{finding.id}（{finding.scope}→{item.scope}）")
        finding.scope = item.scope

    def persist(self, round_no) -> None:
        if self.record_declarations:
            scope_ledger.record_declared(self.issue, self.repo_root, round_no, self.declared_now, records=self.records)
