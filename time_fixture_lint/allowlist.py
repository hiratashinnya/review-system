"""既知の inert 誤検出のための allowlist（Issue #344）。

:mod:`time_fixture_lint.scanner` が「wall clock と比較されうる形のフィールド名」
（``expires_at``/``resetsAt`` 等・詳細は scanner のモジュール docstring）にヒットしても、
実際には固定ペア同士の比較や純粋関数への静的パラメータで real wall clock を一切読まない
inert なケースがある（例: `.codex/hooks/codex-rate-limit-query.py` から実キャプチャした
API レスポンスをそのまま埋め込んだ test fixture）。

こうした誤検出は本ファイルに **(path, name) の組 + 理由** で明記して抑制する
（`asset_parity/exceptions.py` と同じ「消さず理由を残す」運用。新規に inert 判定を
追加するときは、なぜ real clock に触れないかを一次情報＝該当コードの参照とともに書く）。

抑制は per-line ではなく **ファイル内の同名ヒット全部** に効く（同じ定数・同じ dict キーが
複数の assertion で繰り返されるテストで、行ごとに同一エントリを重複登録させないため）。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AllowlistEntry:
    path: str  # repo-root からの相対パス（posix 区切り）
    name: str  # 検出されたフィールド名 / 定数名（大文字小文字区別しない）
    reason: str


ALLOWLIST: tuple[AllowlistEntry, ...] = (
    AllowlistEntry(
        path="tests/unit/test_codex_rate_limit_api.py",
        name="resetsAt",
        reason=(
            "codex app-server の account/rateLimits/read を実キャプチャした静的レスポンス辞書"
            "（REAL_IDLE_RESULT 等）のフィールド。消費先の QMOD.summarize_rate_limits(response, now) は"
            "呼び出し側から now を明示的に受け取る純粋関数で、内部で time.time()/datetime.now() を"
            "一切読まない（#302 で time.time() 相対化された QueryHelperProcessTests の"
            "future_epoch/past_epoch とは別クラスの test data）。"
        ),
    ),
    AllowlistEntry(
        path="tests/unit/test_codex_rate_limit_api.py",
        name="NOW",
        reason=(
            "上記 resetsAt と対になる固定 now 引数。summarize_rate_limits へのパラメータとして"
            "渡されるだけで、real wall clock を読む経路には一切乗らない自己完結ペア。"
        ),
    ),
    AllowlistEntry(
        path="tests/fixtures/blocker_gate/schema_only_waiver.yml",
        name="approved_at",
        reason=(
            "WaiverParserTests（test_blocker_gate_waiver.py）が parse_waiver_yaml() の"
            "schema 解析のみを検証するために使う fixture（#349・F-344-01 是正で"
            "waiver_valid.yml から分離）。parse_waiver_yaml は文字列をそのまま返すだけで"
            "verify_waiver（blocker_gate/waiver.py:301 の approved <= now < expires という"
            "wall clock 比較）を一切呼ばないため、値は不透明な文字列のまま扱われ real clock"
            "に触れる経路が無い。wall clock 比較を実際に行うテストは waiver_valid.yml を"
            "使う WaiverVerifierTests（setUp で now= 注入により保護済み）。"
        ),
    ),
    AllowlistEntry(
        path="tests/fixtures/blocker_gate/schema_only_waiver.yml",
        name="expires_at",
        reason=(
            "上記 approved_at と同じ fixture・同じ理由（parse_waiver_yaml の schema 解析のみ"
            "で消費され、verify_waiver の wall clock 比較には一切乗らない）。"
        ),
    ),
    AllowlistEntry(
        path="tests/fixtures/blocker_gate/waiver_unknown_key.yml",
        name="approved_at",
        reason=(
            "test_blocker_gate_waiver.py::WaiverParserTests."
            "test_unknown_key_and_duplicate_key_are_schema_error が parse_waiver_yaml() の"
            "スキーマ拒否（未知キー）だけを検証するために使う fixture。parse_waiver_yaml は"
            "wall clock を一切読まないため verify_waiver の比較経路に乗らない（schema_only_waiver.yml"
            "の approved_at/expires_at と同じ理由）。"
        ),
    ),
    AllowlistEntry(
        path="tests/fixtures/blocker_gate/waiver_unknown_key.yml",
        name="expires_at",
        reason=(
            "上記 approved_at と同じ fixture・同じ理由（schema 拒否テストのみで消費され、"
            "verify_waiver の wall clock 比較には一切乗らない）。"
        ),
    ),
    AllowlistEntry(
        path="tests/unit/test_blocker_snapshot_fallback.py",
        name="resetAt",
        reason=(
            "GraphQL `rateLimit{cost remaining resetAt}` の実消費を測る telemetry テスト"
            "（#359・F-345-04）が使う固定レスポンス値。`resetAt` は"
            "blocker_gate/github.py::GitHubCollector._accumulate_rate_limit が文字列のまま"
            "`usage['reset_at']` へ写すだけで、判定にも snapshot 内容にも入らず、"
            "blocker_gate/cli.py の stderr 要約へ echo されて終わる（wall clock と比較する"
            "コードが経路上に存在しない）。期限として評価されないので、時間経過で"
            "比較結果が反転する方向が無い。"
        ),
    ),
    AllowlistEntry(
        path="tests/unit/test_blocker_snapshot_fallback.py",
        name="reset_at",
        reason=(
            "上記 resetAt が `_accumulate_rate_limit` を通って `last_rate_limit` に載った"
            "後の同じ値（snake_case 側）。同じ理由で inert（stderr へ echo されるだけで"
            "wall clock と比較されない）。"
        ),
    ),
)


def is_allowlisted(path: str, name: str) -> AllowlistEntry | None:
    """(path, name) に一致する allowlist entry があれば返す（大小文字は無視）。"""
    lname = name.lower()
    for entry in ALLOWLIST:
        if entry.path == path and entry.name.lower() == lname:
            return entry
    return None
