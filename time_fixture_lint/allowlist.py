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
)


def is_allowlisted(path: str, name: str) -> AllowlistEntry | None:
    """(path, name) に一致する allowlist entry があれば返す（大小文字は無視）。"""
    lname = name.lower()
    for entry in ALLOWLIST:
        if entry.path == path and entry.name.lower() == lname:
            return entry
    return None
