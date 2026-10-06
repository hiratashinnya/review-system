---
id: TR-jev-hooks-572-b7ff3e5-before-fail
version: 1
condition: boundary
td_id: TD-jev-hooks-572
result: FAIL
log_ref: jev_hooks/verify/logs/TD-jev-hooks-572-b7ff3e5-lint-canary-fail.txt
---
# Jev hook 追加レビューのテスト設計

## 目的

PR #571の外部レビュー指摘1〜7をXR-571-1〜7として追跡し、既存F-572-001〜004の履歴を保全する。秘密を除いた外送、必須キー欠損、未知判定の観測、匿名計測、R4の意味関連性と独立した機械証拠、tool別TC/TD/TR/ログ配置を検証する。

根拠は [レビュー5421961338](https://github.com/hiratashinnya/review-system/pull/571#pullrequestreview-5421961338)、[訂正6008386799](https://github.com/hiratashinnya/review-system/pull/571#issuecomment-6008386799)、[追加6008731178](https://github.com/hiratashinnya/review-system/pull/571#issuecomment-6008731178)、[配置・採用・課金決定PR #577](https://github.com/hiratashinnya/review-system/pull/577)（e446ddb）。採用と課金は決定済み、結線・実通知配送・enforce移行は本検証に含めない。

## 前提と凍結セット

- 実装はPython、mockは標準ライブラリのみ。公式SDK 0.7.2は任意依存で、HTTP MockTransport以外に通信しない。CIは固定requirementsを導入してSDK互換性TCもskipせず検証する。
- Hook JSON、質問・ルール版、設定、SQLiteの状態/匿名監査schema、Skill selector/semantic契約、request replay、tool対応、fingerprintを境界とする。SDK境界の秘密除去は外送直前に適用する。
- TCは`tests/jev_hooks/`へ直接配置し、CIは`tests/unit/`と`tests/jev_hooks/`を直接discoverし、新lint canaryは`tests/time_fixture_lint/`へ置いて同様に直接discoverする。TD/TR/ログはこの`verify/`へ保存する。旧レビュー履歴はgit mvで`reports/jev-hook-review-history.md`へ移設する。
- scanner公開API `scan` / `scan_fixtures` / `scan_python_literals` と `Finding` / `Report` は維持する。fixtureの置き場、既存allowlist、clock保護判定を変えず、検査rootsだけunit/Jev/time_fixture_lintの3CI rootsに拡張する。
- 変更で409行scannerのexact-content負債fingerprintが無効になるため責務分割し、変更moduleは100物理行以内、データとロジックを別fileとする。baselineは解消したscannerの2entryだけ削除し、免除を追加しない。
- オーナーのcommit/push前確認指示に従い、作業中の検証はbase commit＋未commit差分として記録する。公開commit確定後のCIとは区別する。

## 手順と期待結果

| ケース | 手順・TC | 期待結果 |
|---|---|---|
| C1 既存制御 | `python3 -m unittest discover -s tests/jev_hooks -v`。既存policy/evidence/runner/parallel/Skill契約と新機能のTCを直接探索 | 全制御TC成功。SDK未導入だけSDK実体TC任意skip、APIキー・実Claude Code不要 |
| C2 SDK実体 | `/tmp/jev-sdk-venv/bin/python -m unittest discover -s tests/jev_hooks -v`。transport、redaction、semantic経路をHTTP mock | skipなし。正常authheaderを保ちながらHTTP bodyから秘密canaryを除去。例外catchによる偽passを避け外側でbodyを検査 |
| C3 設定不備 | `test_safety_configuration.py`、`test_audit.py`でjev＋空/空白キー、shadow/enforce、mock、キー復旧・再送を検査 | jev/enforceのStop blockとPreToolUse deny、shadow {}＋missing_api_key監査。mock鍵不要、障害・unknownと区別。復旧後通過 |
| C4 観測 | `test_audit.py`でunknown/低確信/障害、shadow候補、再送、匿名export、review、保持件数と合成exportのcounter consumerを検査 | schema版・相関ID、ルール別分母/候補/拒否を再計算。raw本文・秘密なし。通知はmetadata/not_connected。reviewは人のpositive/false_positiveを記録 |
| C5 R4意味と機械証拠 | `test_skill_semantics.py`と既存boundary/contract/orderingで同義操作・関連検証・無関連/unknown・回復を検査 | 高確信意味yesを使うが、paired成功・最新試行・対象/契約一致なしでは完了不可。保護操作を含む混合コマンドは意味回復yesでも前提を迂回不可。自由文、失敗、途中/後の編集、重複で証拠を偽造しない |
| C6 lint roots | `python3 -m unittest discover -s tests/time_fixture_lint -v` ＋ `python3 -m unittest tests.unit.test_time_fixture_lint -v`。新rootのfixture消費者とPythonepoch違反、保護literalを合成する | 修正前3canary失敗→修正後成功。既存unit19＋新tool-root3の計22成功、fixture全rootの全参照に保護を要求 |
| C7 lint CLI | `python3 -m time_fixture_lint check`、`python3 -m maintainability_lint check`、`git diff --check` | 時刻違反0、保守性違反0。scanner負債2件解消でaccepted_debt136→134、免除追加なし |
| C8 全unit | `python3 -m unittest discover -s tests/unit` | 既存製品/汎用TCの回帰なし。hook中継に依存せずC1で全hook TCを探索 |
| C9 型検査 | 固定pyright 1.1.390をrepository rootから `.github/typechecked-files.txt` の宣言pathへ実行 | CIと同じ限定scopeで型error 0。全repoの型安全を主張しない |
| C10 stdin | 合成イベントをmock shadow/Stop拒否/Ask拒否/jevキー欠損shadow・enforceでCLIへ渡す | stdoutはJSONだけ、終了コード0、shadow {}、Stop block、PreToolUse deny、匿名counterを確認。実API通信なし |

## 検証の限界

38件成功は2026-10-05の既存制御結果であり、追加TC成功や意味精度の代替ではない。実モデルの意味精度・誤拒否率、WSL実機、Claude Code実セッション、設計HTMLとの照合は未検証。既知秘密/credential形式と宣言された環境値の除去であり、未知秘密の完全検出は保証しない。除外された証拠はunknownを増やす。元SQLite・会話・入力・秘密をGitへ含めず、リポジトリから参照するのは匿名metadataだけとする。他ツールの既存TC移設/他workflow固定pathsは #578 の範囲。

## 修正前の実測（失敗を保存）

- TD版: 1。基準実装commit: `b7ff3e5f9c6a1368ec0c0a0882c26e4b8a946846`。実行日: 2026-10-06。新TCは未commit作業treeまたは隔離したarchiveへ追加した。以下は意図した新回帰条件が旧実装で満たされない証拠であり、修正後の成功で上書きしない。
- C6: 新lint root canary3件は全失敗。fixtureに既存保護unit参照と無保護Jev参照を併置しても旧scannerはviolations0。Jev-onlyのPython epochも検出0、保護literalの検査自体も0件だった。[生ログ](../logs/TD-jev-hooks-572-b7ff3e5-lint-canary-fail.txt)。根因はtests/unit固定root。対策は両detectorが同じ3rootを走査すること。
- C2: 隔離した `git archive HEAD` と新SDK外送TCで1件失敗。HTTP bodyに合成値 `auth-canary` が残った。[生ログ](../logs/TD-jev-hooks-572-b7ff3e5-safety-fail.txt)。根因は外送直前の秘密除去が無いこと。対策は既知環境値/credential形式を除去し、送る証拠を限定すること。実API通信なし。
- C5: 隔離archive＋ `test_equivalent_operation_is_gated_before_success` は1件失敗。完全一致と異なる同義納品操作が `{}` で素通りした。[生ログ](../logs/TD-jev-hooks-572-b7ff3e5-r4-fail.txt)。根因は文字列selectorのみだったこと。対策は独立した操作/検証/回復/Skill適用関連性質問で補完し、paired成功など機械条件は保つこと。
- C7: scannerを最小変更した状態でも409行の既存module負債fingerprintが変わり、module-over-100-linesとdata-and-logic-class-cohabitationの2違反が出た。[生ログ](../logs/TD-jev-hooks-572-b7ff3e5-maintainability-fail.txt)。対策は責務分割と解消したbaseline2entryの削除。免除の追加・hash更新はしていない。
- このFAIL記録のC1/C3/C4/C8/C9/C10は修正前一括実行をしていない。旧38件制御PASSは別の[歴史記録](jev-hook-review-history.md)を参照する。修正後の対応は[PASS TR](TR-jev-hooks-572-b7ff3e5-worktree.md)に記録する。
