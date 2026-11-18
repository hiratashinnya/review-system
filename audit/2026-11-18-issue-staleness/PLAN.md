# 全Issue陳腐化棚卸し：調査計画

- 対象：hiratashinnya/review-system の Open / Closed **全Issue**（PR は証拠として別途照合）。
- 基準 main：`f2b61188a1600d0e1048dd38db2c2379809e68aa`（2026-11-18取得）。実調査中の変更は原則読み取り、Issue/PR/コードを変更しない。
- 調査方法：全Issueを作成時期×open/closedで重複なく列挙し、全文を1件ずつ調べ、`memos/issue-XXXX.md` にメモ。メモにはタイトル・状態・本文内のAC、関連参照と現状、陳腐化シグナル、推奨、判定根拠を記す。
- 記録：`memos/`、`reports/INDEX.csv`、`reports/REPORT.md`、`reports/PROGRESS.md`。
- クロスチェック：参照先Issue/PRの状態、廃止方針、現在のmain契約、古い着手条件。AC達成の証拠なしに完了扱いしない。
- 重要：過去時点の記録は当時の事実なので、それだけでは誤り扱いしない。毎日付記・明示済みであれば優先度を下げる。

## チェックリスト
- [x] 計画ファイルを最初に作成
- [ ] 全件列挙・本文確認
- [ ] 各Issueメモ保存
- [ ] 参照関係とPR照合
- [ ] 注目候補の現行main検証
- [ ] サマリ報告・整合確認
