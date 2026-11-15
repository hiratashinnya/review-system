"""Issue #801: review 原本をカルテと同じ保存期間で保管するレシート処理。"""

from hashlib import sha256
from pathlib import Path

from . import paths
from .errors import KarteUsageError
from .review_round_record import ReviewRound


def original_path(repo_root, issue, round_no):
    """既存のカルテ格納域に固定ファイル名で保管する。ユーザー入力をパスとして扱わない。"""
    issue = paths.validate_issue(issue)
    if type(round_no) is not int or round_no < 1:
        raise KarteUsageError("Review Round 番号が不正")
    directory = paths.karte_dir(repo_root, create=True)
    name = f"issue-{issue}-review-round-{round_no}.md"
    return paths.resolve_within_repo(directory / name, repo_root)


def record(karte, round_no, original_report_text, repo_root, issue):
    """台帳書込み前にレビュー原本を安全に保管し、参照とdigestを一致させる。"""
    digest = sha256(original_report_text.encode("utf-8")).hexdigest()
    path = original_path(repo_root, issue, round_no)
    source = str(path.relative_to(Path(repo_root).resolve())).replace("\\", "/")
    if path.exists():
        # 既に記録したラウンドを異なる原本へすり替えない。
        if paths.read_text(path) != original_report_text:
            raise KarteUsageError(f"同じ round の原本が異なるため上書きを拒否: {source}")
    else:
        paths.write_text_atomic(path, original_report_text)
        if sha256(paths.read_text(path).encode("utf-8")).hexdigest() != digest:
            raise KarteUsageError(f"レビュー原本の保存後照合に失敗: {source}")
    karte.review_rounds = [r for r in karte.review_rounds if r.number != round_no]
    karte.review_rounds.append(ReviewRound(round_no, digest, source))
    karte.review_rounds.sort(key=lambda r: r.number)


def restore_scopes(karte, policy):
    """レビューアにオーナー確定scopeを上書きさせない。"""
    if policy:
        for finding in karte.findings:
            if finding.id in policy.owner_scopes:
                finding.scope = policy.owner_scopes[finding.id]
