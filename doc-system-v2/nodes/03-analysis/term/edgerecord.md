**もの**: ノード内に記述された 1 本の無名依存辺の内部表現。`NodeRecord.edges` の各要素。
**用途**: パーサ（MOD-4）がフロントマターの `edges[]` を解析して生成し、drift_checker（参照先版照合）・structure_checker（dangling/必須辺）等が辺の到達先と版を判定するのに用いる。
**Python 型名**: `EdgeRecord`
**保持要素**: `to`（参照先ノード ID・単数）/ `ref_version`（参照先ノードのバッジ x.y）
**定義モジュール**: `spec_inspector/domain.py`（MOD-1）
