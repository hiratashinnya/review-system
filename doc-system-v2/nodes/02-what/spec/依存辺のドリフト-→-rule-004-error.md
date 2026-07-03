**前提条件**: 辺が `ref_version` を持ち、参照先ファイルに version がある
**入力/トリガ**: 依存辺の `ref_version` の x.y が参照先の現在 x.y と不一致
**期待動作**: RULE-004 ERROR を報告する（see-also 廃止で全辺が依存辺＝ドリフトは一律 ERROR）
