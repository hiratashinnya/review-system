"""``karte status`` 判定の通知要否を決める純粋ロジック（Issue #512）。

背景（詳細は GitHub Issue #512 本文「現状と根拠」）:
  PR #509（Issue #431）で、``karte status`` が ``escalate: yes``（無進捗・飽和したアプローチ）を
  出していたにもかかわらず、主文脈がそれを「原因が分かっているから問題ない」と自ら判断して
  オーナーへの報告を歪めた実例がある。Issue #379 が確立した規範
  「PR コメント・カルテ・ノードは永続化目的の副次記録であり、そこに書いたことをもって
  オーナーへの報告済みとはみなさない」に照らせば、機械判定の到達点は**オーナーのチャット**
  でなければならず、AI のコンテキスト（``additionalContext``）へ注入するだけでは同じ歪みの
  経路が残る（Issue #310 の当初設計はこれであり、本 Issue が対応 AC を移譲した理由）。

役割分担: 本モジュールは「**何を・いつ通知するか**」の決定と既読スナップショットの
パス解決／読み書きだけを担う。``karte status --json`` の起動・``systemMessage`` としての
出力は :mod:`karte_notify.hook` に置く（``issue_start.subagent_hooks`` が
「薄い起動口＋判定 python モジュール」で分離しているのと同じ構成）。

既読管理（finding ID 単位）:
  毎回全件を通知すると、解消済み finding が繰り返し表示されノイズになり、フック自体が
  無視されるようになる（Issue #461「異常が無いときは完全に沈黙する」）。一方 ``open`` の
  まま放置されている finding を「変化が無い」という理由で黙らせると、放置を握りつぶす経路を
  新設することになる（本 Issue が塞ごうとしている問題と同型）。したがって沈黙させるのは
  **``resolved`` 済みで通知済みのものだけ**とする（:func:`decide`）。

  判定表（finding ID 単位。詳細は Issue #512 本文「通知条件」）:
    * 現在 ``open``                                → 常に載せる（変化の有無を問わない）。
    * 現在 ``resolved``・前回 ``open`` または未通知  → 載せる（この遷移だけ 1 回）。
    * 現在 ``resolved``・前回も ``resolved``         → 載せない。
  全体状態（``verdict``/``escalate``）:
    * 載せる finding が 1 件以上ある → ヘッダとして ``verdict``/``escalate`` を添える。
    * 載せる finding が 0 件でも ``verdict``/``escalate`` が前回通知時から変化していれば、
      その変化だけを載せる。
    * どちらも無ければメッセージ自体を出さない。
    * ``escalate: yes`` が継続している間は毎回載せる（継続＝未解決の放置であり、
      ``open`` finding と同じ扱い。実際には escalate の原因＝無進捗/飽和はいずれも open
      finding に紐づくため rule 1 で既に載る想定だが、取りこぼしが無いよう独立に強制する）。
    * スナップショット未作成（初回）はこの判定を経ず必ず通知する
      （Issue #512 Acceptance criteria「初回は全件出ること」）。

既読スナップショットの置き場（``tmp/_karte/notified/issue-<N>.json``）は ``tmp/_karte/`` 配下
であり、``dsv2 clean-tmp`` の保護対象（``dsv2/cleantmp.py`` の ``PROTECTED_DIRNAMES``＝
``_handoff``/``_karte``/``_worktree``）に既に入っている——``_karte`` を構成要素に含むパスは
掃除対象から機械的に除外される。

検出対象コマンドの拾い方（is 再発防止・Issue #512 是正・F-512-02）:
  トリガー実行は ``Bash`` 経由とは限らない。主文脈・``issue-implementer``・``issue-fixer``・
  ``pr-reviewer``・``dsv2-lookup`` にはいずれも実行系 MCP ツール（``ctx_execute``・
  ``ctx_batch_execute``）が付与済みで（`.claude/rules/05-skills-agents.md`「ctx_* ツールの
  付与方針」）、``python3 -m karte ingest-review``/``close-attempt`` はこれらの ``tool_input``
  （``code`` / ``commands[].command``）経由でも実行されうる。したがって :func:`extract_commands`
  は ``tool_name`` ごとに検査対象の文字列を取り出し、:func:`detect_trigger` はその文字列単位で
  ``Bash`` と同じ正規表現を適用する（判定ロジック自体は分岐させない＝経路が増えても検出規則は
  一本のまま）。

通知本文の内容（Issue #512 是正・F-512-03）:
  本文には finding ID 単位の既読管理を経た一覧に加え、``verdict`` の3集合
  （``blocking_findings`` ⊇ ``blocking_harmful`` ⊇ ``undecided_disposition``・
  PR #496 F-495-07）と、``escalate: yes`` のときはその根拠（``stalled_findings``・
  ``saturated_groups``）を含める（:func:`_render_message`）。``escalate`` の真偽だけでは
  PR #509／Issue #431 の実例（無進捗 F-431-07・飽和 Attempt 3,5）を本文から再現できず、
  「エスカレーション条件の生の判定が届いている」という主張の裏付けにならないため。

依存仕様: GitHub Issue #512／``karte/paths.py`` のパスガード様式／``karte/cli.py``
``_status_payload`` の出力スキーマ（``issue``/``verdict``/``escalate``/``blocking_findings``/
``blocking_harmful``/``undecided_disposition``/``stalled_findings``/``saturated_groups``/
``findings[].{id,status}``）。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from karte import model as karte_model
from karte import paths as karte_paths

# `karte ingest-review` / `karte close-attempt` の実行を検出する（Issue #512 Scope 1）。
# `-m karte` 経由の module 起動だけを見る（`karte` package の CLI 契約そのものなので、
# エイリアス・別実行形は対象外＝取りこぼしても fail-open で実害が小さい方に倒す）。
TRIGGER_RE = re.compile(r"\bpython3?\s+-m\s+karte\s+(ingest-review|close-attempt)\b")
ISSUE_ARG_RE = re.compile(r"--issue[=\s]+([0-9]+)")

NOTIFIED_DIRNAME = "notified"

# 本フックが検出対象とする tool_name（Issue #512 是正・F-512-02）。`Bash` に加え、
# `.claude/rules/05-skills-agents.md`「ctx_* ツールの付与方針」で issue-implementer /
# issue-fixer / pr-reviewer / 主文脈 / dsv2-lookup に付与済みの実行系 MCP ツール
# （`ctx_execute`/`ctx_batch_execute`）経由の `karte ingest-review`/`close-attempt` 実行も
# 同じ通知対象にする。`ctx_execute_file` は既存方針で全ロール未付与のため対象に含めない
# （`.claude/rules/05-skills-agents.md` 同節）。
SUPPORTED_TOOL_NAMES = (
    "Bash",
    "mcp__plugin_context-mode_context-mode__ctx_execute",
    "mcp__plugin_context-mode_context-mode__ctx_batch_execute",
)


def detect_trigger(command: str) -> str | None:
    """``command`` が ``karte ingest-review``/``close-attempt`` の実行なら verb 名を返す。"""
    match = TRIGGER_RE.search(command)
    return match.group(1) if match else None


def extract_commands(tool_name: str, tool_input: Mapping[str, Any]) -> list[str]:
    """``tool_name``/``tool_input`` から検査対象のコマンド文字列を取り出す（Issue #512 F-512-02）。

    ``Bash`` は ``tool_input.command``。``ctx_execute`` は ``tool_input.code``
    （``language: shell`` 前提の呼び出し規約だが、ここでは ``language`` の真偽は検査しない
    ——実行される文字列そのものを見れば検出には十分で、詐称されていても検出漏れ側には
    倒れない）。``ctx_batch_execute`` は ``tool_input.commands[].command`` の全件を対象にし、
    どれか1件が一致すれば検出する。``tool_name`` が対象外、または形が不正なら空リスト
    （呼び出し側はこれを「検出なし」として扱う＝fail-open）。
    """
    if tool_name == "Bash":
        command = tool_input.get("command")
        return [command] if isinstance(command, str) else []
    if tool_name == "mcp__plugin_context-mode_context-mode__ctx_execute":
        code = tool_input.get("code")
        return [code] if isinstance(code, str) else []
    if tool_name == "mcp__plugin_context-mode_context-mode__ctx_batch_execute":
        commands = tool_input.get("commands")
        result: list[str] = []
        if isinstance(commands, list):
            for item in commands:
                if isinstance(item, Mapping):
                    command = item.get("command")
                    if isinstance(command, str):
                        result.append(command)
        return result
    return []


def issue_from_command(command: str) -> int | None:
    """``--issue N`` を ``command`` からベストエフォートで取り出す（無ければ ``None``）。

    見つからない／不正な形式なら ``None``——呼び出し側は進行ポインタ
    （``tmp/_karte/active.json``）へのフォールバックを別途持つ（``karte status`` 自身の
    ``--issue`` 省略時の補完と同じ扱い）。
    """
    match = ISSUE_ARG_RE.search(command)
    if not match:
        return None
    try:
        return karte_paths.validate_issue(match.group(1))
    except karte_paths.KartePathError:
        return None


def _notified_dir(repo_root: Path, *, create: bool) -> Path:
    base = karte_paths.karte_dir(repo_root, create=create)
    target = base / NOTIFIED_DIRNAME
    if target.is_symlink():
        raise karte_paths.KartePathError(f"通知既読置き場が symlink: {target}")
    if not target.exists():
        if not create:
            raise karte_paths.KarteMissing(f"通知既読置き場が無い: {target}")
        target.mkdir(parents=True)
    if not target.is_dir():
        raise karte_paths.KartePathError(f"通知既読置き場がディレクトリでない: {target}")
    return target


def notified_snapshot_path(repo_root: Path, issue: int, *, create_dir: bool = False) -> Path:
    """``<repo-root>/tmp/_karte/notified/issue-<N>.json`` を返す。

    ``karte/paths.py`` の既存ガード（``karte_dir``＝``tmp``/``_karte`` の symlink・型検査）に
    ``notified`` サブディレクトリ・ファイル自身の symlink 検査を重ねる（同じ様式）。
    """
    number = karte_paths.validate_issue(issue)
    directory = _notified_dir(repo_root, create=create_dir)
    path = directory / f"issue-{number}.json"
    if path.is_symlink():
        raise karte_paths.KartePathError(f"通知既読スナップショットが symlink: {path}")
    return path


def read_snapshot(path: Path) -> dict | None:
    """既読スナップショットを読む。無い／壊れていれば ``None``（＝初回・fail-open）。"""
    if path.is_symlink() or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_snapshot(path: Path, snapshot: Mapping[str, Any]) -> None:
    """既読スナップショットを原子的に書く（``karte.paths.write_text_atomic`` を再利用）。"""
    karte_paths.write_text_atomic(
        path, json.dumps(snapshot, ensure_ascii=False, sort_keys=True) + "\n"
    )


def _findings_status_map(payload: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in payload.get("findings", []) or []:
        if isinstance(item, Mapping):
            fid = item.get("id")
            status = item.get("status")
            if isinstance(fid, str) and isinstance(status, str):
                result[fid] = status
    return result


def _sort_key(finding_id: str):
    try:
        return karte_model.parse_finding_id(finding_id)
    except karte_model.KarteFormatError:
        return (0, finding_id)


def decide(payload: Mapping[str, Any], previous: Mapping[str, Any] | None) -> tuple[str | None, dict]:
    """通知本文（無ければ ``None``）と、次回の既読スナップショットを返す。

    ``payload`` は ``karte status --json`` の出力（``karte/cli.py::_status_payload``）。
    ``previous`` は :func:`read_snapshot` の戻り値（``None``＝スナップショット未作成＝初回）。
    """
    first_run = previous is None
    current_findings = _findings_status_map(payload)
    prev_findings: dict[str, Any] = {}
    prev_verdict: Any = None
    prev_escalate: Any = None
    if previous is not None:
        raw = previous.get("findings")
        if isinstance(raw, dict):
            prev_findings = raw
        prev_verdict = previous.get("verdict")
        prev_escalate = previous.get("escalate")

    shown: list[str] = []
    for fid in sorted(current_findings, key=_sort_key):
        current_status = current_findings[fid]
        prior_status = prev_findings.get(fid)
        if current_status == "open":
            shown.append(fid)
        elif current_status == "resolved" and prior_status != "resolved":
            shown.append(fid)
        # resolved かつ前回も resolved → 載せない（既読）。

    current_verdict = payload.get("verdict")
    current_escalate = bool(payload.get("escalate"))
    verdict_changed = current_verdict != prev_verdict
    escalate_changed = current_escalate != prev_escalate

    notify = (
        first_run
        or bool(shown)
        or verdict_changed
        or escalate_changed
        or current_escalate
    )

    snapshot = {
        "issue": payload.get("issue"),
        "findings": current_findings,
        "verdict": current_verdict,
        "escalate": current_escalate,
    }

    if not notify:
        return None, snapshot

    message = _render_message(
        payload,
        shown_ids=shown,
        verdict_changed=verdict_changed,
        escalate_changed=escalate_changed,
        first_run=first_run,
    )
    return message, snapshot


def _ids_line(label: str, ids: Any) -> str:
    values = [str(item) for item in ids] if isinstance(ids, list) else []
    return f"{label}: {', '.join(values) if values else '(なし)'}"


def _render_saturated(groups: Any) -> str:
    if not isinstance(groups, list) or not groups:
        return "(なし)"
    rendered = []
    for group in groups:
        if isinstance(group, list):
            rendered.append(", ".join(str(item) for item in group))
        else:
            rendered.append(str(group))
    return "; ".join(rendered)


def _render_message(
    payload: Mapping[str, Any],
    *,
    shown_ids: list[str],
    verdict_changed: bool,
    escalate_changed: bool,
    first_run: bool,
) -> str:
    issue = payload.get("issue")
    verdict = payload.get("verdict")
    escalate = bool(payload.get("escalate"))
    lines = [f"[karte status] issue-{issue}（AI の要約を経ない機械判定の直送・Issue #512）"]
    if first_run:
        lines.append("（初回通知：既読スナップショット未作成のため全件を表示）")
    lines.append(f"verdict: {verdict}")
    # PR #496 F-495-07 の3集合を包含関係の順に添える（`karte status` 本文と同じ様式・
    # Issue #512 F-512-03：verdict の真偽だけでなく内訳を通知本文自体に持たせる）。
    lines.append(_ids_line("  clean を妨げる未解消", payload.get("blocking_findings")))
    lines.append(_ids_line("  clean を妨げる実害あり", payload.get("blocking_harmful")))
    lines.append(_ids_line("  実害あり・disposition 未決定", payload.get("undecided_disposition")))
    lines.append(f"escalate: {'yes' if escalate else 'no'}")
    if escalate:
        # escalate: yes を成立させた当の根拠（無進捗・飽和したアプローチ）を本文へ含める
        # （Issue #512 F-512-03：escalate の真偽だけでは PR #509／Issue #431 の実例
        # ＝無進捗 F-431-07／飽和 Attempt 3,5 のような具体を再現できない）。
        lines.append(_ids_line("  無進捗（stalled）", payload.get("stalled_findings")))
        lines.append(
            f"  飽和したアプローチ（saturated）: {_render_saturated(payload.get('saturated_groups'))}"
        )

    findings_by_id = {
        item.get("id"): item
        for item in payload.get("findings", []) or []
        if isinstance(item, Mapping)
    }
    if shown_ids:
        lines.append("")
        lines.append("finding（open は毎回・resolved への遷移は 1 回だけ表示）:")
        for fid in shown_ids:
            item = findings_by_id.get(fid, {})
            disposition = item.get("disposition") or "未決定"
            lines.append(
                f"  - {fid} [{item.get('status')}] [harm={item.get('harm')}] "
                f"[disposition={disposition}]: {item.get('summary')}"
            )
    elif not first_run:
        changed = []
        if verdict_changed:
            changed.append("verdict")
        if escalate_changed:
            changed.append("escalate")
        if not changed and escalate:
            changed.append("escalate（継続）")
        lines.append(f"（{'/'.join(changed) or '状態'} の変化のみ。個別 finding の変化なし）")
    return "\n".join(lines)
