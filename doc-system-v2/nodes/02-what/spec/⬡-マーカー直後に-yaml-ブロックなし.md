**概要**: `⬡` マーカー直後に YAML ブロックがない場合のパース異常（RULE-024）。検証アサーションは子 SPEC-32-1〜2 を参照（出力と中断を1アサーション1SPEC に分割・FND-59）。
**例**: `doc-system/03-analysis/02-io.md` 行20に `⬡ I-1 · v0.3.0`、行21が `## I-1-1:` → `ERROR|doc-system/03-analysis/02-io.md:20|RULE-024|(none)|⬡ marker at line 20 has no YAML block following`。
