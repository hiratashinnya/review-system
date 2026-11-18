# Issue #466「stateReason が DUPLICATE / null の closed Issue が UNKNOWN 扱いになり、blocker gate と Project Status 同期を止めうる」

- URL: https://github.com/hiratashinnya/review-system/issues/466
- 状態: closed（2026-11-18取得）
- 本文: 3806文字/ 63行。全文: `../raw/issues-2026-09.jsonl`
- AC: 6件（未チェック: 6）
- Issue参照: #465, #460, #345, #295, #297, #298
- PR参照: #465
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ### 実測（2026-09-03・主文脈が GraphQL で全走査） | ### なぜ blocker gate 側にも及ぶか | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- `blocker_gate/github.py` の `_graphql_state` は Issue の状態を `IssueClass` へ写像するとき、`OPEN` / `CLOSED`+`COMPLETED` / `CLOSED`+`NOT_PLANNED` の3通りだけを認識し、**それ以外をすべて末尾の `return "UNKNOWN"` で `UNKNOWN` に落とす**。
- - **露出面が gate と同期ツールで大きく違う**：issue-start gate は着手時に**1 Issue の到達閉包**しか見ないが、Project Status 同期は毎回**全 open item の閉包の和集合**を評価する。同じ性質の欠陥でも、後者が踏む確率は桁違いに高い。
- - **`DUPLICATE` を `CLOSED_COMPLETED` として扱う**：重複先で対処されるという解釈。ただし重複先が open なら実際には未解決であり、ブロックを見逃す方向（fail-open）になりうる。
- - [ ] **将来 GitHub が新しい `stateReason` を追加した場合の扱いが決まっている**（未知値を無条件に `UNKNOWN` へ落とす現在の挙動を維持するのか、別の既定に倒すのか）。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
