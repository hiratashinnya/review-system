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
   cancelled run、100件を超える annotation、workflow 単位の API/response error を fake API へ与える。
2. anomaly report と clean report を local orphan branch に publish し、hook を起動する。
3. branch/report missing、remote unreachable、壊れた JSON、未知 schema、oversized report、fetch
   timeout、Python crash でも hook を起動する。改行・制御文字を含む非信頼値と大量 anomaly も与える。
4. SessionStart の matcher/command path/timeout と workflow の permissions/reusable call/concurrency
   group を構造的に静的検査する。
5. repository 全 unittest と coverage を実行する。

# 期待結果

- failure は `error`、warning annotation は `warning` として必須メタデータ付きで出力される。
- workflow 名の allowlist はなく、repository-owned workflow が動的に対象になる。
- collector 自身も対象になり、個別 API/response failure は collection error を残して後続を継続する。
- 100件境界を越えた collection も次ページまで取得する。
- clean report は空配列で、hook は stdout/stderr とも無出力になる。
- anomaly 時だけ SessionStart additionalContext が出力され、非信頼値は無害化・引用され、入力と
  context のサイズ上限を超えない。
- fetch/branch/report/schema/Python の失敗は常に exit 0・無出力になる。
- 全 unittest が PASS し、coverage HTML が生成される。
