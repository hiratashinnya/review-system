---
id: TR-agy-delegate-606-working-tree
version: 1
condition: failure
result: PASS
log_ref: tests/logs/TD-agy-delegate-606-working-tree.txt
---
# agy-delegate wrapper 受入テスト結果

TD: [TD-agy-delegate-606 v1](../designs/TD-agy-delegate-606.md)。対象は未commit作業ツリー（ユーザーのcommit禁止指示を優先）。実装commit id未確定、prompt版なし、基準content_hash該当なし。実行日2026-10-13、Linux/Python3/fake agy、実機agyは未使用。

## 手順と期待結果

TD記載の7 test modulesを `python3 -m unittest` で実行。起動禁止、全異常理由、会話/画像/並列/外側gate、アンカー/意味的未検証/成果欠落を検査する。

## 実測

33 tests PASS、1.686秒。stdoutはlog_ref。maintainability checkはviolations=0、accepted_debt=104、baseline更新なし。全量unittest/coverage/asset_parity/生成同期は主文脈の統合結果に従う。

## レビュー是正後の検証

初回33件の記録は上記log_refに保持する。R1/R2是正後、主文脈が `python3 -m unittest discover -s tests/unit -p 'test_agy_delegate*.py'` を実行し、41 tests PASS、1.546秒を確認した。

別文脈の再レビューR3（成功候補のresponse=nullを継続できる）について、成功候補にstrを要求する処置と起動前停止テストを追加した。同じdiscoverコマンドを再実行し、**42 tests PASS、1.389秒**を確認した。最終ログは [TD-agy-delegate-606-review-final.txt](../logs/TD-agy-delegate-606-review-final.txt)。これは合成契約の検証であり、実機契約の未検証制約は維持する。同一PR内の初版結果追記のためversion 1を維持する。

再レビューR4（外側timeout時のstderr消失）を是正した。`TimeoutExpired.stderr` をbytes/str/Noneに対応して保持し、print timeout信号を追加した上で共通normalizeを通す。Issue `Issue #606 本文` 仕様詳細§3のtimeout経路を照合し、D0/ERROR/deny/error/no-output/非0/JSON契約異常と部分応答・ID・打切りの保持、自動再試行なし、completed=falseを3つの追加テストで固定した。最終関連discoverは **45 tests PASS、1.370秒**。maintainability checkはviolations=0、accepted_debt=104、baseline未更新。42件を含む過去ログは保持し、R4最終ログは [TD-agy-delegate-606-review-r4.txt](../logs/TD-agy-delegate-606-review-r4.txt)。

全量検査で旧`agy-delegate`文言を期待する共有資産配置テストの追随漏れを検出した。検出手順の所有者が現正本 `.ai/agents/agy-delegate.md` であること、正本ファイルの存在、#606でClaude/Codex接続済み、実測契約・設定合成未確認による通常実行停止を期待するよう更新した。#605一般則の本文変更なし。`python3 -m unittest tests.unit.test_silent_failure_diagnosis_layout` は **8 tests PASS、0.001秒**、関連agy discover再確認は **45 tests PASS、1.540秒**。maintainability checkはviolations=0、accepted_debt=104。ログは [TD-agy-delegate-606-layout-followup.txt](../logs/TD-agy-delegate-606-layout-followup.txt)。

通常runは実測契約/設定層/起動環境の未確認で停止する。本試験の合成JSON成功は、実機agy・WSL・設定合成・内部symlink保護・認証・実機UCの達成を証明しない。#607の撤去可能という判定は未実施。

履歴成績書。実行対象と件数・合否は当時の記録に限る（対象commitが記録されていない試験は未特定）。本作業の基点は41be85d、r4是正差分の最終結果は [r4 合成最終成績書](TR-agy-delegate-606-synthetic-final-r4.md)。過去のPASS/FAIL/件数を修正・再認定しない。実機UCのPASSを意味しない。
