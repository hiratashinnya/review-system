---
id: TD-ci-anomaly-report-461
version: 1
condition: normal
---

# 目的

Issue #461 の配送経路が、`.github/workflows/` 配下の全 workflow の `main` 最新完了 run
から failure と warning annotation を収集し、SessionStart では異常時だけ context を返すことを
確認する。取得・契約エラーは session を止めず完全に沈黙することも固定する。

# 前提

- collector API は fake transport で決定化する。
- hook の fetch は一時 local bare remote を使い、ネットワークと GitHub 認証に依存させない。
- production remote に対する API response shape は `gh api` の read-only 実測で補完する。

# 手順

1. failure run と warning annotation、clean run、新規 workflow、dynamic workflow、collector 自身、
   cancelled run を fake API へ与える。
2. anomaly report と clean report を local orphan branch に publish し、hook を起動する。
3. branch missing、remote unreachable、未知 schema でも hook を起動する。
4. SessionStart 設定と blocker-snapshot からの reusable workflow call を静的検査する。
5. repository 全 unittest と coverage を実行する。

# 期待結果

- failure は `error`、warning annotation は `warning` として必須メタデータ付きで出力される。
- workflow 名の allowlist はなく、repository-owned workflow が動的に対象になる。
- clean report は空配列で、hook は stdout/stderr とも無出力になる。
- anomaly 時だけ SessionStart additionalContext が出力され、診断データを命令扱いしない注意を含む。
- fetch/branch/schema の失敗は常に exit 0・無出力になる。
- 全 unittest が PASS し、coverage HTML が生成される。
