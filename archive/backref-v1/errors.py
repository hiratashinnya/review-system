"""backref の例外。"""

from __future__ import annotations


class BackrefError(Exception):
    """前提違反・想定外フォーマットで処理を停止するとき送出する（fail-close）。

    正本（doc-system/*.md）への書込ツールであるため、ノードの YAML/本文が想定形
    （04-notation §3・summary バッジ・2スペース block list 等）から外れた場合は、
    推測で書き換えて破壊するより停止して利用者に知らせる。CLI 層が exit 4 へ写像する。
    """
