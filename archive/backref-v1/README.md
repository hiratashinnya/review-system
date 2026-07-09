# backref — FND バックリファレンス（辺逆転）の自動化

FND を resolved にするときの「辺逆転」を**決定的に機械実行**する write ツール。手作業の取りこぼし
（forward 辺の消し忘れ・backref 付与漏れ・DD-3 凍結記録漏れ・z バンプ忘れ）を排除する（issue #48）。
パース（ノード発見・file:line・edges）は read-only の [docidx](../../docidx/README.md) を再利用し、
本パッケージは**書込責務のみ**を担う。標準ライブラリのみ。

> 運用イメージ：正本への唯一の書込担当である `reconciliation` エージェントが、FND の辺逆転を手編集
> でなく `python -m backref reverse <FND-id> --apply` で実行する。

## 何を機械化するか（辺逆転の手順）

CLAUDE.md L27–29 / DD-3 / DD-16 / DD-8 §4 の手順：

1. FND の forward 辺（`→処置対象`）を削除し `edges: []`・`resolved: true` を付与（＋FND バッジ z バンプ）
2. 各**処置対象（通常ノード）**へ `→FND-x` backward 辺を付与（ref_version = FND バッジの x.y）＋対象バッジ z バンプ
3. **provenance**（宛先型 ∈ {FND, DD, Q, PEND}）は backref を張らず削除し、本文記録のみ（DD-16）
4. **削除済み対象**（グラフに不在）は「付与先なし」を本文に記録
5. **DD-3**：辺が消える前に `**指摘時 ref_version**:` を FND 本文へ凍結記録

## 使い方

```bash
python -m backref reverse FND-18              # 辺逆転の差分を表示（既定 dry-run・書込まない）
python -m backref reverse FND-18 --apply      # 正本へ書き込む
python -m backref reverse FND-2 FND-3 --apply # 複数 FND をまとめて
python -m backref check                       # 辺逆転の不整合を監査（read-only）
python -m backref check --id 'FND-1*'         # ID グロブで絞り込み
```

- `--root` でリポジトリ root を明示（既定: `doc-system/` を上方向に自動検出）
- `--config` で `config.yaml` のパスを明示（既定: `<root>/docs/doc-system/config.yaml`）
- 終了コード: `0` 正常 / `1` `check` で error 級あり / `2` 未検出 / `3` 用法 / `4` config・前提違反

## 安全設計（fail-close）

- **既定 dry-run**：`--apply` を付けない限り書き込まない（差分のみ表示）。
- **2 フェーズ（plan→apply）**：全ファイルの変更をメモリ上で算出・検証してから一括書込。途中失敗で部分破壊しない。
- **冪等**：対象に既に `→FND-x` があれば付与もバッジ更新もスキップ。
- **想定外フォーマットは停止**：summary バッジ・YAML フェンス・2スペース block list 等の想定形から外れたら `BackrefError` で停止（推測で書き換えて壊さない）。
- **既存の DD-3 行は上書きしない**（PR8「消さない」）。既存があり辺由来と食い違う場合は**警告して人手の照合に委ねる**。
- **改訂理由（散文）は自動記入しない**：機械生成した推奨文を提示するのみ（本文散文の破壊を避ける）。書込対象は edges／summary バッジ／DD-3 凍結行に限定。

## 自動化しない（人手の前段）

削除済み対象を生存ノードへ**張替**する判断（どのノードが役割を吸収したか＝FND-1 の ACTOR-3→P-1）は
人手。人が forward 辺を生存ノードへ張り替えてから `reverse` を実行する。本ツールは「現在の forward 辺」
をそのまま逆転する。

## フォーマット依存マップ（関数単位）

doc-system の Markdown／edge フォーマット仕様に依存する。仕様改版時は下表と各 docstring の
`依存仕様:` 行を見直すこと。

**参照原則（再発防止）**：`依存仕様` は **in-graph の版付きノード（SPEC-x / DD-x ＋ vX.Y.Z）** を
一次アンカーにする。`docs/doc-system/04-notation.md`・`02-meta-schema.md`・`config.yaml`・`CLAUDE.md`
は **out-of-graph で版を持たない**（ファイル frontmatter version は DD-8/FND-104 で廃止）ため、これらを
**唯一の根拠にしない**——版が無いと仕様変更を取りこぼす。補助（人間向けナビ）としてのみ併記する。
版付きノードがまだ無いフォーマット事実（例: edge スキーマが out-of-graph の meta-schema にしか無い）は、
その不足自体を FND/Q で起票する（FND-18 が同種の指摘）。

| 関数 / 型 | 依存ポイント | 依存仕様（in-graph 版付きノード／補助: out-of-graph・版なし） |
|---|---|---|
| `locate.find_yaml_block` / `find_edges_span` / `find_body_region` | summary 行→YAML フェンス／`edges:` block・inline／本文範囲（`</details>` 後〜次境界） | **SPEC-1 v0.3.0・SPEC-1-1 v0.1.1・SPEC-2 v0.3.0**（補助: 04-notation §3,§8・02-meta-schema §4） |
| `edit.bump_summary_z` | summary バッジ `vX.Y.Z`／backref 追加＝z | **DD-8 v0.1.1・DD-21 v0.1.1**（補助: 02-meta-schema §1） |
| `edit.render_edge_entry` | edge block 項目（`- to:`＋`ref_version`・2スペース） | **SPEC-2 v0.3.0**（補助: 04-notation §3） |
| `reverse`（provenance 分類・義務辺） | 宛先型 {FND,DD,Q,PEND} は backref なし／FND ライフサイクル | **DD-16 v0.1.0**（補助: config.yaml fnd_lifecycle） |
| `reverse`（DD-3 凍結行） | `**指摘時 ref_version**:` 記録形式 | **DD-3 v0.1.0**（補助: CLAUDE.md） |
| `reverse` / `check`（z バンプ種別） | backref 追加＝z | **DD-8 v0.1.1・DD-21 v0.1.1** |
| `check`（不整合分類） | resolved/forward/backward の義務辺 | **DD-16 v0.1.0**（`must_link_to`/`must_be_linked_from`/`must_not_link_to`・補助: config.yaml fnd_lifecycle） |

## スコープ外

グラフ全体の RULE 検証（docidx 同様 backref はその一部のみ扱う）、張替先の自動判定、本文散文の生成、
`.idx` キャッシュ。検証の網羅は doc-system 検証ツール側の責務。
