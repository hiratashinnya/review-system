# dsv2-lookup — 回復手順（非規範）

meta.json が古い、候補の body_path が存在しない、または index と corpus の件数が合わない場合は、本文を丸読みして補正せず、`dsv2 index --root doc-system-v2` を安全な出力先へ再生成してから候補を絞り直す。既存の corpus ノードへ直接書き込んで整合を直してはならない。

外部検索を使う場合は source の既存登録を確認し、同じ source を再 index しない。重複登録や検索結果の stale が疑われる場合は外部索引の管理者へ報告し、リポジトリの node を検索結果に合わせて変更しない。
