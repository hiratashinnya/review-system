# Copilot PR base 取り込み（Issue #629）

## 判断と比較

CopilotにClaudeのtrusted hook・role gate・dispatch worktreeを模倣させない。
明示的ローカル認可登録を採用し、固定engineを再利用する。登録は認証済み
Copilot identityではなく、信頼操作者が対象を狭く承認した記録である。
実行者のhost identityはCopilot環境から観測できないため状態として捏造しない。

| 案 | 評価 |
|---|---|
| platform値/環境変数だけを許可 | 対象操作の認可がなく、既存Claude identityと混同するため却下 |
| owner発行secret/capabilityファイル | 発行者を認証する外部基盤がなく、同じローカル権限で生成できるsecretは保証を増やさないため却下 |
| 明示的ローカル認可＋固定engine | live検証済み単一PR/exact OID/workspaceへ限定でき、不要なidentity保証を謳わずCopilotの通常cloneで実行できるため採用 |
| 手動Git取り込みだけを文書化 | Copilot固定経路とpending fenceのACを満たさないため却下 |

最小認可はrepository/PR/workspace/branch/head/baseと一意sessionである。
登録済みrequest以外の開始は拒否し、pending中はsession再登録を禁止する。
終端後の再登録は旧sessionをrevokedにし、認可とoperation履歴を残す。
Claude entryや既存Codex entryをCopilot entryへ書き換える経路は持たない。

## 凍結セット

- module: 100行以内のstdlib adapter `gitgate/base_copilot.py`。live API・snapshot・ledger lock・Git engineは既存moduleを再利用。
- interface: `integrate-base-copilot-register` は開始と同じ4引数のみ。3操作の固定interfaceは維持。
- protocol: 登録はclean/live OPEN same-repository PR/fresh fetch/exact OID。開始は認可一致、続行は既存固定unittest/内容CAS/2親/tree、abortはAPI不要。
- persistence: canonical `tmp/_worktree/ledger.json` の専用 `base_authorizations` collectionに認可とoperationを保存。通常cloneはroot内、linked worktreeは共有main内へ収束。登録も既存atomic locked writerを使う。
- orchestration: Copilotの信頼操作者が明示登録。Claude/Codex hookは登録CLIを全roleで拒否し、既存fixer-only境界は維持。
- prompt: Copilot guidance正本を編集しinstructionsを生成。commit/pushはgitgate、判断不能/契約変更/driftはSTOP。
- log/version: policy 1.1 → 1.2、operation schema v1維持。session/認可履歴と通常operation証跡を保存。
- test strategy: 実bare remote・通常clone・fake read-only APIで正常/衝突/abort、drift・再登録・session切替・test失敗/0件・CAS・publish fenceを確認。既存Claude/Codex回帰と全unit・3チェックを実施。

## 境界と限界

Copilotにproject hookがないためraw Git、直接Python、台帳直接編集を阻止する
sandboxではない。認可台帳へ書けるローカル操作者を信頼する。通常wrapper内で
固定merge戦略、任意Git option禁止、成功かつ非ゼロのunittest、内容CAS、2親/tree、
pending commit/push禁止がClaudeと同一のコードで強制される。Claude側の既存hookも
台帳やtest runnerへの直接ローカルアクセスを隔離するsandboxではない。

`.ai/guidance/` と `.github/copilot-instructions.md` をincoming保護対象へ追加し、
新経路の契約を古い契約で読み替えて続行することを拒否する。

## この実装作業限定の運用例外

2026-10-14、オーナーはチャットで「はい、進めてください」と、#629限定で
専用branchの別担当実装・検証と独立レビューを認めた。Codex transport退役により
正規dispatch不能だったための記録付き運用例外であり、protected dispatchやroleを
偽装していない。製品の恒常認可ゲートを緩和せず、push/PR公開前に成果を提示する。

## F-629-01 是正: dispatchと認可の名前空間

初回は認可をdispatch用 `entries` の `running` として保存したため、Claude consumerの
live dispatch判定が別workspaceのCopilot認可まで拾い、差分束縛を拒否した。
完了時だけreleasedにする案は登録中・pending中の退行を残すため却下。
Claude consumerへplatform特例を足す案は全dispatch lifecycle consumerへの波及を
招くため却下。認可はdispatchではないので `base_authorizations` へ分離する。
認可の状態は `authorized` / `revoked`、operationは既存のpending/終端状態である。
通常dispatch writerが専用collectionを保存する既存atomic locked writerを再利用し、
base adapterのみ両collectionのCAS、競合、pending publish fenceを検査する。
本物Claude runningの差分束縛拒否は維持し、認可が各operation段階にあっても
Claudeの単一候補fallbackは影響を受けない。公開前是正のため旧running認可の
移行経路は設けず、旧形式では認可拒否として安全側へ倒す。
policy 1.2は同一PR内のMINOR遷移途中の是正であり、共通guidanceの一PR一遷移に
従って据え置く。operation schema v1とshared ledger schemaも変更しない。
