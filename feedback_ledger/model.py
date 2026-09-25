"""文書の読み込み・正規化・単体検証（L1／L4／L5）。

**正規化（normalize）と検証（validate）を1回の走査で同時に行う**のがこのモジュールの役割で、
下書きの取り込み（``new-entry`` 等）と既存文書の検査（``check``）が**同じ関数**を通る。
別実装にすると「CLI は通すが check は落とす（またはその逆）」という食い違いが必ず生まれる。

正規化の内容（canonical の定義の一部・:mod:`feedback_ledger.tomlwrite` と対）:
  * 1行文字列 … 前後の空白を除去する。
  * 複数行文字列 … CRLF/CR を LF へ、各行の行末空白を除去、前後の空行を落とし、末尾を改行1つにする。
  * 文字列配列 … 各要素を strip し、空要素を落とし、**重複除去して昇順に並べ替える**。
    順序に意味を持たせない（＝同じ内容が1つのバイト列になる）ための決定。

検証（このモジュールが出すもの）:
  * **L1** キー集合の完全一致（欠落・未知とも拒否）／型／enum／``id`` の書式／必須欄の空値拒否
  * **L4** ``owner_verbatim``（逐語引用）への**推測語彙**の混入を拒否する
  * **L5** ``inferred_reason`` は ``推測：`` マーカー必須・**断定語彙**を拒否する

L2（パス実在）・L6（immutability）・L7（canonical）・P1〜P4・T1 は文書をまたぐ検査なので
:mod:`feedback_ledger.check` にある。

依存仕様: Issue #522「lint 規則（check）」／``karte/model.py``「``harm_detail`` の内容 lint」（L4/L5 の原型）。
"""

from __future__ import annotations

import datetime
import tomllib
from dataclasses import dataclass

from . import schema as schema_module
from .allowlist import is_allowlisted
from .schema import DocSpec, Field
from .tomlwrite import DATE, INT, LINE, OPTDATE, STRLIST, TEXT

ERROR = "ERROR"
WARN = "WARN"

# L4: 逐語引用の欄に混ざってはいけない**書き手の推測**を示す語彙。
# 「オーナーが何と言ったか」と「AI がそれをどう解釈したか」を1つの欄で混ぜると、
# 後から読む者が引用と解釈を区別できなくなる（この台帳の一次情報としての価値が消える）。
SPECULATION_TERMS = (
    "おそらく", "と思われる", "と思う", "意図は", "だろう", "らしい", "ようだ",
    "のではないか", "かもしれない", "推測",
)
# L5: 推論欄に書いてはいけない**断定**の語彙。推論を発言そのものとして記録すると、
# 存在しない発言が一次情報として残る。
ASSERTION_TERMS = ("と述べた", "と明言", "と言った", "と断言", "と確言", "と発言した")
INFERRED_MARKER = "推測："


@dataclass(frozen=True)
class Finding:
    """1件の検査結果。``level`` が ``ERROR`` のとき CLI は終了コード 4 で落とす。"""

    rule: str
    level: str
    locus: str
    message: str

    def render(self) -> str:
        return f"{self.level}: [{self.rule}] {self.locus}: {self.message}"


class DocumentError(Exception):
    """TOML として読めない（構文エラー）。"""


def parse_toml(text: str) -> dict:
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise DocumentError(f"TOML として読めない: {exc}") from exc


def normalize_line(value: str) -> str:
    return value.strip()


def normalize_text(value: str) -> str:
    body = value.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip(" \t") for line in body.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    while lines and lines[0] == "":
        lines.pop(0)
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def normalize_strlist(value) -> list[str]:
    return sorted({item.strip() for item in value if str(item).strip()})


def _is_plain_date(value) -> bool:
    return isinstance(value, datetime.date) and not isinstance(value, datetime.datetime)


def _normalize_field(field: Field, raw, locus: str, findings: list[Finding]):
    """1つの欄を正規化して返す。値として使えないときは ``None`` を返す。"""
    if field.kind in (LINE,):
        if not isinstance(raw, str):
            findings.append(Finding("L1", ERROR, locus, f"文字列でなければならない: {raw!r}"))
            return None
        value = normalize_line(raw)
        if "\n" in value:
            findings.append(Finding("L1", ERROR, locus, "1行の値に改行を含めてはならない"))
            return None
    elif field.kind == TEXT:
        if not isinstance(raw, str):
            findings.append(Finding("L1", ERROR, locus, f"文字列でなければならない: {raw!r}"))
            return None
        if "'''" in raw:
            findings.append(
                Finding("L1", ERROR, locus, "複数行の値に ''' を含めてはならない")
            )
            return None
        value = normalize_text(raw)
    elif field.kind == INT:
        if isinstance(raw, bool) or not isinstance(raw, int):
            findings.append(Finding("L1", ERROR, locus, f"整数でなければならない: {raw!r}"))
            return None
        if raw < 0:
            findings.append(Finding("L1", ERROR, locus, f"負の整数は使えない: {raw}"))
            return None
        value = raw
    elif field.kind == DATE:
        if not _is_plain_date(raw):
            findings.append(
                Finding("L1", ERROR, locus, f"TOML の日付（YYYY-MM-DD）でなければならない: {raw!r}")
            )
            return None
        value = raw
    elif field.kind == OPTDATE:
        if raw == "":
            value = ""
        elif _is_plain_date(raw):
            value = raw
        else:
            findings.append(
                Finding("L1", ERROR, locus,
                        f"日付（YYYY-MM-DD）または空文字でなければならない: {raw!r}")
            )
            return None
    elif field.kind == STRLIST:
        if not isinstance(raw, list) or any(not isinstance(item, str) for item in raw):
            findings.append(
                Finding("L1", ERROR, locus, f"文字列の配列でなければならない: {raw!r}")
            )
            return None
        value = normalize_strlist(raw)
    else:  # pragma: no cover - schema 側のプログラミングエラー
        raise ValueError(f"未知の値種別: {field.kind}")

    empty = value in ("", [], 0)
    if field.required_nonempty and empty:
        findings.append(Finding("L1", ERROR, locus, "必須の欄が空になっている"))
        return value
    if empty:
        return value

    if field.enum is not None and value not in field.enum:
        findings.append(
            Finding("L1", ERROR, locus,
                    f"語彙外の値: {value!r}（許可: {', '.join(field.enum)}）")
        )
    if field.pattern is not None:
        items = value if isinstance(value, list) else [value]
        for item in items:
            if not field.pattern.match(item):
                findings.append(
                    Finding("L1", ERROR, locus,
                            f"書式に合わない値: {item!r}（期待: {field.pattern.pattern}）")
                )
    return value


def _lint_narrative(document_id, field: Field, value: str, locus, findings):
    """L4／L5（語彙 lint）。誤検出は allowlist で理由付きに抑制する。"""
    if not value:
        return
    if field.lint == "owner-verbatim":
        for term in SPECULATION_TERMS:
            if term in value:
                if is_allowlisted(document_id, "L4", term, value):
                    continue
                findings.append(Finding(
                    "L4", ERROR, locus,
                    f"逐語引用の欄に推測語彙 {term!r} が混ざっている"
                    "（解釈は inferred_reason へ分ける。不可避なら"
                    " feedback_ledger/allowlist.py へ理由付きで登録する）",
                ))
    elif field.lint == "inferred":
        if not value.startswith(INFERRED_MARKER):
            findings.append(Finding(
                "L5", ERROR, locus,
                f"推論の欄は {INFERRED_MARKER!r} で始めなければならない"
                "（引用と推論を読み手が区別できるようにするため）",
            ))
        for term in ASSERTION_TERMS:
            if term in value:
                if is_allowlisted(document_id, "L5", term, value):
                    continue
                findings.append(Finding(
                    "L5", ERROR, locus,
                    f"推論の欄に断定語彙 {term!r} が使われている"
                    "（発言として記録できるのは owner_verbatim だけ）",
                ))


def normalize_document(spec: DocSpec, raw: dict, locus: str) -> tuple[dict | None, list[Finding]]:
    """L1／L4／L5 を検査しつつ canonical な内部表現へ正規化する。

    戻り値の ``data`` は「シリアライズできる形」まで揃ったときだけ非 ``None`` になる
    （キーが欠けている・型が違う欄があると ``None``）。``findings`` は空でなくても
    ``data`` が返ることがある（enum 違反など、値としては書けるが規則違反である場合）。
    """
    findings: list[Finding] = []
    if not isinstance(raw, dict):
        findings.append(Finding("L1", ERROR, locus, "トップレベルがテーブルでない"))
        return None, findings

    document_id = raw.get("id") if isinstance(raw.get("id"), str) else locus
    data: dict = {}
    complete = True

    declared_tables = {table.name for table in spec.tables if table.name}
    top_fields = {field.name for table in spec.tables if not table.name for field in table.fields}
    unknown_top = sorted(set(raw) - top_fields - declared_tables)
    for key in unknown_top:
        findings.append(Finding("L1", ERROR, f"{locus}::{key}", "宣言されていないキー"))

    for table in spec.tables:
        if not table.name:
            for field in table.fields:
                where = f"{locus}::{field.name}"
                if field.name not in raw:
                    findings.append(Finding("L1", ERROR, where, "必須のキーが無い"))
                    complete = False
                    continue
                value = _normalize_field(field, raw[field.name], where, findings)
                if value is None:
                    complete = False
                    continue
                data[field.name] = value
            continue

        if table.name not in raw:
            findings.append(
                Finding("L1", ERROR, f"{locus}::[{table.name}]", "必須のテーブルが無い")
            )
            complete = False
            continue

        section = raw[table.name]
        if table.repeated:
            if not isinstance(section, list):
                findings.append(Finding(
                    "L1", ERROR, f"{locus}::[[{table.name}]]",
                    "テーブルの配列でなければならない",
                ))
                complete = False
                continue
            items = []
            for index, element in enumerate(section):
                item, ok = _normalize_subtable(
                    table, element, f"{locus}::[[{table.name}]][{index}]",
                    document_id, findings,
                )
                complete = complete and ok
                if ok:
                    items.append(item)
            items.sort(key=lambda entry: tuple(str(entry[f.name]) for f in table.fields))
            data[table.name] = items
            continue

        item, ok = _normalize_subtable(
            table, section, f"{locus}::[{table.name}]", document_id, findings
        )
        complete = complete and ok
        if ok:
            data[table.name] = item

    if not complete:
        return None, findings
    return data, findings


def _normalize_subtable(table, section, locus, document_id, findings):
    if not isinstance(section, dict):
        findings.append(Finding("L1", ERROR, locus, "テーブルでなければならない"))
        return None, False
    declared = {field.name for field in table.fields}
    for key in sorted(set(section) - declared):
        findings.append(Finding("L1", ERROR, f"{locus}::{key}", "宣言されていないキー"))
    item = {}
    ok = True
    for field in table.fields:
        where = f"{locus}::{field.name}"
        if field.name not in section:
            findings.append(Finding("L1", ERROR, where, "必須のキーが無い"))
            ok = False
            continue
        value = _normalize_field(field, section[field.name], where, findings)
        if value is None:
            ok = False
            continue
        if field.lint and isinstance(value, str):
            _lint_narrative(document_id, field, value, where, findings)
        item[field.name] = value
    return item, ok


def check_document_identity(spec: DocSpec, data: dict, locus: str) -> list[Finding]:
    """``schema`` 定数・``id`` 書式・``overridden_role`` 拡張形（L1 の残り）。"""
    findings: list[Finding] = []
    if data.get("schema") != spec.schema_const:
        findings.append(Finding(
            "L1", ERROR, f"{locus}::schema",
            f"schema は {spec.schema_const!r} でなければならない: {data.get('schema')!r}",
        ))
    if spec.kind == schema_module.LEDGER:
        role = data.get("overridden_role", "")
        if role and not schema_module.valid_overridden_role(role):
            findings.append(Finding(
                "L1", ERROR, f"{locus}::overridden_role",
                f"語彙外の値: {role!r}"
                f"（許可: {', '.join(schema_module.OVERRIDDEN_ROLES)}, skill:<name>）",
            ))
    if spec.kind in (schema_module.LEDGER, schema_module.PROPOSAL):
        match = spec.id_re.match(data.get("id", ""))
        if match:
            stamp = match.group("date")
            try:
                datetime.date(int(stamp[0:4]), int(stamp[4:6]), int(stamp[6:8]))
            except ValueError:
                findings.append(Finding(
                    "L1", ERROR, f"{locus}::id",
                    f"id の日付部分が実在しない日付: {stamp}",
                ))
    return findings
