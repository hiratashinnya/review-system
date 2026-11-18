# 2026-08 / 09 部分照合

対象154件。Open Issue の PR 関連状態と旧スナップショットの矛盾候補。本文記述が歴史的スナップショットなら追加検証が必要。

- #284「agy-mcp-bridge のローカルパッチを更新・再 clone 後も安全に維持する」：廃止・置換可能性の要確認。参照PR: #259 closed
- #285「CLAUDE.md の codex-review 要約を正本の安全な実行契約へ同期する」：廃止・置換可能性の要確認。参照PR: #260 closed
- #291「PR #260: silent-failure 診断資産と codex-review の安全な実行契約を確立する」：廃止・置換可能性の要確認。参照PR: #260 closed, #259 closed
- #333「FND「検査対象探索の欠陥」と「ミラー未同期」を1件に統合すべきか（双方 ERROR・同じ下流損害）」：PR #326 merged / PR #326 で起票した open FND 2件が、**同じ下流の損害を根拠に、どちらも ERROR** になっています。。参照PR: #326 merged
- #375「pr-reviewer の finding をファイルハンドオフ化する（主文脈のコンテキスト通過を止める）」：PR #697 merged / | （新規） | Write パス制限の hook 依存（fail-open の限界） | #803 | PR #697 レビュー由来（F-375-26）。#694 項目 (10) と境界を設けた |。参照PR: #697 merged, #341 merged, #479 merged, #696 merged
- #547「blocker_gate に非ブロッキング診断チャネルを追加し、機械可読レポートとして publish する」：PR #479 merged / - **緊急度をP2/Nextとする理由**：PR #479のギャップは現存するが、誤ALLOWやfail-openは発生していない実測。#461の実装を中断してまで割り込む優先度ではない。。参照PR: #479 merged
