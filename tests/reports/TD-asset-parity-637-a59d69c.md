---
id: TD-asset-parity-637
version: 1
condition: normal
result: PASS
log_ref: tests/logs/TD-asset-parity-637-a59d69c.txt
---
# 目的
Issue #637 全ACと F-617-36/38/39 を検証する。

# 前提
先行 PR #669 の head 8f4863b を凍結し、baseline は変更しない。

# 手順
- commit 後に全 asset_parity unit test を実行する。
- pyright 1.1.390 を repo root から asset_parity と test_asset_parity*.py に実行する。
- CI と同じ宣言ファイル全件に pyright を実行する。
- maintainability_lint を実行し、先行headからbaseline差分ゼロを確認する。

# 期待結果
- 原則skillの通常skill/prompt誤配置が exemption 有無・inline 有無にかかわらず JSON reason と text detail に出る。
- 両フラグ併記は principle を優先する。
- 仮想slot名は Windows 禁止文字を含まず、実ファイルもmirrorとして認めない。
- AST補助検査が文字列加算、大小文字、日本語・記号のpath要素を検出し、散文を除外する。
- 不正なPath引数は境界でTypeErrorとなる。
- unit tests と typecheck が成功し lint violations=0、baseline差分ゼロ。

## 実測
- TD版1 / 実装a59d69c / プロンプト雛形版・基準content_hash: 対象外
- 実行日時: 2026-10-19T12:22:26.501372+00:00 / Linux Python 3
- unit 116件 PASS、pyright 1.1.390宣言全件0 errors、lint violations=0 accepted_debt=77、下段8f4863bからbaseline差分ゼロ。F-637-01の完成値除外7式・実パス/動的断片検出7式を回帰確認。
