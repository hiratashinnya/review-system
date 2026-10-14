# PR base 取り込み契約（gitgate-base-integration/1.2）

設計判断・決定履歴は `.ai/rationale/gitgate-base-integration-594.md` と `.ai/rationale/gitgate-copilot-base-integration-629.md` に保持する。policy 1.2（Issue #629）は、Copilot の明示的ローカル認可登録を追加した MINOR である。固定取り込み protocol と operation schema v1 は維持する。

## 凍結した設計

- module: `gitgate/base_*` は限定 Git 操作・live PR 検証・snapshot・台帳状態・解消検証を分離する。origin正規化は既存の共通 `branch_source.policy` を使う。
- interface: Claude issue-fixer と登録済み Copilot 操作者の `integrate-base --repository OWNER/REPO --pr N --expected-head OID --expected-base OID`、`integrate-base-continue [--test-module dotted.name ...]`、`integrate-base-abort`。固定schemaで、任意ref/option/strategy/commandは受けない。
- protocol: 同一repositoryのOPEN PRのbase exact OIDをheadへ `--no-ff --no-commit` で取り込む。成功でも確定前はpending。衝突はexit 3とファイル一覧、判断不能・protectedはSTOP。既に祖先ならno-change。
- persistence: canonical main worktree ledgerの当該dispatch（`entries`）または明示認可（`base_authorizations`）にoperation ID、entry/role/task/agent/attempt/workspace、元HEAD/base/MERGE_HEAD、stage indexと内容snapshot、PID/start token、状態・テスト結果・親列を保存する。予約前と確定時にCAS。worktree内の偽stateは権威にしない。
- orchestration: trusted hookのfixer identityとlive ledgerを併用し、通常Claudeのrunning dispatchまたは明示登録済みCopilot専用認可だけを許可する。platform欠落の既存Claude entryは互換扱い、専用認可を持たず `platform` が `claude` 以外のentry（台帳に残る `codex-supervisor` の既存entryとunknown platform）とopenだけのentryは拒否する。
- prompt: fixerは衝突内容を編集し判断できないものをSTOP。専用continueが衝突ファイルだけstageし、固定unittestと内容CAS後に確定する。Copilot は後述の明示登録経路を使う。その他の未対応実行環境ではSTOPして報告する。
- log/version: policy 1.2、operation schema v1。開始・テスト・確定・abortは履歴を残す。testing/abortingも実行中のPID/start token予約を保持し、side effect完了または停止して戻るときに解除する。
- test strategy: 実bare remote + linked worktreeとfake read-only PR APIで正常・衝突・continue・abort・tamper・drift・test failure・予約競合拒否を検証。両PFのhookで非fixerとraw merge/PR mergeを拒否し、通常CLIで `platform` が `codex-supervisor` の既存entryの拒否を確認する。

## 利用と停止条件

開始はcleanな専用Claude fixer worktreeまたは登録済みCopilot PR branch checkoutに限る。remote URL、live PRのrepository/head/base/default branch、fresh fetchのhead/baseと入力exact OIDを照合する。fork、closed、同じhead/base、default branch、detached、dirty、既存merge/rebase/cherry-pick/revertは拒否する。PR自体のmerge/auto-mergeとraw git mergeは全ロールで禁止を維持する。

衝突編集中は通常 `gitgate commit` / `push` を拒否する。continueは非衝突stageのすり替え、無関係な編集、未解消index、MERGE_HEADのすり替えを拒否する。固定unittest経路の成功、テスト前後の内容CAS、全親列 `[元HEAD, base OID]` とtreeを検証して確定する。任意shell test commandは渡せない。`--test-module` がなければ `unittest discover -s tests/unit` を実行し、0件は成功扱いにしない。これは通常fixerのテスト経路であり、テストrunner自体のsandboxや共通Git read-onlyを保証するものではない。

abortはPR APIに依存せず、自分のoperationと現在のHEAD/MERGE_HEADを照合する。開始後の編集（無関係なtracked/untrackedも含む）をmainの `tmp/_base_integration_recovery/<operation>-<reservation>.tar` へ保存してから `merge --abort` を実行する。Gitの解消編集を失う操作なので保存先を返す。偽operation、foreign merge、保存不能なら実行しない。

取り込み経路は通常Claude fixerのrunning dispatchと明示登録済みCopilot checkoutにある。未対応実行環境ではSTOPして報告する。protected/契約資産のincoming changeは開始前にSTOPし、古い契約で編集を続行しない。別host入口やraw Gitで未対応経路を代替しない。

## 変更不能時の回復

API failure・OID drift・test failure・CAS mismatchは変更を保存してSTOP。通常publishは未完了operationを受理しない。プロセス死亡後に予約状態が残る場合も成功扱いや新規開始をせず、束縛されたmergeをabortするか保存成果物をオーナーが確認する。


## Copilot の明示的ローカル認可

Copilot はローカル信頼操作者として、取り込み対象を明示登録する。これはホストやroleの認証ではなく、単一workspace・repository・PR・branch・head/base exact OIDへの操作認可である。環境変数や `platform` の自称値だけでは認可しない。通常cloneでも、live PRの非default head branch checkoutなら使える。

```sh
python3 -m gitgate integrate-base-copilot-register --repository OWNER/REPO --pr N --expected-head HEAD_OID --expected-base BASE_OID
python3 -m gitgate integrate-base --repository OWNER/REPO --pr N --expected-head HEAD_OID --expected-base BASE_OID
# 衝突したファイルだけ編集する
python3 -m gitgate integrate-base-continue
# 中止する場合
python3 -m gitgate integrate-base-abort
```

登録はclean tree・live OPEN same-repository PR・fresh fetch exact OID照合を行い、canonical ledgerの専用 `base_authorizations` collectionに認可内容と一意sessionを保存する。dispatch用 `entries` とは分離し、認可状態は `authorized` / `revoked` とする。開始の入力は登録内容と完全一致が必要。workspace・branch・repositoryの変更、pending中のsession切替・認可変更は拒否する。未完了operation中の再登録は拒否し、終端後の再登録は旧認可をrevokedにして履歴を保持する。abortはAPI無しで使える。

Claude/Codexのcommand hookは登録CLIを全roleで拒否する。Claude fixer専用境界、Codex既存台帳の拒否、raw mergeとPR merge/auto-merge禁止は維持する。Copilotはcommit/pushを必ずgitgate経由にし、pending中はwrapperが拒否する。Copilotには同等のproject hookがないため、raw Git・直接Python呼出し・台帳編集まで機械的に阻止するsandboxや認証済みroleは保証しない。既存Claude側も固定test runnerや台帳への直接書込を隔離するsandboxではない。固定engine内の戦略・オプション・テスト・CAS・親列・publish fenceは両経路で同じである。
