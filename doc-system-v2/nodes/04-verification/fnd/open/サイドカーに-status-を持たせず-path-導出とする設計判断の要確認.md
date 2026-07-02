**指摘**: status（FND=open/resolved 等）を path で表す設計は `git mv` を伴う。id が path 非依存の
slug のため参照は壊れないが、多状態型（Q の4状態）ではディレクトリが増える非対称が生じる。

**深刻度**: low（設計判断の記録・オーナー確認済みで path 化を採用）。

**推奨**: FND/Q/DD とも status を path 化し、遷移は reconciliation が `git mv`＋edge逆転として機械実行する。

> 注: 新フォーマットのサンプル FND。**status=open は path（.../fnd/open/）で表現**し、サイドカーには持たない。
> これは open 状態のサンプルであり、resolved へ移すときは `.../fnd/resolved/` へ `git mv` する（id 不変）。
