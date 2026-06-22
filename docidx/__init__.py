"""docidx — md2idx 思想の doc-system ノード検索/読み込みツール。

巨大な Markdown ファイルに埋め込まれた型付き ID グラフ（doc-system）から、
軽量なインデックスを作り、必要なノードだけをオンデマンドで読み込む read-only ユーティリティ。
標準ライブラリのみで実装する。
"""

from .model import Edge, Node, NodeIndex

__all__ = ["Edge", "Node", "NodeIndex"]
