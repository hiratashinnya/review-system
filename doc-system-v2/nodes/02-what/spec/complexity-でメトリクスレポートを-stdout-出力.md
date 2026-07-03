**前提条件**: spec-inspector がノードグラフを正常にパース済みで（SPEC-1 の正常系が先行）、グラフに1件以上のノードが存在し、`--complexity` オプションが指定されている。
**入力/トリガ**: `spec-inspector --complexity` を実行する。
**期待動作**: `--complexity` 指定時、各ノードの in-degree・out-degree・ハブ判定を含むメトリクスレポートを id 昇順の行形式（`{node-id} | in={N} | out={N} | hub={yes/no}`）で stdout に出力する。
**合格例**: ノード FR-1（被参照: SPEC-1, SPEC-2 の 2 件、参照先: SR-1 の 1 件）を含むグラフに `--complexity` 実行 → stdout に `FR-1 | in=2 | out=1 | hub=no` が含まれる。
**違反例**: stdout に何も出力されない・またはメトリクス行に `in=` / `out=` フィールドが欠落する → 期待動作を満たさない。
