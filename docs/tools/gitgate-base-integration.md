# PR base 取り込み契約（gitgate-base-integration/1.0）

設計判断・決定履歴は `.ai/rationale/gitgate-base-integration-594.md` に保持する。版注記: 初版導入と同一 PR 内のレビュー是正は一つの版遷移に属するため、当該是正では policy 1.0 を維持する。

## 凍結した設計

- module: `gitgate/base_*` は限定 Git 操作・live PR 検証・snapshot・台帳状態・解消検証を分離する。origin正規化は既存の共通 `branch_source.policy` を使う。
- interface: 通常 Claude issue-fixer の `integrate-base --repository OWNER/REPO --pr N --expected-head OID --expected-base OID`、`integrate-base-continue [--test-module dotted.name ...]`、`integrate-base-abort`。固定schemaで、任意ref/option/strategy/commandは受けない。
- protocol: 同一repositoryのOPEN PRのbase exact OIDをheadへ `--no-ff --no-commit` で取り込む。成功でも確定前はpending。衝突はexit 3とファイル一覧、判断不能・protectedはSTOP。既に祖先ならno-change。
- persistence: canonical main worktree ledgerの当該dispatchにoperation ID、entry/role/task/agent/attempt/workspace、元HEAD/base/MERGE_HEAD、stage indexと内容snapshot、PID/start token、状態・テスト結果・親列を保存する。予約前と確定時にCAS。worktree内の偽stateは権威にしない。
- orchestration: trusted hookのfixer identityとlive ledgerを併用し、通常Claudeのrunning dispatchだけを許可する。platform欠落の既存Claude entryは互換扱い、Codex supervisor・unknown platform・openだけのentryは拒否する。
- prompt: fixerは衝突内容を編集し判断できないものをSTOP。専用continueが衝突ファイルだけstageし、固定unittestと内容CAS後に確定する。Codex supervisorは未対応なので取り込みが必要ならSTOPして報告する。
- log/version: policy 1.0、operation schema v1。開始・テスト・確定・abortは履歴を残す。testing/abortingも実行中のPID/start token予約を保持し、side effect完了または停止して戻るときに解除する。
- test strategy: 実bare remote + linked worktreeとfake read-only PR APIで正常・衝突・continue・abort・tamper・drift・test failure・予約競合拒否を検証。両PFのhookで非fixerとraw merge/PR mergeを拒否し、通常CLIでCodex supervisor entryの拒否を確認する。

## 利用と停止条件

開始はcleanな専用Claude fixer worktreeに限る。remote URL、live PRのrepository/head/base/default branch、fresh fetchのhead/baseと入力exact OIDを照合する。fork、closed、同じhead/base、default branch、detached、dirty、既存merge/rebase/cherry-pick/revertは拒否する。PR自体のmerge/auto-mergeとraw git mergeは全ロールで禁止を維持する。

衝突編集中は通常 `gitgate commit` / `push` を拒否する。continueは非衝突stageのすり替え、無関係な編集、未解消index、MERGE_HEADのすり替えを拒否する。固定unittest経路の成功、テスト前後の内容CAS、全親列 `[元HEAD, base OID]` とtreeを検証して確定する。任意shell test commandは渡せない。`--test-module` がなければ `unittest discover -s tests/unit` を実行し、0件は成功扱いにしない。これは通常fixerのテスト経路であり、テストrunner自体のsandboxや共通Git read-onlyを保証するものではない。

abortはPR APIに依存せず、自分のoperationと現在のHEAD/MERGE_HEADを照合する。開始後の編集（無関係なtracked/untrackedも含む）をmainの `tmp/_base_integration_recovery/<operation>-<reservation>.tar` へ保存してから `merge --abort` を実行する。Gitの解消編集を失う操作なので保存先を返す。偽operation、foreign merge、保存不能なら実行しない。

Codex supervisorの取り込み接続は未対応であり、取り込みが必要ならSTOPして報告する。supervised innerの共通Git read-only境界を維持する。protected/契約資産のincoming changeは開始前にSTOPし、古い契約で編集を続行しない。別host入口やraw Gitで未対応経路を代替しない。

## 変更不能時の回復

API failure・OID drift・test failure・CAS mismatchは変更を保存してSTOP。通常publishは未完了operationを受理しない。プロセス死亡後に予約状態が残る場合も成功扱いや新規開始をせず、束縛されたmergeをabortするか保存成果物をオーナーが確認する。
