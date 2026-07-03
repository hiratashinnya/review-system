現在のステージ（requirements / analysis / design / implementation / verification のいずれか）を示す単一の文字列値。各接続ルール・属性検査ルールの `activate_stage` と比較され、current_stage がその段階以上に達して初めて当該ルールが発火する（段階ゲートの基準点）。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `current_stage: "design"`（現在値）。`stages`（CFG-1-4）の要素のいずれか。
