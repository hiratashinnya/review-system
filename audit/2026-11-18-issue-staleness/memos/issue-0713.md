# Issue #713「feat(issue-pipeline): フェーズ承認を一時タグで固定し、PR本文へSHAを残して通常マージ後に後始末する」

- URL: https://github.com/hiratashinnya/review-system/issues/713
- 状態: open（2026-11-18取得）
- 本文: 4316文字/ 77行。全文: `../raw/issues-2026-11.jsonl`
- AC: 9件（未チェック: 9）
- Issue参照: #710, #409, #705, #371, #662, #310, #375
- PR参照: なし
- 主見出し: ## 目的・背景 | ### 利用者価値 | ## 対象 harness | ## 現状と根拠 | ## 運用ルール（採用方針） | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: 時点記述あり・現行照合候補

## 本文内の現状・前提・依存記述（要時点照合）
- - 同Skillの「作成工程」では、1a/1b/2aに独立レビューと必要なowner decisionを要求する。2bのdraft PR作成までPR本文は存在しない。
- 7. **マージ後の後始末**: PRの`merged`・実際のmerge commitが2親であること・タグ対象SHAおよびPR headのmainへの祖先包含・PR本文へのSHA記録・対象タグの現在OID一致・他のオープンPRによる参照なし・既存worktree回収／解放を確認した後、**当該Issueの一時タグと作業ブランチのみ**削除する。リモートref削除は安全な対象限定／再確認付きで行い、既存の権限規律に従う。削除は冪等にし、失敗・検証不能なら
- 8. **未マージ時**: OPEN PR／未マージCLOSED PR／STOP中はタグを自動削除しない。中断・放棄時の処分は別途オーナー判断。歴史的・無関係なタグやブランチを一括削除しない。
- - [ ] OPEN／未マージCLOSED／squash／rebase／SHA不一致／ref更新競合／他PR利用中／回収未了は自動削除せず、理由を示して停止またはスキップする。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
