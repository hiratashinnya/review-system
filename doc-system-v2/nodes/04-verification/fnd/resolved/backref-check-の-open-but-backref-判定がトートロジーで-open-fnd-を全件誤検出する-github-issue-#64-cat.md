**改訂理由（z バンプ v0.1.0→v0.1.1・issue #158 lifecycle 配置整理）**:
本文上は 2026-07-01 に resolved 済みだった本 FND を、path 由来 lifecycle とも整合するよう `fnd/open/` から `fnd/resolved/` へ移動した。既存の `edges: []` は維持し、処置対象は out-of-graph の v1 archive 実装資産（`archive/backref-v1/check.py`。起票時は `backref/check.py`）のため対象ファイルへ backref は張らない。in-graph 代表 backref は既に SPEC「ノード本文に孤立 `---`（ノード分離記法の本文内誤用）が存在しない」から `→FND` として存在するため、重複追加しない。lifecycle 配置のみの整理であり、下流意味内容を変えないため z バンプとする。

**対応状況**: resolved（2026-07-01・本セッション内で修正・回帰テスト追加完了）

**深刻度**: ERROR

**指摘対象**: `backref/check.py` の `check()` 関数内 `open-but-backref-exists` 判定（修正前の行 `fid in index.dependents.get(e.to, ())`）

**指摘時 ref_version**: 付与先なし（指摘対象 `backref/check.py` は out-of-graph のためノード版なし）

**内容**:

`backref check` の `open-but-backref-exists` 判定は、open な FND が forward 辺 `fid→e.to` を持つとき、対象 `e.to` が既に `→fid` の backward 辺を保有している（＝辺逆転が未完で forward/backward が同時存在する）状態を検出することを意図している。しかし修正前の判定式が

```python
fid in index.dependents.get(e.to, ())
```

となっており、これは**トートロジー**であった。`index.dependents[e.to]` は「`e.to` を指す辺の始点集合」であり、open FND は自身の forward 辺 `fid→e.to` を持つため `fid` は必ずこの集合に含まれる。すなわち open な FND が forward 辺を 1 本でも持てば判定は**構造的に常に真**になり、対象 `e.to` が実際に `→fid`（fid への backward 辺）を持つかどうかを一切見ていなかった。

正しくは「対象 `e.to` が `→fid` の backward 辺を持つか」＝「`fid` を指す辺の始点集合 `index.dependents[fid]` に `e.to` が含まれるか」を判定すべきで、式は `e.to in index.dependents.get(fid, ())` でなければならない。

このバグにより、**open かつ forward 辺を持つ FND 全件**（FND-35, FND-79, FND-81, FND-82, FND-83, FND-88, FND-89, FND-91 の計 8 件）が、実際には辺逆転未完ではないにもかかわらず誤って `open-but-backref-exists` ERROR として報告されていた（GitHub issue #64 の Category A）。

特に **FND-35 はオーナー承認済み sprint-2 で意図的に open のまま据え置かれていたノード**であり、この誤検出に基づいて `python -m backref reverse --apply` を適用すると、**オーナー判断を無視して強制的に resolved 化してしまう危険**があった（スケジュール独断禁止・CLAUDE.md に反する破壊的操作）。機械判定の false positive がオーナー承認済みのスケジュール決定を破壊しかねなかったため、深刻度は **ERROR** と判定する。

**再現手順**: 空の open FND（`resolved` 未設定）が forward 辺を 1 本持つだけの最小フィクスチャで `python -m backref check` を実行すると、対象ノードに `→fid` の backward 辺が一切無くても `open-but-backref-exists` が発火する。既存テスト `tests/unit/test_backref_cli.py::test_check_open_but_backref` は本来 `P-100→FND-100` の逆辺を追加してから検証する意図だったが、その逆辺を追加する前の状態（対象に backward 辺が無い状態）でも既に誤検出していたことが判明した。

**修正内容**:
- `backref/check.py`: `open-but-backref-exists` 判定を `fid in index.dependents.get(e.to, ())`（トートロジー）から `e.to in index.dependents.get(fid, ())`（「対象 `e.to` が `fid` への backward 辺を持つか」を正しく判定）に修正。
- `tests/unit/test_backref_cli.py`: 回帰防止テスト `test_check_open_without_backref_is_not_flagged`（open FND が forward 辺のみを持ち対象に backward 辺が無い場合は `open-but-backref-exists` を発火しない）を追加済み。
- バックリファレンス付与先なし（指摘対象 `backref/check.py` は out-of-graph）。reconciliation で確認した結果、`open-but-backref-exists` 判定は config.yaml の `fnd_lifecycle` にも in-graph SPEC にも定義がない check.py 固有の追加検査（FND-108 の `_drift` は SPEC-9／RULE-004 で仕様化済みだった点と異なる）であり、本 FND を backref すべき関連 SPEC は存在しない。よって `SPEC-9 → FND-112` 辺は付与しない（無関係な RULE-004 ドリフト検査への誤ったトレースを作らないため）。

**関連して発見した第二の不整合（FND-94 の本文フォーマット）**: 本バグの修正後に `backref check` を再実行したところ、Category B の対象であった FND-94 が新たに resolved-no-dd3 で発火した。調査の結果、FND-94 の本文が G1/G4/G9 サブセクション間の区切りとして `---` を使用しており（`04-notation.md`「複数ノードを同一ファイルに置く場合は `---` で区切る」＝ノード分離専用の規約に反する）、`backref/locate.py` の `find_body_region`/`_is_boundary`（孤立 `---` 行を無条件でノード境界とみなす）がこの内部区切りで本文を截断し、実在する `**指摘時 ref_version**:` 行を「本文」の範囲外にしていたことが判明した（コードは正しく動作しており、原因は FND-94 側の規約違反）。`locate.py` 側は変更せず、FND-94 の内部 `---` を削除して規約に合わせる形で是正した（実質内容の変更なし・FND-94 側で z バンプ記録済み）。
