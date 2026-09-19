"""台帳エントリの**導出状態**と滞留の算出。

**台帳側に ``status`` を保存しない**（PR5「毎回作り直せる導出物は状態化しない」）。
エントリの状態は「そのエントリを参照する改訂案と棚卸し記録から毎回導出できる」ので、
保存すると二重帳簿になり、片方だけ古くなる事故を招く。

導出状態:
  ``untriaged``   どの棚卸し記録にも載っていない（週次棚卸しの入力）
  ``carried``     棚卸しで ``need-more-evidence``（＝次週へ持ち越し）
  ``proposed``    ``pending`` の改訂案がある
  ``approved``    承認済みの改訂案がある（反映待ち）
  ``applied``     反映済みの改訂案がある
  ``rejected``    改訂案がすべて却下された
  ``closed``      棚卸しで ``no-change`` / ``merged-into`` に決着し、改訂案を持たない

``closed`` は Issue #522 が列挙した6状態には無い。``no-change``/``merged-into`` の verdict は
6状態のどれにも当てはまらず（未処理でも持ち越しでもない）、``untriaged`` に落とすと決着済みの
エントリが毎週の棚卸し入力に出続けるため、決着を表す状態として**追加**した。

**滞留判定の wall clock は ``now`` 引数で注入する**（`.claude/rules/04-test-data.md`
「時刻依存 test data の規律」）。本モジュールは ``datetime.date.today()`` を読まない
——読むのは CLI の既定値算出だけで、テストは常に ``--now`` を渡す。

依存仕様: Issue #522「CLI verb / status」。
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from . import schema as schema_module
from .store import Store

UNTRIAGED = "untriaged"
CARRIED = "carried"
PROPOSED = "proposed"
APPROVED = "approved"
APPLIED = "applied"
REJECTED = "rejected"
CLOSED = "closed"

STATES = (UNTRIAGED, CARRIED, PROPOSED, APPROVED, APPLIED, REJECTED, CLOSED)

# 滞留の閾値（日）。週次棚卸しが前提なので、2週間放置＝1回飛ばしたことを意味する。
UNTRIAGED_STALE_DAYS = 14
PROPOSED_STALE_DAYS = 14
APPROVED_STALE_DAYS = 28

_STALE_THRESHOLDS = {
    UNTRIAGED: UNTRIAGED_STALE_DAYS,
    CARRIED: UNTRIAGED_STALE_DAYS,
    PROPOSED: PROPOSED_STALE_DAYS,
    APPROVED: APPROVED_STALE_DAYS,
}


@dataclass(frozen=True)
class EntryState:
    entry_id: str
    state: str
    since: datetime.date
    age_days: int
    stale: bool
    detail: str

    def as_dict(self) -> dict:
        return {
            "entry": self.entry_id,
            "state": self.state,
            "since": self.since.isoformat(),
            "age_days": self.age_days,
            "stale": self.stale,
            "detail": self.detail,
        }


def _proposals_for(store: Store, entry_id: str) -> list:
    return [
        document
        for document in store.of(schema_module.PROPOSAL)
        if entry_id in document.data.get("derived_from", [])
    ]


def _triage_outcomes_for(store: Store, entry_id: str) -> list:
    found = []
    for document in store.of(schema_module.TRIAGE):
        for item in document.data.get("outcomes", []):
            if item.get("entry") == entry_id:
                found.append((document.data["period_end"], document.document_id, item))
    found.sort(key=lambda triple: (triple[0], triple[1]))
    return found


def _state_for(store: Store, entry) -> tuple[str, datetime.date, str]:
    entry_id = entry.document_id
    proposals = _proposals_for(store, entry_id)
    live = [p for p in proposals if p.data.get("status") != "superseded"]

    def _pick(status):
        return [p for p in live if p.data.get("status") == status]

    for status, state in (("applied", APPLIED), ("approved", APPROVED), ("pending", PROPOSED)):
        picked = _pick(status)
        if picked:
            chosen = picked[-1]
            since = chosen.data.get("decided_at") or chosen.data["proposed_at"]
            if not isinstance(since, datetime.date):
                since = chosen.data["proposed_at"]
            return state, since, f"{chosen.document_id} ({status})"
    rejected = _pick("rejected")
    if rejected:
        chosen = rejected[-1]
        since = chosen.data.get("decided_at") or chosen.data["proposed_at"]
        if not isinstance(since, datetime.date):
            since = chosen.data["proposed_at"]
        return REJECTED, since, f"{chosen.document_id} (rejected)"

    outcomes = _triage_outcomes_for(store, entry_id)
    if outcomes:
        period_end, triage_id, item = outcomes[-1]
        verdict = item.get("verdict", "")
        if verdict in ("no-change", "merged-into"):
            return CLOSED, period_end, f"{triage_id} ({verdict})"
        # need-more-evidence、および改訂案が superseded されて残っていない proposed も
        # 「もう一度見る」対象なので carried に寄せる。
        return CARRIED, period_end, f"{triage_id} ({verdict})"
    return UNTRIAGED, entry.data["occurred_at"], "棚卸し未実施"


def compute(store: Store, now: datetime.date) -> list[EntryState]:
    """全台帳エントリの導出状態を ``now`` 基準で算出する。"""
    states: list[EntryState] = []
    for entry in sorted(store.of(schema_module.LEDGER), key=lambda d: d.document_id):
        state, since, detail = _state_for(store, entry)
        age = (now - since).days
        threshold = _STALE_THRESHOLDS.get(state)
        stale = threshold is not None and age > threshold
        states.append(EntryState(
            entry_id=entry.document_id,
            state=state,
            since=since,
            age_days=age,
            stale=stale,
            detail=detail,
        ))
    return states


def untriaged_ids(store: Store, now: datetime.date) -> list[str]:
    """棚卸しの入力（``untriaged`` と ``carried``）を id 昇順で返す。"""
    return [
        item.entry_id
        for item in compute(store, now)
        if item.state in (UNTRIAGED, CARRIED)
    ]


def summarize(states) -> dict:
    counts = {state: 0 for state in STATES}
    for item in states:
        counts[item.state] = counts.get(item.state, 0) + 1
    return {
        "total": len(states),
        "stale": sum(1 for item in states if item.stale),
        "by_state": counts,
    }
