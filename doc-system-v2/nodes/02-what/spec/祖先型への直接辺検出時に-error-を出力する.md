**前提条件**: in-graph に SPEC ノードが1件以上存在し、全ノードがパース済みである。
**入力/トリガ**: 検証ツールが SPEC ノードの `edges[].to` に祖先型（SR・VAL 等）への直接辺を1件以上検出する。
**期待動作**: 祖先型への直接辺を検出したとき、当該辺を指す ERROR を1件出力する。
**例**: `SPEC-99` の edges に `{to: "SR-2", ref_version: "0.2"}` が含まれる → `ERROR|{file}:{line}|NFR-5-check|SPEC-99|direct ancestor edge to SR-2 violates 1-level constraint` を出力。
