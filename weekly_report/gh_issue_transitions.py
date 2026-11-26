"""Read and verify GitHub issue close and reopen history."""

from collections import Counter

from .gh_issue_history import CLOSE_EVENT_DELAY, TRANSITIONS, event_time, verified_events
from .github import evidence
from .records import _moment, _number, _text


def transition(row):
    event = _text(row["event"])
    value = {"id": _number(row["id"]), "event": event}
    if event in TRANSITIONS:
        value.update(created_at=_moment(row["created_at"]), state_reason=row.get("state_reason"))
    elif event == "transferred":
        value["created_at"] = _moment(row["created_at"])
    return value


def candidates(issues, period):
    return [
        row for row in issues if row["created_at"] < period.cutoff
        and (row["updated_at"] >= period.start or (
            row["closed_at"] is not None and row["closed_at"] >= period.start
        ))
    ]


def transition_evidence(repository, issues, details, period, consistency):
    source = f"https://api.github.com/repos/{repository}/issues/{{number}}/events"
    if issues["rows"] is None:
        return evidence(source, reason="Issue 一覧が未取得です", known_rows=[], target_issue_numbers=None,
                        transfer_events=None)
    targets = candidates(issues["rows"], period)
    rows, transfers, unavailable = [], [], {}
    for issue in targets:
        number = issue["number"]
        detail = details.get(number)
        if detail is None or detail["rows"] is None:
            unavailable[number] = detail["reason"] if detail else "イベント証跡がありません"
            continue
        transfers.extend({**event, "number": number, "title": issue["title"], "repository": repository}
                         for event in detail["rows"] if event["event"] == "transferred")
        normalized = verified_events(issue, detail["rows"])
        if normalized is None:
            unavailable[number] = "最新 Issue 状態と close/reopen 履歴を照合できません"
        else:
            rows.extend(event for event in normalized if event_time(event) >= period.start)
    reason = None
    if unavailable:
        reason = "一部の Issue の close/reopen 履歴を確定できません"
    elif consistency["status"] != "unchanged":
        reason = "取得前後に Issue 一覧の同一性を確認できません"
    ids = Counter(row["id"] for row in rows + transfers)
    if any(amount > 1 for amount in ids.values()):
        reason = "Issue をまたいで重複するイベント証跡があります"
        rows = [row for row in rows if ids[row["id"]] == 1]
        transfers = [row for row in transfers if ids[row["id"]] == 1]
    rows.sort(key=lambda event: (event_time(event), event["id"]))
    transfers.sort(key=lambda event: (event["created_at"], event["id"]))
    known = {"known_rows": rows} if reason else {}
    return evidence(source, rows if reason is None else None, reason=reason, **known,
                    target_issue_numbers=[issue["number"] for issue in targets], unavailable_issues=unavailable,
                    history_start=period.start, transfer_events=transfers,
                    terminal_close_delay_limit_seconds=int(CLOSE_EVENT_DELAY.total_seconds()))
