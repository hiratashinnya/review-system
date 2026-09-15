"""``harm_detail`` 内容 lint（Issue #511）の既知 false positive を理由付きで抑制する allowlist。

:func:`karte.model.check_harm_detail` は ``harm_detail``（放置時の実害を書く欄）に
**処置方針・判断経緯の語彙**が混ざっていたら ``ingest-review`` の取り込みごと拒否する
（fail-close）。語彙照合は決定論的な部分文字列一致なので、**実害そのものを述べるために
その語を使わざるを得ない**ケースが原理的に残る（例：``karte`` 自身をレビューしたときの
「``deferred`` の finding が診断網羅から外れない」のように、禁止語彙が *仕様用語* として
現れる指摘）。

こうした誤検出は本ファイルに **(issue, term, harm_detail) の組 ＋ 理由** で明記して抑制する
（``time_fixture_lint/allowlist.py``・``asset_parity/exceptions.py`` と同じ
「消さず理由を残す」運用）。**理由（``reason``）の記載は必須**で、空のまま登録すると
:class:`ValueError` でモジュールの import 自体が失敗する（理由なき例外登録を作れない）。

抑制の粒度を **``harm_detail`` の全文一致**にしてあるのは、語彙単位や Issue 単位で抑制すると
「一度例外を認めた語は以後その Issue のあいだ書き放題」になり、lint が塞いだはずの経路が
そのまま開くため。文面を書き換えたら登録し直す必要がある（＝再承認が要る）ことは、
この粒度の意図した性質である。
"""

from __future__ import annotations

from dataclasses import dataclass


def collapse(value: str) -> str:
    """照合用の空白正規化（前後の除去と連続空白の1個への圧縮）。"""
    return " ".join(str(value).split())


@dataclass(frozen=True)
class AllowlistEntry:
    """1 件の例外登録。

    issue
        対象 Issue 番号（``ingest-review --issue`` の値）。
    term
        検出された禁止語彙（:data:`karte.model.HARM_DETAIL_FORBIDDEN_TERMS` の要素。
        大小文字は無視して照合する）。
    harm_detail
        例外を認める ``harm_detail`` の **全文**（空白を畳んで完全一致で照合する）。
    reason
        なぜ実害の記述としてその語彙が不可避なのか。**必須**。
    """

    issue: int
    term: str
    harm_detail: str
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.issue, int) or self.issue <= 0:
            raise ValueError(f"allowlist entry の issue は正の整数: {self.issue!r}")
        if not collapse(self.term):
            raise ValueError("allowlist entry の term が空")
        if not collapse(self.harm_detail):
            raise ValueError("allowlist entry の harm_detail が空")
        if not collapse(self.reason):
            raise ValueError(
                "allowlist entry には理由（reason）が必須"
                f"（issue={self.issue} term={self.term!r}）"
            )


# 既知の false positive はまだ無い。追加するときは「なぜその語を使わないと実害を述べられないか」を
# 一次情報（該当 finding・該当コード）とともに ``reason`` へ書くこと。
ALLOWLIST: tuple[AllowlistEntry, ...] = ()


def is_allowlisted(issue: int, term: str, harm_detail: str):
    """(issue, term, harm_detail) に一致する登録があれば返す（無ければ ``None``）。"""
    lterm = collapse(term).casefold()
    detail = collapse(harm_detail)
    for entry in ALLOWLIST:
        if (
            entry.issue == issue
            and collapse(entry.term).casefold() == lterm
            and collapse(entry.harm_detail) == detail
        ):
            return entry
    return None
