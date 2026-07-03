検証ツールがトレース（ノード抽出・整合検査）の対象とするファイル集合を、include / exclude の glob パターンで画定する実インスタンス。exclude されたファイルは out-of-graph 扱いとなりノードを持たない。
**ファイルパス**: `docs/doc-system/config.yaml`
**主要項目**: `trace_scope:` 配下。`include: ["doc-system/**/*.md"]`・`exclude: ["docs/**", "**/README.md", "**/00-dashboard.md", "**/00-dfd.md"]`（ダッシュボードと DFD 図はノード非対象）。

---

## PROMPT（プロンプト）
