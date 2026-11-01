---
id: TD-agy-delegate-606
version: 1
condition: failure
result: PASS
log_ref: tests/logs/TD-agy-delegate-606-working-tree-r2.txt
---
# agy-delegate wrapper 受入テスト

## 目的

Issue #606 の直接起動・許可・結果・会話・画像・外側gate・成果採用条件を、実機agyを使わず検査する。

## 前提

未commit作業ツリー。ユーザーのcommit禁止がtest-strategyのcommit-before-testより優先する。
`tests/unit/agy_delegate_fixtures.py` は実測型に沿う合成データの偽プロセスであり、設定合成・wrapperの実機起動を実証しない。r2で tests/fixtures/agy_delegate/1.3.3/ の実測JSON（成功・拒否・print-timeout・クォータERROR）を追加し、正規化の実証に用いる。/usageは完全JSONが無いためfixture化しない。

## 手順

`python3 -m unittest tests.unit.test_agy_delegate_results tests.unit.test_agy_delegate_permissions tests.unit.test_agy_delegate_runner tests.unit.test_agy_delegate_artifacts tests.unit.test_agy_delegate_cli tests.unit.test_agy_delegate_gates tests.unit.test_agy_delegate_adoption`

レビュー是正後の最終検証は `python3 -m unittest discover -s tests/unit -p 'test_agy_delegate*.py'` で行う。上記初回7モジュールに加え、重複JSONキーと会話記録の厳密検証を含む。新規TDの同一PR内是正であるためversion 1を維持する。

共有資産の接続説明への追随も `python3 -m unittest tests.unit.test_silent_failure_diagnosis_layout` で検査する。#605一般則を変更せず、agy固有検出手順の正本への参照、#606接続済み、設定適用層・合成規則と起動環境未確認による通常実行停止を維持する。

## 期待結果

- 通常runはruntime未検証、欠落/過剰/競合設定、停止申告、環境不足で起動しない。
- 実測4ケースの分類・全理由・応答・ID・error・打切りを保持し、実測成功のみ候補とする。出力ゲートだけ解除し、設定/起動2ゲートは子プロセス未起動で維持する。
- 必須6キー、optional denied_actions/error、拒否要素2キー、usage5キー、有限非負duration、boolを除く非負整数turns/tokensを検査する。未知キー/型・数値overflow・空IDを拒否し、token算術は推測しない。
- 合成SUCCESS＋拒否、ERROR＋応答、timeout＋部分応答、非0exit、壊れたJSON/型/未知フィールドは非0。
- 拒否を優先し全理由保持。自動retryなし。shell連結せずJSONフラグは-pより前。
- 外側process timeoutでもbytes/str/Noneのstdout/stderrを正規化し、stderrの認証・セキュリティ拒否、error/no-output、JSONのERROR/deny/契約違反を保持する。部分応答・IDは診断用に保持し、非0・未完了・打切りを維持する。
- 継続の記録なし/別workspace/既失敗/ID不一致は拒否。child例外後lock解放と記録更新。
- JSONの重複キー・非標準数値は拒否し、後続値で拒否を上書きさせない。
- 会話記録の必須項目・型・run_id・取得ID対応を検査する。success_candidateでもERROR/exit異常/reasons/deny/truncated/response=nullを継続させず、起動前に定型理由で停止する。
- 有限並列の各結果/ID分離、全workspace排他。画像は返却IDだけ、旧画像/symlink/他会話fallback拒否。
- 厳密commandテンプレートは空白日本語pathを許し、連結/部分式/改行/過剰許可/deny globを拒否。
- Claude/Codexの実際のgateへ外側起動を渡し、専用ロール境界を緩和しない。
- アンカー不一致/前置き未検証/画像欠落を採用しない。wrapper成功は候補でcompleted=false。

## r2 実測

- TD版: 1（未merge同一変更内での実測追随のため再bumpなし）。実装commit: 未commit作業ツリー。ユーザーのcommit禁止を優先。
- 実行日時: 2026-10-13T08:28:06.874518+09:00; Python標準unittest、実機agyの実行なし。
- wrapper関連51件PASS、共有配置・同期関連48件PASS。maintainability_lint: violations=0 / accepted_debt=104。asset_parity: 0 MISSING（既存stale警告あり）。guidance_sync: check OK。
- prompt雛形版・S6基準content_hash: wrapperでは対象外。実測元: tests/fixtures/agy_delegate/1.3.3/README.md、agy 1.3.3 / WSL / 2026-10-13。
- 4件のstdout/stderr/exitをfixtureで再生し、成功候補・D0拒否・打切り・ERRORの全理由と応答/ID/errorを確認。/usageは完全JSON不足なので合成境界テストのみ。
- 出力型不足ゲートだけ撤去。設定適用層・合成規則とWSL→Windows変換の検査不能停止は維持し、通常runは未起動。許可未特定時未起動のmock検証を保持。
- wrapperの実機UC、実効許可、画像/並列/会話継続の実機確認、default branch到達は未達。全量coverageと独立レビューは主文脈で別記録。

履歴成績書。実行対象と件数・合否は当時の記録に限る（対象commitが記録されていない試験は未特定）。本作業の基点は41be85d、r4是正差分の最終結果は [r4 合成最終成績書](TR-agy-delegate-606-synthetic-final-r4.md)。過去のPASS/FAIL/件数を修正・再認定しない。実機UCのPASSを意味しない。
