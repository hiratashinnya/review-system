"""dsv2 — doc-system v2（新フォーマット）向けツール群（stdlib のみ）。

新フォーマット（Sub-A・`doc-system-v2/FORMAT.md`）は「1ノード=2ファイル」（`{slug}.md` 本文＋
`{slug}.yaml` サイドカー）・`id`＝ファイル stem・`stage/type/status`＝path 導出・無名依存辺という
構造を採る。本パッケージはその v2 コーパスに対する索引生成とグラフ照会・機械改変を提供する:

  * ``index``       … ``nodes/**/*.yaml`` を走査し ``meta.json`` を生成（サイドカー集約）。
  * ``deps/dependents/orphans/drift`` … meta.json 上のグラフ照会（RULE-004 ドリフト含む）。
  * ``reverse``     … FND 辺逆転（forward 削除＋backward 付与＋DD-3 本文記録＋z バンプ＋git mv）。
  * ``rename``      … slug 改題（md/yaml 改名＋全 referrer の edges[].to 一括張替え）。

サイドカー YAML の読取は既存 ``docidx.nodeyaml`` を再利用する（独自 YAML パーサを持ち込まない）。
旧フォーマットの stray-`---` lint（backref/notation.py）は v2 では本文とメタが分離され不要のため
移植しない。
"""
