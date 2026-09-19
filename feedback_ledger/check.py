"""文書をまたぐ検査（L2／L3／L6／L7／P1〜P4／T1）。

単体の検査（L1／L4／L5）は :mod:`feedback_ledger.model` にある。ここは「他の文書・
リポジトリの実体・git 履歴と突き合わせないと判定できない」規則だけを持つ。

規則の一覧:
  * **L2** ``affected_assets`` / ``target_assets`` の全パスが実在する。
  * **L3** 文書 id 参照（``supersedes``／``decided_in``）の実在。
    Issue #522 の規則一覧は L1・L2・L4〜L7 で **L3 を空き番号にしている**ため、
    そこへ「参照 id の実在」を割り当てた（L2 のパス実在と対になる検査）。
  * **L6 immutability** merge base に在る台帳エントリのバイト変更・削除を拒否する。
    訂正は新エントリ＋``supersedes`` で行う（履歴を書き換えない）。
  * **L7 canonical** パース→再シリアライズ→バイト比較。手編集・整形崩れを検出する。
  * **P1** 改訂案の状態遷移（``pending→approved→applied`` ／ ``pending→rejected`` ／
    ``*→superseded``）が merge base からの差分として妥当である。
  * **P2** ``approved`` に ``decided_by``/``decided_at``/``decided_in``、``rejected`` に
    ``decision_reason``、``applied`` に ``issue_ref``/``applied_pr`` が揃っている。
  * **P3** ``derived_from`` が非空でかつ実在する台帳エントリを指す。
  * **P4** ``routing`` が起票先の判定表（:mod:`feedback_ledger.routing`）と一致する。
  * **T1** 棚卸し記録の ``reviewed`` と ``outcomes[].entry`` の集合一致、参照の実在、
    verdict ごとの必須欄、id と期間（ISO 週）の一致、週の重複・欠落。

**git が無い／base ref を解決できない環境では L6・P1 を WARN で skip する**（ERROR にしない）。
ここを fail-close にすると、shallow clone や git 非依存の実行環境でビルドが必ず落ちる一方、
**検査できていないことは WARN として必ず出力される**ので黙って通ることはない。この非対称は
意図的な設計であり、既知の限界として ``feedback_ledger/README.md`` にも記載する。

依存仕様: Issue #522「lint 規則（check）」。
"""

from __future__ import annotations

import datetime
import shutil
import subprocess
from pathlib import Path

from . import routing as routing_module
from . import schema as schema_module
from .model import ERROR, WARN, Finding
from .paths import FeedbackPathError, resolve_within_repo
from .schema import SPECS
from .store import Store, canonical_text, load_store

LEDGER_PREFIX = ".ai/feedback/ledger/"
QUEUE_PREFIX = ".ai/feedback/queue/"

DEFAULT_BASE_REFS = ("origin/main", "main")

ALLOWED_TRANSITIONS = {
    ("pending", "pending"),
    ("pending", "approved"),
    ("pending", "rejected"),
    ("approved", "approved"),
    ("approved", "applied"),
    ("rejected", "rejected"),
    ("applied", "applied"),
    ("superseded", "superseded"),
}


def _git(root, *args) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(root),
        capture_output=True,
        text=False,
        shell=False,
        check=False,
    )


def resolve_base(root, base_ref) -> str | None:
    """比較対象のコミットを解決する。解決できなければ ``None``。"""
    if shutil.which("git") is None:
        return None
    candidates = (base_ref,) if base_ref else DEFAULT_BASE_REFS
    for candidate in candidates:
        completed = _git(root, "rev-parse", "--verify", "--quiet", f"{candidate}^{{commit}}")
        if completed.returncode != 0:
            continue
        head = _git(root, "merge-base", candidate, "HEAD")
        if head.returncode == 0 and head.stdout.strip():
            return head.stdout.decode("utf-8").strip()
        return completed.stdout.decode("utf-8").strip()
    return None


def _base_files(root, base: str, prefix: str) -> list[str]:
    completed = _git(root, "ls-tree", "-r", "--name-only", "-z", base, "--", prefix)
    if completed.returncode != 0:
        return []
    return [item.decode("utf-8") for item in completed.stdout.split(b"\0") if item]


def _base_blob(root, base: str, relpath: str) -> bytes | None:
    completed = _git(root, "show", f"{base}:{relpath}")
    if completed.returncode != 0:
        return None
    return completed.stdout


def check_paths_exist(store: Store) -> list[Finding]:
    """L2: 資産パスの実在。"""
    findings: list[Finding] = []
    targets = (
        (schema_module.LEDGER, "affected_assets"),
        (schema_module.PROPOSAL, "target_assets"),
    )
    for kind, key in targets:
        for document in store.of(kind):
            for candidate in document.data.get(key, []):
                where = f"{document.relpath}::{key}"
                try:
                    resolved = resolve_within_repo(candidate, store.root)
                except FeedbackPathError as exc:
                    findings.append(Finding("L2", ERROR, where, str(exc)))
                    continue
                if not resolved.exists():
                    findings.append(Finding(
                        "L2", ERROR, where,
                        f"実在しない資産パス: {candidate}",
                    ))
    return findings


def check_id_references(store: Store) -> list[Finding]:
    """L3: 文書 id 参照の実在（``supersedes`` / ``decided_in``）。"""
    findings: list[Finding] = []
    ledger_ids = store.ids(schema_module.LEDGER)
    triage_ids = store.ids(schema_module.TRIAGE)
    for document in store.of(schema_module.LEDGER):
        target = document.data.get("supersedes", "")
        if target and target not in ledger_ids:
            findings.append(Finding(
                "L3", ERROR, f"{document.relpath}::supersedes",
                f"実在しない台帳エントリを指している: {target}",
            ))
        if target and target == document.document_id:
            findings.append(Finding(
                "L3", ERROR, f"{document.relpath}::supersedes",
                "自分自身を supersedes にはできない",
            ))
    for document in store.of(schema_module.PROPOSAL):
        target = document.data.get("decided_in", "")
        if target and target not in triage_ids:
            findings.append(Finding(
                "L3", ERROR, f"{document.relpath}::decided_in",
                f"実在しない棚卸し記録を指している: {target}",
            ))
    return findings


def check_canonical(store: Store) -> list[Finding]:
    """L7: 保存されているバイト列が canonical 表現と一致する。"""
    findings: list[Finding] = []
    for kind, spec in SPECS.items():
        for document in store.of(kind):
            expected = canonical_text(spec, document.data)
            if document.text != expected:
                findings.append(Finding(
                    "L7", ERROR, document.relpath,
                    "canonical 表現と一致しない（手編集の疑い）。"
                    " 訂正は CLI（new-entry / amend-proposal / triage-close）で行う",
                ))
    return findings


def check_immutability(store: Store, base: str | None) -> list[Finding]:
    """L6: merge base に在る台帳エントリのバイト変更・削除を拒否する。"""
    if base is None:
        return [Finding(
            "L6", WARN, LEDGER_PREFIX,
            "比較対象（merge base）を解決できないため immutability を検査していない",
        )]
    findings: list[Finding] = []
    for relative in _base_files(store.root, base, LEDGER_PREFIX):
        if not relative.endswith(".toml"):
            continue
        original = _base_blob(store.root, base, relative)
        current_path = Path(store.root) / relative
        if not current_path.is_file():
            findings.append(Finding(
                "L6", ERROR, relative,
                "merge base に在る台帳エントリが削除されている"
                "（訂正は新エントリ＋supersedes で行う）",
            ))
            continue
        if original is not None and current_path.read_bytes() != original:
            findings.append(Finding(
                "L6", ERROR, relative,
                "merge base に在る台帳エントリが変更されている"
                "（台帳は追記のみ。訂正は新エントリ＋supersedes で行う）",
            ))
    return findings


def check_proposals(store: Store, base: str | None) -> list[Finding]:
    """P1〜P4。"""
    findings: list[Finding] = []
    ledger_ids = store.ids(schema_module.LEDGER)
    base_status = _base_proposal_statuses(store, base)
    if base is None:
        findings.append(Finding(
            "P1", WARN, QUEUE_PREFIX,
            "比較対象（merge base）を解決できないため状態遷移を検査していない",
        ))
    for document in store.of(schema_module.PROPOSAL):
        data = document.data
        status = data.get("status", "")
        where = document.relpath

        previous = base_status.get(document.relpath)
        if previous is not None and (previous, status) not in ALLOWED_TRANSITIONS:
            findings.append(Finding(
                "P1", ERROR, f"{where}::status",
                f"許可されていない状態遷移: {previous} → {status}",
            ))

        if status == "approved":
            for key in ("decided_by", "decided_at", "decided_in"):
                if not data.get(key):
                    findings.append(Finding(
                        "P2", ERROR, f"{where}::{key}",
                        "approved には承認者・承認日・承認した棚卸し記録が必要",
                    ))
        if status == "rejected" and not data.get("decision_reason"):
            findings.append(Finding(
                "P2", ERROR, f"{where}::decision_reason",
                "rejected には却下理由が必要（理由なき却下を記録に残さない）",
            ))
        if status == "applied":
            for key in ("issue_ref", "applied_pr"):
                if not data.get(key):
                    findings.append(Finding(
                        "P2", ERROR, f"{where}::{key}",
                        "applied には反映先の Issue 参照と PR 番号が必要",
                    ))

        derived = data.get("derived_from", [])
        if not derived:
            findings.append(Finding(
                "P3", ERROR, f"{where}::derived_from",
                "改訂案は必ず1件以上の台帳エントリから導出する",
            ))
        for entry_id in derived:
            if entry_id not in ledger_ids:
                findings.append(Finding(
                    "P3", ERROR, f"{where}::derived_from",
                    f"実在しない台帳エントリを指している: {entry_id}",
                ))

        expected, node_paths, issue_paths = routing_module.expected_routing(
            data.get("target_assets", [])
        )
        if expected is None and node_paths and issue_paths:
            findings.append(Finding(
                "P4", ERROR, f"{where}::routing",
                "起票先が異なる資産が混在している（node: "
                f"{', '.join(node_paths)} / issue: {', '.join(issue_paths)}）。"
                "改訂案を分割する",
            ))
        elif expected is not None and data.get("routing") != expected:
            findings.append(Finding(
                "P4", ERROR, f"{where}::routing",
                f"判定表では {expected} になる対象資産に routing={data.get('routing')!r} が"
                "設定されている（.claude/rules/02-decision-process.md「起票先はプロジェクト"
                "区分で決める」）",
            ))
    return findings


def _base_proposal_statuses(store: Store, base: str | None) -> dict:
    if base is None:
        return {}
    from .model import parse_toml  # 局所 import: 失敗しても check 全体は続行する

    statuses: dict[str, str] = {}
    for relative in _base_files(store.root, base, QUEUE_PREFIX):
        if not relative.endswith(".toml"):
            continue
        blob = _base_blob(store.root, base, relative)
        if blob is None:
            continue
        try:
            raw = parse_toml(blob.decode("utf-8"))
        except Exception:
            continue
        status = raw.get("status")
        if isinstance(status, str):
            statuses[relative] = status
    return statuses


def check_triage(store: Store) -> list[Finding]:
    """T1。"""
    findings: list[Finding] = []
    ledger_ids = store.ids(schema_module.LEDGER)
    proposal_ids = store.ids(schema_module.PROPOSAL)
    weeks: list[tuple[int, int, str]] = []

    for document in store.of(schema_module.TRIAGE):
        data = document.data
        where = document.relpath
        reviewed = set(data.get("reviewed", []))
        outcomes = data.get("outcomes", [])
        recorded = {item["entry"] for item in outcomes}
        if reviewed != recorded:
            missing = sorted(reviewed - recorded)
            extra = sorted(recorded - reviewed)
            findings.append(Finding(
                "T1", ERROR, f"{where}::reviewed",
                "reviewed と outcomes[].entry の集合が一致しない"
                f"（outcomes 欠落: {missing or 'なし'} / reviewed 欠落: {extra or 'なし'}）",
            ))
        if len(recorded) != len(outcomes):
            findings.append(Finding(
                "T1", ERROR, f"{where}::outcomes",
                "同じ台帳エントリに対する outcomes が重複している",
            ))
        for entry_id in sorted(reviewed):
            if entry_id not in ledger_ids:
                findings.append(Finding(
                    "T1", ERROR, f"{where}::reviewed",
                    f"実在しない台帳エントリを指している: {entry_id}",
                ))
        for item in outcomes:
            verdict = item.get("verdict", "")
            locus = f"{where}::outcomes[{item.get('entry', '')}]"
            if verdict == "proposed":
                if not item.get("proposal"):
                    findings.append(Finding(
                        "T1", ERROR, locus, "verdict=proposed には proposal が必要"))
                elif item["proposal"] not in proposal_ids:
                    findings.append(Finding(
                        "T1", ERROR, locus,
                        f"実在しない改訂案を指している: {item['proposal']}"))
            elif verdict == "merged-into":
                if not item.get("merged_into"):
                    findings.append(Finding(
                        "T1", ERROR, locus, "verdict=merged-into には merged_into が必要"))
                elif item["merged_into"] not in ledger_ids:
                    findings.append(Finding(
                        "T1", ERROR, locus,
                        f"実在しない台帳エントリを指している: {item['merged_into']}"))
            elif verdict in ("no-change", "need-more-evidence") and not item.get("reason"):
                findings.append(Finding(
                    "T1", ERROR, locus, f"verdict={verdict} には reason が必要"))

        match = schema_module.TRIAGE_ID_RE.match(data.get("id", ""))
        if match:
            year = int(match.group("year"))
            week = int(match.group("week"))
            try:
                start = datetime.date.fromisocalendar(year, week, 1)
                end = datetime.date.fromisocalendar(year, week, 7)
            except ValueError:
                findings.append(Finding(
                    "T1", ERROR, f"{where}::id",
                    f"実在しない ISO 週: {year}-W{week:02d}"))
            else:
                weeks.append((year, week, where))
                if data.get("period_start") != start or data.get("period_end") != end:
                    findings.append(Finding(
                        "T1", ERROR, f"{where}::period_start",
                        f"id の ISO 週と期間が一致しない（期待: {start} 〜 {end}）",
                    ))

    findings.extend(_week_gaps(weeks))
    return findings


def _week_gaps(weeks) -> list[Finding]:
    """週の重複・欠落。欠落は WARN（棚卸しを飛ばした事実は記録に残すが CI は止めない）。"""
    findings: list[Finding] = []
    seen: dict[tuple[int, int], str] = {}
    for year, week, where in weeks:
        key = (year, week)
        if key in seen:
            findings.append(Finding(
                "T1", ERROR, where,
                f"同じ ISO 週の棚卸し記録が重複している: {seen[key]}",
            ))
        seen[key] = where
    if len(seen) < 2:
        return findings
    mondays = sorted(datetime.date.fromisocalendar(year, week, 1) for year, week in seen)
    present = set(mondays)
    cursor = mondays[0] + datetime.timedelta(days=7)
    while cursor < mondays[-1]:
        if cursor not in present:
            iso = cursor.isocalendar()
            findings.append(Finding(
                "T1", WARN, ".ai/feedback/triage",
                f"棚卸し記録が無い週がある: TRG-{iso[0]:04d}-W{iso[1]:02d}",
            ))
        cursor += datetime.timedelta(days=7)
    return findings


def run_checks(root, *, canonical: bool = False, base_ref: str | None = None) -> list[Finding]:
    """全規則を実行して findings を返す（表示・終了コードは CLI 側）。"""
    store = load_store(root)
    base = resolve_base(root, base_ref)
    findings = list(store.findings)
    findings.extend(check_paths_exist(store))
    findings.extend(check_id_references(store))
    findings.extend(check_immutability(store, base))
    findings.extend(check_proposals(store, base))
    findings.extend(check_triage(store))
    if canonical:
        findings.extend(check_canonical(store))
    return findings
