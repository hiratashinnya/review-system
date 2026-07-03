**もの**: パース結果として得られる単一ノードの内部表現。1つの `.md` ノードを 1 レコードに射影したもの。
**用途**: パーサ（MOD-4）がフロントマターを解析して生成し、各 checker / coverage / projector が読み取って検査・射影の入力とする。グラフ全体は `list[NodeRecord]` で表す。
**Python 型名**: `NodeRecord`
**保持要素**: `id` / `type` / `labels` / `scheduled` / `edges`（EdgeRecord のリスト）
**定義モジュール**: `spec_inspector/domain.py`（MOD-1）
