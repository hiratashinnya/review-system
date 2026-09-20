"""語彙 lint（L4／L5）の既知 false positive を**理由付きで**抑制する allowlist。

L4（``owner_verbatim`` に推測語彙を混ぜない）と L5（``inferred_reason`` に断定語彙を書かない）は
決定論的な部分文字列一致で判定する。したがって**その語をどうしても使わざるを得ない**正当な
記録が原理的に残る——典型は「オーナー自身が『おそらく』と言った」場合で、逐語引用である
``owner_verbatim`` は推測語彙を含んだまま記録するのが正しい。

こうした誤検出は本ファイルに **(document_id, rule, term, value) の組 ＋ 理由** で明記して抑制する
（``time_fixture_lint/allowlist.py``・``asset_parity/exceptions.py``・``karte/allowlist.py`` と同じ
「消さず理由を残す」運用）。**理由（``reason``）の記載は必須**で、空のまま登録すると
:class:`ValueError` でモジュールの import 自体が失敗する（理由なき例外登録を作れない）。

抑制の粒度を **値の全文一致**にしてあるのは、語彙単位や文書単位で抑制すると「一度例外を認めた
語はその文書のあいだ書き放題」になり、lint が塞いだはずの経路がそのまま開くため。文面を
書き換えたら登録し直す必要がある（＝再承認が要る）ことは、この粒度の意図した性質である。
"""

from __future__ import annotations

from dataclasses import dataclass

RULES = ("L4", "L5")


def collapse(value: str) -> str:
    """照合用の空白正規化（前後の除去と連続空白の1個への圧縮）。"""
    return " ".join(str(value).split())


@dataclass(frozen=True)
class AllowlistEntry:
    """1 件の例外登録。

    document_id
        対象文書の id（``FBK-…``）。
    rule
        抑制する規則（``L4`` または ``L5``）。
    term
        検出された語彙（大小文字を無視して照合する）。
    value
        例外を認める欄の**全文**（空白を畳んで完全一致で照合する）。
    reason
        なぜその語彙が不可避なのか。**必須**。
    """

    document_id: str
    rule: str
    term: str
    value: str
    reason: str

    def __post_init__(self) -> None:
        if not collapse(self.document_id):
            raise ValueError("allowlist entry の document_id が空")
        if self.rule not in RULES:
            raise ValueError(
                f"allowlist entry の rule は {RULES} のいずれか: {self.rule!r}"
            )
        if not collapse(self.term):
            raise ValueError("allowlist entry の term が空")
        if not collapse(self.value):
            raise ValueError("allowlist entry の value が空")
        if not collapse(self.reason):
            raise ValueError(
                "allowlist entry には理由（reason）が必須"
                f"（document_id={self.document_id} rule={self.rule} term={self.term!r}）"
            )


# 既知の false positive はまだ無い。追加するときは「なぜその語を使わないと記録できないか」を
# 一次情報（該当文書・該当議事）とともに ``reason`` へ書くこと。
ALLOWLIST: tuple[AllowlistEntry, ...] = ()


def is_allowlisted(document_id: str, rule: str, term: str, value: str):
    """(document_id, rule, term, value) に一致する登録があれば返す（無ければ ``None``）。"""
    lowered = collapse(term).casefold()
    body = collapse(value)
    for entry in ALLOWLIST:
        if (
            entry.document_id == document_id
            and entry.rule == rule
            and collapse(entry.term).casefold() == lowered
            and collapse(entry.value) == body
        ):
            return entry
    return None
