---
id: TR-jev-hooks-572-b7ff3e5-worktree
version: 1
condition: boundary
td_id: TD-jev-hooks-572
result: FAIL
log_ref: jev_hooks/verify/logs/TD-jev-hooks-572-b7ff3e5-unit-worktree.txt
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

## 実測（2026-10-06）

TD版1、基準実装commit `b7ff3e5f9c6a1368ec0c0a0882c26e4b8a946846`＋未commit作業tree、質問/ルール版1.1、Python3.12.14/managed Linux。公開前の検証であり、公開commitのCI結果とは区別する。snapshotは検証対象のsource/configと関連README・規範をpath/sha256で収録し、証跡を除外して循環stampを避ける。

- source snapshot SHA256: `e8fa1ea43aa51fa41587a82ca02c976312634e449b3d038dee0b49169d39d079`
- [snapshot manifest](../logs/TD-jev-hooks-572-b7ff3e5-source-snapshot.json)

| ケース | 実測 | 生ログ |
|---|---|---|
| C1/C2 | SDK0.7.2導入済venvで60件すべてPASS、skip0。標準環境は60件中58PASS、任意SDK実体2件skip。実API通信なし | [SDK](../logs/TD-jev-hooks-572-b7ff3e5-sdk-pass.txt) / [標準環境](../logs/TD-jev-hooks-572-b7ff3e5-stdlib-pass.txt) |
| C3/C4/C5 | キー欠損/復旧/再送、秘密除去、通知metadata、匿名export/counters/review、意味R4関連性と独立した機械条件を上記60TCでPASS | 同上 |
| C6 | 既存unit19件＋新tool-root3件＝22PASS。新3件はJev/time_fixture_lint両folderでsubtestし、無保護fixture consumer、Python epoch、保護literalを確認 | [既存19](../logs/TD-jev-hooks-572-b7ff3e5-lint-unit-pass.txt) / [新3](../logs/TD-jev-hooks-572-b7ff3e5-lint-tool-root-pass.txt) |
| C7 | time_fixture_lint 16hits/violations0。maintainability violations0/accepted_debt134。git diff --check成功 | [time](../logs/TD-jev-hooks-572-b7ff3e5-time-check-pass.txt) / [保守性](../logs/TD-jev-hooks-572-b7ff3e5-maintainability-pass.txt) |
| C8 | 全unit2105件を501.934秒で完走。11fail/1error/11skipでFAIL。今回由来marker1failを修正し、governance全12件PASS。残10fail/1errorは旧HEADでも再現 | [全unit FAIL](../logs/TD-jev-hooks-572-b7ff3e5-unit-worktree.txt) / [旧HEAD切分け](../logs/TD-jev-hooks-572-b7ff3e5-unit-baseline-fail.txt) / [governance修正後](../logs/TD-jev-hooks-572-b7ff3e5-governance-pass.txt) |
| C9 | CIと同じ固定pyright1.1.390を宣言path3件へ実行。0errors/0warnings/0informations | [pyright](../logs/TD-jev-hooks-572-b7ff3e5-pyright-pass.txt) |
| C10 | mock shadow/Stop block/PreToolUse deny、jevキー欠損enforce/shadowの5合成stdinケースPASS。stdout JSONのみ、exit0、匿名counter確認 | [stdin](../logs/TD-jev-hooks-572-b7ff3e5-stdin-pass.txt) |

### 全unit失敗の原因と処置

`.claude/rules/02-decision-process.md`への分類表追記で規範集合hashが変わり、配送用写しmarkerが不一致になった。`.claude/hooks/governance-directives.md`の中核本文を照合し、今回の変更は分類表追加だけで中核規範契約を変えないことを確認した上でmarkerを`220f0ecb50d6`へ更新した。governance suite12件はすべてPASS。

残る失敗は変更前のgit archive HEADに同じ12 TCを隔離実行して切り分けた。旧HEADのmarker TCだけPASS、残10fail/1errorは同様に再現した。内訳はrate-limit hook8件（managed環境のno-op/fixture command境界）、bwrap uid map read-only2件、インストール済Codexのfeature catalog unknown1error。関連コードは変更していない。全unit成功とは主張せず、公開後のGitHub CI全suiteで判定する。

全unit開始時に新canaryは`tests/unit/`で3件読み込まれていた。最終配置は現行決定に合わせ`tests/time_fixture_lint/`へ移し、両tool folderでsubtestを追加して直接discover3件を再実行した。従って次のCIのunit rootは2102件相当＋新root3件であり、2105件ログの探索pathと最終配置はこの差を持つ。hook TCは別の直接discover60件として検証済みで、中継はない。

### 外部レビュー追跡

| ID | 最終対応と境界 |
|---|---|
| XR-571-1 | PR #577でshadow採用決定済み。実装取込みのみで、結線・観測窓開始・enforce移行は実施しない |
| XR-571-2 | 課金認可済み。SDK直前に外送証拠を限定し既知秘密を除去。未知秘密完全検出は保証しない、独自秘密はsecret_env_varsへ宣言する |
| XR-571-3 | TCはtests/jev_hooksへ集約、SDK/evaluator移設、中継削除。新lint TCはtests/time_fixture_lint。CIとlintが3rootsを直接対象とする。旧レビューはgit mv、TD/TR/ログはtoolverify |
| XR-571-4 | jevキー欠損はenforceでStop block/PreToolUse deny、shadow {}＋固定監査。unknown/低確信/API障害は通過し通知metadataを保存。notice_delivery=not_connected、実配送なし |
| XR-571-5 | audit schema1、匿名相関ID、rule別分母/候補/拒否、coverage/dimensions、export consumer、人のpositive/false_positiveレビュー。元SQLite/本文/キーをGitへ保存しない。保持分だけの集計で、期間フィルタ・全期間精度ではない |
| XR-571-6 | Issue #572は既存labels集合を保存してarea:harness/audit:2026-09-pipeline-redesign追加。分類表へjev_hooks追加と配送marker追随 |
| XR-571-7 | R4適用/操作/step/回復の独立意味質問で補完。実行成功、paired tool ID/入力、最新試行、fingerprint/契約はコードで要求。保護操作を含む混合コマンドは意味回復yesでも迂回不可。意味精度未検証 |

旧F-572-001〜004と38件成功の制御証跡は[移設した履歴](jev-hook-review-history.md)を参照し、今回のXR系列と分ける。[修正前FAIL TR](TR-jev-hooks-572-b7ff3e5-before-fail.md)のログは保存し、今回の成功で上書きしていない。

settings結線、merge、実API、実通知配送、実Jev意味精度、WSL実機、Claude Code実セッション、設計HTML照合は実施していない。GitHub CIは公開後に別途確認する。他ツールの移設/他workflowの固定path追随は#578の範囲。
