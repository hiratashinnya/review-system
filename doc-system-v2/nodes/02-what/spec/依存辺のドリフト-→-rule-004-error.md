**前提条件**: 辺が `ref_version` を持ち、参照先ファイルに version がある
**入力/トリガ**: 依存辺の `ref_version` の x.y が参照先の現在 x.y と不一致
**期待動作**: RULE-004 ERROR を報告する（see-also 廃止で全辺が依存辺＝ドリフトは一律 ERROR）
**責務境界**: 本 SPEC は「検査時点で既に存在する依存辺の `ref_version` と参照先 version の不一致」を failure として検出する責務を持つ。ファイル/ノードの x.y 上昇を契機にドリフト検査を再実行し、再反映を促す normal 系の責務は SPEC-10 系（SPEC-10-1/10-2）に委ねる。
