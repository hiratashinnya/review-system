---
id: TD-agy-delegate-606
version: 1
condition: failure
---
# agy-delegate wrapper 受入テスト

## 目的

Issue #606 の直接起動・許可・結果・会話・画像・外側gate・成果採用条件を、実機agyを使わず検査する。

## 前提

未commit作業ツリー。ユーザーのcommit禁止がtest-strategyのcommit-before-testより優先する。
`tests/unit/agy_delegate_fixtures.py` は実測型に沿う合成データの偽プロセスであり、設定合成・wrapperの実機起動を実証しない。r2で tests/fixtures/agy_delegate/1.3.3/ の実測JSON（成功・拒否・print-timeout・クォータERROR）を追加し、正規化の実証に用いる。/usageは完全JSONが無いためfixture化しない。

## 手順

`python3 -m unittest tests.unit.test_agy_delegate_results tests.unit.test_agy_delegate_permissions tests.unit.test_agy_delegate_runner tests.unit.test_agy_delegate_artifacts tests.unit.test_agy_delegate_cli tests.unit.test_agy_delegate_gates`

レビュー是正後の最終検証は `python3 -m unittest discover -s tests/unit -p 'test_agy_delegate*.py'` で行う。上記責務別モジュールに加え、重複JSONキーと会話記録の厳密検証を含む。新規TDの同一PR内是正であるためversion 1を維持する。

共有資産の配置は `python3 -m unittest tests.unit.test_silent_failure_diagnosis_layout` で検査する。検査対象は共通本文参照・PF非依存・一般則・agy固有正本参照・rationale到達性とCopilot非移植記録。運用状態の検査はこの配置テストの責務に含めない。

## 期待結果

r3の `test_agy_delegate_settings_layers.py` は偽pathとfixture専用schemaだけを使う。実機設定/認証ファイルを読まずagyを起動しない。同一未merge変更内の追記でversion 1を維持する。

- 全4参加元が特定されread-only読取できた場合だけ保守的監査を行い、bytes不変を確認する。
- project allowがglobal deny/共有user askを消さず、corpus deny欠落・広いcommand許可は停止する。実効mergeの実測ではない。
- 未特定path/schema、層不足、JSON不正、一部未読とadmin明示不存在/読取拒否/再出現を区別し停止する。
- fake全層監査合格でもruntimeの配列合成と起動環境STOPを維持する。通常CLIで層別未特定理由を返し子プロセスを起動しない。

- 通常runはruntime未検証、欠落/過剰/競合設定、停止申告、環境不足で起動しない。
- 実測4ケースの分類・全理由・応答・ID・error・打切りを保持し、実測成功のみ候補とする。出力ゲートだけ解除し、設定/起動2ゲートは子プロセス未起動で維持する。
- 必須6キー、optional denied_actions/error、拒否要素2キー、usage5キー、有限非負duration、boolを除く非負整数turns/tokensを検査する。未知キー/型・数値overflow・空IDを拒否し、token算術は推測しない。
- 合成SUCCESS＋拒否、ERROR＋応答、timeout＋部分応答、非0exit、壊れたJSON/型/未知フィールドは非0。
- 拒否を優先し全理由保持。自動retryなし。shell連結せずJSONフラグは-pより前。
- 外側process timeoutでもbytes/str/Noneのstdout/stderrを正規化し、stderrの未知内容をstderr_unrecognizedとし、error/no-output、JSONのERROR/deny/契約違反を保持する。部分応答・IDは診断用に保持し、非0・未完了・打切りを維持する。
- 継続の記録なし/別workspace/既失敗/ID不一致は拒否。child例外後lock解放と記録更新。
- JSONの重複キー・非標準数値は拒否し、後続値で拒否を上書きさせない。
- 会話記録の必須項目・型・run_id・取得ID対応を検査する。success_candidateでもERROR/exit異常/reasons/deny/truncated/response=nullを継続させず、起動前に定型理由で停止する。
- 有限並列の各結果/ID分離、全workspace排他。画像は返却IDだけ、旧画像/symlink/他会話fallback拒否。
- 厳密commandテンプレートは空白日本語pathを許し、連結/部分式/改行/過剰許可/deny globを拒否。
- Claude/Codexの実際のgateへ外側起動を渡し、専用ロール境界を緩和しない。
- アンカー不一致/前置き未検証/画像欠落を採用しない。wrapper成功は候補で意味的完了は呼出agentが別途確認する。
- CLI公開stdoutではerror/response/拒否情報/画像pathを秘匿し、理由/status/exitは保持する。生診断は0600のlocal result.jsonだけに保存する（r2レビュー是正）。fixture環境説明の利用者homeは秘匿する。

## r4 是正差分の試験契約

実行対象は commit 1940b14 ＋未commit是正差分。責務別テストはcaller必須・本番注入拒否・公開無効果項目撤去・CLI複数prompt結果・workspace待機・未知stderr・版不一致未起動/版記録・path許可集合・作成時0600/最小会話記録を検証する。hookはhandler直接起動による合成入力でありliveセッション発火の証明ではない。adoption APIは未接続のため撤去し、成果採用はagent契約で確認する。全層監査はruntimeから呼ばれるが実効adapter未達のSTOPを維持する。

最終成績書は tests/reports/TR-agy-delegate-606-synthetic-final-r4.md。過去試験の件数/合否を再認定しない。同一未merge PRの是正のため既存版遷移を維持し追加bumpしない。mutation recheckは --skip-inspection 仮追加で否定テストがFAILすることを確認し、finallyで本体を復元する。

TC: `tests/unit/test_agy_delegate_merge_guard.py` は合成 Request を本番 resolver の `verify_runtime` に渡し、停止理由が1つもないことを検査する受入テスト1件。Issue #628 の AC 未達の間は意図的に赤、adapter により未確認理由が解消すれば緑となる。実機設定・agyを使わず、skip/削除/期待値反転で解除しない。

同workspaceは順次バッチ。10秒超の偽agyをCLIで2prompt実行し成功すること。gitなし前後差分、symlink非追従、観測不能をテストする。
