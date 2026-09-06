"""欠陥混入率指標のデータモデルと**コードに固定した指標定義**（Issue #488）。

なぜ定義をコードへ固定するのか
------------------------------
Issue #368 は基線を「2026-08-01〜08-16 の実測・15日・PR 1本あたり 1.86」と散文で
記していたが、2026-09-06 の再計測で **1.86 を再現する窓は
``2026-08-02T00:00Z <= t < 2026-08-16T00:00Z``（14日）に一意に定まる**ことが判明した
（08-01 起点なら 2.38、08-16 を含めると 2.62）。定義が散文にある限り、窓の起点・
境界の開閉・分子の数え方が読み手ごとにずれ、同じズレが再計測のたびに再発する。
本モジュールは窓の境界条件（半開区間）・分母・分子・派生判定の地平線を**定数と型**
として固定し、散文への依存を断つ。

固定した定義（Issue #488「提案挙動」1.）
---------------------------------------
* **窓**: ``lo <= t < hi`` の半開区間・UTC（:class:`Window`）。閉区間にすると
  隣接窓が境界の1点を二重計上する。
* **分母**: 窓内に merge された PR 数（``mergedAt`` が窓に入るもの）。
* **分子（主指標）**: 窓内に作成された Issue のうち、本文が参照する ``#N`` に
  「その Issue の起票時刻から遡って :data:`DERIVATION_HORIZON` 以内に merge された
  PR」が1つ以上含まれるもの＝**派生 Issue**。
* **分子（副指標）**: 窓内に作成された全 Issue 数。起票粒度の変化に汚染されるため
  主指標と対で出す（Issue #488「現状と根拠」＝直近窓の改善が対策由来か起票粒度の
  変化かを分離できるようにする）。
* **open Issue 純増**: 窓内作成 − 窓内 close。

参照値（Issue #488「現状と根拠」の実測表）
-----------------------------------------
基線窓 ``2026-08-02 〜 08-16``: merged PR 22 / 全 Issue 41 / 全 Issue/PR 1.86 /
派生 Issue 15 / 派生/PR 0.68。:data:`BASELINE_WINDOW` と :data:`BASELINE_DERIVED_PER_PR`
はこの実測値であり、閾値判定（:mod:`defect_metrics.threshold`）の基線でもある。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

#: publish する JSON レポートのスキーマ版（読取側の互換判定用）。
#: 本 PR（Issue #488）で新設した初版であり、同 PR 内のレビュー是正で
#: ``baseline_verification`` / ``trailing_4_weeks.aggregation`` を追加した際も **1 のまま
#: 据え置く**——未 merge の初版がまだ確定していない途中であり、是正だけを理由に版を
#: もう一度動かさない（`.ai/guidance/common.md`「正本・実装規約」）。
SCHEMA_VERSION = 1

#: 派生 Issue と判定する地平線。Issue 起票時刻から遡ってこの時間内に merge された
#: PR を本文が参照していれば「その PR に由来する欠陥の起票」とみなす（Issue #488）。
DERIVATION_HORIZON = timedelta(hours=72)

#: 既定のレポート窓幅（週次 publish に合わせる）。
DEFAULT_REPORT_WINDOW = timedelta(days=7)

#: 「直近4週平均」の比較窓幅。レポート窓の直前に接続する28日間を指す。
TRAILING_WINDOW = timedelta(days=28)

#: 「直近4週平均から 50% 以上悪化」の判定係数（current >= trailing * 1.5）。
REGRESSION_FACTOR = 1.5

#: 表示用の丸め桁数。閾値判定は丸め前の厳密値で行う（丸めで判定が動かないように）。
RATIO_DIGITS = 2


def parse_timestamp(text: str) -> datetime:
    """ISO8601 文字列を UTC の aware datetime にする。

    ``2026-08-02`` のような日付のみの指定は ``2026-08-02T00:00:00Z`` として扱う。
    末尾 ``Z`` は :func:`datetime.fromisoformat` の古い実装が扱えないため明示変換する。
    tz 指定が無い入力は UTC とみなす（本ツールの窓定義は常に UTC・上記 docstring）。
    """
    raw = text.strip()
    if not raw:
        raise ValueError("空のタイムスタンプは解釈できない")
    if raw.endswith(("Z", "z")):
        raw = raw[:-1] + "+00:00"
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_timestamp(value: datetime) -> str:
    """UTC の ``YYYY-MM-DDTHH:MM:SSZ`` 表記にする（レポートの時刻表記を1つに固定する）。"""
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class Window:
    """UTC の半開区間 ``[start, end)``。"""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("Window の境界は tz-aware でなければならない")
        if self.end <= self.start:
            raise ValueError(f"window end({self.end}) は start({self.start}) より後でなければならない")

    def contains(self, moment: datetime | None) -> bool:
        """``start <= moment < end`` か。``None``（未 close 等）は常に False。"""
        if moment is None:
            return False
        return self.start <= moment < self.end

    @property
    def days(self) -> float:
        return (self.end - self.start).total_seconds() / 86400.0

    def shifted_back(self, span: timedelta) -> "Window":
        """この窓の直前に接続する幅 ``span`` の窓（``[start - span, start)``）を返す。"""
        return Window(start=self.start - span, end=self.start)

    def as_dict(self) -> dict[str, object]:
        return {
            "start": format_timestamp(self.start),
            "end": format_timestamp(self.end),
            "days": self.days,
            "boundary": "start <= t < end (UTC)",
        }


#: Issue #368「現状と根拠」を 2026-09-06 に訂正した基線窓（14日・半開区間）。
BASELINE_WINDOW = Window(
    start=datetime(2026, 8, 2, tzinfo=timezone.utc),
    end=datetime(2026, 8, 16, tzinfo=timezone.utc),
)

#: 基線窓の実測値（Issue #488「現状と根拠」の表）。
BASELINE_MERGED_PRS = 22
BASELINE_ALL_ISSUES = 41
BASELINE_DERIVED_ISSUES = 15
BASELINE_ISSUES_PER_PR = 1.86
BASELINE_DERIVED_PER_PR = 0.68


@dataclass(frozen=True)
class IssueRecord:
    """計測に必要な Issue の最小情報（``gh issue list --json`` 由来）。"""

    number: int
    created_at: datetime
    closed_at: datetime | None
    body: str


@dataclass(frozen=True)
class PullRequestRecord:
    """計測に必要な merged PR の最小情報（``gh pr list --json`` 由来）。"""

    number: int
    merged_at: datetime
