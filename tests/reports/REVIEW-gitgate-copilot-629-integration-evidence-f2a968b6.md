# PR #640 統合後証跡の独立追加確認（Codex）

対象: 既にcode/docsレビュー済みのf2a968b6cf78d0ca54ac1e45c167bb706a91615c → 証跡HEAD bc0a9eba86d1a19428763eacd7fa5bea749cd404。前回と同じ独立reviewerが保存証跡を追加確認した。既存sessionを継承し、モデル系統/層の再選択、resolved ID生成、LLM呼出しは行っていない。

## 1. 判定

追加確認はclean、新findingなし。F-629-01 resolvedと既存disposition fix-hereを維持し、前回のcode/docs clean判定を維持する。前回残した全unit/残check/完成TR/証跡commitの未確認範囲は今回解消した。新findingがないため新ラウンドfindingsの再取込を要求しない。

## 2. 確認範囲と整合

f2→bc0の全追加diffは12files（tests/logs9＋tests/reports3）、全570行。1–100、101–200、201–300、301–400、401–500、501–570を切詰め・欠番なく末尾まで読了した。diffの全pathがtests/logs/またはtests/reports/に属することを機械確認し、code/docs/生成asset/既存ledger/baselineに追加差分がない。bc0の親はf2のみで、確認終了時HEADはbc0、git status --porcelainは空だった。

検証対象OIDは全実行ログ・TR・PR草稿でf2に一致する。f2の実親列は厳密にdd78c17a2430304f6738826dc80353e8a24ed61a、d5ede8370a8cc39745c172c0e7dbfbedabee132bで、treeは8962e8bbdcd43a0188543dec127dd81336ce4199。integrityログと既レビュー結果に一致する。現正本の実SHA256もb0a5933ae86454289a0a3fd5c08597fdf5706848c16e357b2ed20b6628469abbに一致した。

全unitログを最終stdoutとexit記録まで確認した。実runner結果は2083 tests / 376.927s / OK (skipped=10)、プロセスexit0。末尾のreport.htmlや負例エラー文を追加失敗とは扱わず、保存された最終runner結果とTRの主張が整合する。対象ログは50 tests / 57.347s / OK、exit0。

5checksはasset_parity 41assets/0 MISSING/18 heuristic staleness、maintainability violations=0 accepted_debt=94、time_fixture violations=0、guidance_sync check OK、model_policy check OKで、全てexit0。integrityもexit0。停止agentとtracked-runtimeの包含はmodel_policy/__main__.pyのcheck分岐に至る前の両検査を本文確認し、両workflowの正式model_policy check呼出しも確認した。

skip-inventoryを末尾まで読み、退役Codex経路の固定skip9件とrate-limit testの動的skip1件を分けていることを確認した。後者の単独再実行は1 test / OK(skipped=1)で理由を保存する。既存test_rate_limit_hook.pyのnow.hour >= 21条件と全unit開始22:54 UTCは整合する。この補助実行を全unitの件数に加算していない。

完成TRの実測、親列/tree/sourcehash/上流24file byte一致、旧履歴の扱いは保存ログと整合する。旧実装の43件/2031件・skip9、旧中断exit130・setup失敗を今回の2083件/skip10と混同していない。独立codeレビュー記録は当時の未確認事項を保持し、完成TRも今回の追確認待ちとして正確に表現している。

PR草稿tmp/_handoff/issue-629-pr-body.mdも冒頭AI表記から末尾Closes #629まで読み、今回の検証値、local信頼操作者認可/非sandboxの限界、固定engineとnamespace分離の説明を照合した。草稿は追加push前のローカル検証と明示し、更新後PR CIを未確認、完成TR/証跡追加追確認を待ちとしており、この確認直前時点の事実に一致する。

## 3. 次の処置とOwner report

主文脈は今回追確認のcleanとreportを保存し、TR/PR草稿の追確認待ち記述を結果参照へ更新できる。code/docsはf2の凍結を維持する。reviewerは追跡保存、TR/PR草稿編集、commit/push、外部投稿、テスト再実行、branch変更を行っていない。今回の書込は指定の本reportのみ。

保存済みローカル検証の整合確認であり、更新後PR CI合格・GitHub承認・PR merge認可を意味しない。追加push後の公開head同一性、PR checks、fresh blocker/owner reportは主文脈の後続確認対象であり、ownerの手動merge判断へ渡す必要がある。reviewerはmergeしない。
