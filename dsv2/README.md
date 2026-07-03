# dsv2 — doc-system v2 ツール（フォーマット依存マップ）

doc-system **v2**（1ファイル1ノード＝`.md` 本文＋`.yaml` サイドカー・slug id・path 導出 stage/type/status・
無名依存辺）向けの索引・照会・辺逆転・改題・HTML ビューア生成ツール。**標準ライブラリのみ**。`python3 -m dsv2 <cmd>`。

サブコマンド: `index`（meta.json 生成）/ `deps` / `dependents` / `orphans` / `drift` /
`reverse`（FND 辺逆転）/ `rename`（slug 改題）/ **`build-view`**（`meta.json`＋本文 → 単一 `doc_view.html`・Sub-F #75）。

新フォーマットの正本は `doc-system-v2/FORMAT.md`・`doc-system-v2/config.yml`・
`doc-system-v2/schema/sidecar.schema.json`。サイドカー YAML の読取は既存 **`docidx.nodeyaml`** を再利用する
（独自 YAML パーサを持ち込まない）。

## フォーマット依存マップ（モジュール → 依存する仕様・キー）

| モジュール | 依存フォーマット事実 | 一次アンカー（版付きノード）＋補助（out-of-graph） |
|---|---|---|
| `meta.py` | path `nodes/<stage>/<type>/[<status>/]{slug}` から stage/type/status を導出。`LAYOUT`/`STATUS_DIRS` は `config.yml` の `layout`/`status_dirs` と一致させ、不正配置は `MetaError` で fail-close。サイドカーは `title/version/condition?/labels/scheduled/suppress/suppress_reason?/result?/log_ref?/carrier?/edges`（`suppress` 等は #81 で正式化）を集約。`id`=ファイル stem。 | 補助: FORMAT.md「path 規約」「1ノード=2ファイル」・config.yml `layout`/`status_dirs`。※ 版付きノード未整備（Sub-B 移行後に SCM/SPEC で整備予定）。 |
| `query.py` | `deps`/`dependents`/`orphans`/`drift`。**RULE-004 ドリフト**＝辺の `ref_version`(x.y) ≠ 参照先サイドカー `version`(x.y.z) の x.y（z は不問）。参照元が `suppress: [RULE-004]` を持つ辺は drift 免除（#81 で正式化・DD-2）。`orphans`(RULE-005=always_error) は suppress 無視で正。 | 補助: FORMAT.md「版（DD-8 踏襲）」「edges」・config.yml（RULE-004 / always_error）。 |
| `yamledit.py` | サイドカー yaml の行ベース最小改変（version z バンプ・edges 追加/削除/retarget）。コメント保持＝**消さない（PR8）**。 | 補助: FORMAT.md「edges」「版」・DD-8。 |
| `reverse.py` | FND 辺逆転＝forward(`FND→対象`)削除＋backward(`対象→FND`)付与＋DD-3 本文凍結＋z バンプ＋`git mv`（`fnd/open/`→`fnd/resolved/`）。status は path 導出。 | 補助: FORMAT.md「status 遷移（git mv）」・config.yml `fnd_lifecycle`（DD-16）・DD-3。 |
| `rename.py` | slug 改題＝`.md`/`.yaml` 改名＋全 referrer の `edges[].to` 一括張替え（meta.json 経由）。 | 補助: FORMAT.md「id / slug」（rename ツール）。 |
| `viewer.py` | `meta.json`＋各ノードの `.md` 本文から**単一 `doc_view.html`** を生成（`build-view`）。stage/type/status フィルタ＋`ls` 風階層ブラウズ・deps/dependents/親子（同型辺）表示・**ドリフト可視化**（辺 `ref_version` x.y ≠ 参照先 x.y・`suppress:[RULE-004]` 免除）・最小 Markdown レンダラ（見出し/リスト/コードフェンス/強調/リンク/引用・HTML エスケープ）。**deps/dependents/drift は `query.py` を再利用し CLI と完全一致**。データは `<script type="application/json">` にインラインし**外部 CDN/ネットワーク参照ゼロ**（オフライン自己完結）。 | 補助: FORMAT.md「1ノード=2ファイル」「edges」「版」・config.yml `layout`/`status_dirs`（stage/type/status 並び）。ドリフト規則は `query.py`（RULE-004・DD-2・#81）。 |
| `gitutil.py` | `git mv` の薄いラッパ（失敗時 FS フォールバック）。 | — |
| `cli.py` | サブコマンド配線。終了コード 0/2/4（2=未検出 or argparse 用法・4=前提違反）。 | — |

**再利用**: `docidx.nodeyaml.parse`（サイドカー yaml の限定 YAML 読取）。

## meta.json の管理方針（生成物）

`dsv2 index` は `<root>/meta.json`（既定 `doc-system-v2/meta.json`）を生成する。これは**生成物**であり
**手編集・コミットしない**（`.gitignore` 済み）。FORMAT.md「meta.json＝生成物・手編集しない・再生成で最新化」に従う。
照会系（`deps`/`dependents`/`orphans`/`drift`）は `meta.json` があれば読み、無ければディスク走査で構築する
（stale 回避のため照会前に `index` を推奨）。改変系（`reverse`/`rename`）は常にディスク走査で現状を反映する。
`build-view` も同様に `meta.json` を読み（無ければ走査）、既定で `<root>/doc_view.html` を出力する。**`doc_view.html`
も生成物**（`.gitignore` 済み・`build-view` で再生成）でコミットしない。

## 依存仕様の版付きアンカーについて（CLAUDE.md 準拠）

CLAUDE.md「依存仕様の参照原則」に従い、本ツールの依存フォーマット事実は**版付き in-graph ノードを一次アンカー**に
すべきだが、v2 のフォーマット定義ノード（SCM/SPEC 等）は**移行（Sub-B #71）後に整備**するため現時点は未整備。
それまでは `FORMAT.md`/`config.yml`（out-of-graph・版なし）を補助ナビとして参照する。版付きノード整備後に
各 docstring と本マップの一次アンカーを差し替える。
