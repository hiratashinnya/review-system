"""Issue #801: 承認されたreview roundの原本digestとオーナーscopeを保存する。"""

from hashlib import sha256

from .review_round_record import ReviewRound


def record(karte, round_no, original_report_text):
    """Summary 付き0件も台帳のlatest roundとして残す。同一roundの再取込は置換。"""
    digest = sha256(original_report_text.encode("utf-8")).hexdigest()
    karte.review_rounds = [r for r in karte.review_rounds if r.number != round_no]
    karte.review_rounds.append(ReviewRound(round_no, digest))
    karte.review_rounds.sort(key=lambda r: r.number)


def restore_scopes(karte, policy):
    """レビューアにオーナー確定scopeを上書きさせない。"""
    if policy:
        for finding in karte.findings:
            if finding.id in policy.owner_scopes:
                finding.scope = policy.owner_scopes[finding.id]
