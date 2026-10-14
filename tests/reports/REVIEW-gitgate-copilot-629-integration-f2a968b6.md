# PR #640 main統合後の独立ローカルレビュー（Codex）

対象: f2a968b6cf78d0ca54ac1e45c167bb706a91615c。初回実装・是正・再検証担当と別コンテキストで実施。既存sessionのモデル設定を継承し、系統/層の新選択やresolved ID生成は行っていない。

## 1. 判定

clean（凍結code/docsと今回のmain統合内容に対するローカルレビュー）。新findingなし、F-629-01 resolvedを維持する。最新main適合の全unitと最終証跡追加は実行中/未完成のため、作業全体完了・PR CI合格・追加push済み・merge可能とは判定しない。

AGENTS.mdと.ai/agents/pr-reviewer.mdを読み、権限・共有台帳を扱う高リスク変更として、固定経路、fail-close、回復、CAS、最小権限、正本同期、既存consumer退行を確認した。共有code/追跡ファイル/branch/commit/push/外部投稿を変更せず、書込は今回のhandoff report/findingsのみ。仮説再現・手元test runnerは今回実行していない。

## 2. 読了範囲と統合整合

`git diff --no-ext-diff d5ede837 f2a968b6` は38 files、全2372行。1–100、101–200、201–300、301–400、401–500、501–600、601–700、701–800、801–900、901–1000、1001–1100、1101–1200、1201–1300、1301–1400、1401–1500、1501–1600、1601–1700、1701–1800、1801–1900、1901–2000、2001–2100、2101–2200、2201–2300、2301–2372を欠番なく末尾まで読み、旧629実装、全保存証跡、今回例外rationaleを確認した。最初の広い表示は切詰めがあったため、この範囲読取で全差分を読み直した。未読のPR固有diffはない。

変更production moduleの本文、既存start/continue/live/tests/resolution/abort/commit、公開dispatch、canonical ledger read/update/atomic writerとClaude fallback、両hookの変更関数と呼出箇所を追跡した。Copilot正本、fixer現行契約、base integration契約、生成instructions全126行、r1/r2/final-evidence/TRは末尾まで確認した。

親列は厳密に `[dd78c17a2430304f6738826dc80353e8a24ed61a, d5ede8370a8cc39745c172c0e7dbfbedabee132b]`、treeは8962e8bbdcd43a0188543dec127dd81336ce4199。dd78→f2の対象解消箇所とrationaleを読み、mainのCopilot Agents停止template/同一surface/runtime準備追記とPRのbase節、fixerのモデル証跡追記とpolicy1.2が両方残ることを確認した。merge-tree exact記録の競合対象は.github/copilot-instructions.mdのみ。生成headerのplatform-source SHA256は統合正本の実bytesから求めたb0a5933ae86454289a0a3fd5c08597fdf5706848c16e357b2ed20b6628469abbに一致する。

model_policy/、asset_parity/、.ai/model-policy.jsonの全24pathはd5とf2でbyte一致。さらにdd78→f2の全61pathのうち、今回の統合SoT/生成物/rationale/TDの5path以外の上流56pathもd5とf2で全てbyte一致する。上流45+16filesの既存処置自体を新規に再レビューしたという主張はしない。任意参照した旧merge-treeの大量上流表示は今回の網羅性の根拠に使用しない。

## 3. 安全境界と証跡

認可はdispatch用entriesと分離したbase_authorizationsに保存しauthorized/revokedで管理する。登録はclean/live OPEN same-repository PR/fresh fetch/exact head/base OIDを確認し、一意session/workspace/repository/branch/requestへ束縛する。未完了operation中再登録とsession変更を拒否し、終端再登録は旧認可をrevokedとして履歴を残す。両collectionを対象に予約CASとpending publish fenceを行い、既存writerはdocument全体を保存するため認可を失わない。F-629-01の是正はmain統合で戻っていない。

固定--no-ff --no-commit、厳密な引数schema、任意strategy/option/command禁止、成功かつ非ゼロunittest、内容CAS、全2親とtree、解消対象外の編集拒否、API不要abort/recoveryを共通engineで維持する。Claudeのrunning issue-fixer境界、Codex/unknown entry拒否、両host全roleのCopilot登録CLI拒否、raw merge/PR merge/auto-merge禁止を維持する。incoming保護はCopilot guidanceも追加する方向であり、今回のowner例外を製品恒久gate緩和にしていない。Copilotをhost認証/role認証/sandboxとは説明していない。新規production moduleは70行と14行、stdlibのみ、既存worktree_ledger/baselineへのPR固有差分はない。

旧target43成功、旧全unit中断exit130、0件runner期待失敗、是正中setup失敗49/50件を最終成功とは扱っていない。r1 finding open→r2 resolved、disposition fix-here、最終旧版2031件/9skipの履歴を分けて記録している。今回のf2保存ログのうち対象50件/57.347s/OK/exit0、model_policy check OK/exit0、guidance_sync check OK/exit0は確認した。これは保存済みローカル検証の読取でありPR CIの成功ではない。今回全unit/残check/完成版TR/後続証跡commitは本レビューの確定範囲外として次回追確認する。

## 4. Finding / 次の処置 / Owner report

### F-629-01
harm: real
harm_detail: Copilot認可をdispatchのrunning entryとして保存すると、後続Claudeのworktree差分束縛がambiguous-runningとなり既存実行経路を利用できなくなる。
severity: major
scope: in
locus: [gitgate/base_copilot.py::register, gitgate/base_records.py::authorization_records, issue_start/worktree_ledger.py::resolve_worktree_for_agent]
summary: 認可を専用base_authorizationsとauthorized/revoked lifecycleへ分離した是正を維持している。
evidence: f2a968b6の全PR固有diff2372行とregister/authority/records/journal/既存atomic writer/fallback本文を確認し、認可はentriesへ追加されず通常writerも専用collectionを保存する。
expected: 認可とoperation証跡を保持し、Claude dispatchがない時の既存worktree差分束縛を妨げない。
recheck: tests.unit.test_base_copilotの登録/pending/committed/abortedのfallback、実running拒否、再登録revoked、dispatch更新保持、破損collection拒否の対象ケースと保存ログを照合する。
status: resolved
disposition: fix-here

新findingなし。主文脈はF-629-01 resolvedを既存fix-hereのまま保持し、全unitと5checks終了後に完成TR・保存ログ・証跡追加diffを本reviewerへ渡して追確認する。code/docsがf2から変わった場合は別途再レビューが必要。

これは追加push前のexact local統合OIDレビューでありremote PR差分取得は未実施（rtk未配置）。リモート公開headとの同一性・PR checks・fresh blocker/owner reportは主文脈の後続確認対象。現時点でowner reportは未取得であり、cleanをGitHub承認やmerge認可として扱わない。ownerの手動merge判断には公開後の最新checks/fresh blocker reportが必要で、reviewerはmergeしない。
