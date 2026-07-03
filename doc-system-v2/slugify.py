"""ノードタイトル → slug（＝ファイル名 stem ＝ id）の正規化（参照実装・stdlib のみ）。

新フォーマットでは **id = 正規化した読めるタイトル**（ファイル名 stem・パス非依存・グローバル一意）。
本モジュールはその正規化規則の唯一の参照実装。移行スクリプト（Sub-B）・著作パイプライン
（Sub-D）・rename ツール（Sub-C）はここを再利用する（規則の独自再実装を禁じる）。

正規化規則（FORMAT.md §slug と一致させること）:
  1. 末尾の condition マーカー（（normal）/（failure）/（umbrella））を除去（condition はサイドカーへ）。
  2. Unicode NFC 正規化。
  3. code バッククォート ``` ` ``` と path/shell 敵性文字（``/ \\ : * ? " < > | 半角/全角括弧 [] {} ' 「」【】``）を空白へ。
  4. 連続空白を単一 ``-`` へ。
  5. ASCII は小文字化（日本語はそのまま）＝ 大小無視 FS での衝突回避。
  6. 連続 ``-`` を単一化、先頭末尾の ``-`` を除去。
  7. UTF-8 で MAX_BYTES を超える場合は文字境界で切り詰め。

一意性（グローバル重複の検出）は本モジュールの責務ではない＝reconciliation-validator が fail-close で担保（DD-22・Sub-D）。
"""

from __future__ import annotations

import re
import unicodedata

MAX_BYTES = 120

# 末尾 condition マーカー。config.yml condition_vocab（normal/boundary/empty/failure/error）と一致させる。
# 実コーパスは （normal） だけでなく （normal・アンブレラ）（error・…）等の派生形を持つため
# 「vocab 語で始まる末尾括弧群」を対象にする（umbrella は #81 で condition から外れたため含めない）。
_CONDITION_SUFFIX = re.compile(r"[（(](?:normal|boundary|empty|failure|error)[^）)]*[)）]\s*$")
# path/shell 敵性文字。これらは slug から除去（空白化→後段でハイフン化）。
_HOSTILE = set('/\\:*?"<>|`\'()[]{}（）「」【】〔〕')
_WS = re.compile(r"\s+")
_DASHES = re.compile(r"-{2,}")


def strip_condition(title: str) -> str:
    """タイトル末尾の condition マーカー（（failure）等）を除去して返す。"""
    return _CONDITION_SUFFIX.sub("", title).strip()


def slugify(title: str, *, max_bytes: int = MAX_BYTES) -> str:
    """ノードタイトルを slug（ファイル名 stem／id）へ正規化する。

    依存: FORMAT.md §slug（新フォーマット仕様・Sub-A）。
    """
    t = strip_condition(title)
    t = unicodedata.normalize("NFC", t)
    t = "".join(" " if ch in _HOSTILE else ch for ch in t)
    t = _WS.sub("-", t)
    t = t.lower()  # ASCII のみ小文字化（日本語は不変）
    t = _DASHES.sub("-", t).strip("-")
    # UTF-8 バイト長で上限を課す（多バイト文字を割らない）
    if len(t.encode("utf-8")) > max_bytes:
        out = []
        n = 0
        for ch in t:
            b = len(ch.encode("utf-8"))
            if n + b > max_bytes:
                break
            out.append(ch)
            n += b
        t = "".join(out).strip("-")
    return t


def _selftest() -> None:
    # (1) 厳密な等価（実装が保証すべき正規化結果）
    exact = {
        "本文中の孤立 `---` を検出したとき WARNING を出力する（failure）":
            "本文中の孤立-を検出したとき-warning-を出力する",
        "ノード本文に孤立 `---`（ノード分離記法の本文内誤用）が存在しない（normal・アンブレラ）":
            "ノード本文に孤立-ノード分離記法の本文内誤用-が存在しない",
        "  複数   空白  と-- 連続ハイフン  ":
            "複数-空白-と-連続ハイフン",
    }
    for src, want in exact.items():
        got = slugify(src)
        assert got == want, f"{src!r}\n  got : {got!r}\n  want: {want!r}"
    # (2) 不変条件（任意入力で常に満たす）
    for src in [*exact, "Q-6: pipeline と skill の責務分界", "A/B\\C:D*E?", "」【x】「"]:
        out = slugify(src)
        assert out == unicodedata.normalize("NFC", out)
        assert not (set(out) & _HOSTILE), f"hostile char残存: {src!r} -> {out!r}"
        assert not out.startswith("-") and not out.endswith("-"), out
        assert "--" not in out, out
        assert len(out.encode("utf-8")) <= MAX_BYTES, out
    # (3) condition ストリップ（config.yml condition_vocab に一致）
    for cond in ("normal", "boundary", "empty", "failure", "error"):
        assert strip_condition(f"題（{cond}）") == "題", cond
    assert strip_condition("題（normal・アンブレラ）") == "題"
    # umbrella は #81 で condition 値でなくなったため除去しない（漏れではなく仕様）
    assert strip_condition("題（umbrella）") == "題（umbrella）"
    # slug でも （error） 等が漏れないこと（本指摘①の回帰）
    assert slugify("何かの検査（error）") == "何かの検査", slugify("何かの検査（error）")
    assert strip_condition("題") == "題"
    # (4) 長さ上限（多バイト境界を割らない）
    s = slugify("あ" * 100)  # 300 bytes
    assert len(s.encode("utf-8")) <= MAX_BYTES and "�" not in s
    print("slugify self-test OK")
    for src in exact:
        print(f"  {src!r}\n    -> {slugify(src)!r}")


if __name__ == "__main__":
    _selftest()
