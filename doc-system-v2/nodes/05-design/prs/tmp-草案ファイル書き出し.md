D-8（ノード草案）を `tmp/<sprint>/<parent-id>.md` に .md ファイルとして書き出す永続化。doc-system 記法（summary バッジ・YAML フロントマター・無名依存辺）に準拠したテキストで保存する。
**保存形式**: テキスト .md ファイル（doc-system 記法準拠・1 親ノードにつき 1 ファイル `tmp/<sprint>/<parent-id>.md`）。append-only ではなく親 ID 単位で上書き。
**ライフサイクル**: P-7-1-3（草案 tmp 書出）が著作のたびに作成・上書き。reconciliation（P-7-2）が本ファイルへ反映した後は削除可（一時領域）。
