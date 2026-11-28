"""Read date-stamped proposals and measure the waiting age at capture time."""

from datetime import date, datetime, time, timedelta
from statistics import median

from feedback_ledger.schema import PROPOSAL
from feedback_ledger.store import load_store

from .period import JST, parse_jst
from .quantities import measured

SOURCE = ".ai/feedback/queue"
PENDING = "フィードバック台帳で承認待ち (pending) の改訂案"
AGE = "承認待ちの改訂案の提案日から取得日までの中央値（JST、日付精度）"
DECISION_WAIT = "期間内に決定した改訂案の提案日から決定日までの中央値（JST、日付精度）"
DECIDED = {"approved", "rejected", "applied"}


def capture(root):
    try:
        if not (root / SOURCE).is_dir():
            return {"source": SOURCE, "rows": None, "reason": "台帳ディレクトリがありません"}
        store = load_store(root)
        if any(finding.level == "ERROR" for finding in store.findings):
            return {"source": SOURCE, "rows": None, "reason": "台帳の検証に失敗しました"}
        rows = [{"id": doc.document_id, "path": doc.relpath, "status": doc.data["status"],
                 "proposed_at": doc.data["proposed_at"].isoformat(),
                 "decided_at": doc.data["decided_at"].isoformat() if doc.data.get("decided_at") else None}
                for doc in store.of(PROPOSAL)]
        return {"rows": rows, "source": SOURCE, "reason": None}
    except (OSError, ValueError, RuntimeError, KeyError, AttributeError) as exc:
        return {"rows": None, "source": SOURCE, "reason": f"台帳を取得できません ({type(exc).__name__})"}


def measure(evidence, observed_at=None):
    source, rows, reason = evidence["source"], evidence["rows"], evidence["reason"]
    pending = None if rows is None else [row for row in rows if row["status"] == "pending"]
    metric = measured(None if pending is None else len(pending), PENDING, source, reason=reason,
                      status="not_retrieved" if pending is None else None)
    if pending is not None:
        metric["proposals"] = [row["path"] for row in pending]
        metric["observed_ledger_records"] = len(rows)
    return {"owner_pending_proposals": metric,
            "owner_pending_proposal_age_days": _age(pending, source, reason, observed_at)}


def _age(pending, source, reason, observed_at):
    if pending is None:
        return measured(None, AGE, source, reason=reason, unit="日", n=None, status="not_retrieved")
    if not pending:
        return measured(None, AGE, source, reason="対象が0件", unit="日", n=0)
    if observed_at is None:
        return measured(None, AGE, source, reason="実際の取得時点が確認できません", unit="日", n=None)
    try:
        observed = parse_jst(observed_at) if isinstance(observed_at, str) else observed_at.astimezone(JST)
        ages = {row["id"]: (observed.date() - date.fromisoformat(row["proposed_at"])).days for row in pending}
        if any(value < 0 for value in ages.values()):
            raise ValueError("future proposal date")
    except (ValueError, TypeError, AttributeError):
        return measured(None, AGE, source, reason="提案日が欠損、または取得日より後です", unit="日", n=None)
    return measured(median(ages.values()), AGE, source, unit="日", n=len(ages), age_days_by_proposal=ages)


def measure_decisions(period, evidence):
    source, rows = evidence["source"], evidence["rows"]
    if rows is None:
        return measured(None, DECISION_WAIT, source, reason=evidence["reason"],
                        status="not_retrieved", unit="日", n=None)
    ages, ambiguous = {}, []
    for row in rows:
        if row["status"] not in DECIDED:
            continue
        try:
            decided = date.fromisoformat(row["decided_at"])
            start = datetime.combine(decided, time.min, JST)
            end = start + timedelta(days=1)
            if start >= period.cutoff or end <= period.start:
                continue
            age = (decided - date.fromisoformat(row["proposed_at"])).days
            if age < 0 or start < period.start or end > period.cutoff:
                raise ValueError("unknown window or age")
            ages[row["id"]] = age
        except (ValueError, TypeError, OverflowError):
            ambiguous.append(row["id"])
    reason = None
    if ambiguous:
        reason = "日付しかない期間境界の記録、または日時欠損により母数を確定できません"
    elif not ages:
        reason = "対象が0件"
    return measured(median(ages.values()) if ages and not reason else None, DECISION_WAIT, source,
                    reason=reason, unit="日", n=None if ambiguous else len(ages),
                    observed_age_days_by_proposal=ages, ambiguous_proposal_ids=ambiguous)
