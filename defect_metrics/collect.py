"""計測入力の取得と解釈（Issue #488）。

入力は2系統ある。

* ``gh`` CLI から取得する（既定・GitHub Actions 上の運用経路）。
  ``gh issue list --state all`` は PR を含まないため、Issue と PR の取り違えが起きない。
* 既に保存された ``gh ... --json`` 出力（JSON 配列）を読む（``--issues-json`` /
  ``--pulls-json``）。再現検証と単体テストがネットワーク・認証に依存しないようにするため。

どちらの経路でも :func:`load_issues` / :func:`load_pulls` が同じ形へ正規化する。

取得件数の打ち切りは致命エラーにする
------------------------------------
``gh ... list --limit N`` は **新しい方から N 件** を返して打ち切る。全件が N を超えると
古い側が黙って落ちるため、まず基線窓（過去の固定窓）の再現が壊れ、次に
:func:`defect_metrics.metrics.is_derived` の参照先 PR 辞書が欠ける。``gh`` 自身は成功終了し
JSON も正当なので、この欠落は :func:`load_issues` / :func:`load_pulls` のスキーマ検査には
掛からない——**レポートは正常な体裁のまま誤った数字を載せる**。そこで
:func:`_ensure_not_truncated` が「取得件数が ``--limit`` に達した」時点で
:class:`CollectionError` を送出し、``.github/workflows/defect-metrics.yml`` が宣言する
fail-close（generator が exit 1 で止まり publish しない）へ乗せる。
``--limit`` を上げるだけでは同じ穴を先送りするだけなので、既定値の引き上げではなく検出で扱う。
"""

from __future__ import annotations

import json
import subprocess

from .model import IssueRecord, PullRequestRecord, parse_timestamp

#: ``gh ... list --limit`` の既定。本 repository の全件（Issue 246 / merged PR 228・
#: 2026-09-06 時点）に対し十分な余裕を取る。窓で絞る前の全件が必要な理由は
#: :func:`defect_metrics.metrics.is_derived`（窓外 PR も参照先になりうる）を参照。
DEFAULT_FETCH_LIMIT = 2000

ISSUE_FIELDS = "number,createdAt,closedAt,body"
PULL_FIELDS = "number,mergedAt"


class CollectionError(RuntimeError):
    """入力の取得・解釈に失敗した（レポートを作れない致命エラー）。"""


def _optional_timestamp(value: object) -> "None | object":
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise CollectionError(f"タイムスタンプが文字列ではない: {value!r}")
    return parse_timestamp(value)


def load_issues(payload: object) -> list[IssueRecord]:
    """``gh issue list --json number,createdAt,closedAt,body`` 相当の配列を正規化する。"""
    if not isinstance(payload, list):
        raise CollectionError("issue payload が JSON 配列ではない")
    records: list[IssueRecord] = []
    for entry in payload:
        if not isinstance(entry, dict):
            raise CollectionError(f"issue entry が object ではない: {entry!r}")
        try:
            number = int(entry["number"])
            created_raw = entry["createdAt"]
        except (KeyError, TypeError, ValueError) as exc:
            raise CollectionError(f"issue entry に number/createdAt が無い: {entry!r}") from exc
        if not isinstance(created_raw, str):
            raise CollectionError(f"issue {number} の createdAt が文字列ではない")
        records.append(
            IssueRecord(
                number=number,
                created_at=parse_timestamp(created_raw),
                closed_at=_optional_timestamp(entry.get("closedAt")),  # type: ignore[arg-type]
                body=entry.get("body") or "",
            )
        )
    return records


def load_pulls(payload: object) -> list[PullRequestRecord]:
    """``gh pr list --state merged --json number,mergedAt`` 相当の配列を正規化する。

    ``mergedAt`` が空の行（merge されていない PR が混ざった場合）は無視する——
    分母は「merge された PR」であり、未 merge を数えると定義がぶれるため。
    """
    if not isinstance(payload, list):
        raise CollectionError("pull request payload が JSON 配列ではない")
    records: list[PullRequestRecord] = []
    for entry in payload:
        if not isinstance(entry, dict):
            raise CollectionError(f"pull request entry が object ではない: {entry!r}")
        merged_raw = entry.get("mergedAt")
        if merged_raw in (None, ""):
            continue
        try:
            number = int(entry["number"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CollectionError(f"pull request entry に number が無い: {entry!r}") from exc
        if not isinstance(merged_raw, str):
            raise CollectionError(f"PR {number} の mergedAt が文字列ではない")
        records.append(PullRequestRecord(number=number, merged_at=parse_timestamp(merged_raw)))
    return records


def read_json_file(path: str) -> object:
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except OSError as exc:
        raise CollectionError(f"{path} を読めない: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise CollectionError(f"{path} が JSON として壊れている: {exc}") from exc


def _run_gh(args: list[str]) -> object:
    try:
        completed = subprocess.run(
            ["gh", *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:  # gh 未導入の環境
        raise CollectionError("gh CLI が見つからない（GitHub Actions では既定で導入済み）") from exc
    if completed.returncode != 0:
        raise CollectionError(
            f"`gh {' '.join(args)}` が exit {completed.returncode}: {completed.stderr.strip()}"
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise CollectionError(f"`gh {' '.join(args)}` の出力が JSON ではない: {exc}") from exc


def _ensure_not_truncated(kind: str, payload: object, limit: int) -> None:
    """取得件数が ``--limit`` に達していたら :class:`CollectionError` にする。

    ちょうど ``limit`` 件のときは「全件がたまたま ``limit`` 件」なのか「打ち切られた」のかを
    区別できない。区別できない側は**打ち切り扱い**にする（誤った数字を publish するより、
    レポートを作らずに止まる方が安全＝fail-close）。
    """
    if isinstance(payload, list) and len(payload) >= limit:
        raise CollectionError(
            f"{kind} の取得件数が --limit ({limit}) に達した。"
            "`gh ... list` は新しい側から打ち切るため古い側が黙って落ち、基線窓の再現も"
            "派生判定の参照先 PR も誤る。--limit を十分大きい値へ上げて再実行すること"
            "（誤った数字を publish しないための fail-close）。"
        )


def fetch_issues(repository: str, limit: int = DEFAULT_FETCH_LIMIT) -> list[IssueRecord]:
    payload = _run_gh(
        [
            "issue",
            "list",
            "--repo",
            repository,
            "--state",
            "all",
            "--limit",
            str(limit),
            "--json",
            ISSUE_FIELDS,
        ]
    )
    _ensure_not_truncated("issue", payload, limit)
    return load_issues(payload)


def fetch_pulls(repository: str, limit: int = DEFAULT_FETCH_LIMIT) -> list[PullRequestRecord]:
    payload = _run_gh(
        [
            "pr",
            "list",
            "--repo",
            repository,
            "--state",
            "merged",
            "--limit",
            str(limit),
            "--json",
            PULL_FIELDS,
        ]
    )
    # 打ち切り判定は正規化前の生 payload で行う（load_pulls は未 merge 行を落とすため、
    # 正規化後の件数で比べると打ち切りを見逃す）。
    _ensure_not_truncated("pull request", payload, limit)
    return load_pulls(payload)
