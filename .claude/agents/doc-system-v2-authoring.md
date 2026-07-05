# doc-system v2 著作コントラクト（全 `*-author` 共通・正本 = `doc-system-v2/FORMAT.md`）

各 `*-author` エージェントはこの共通契約に従って v2 ノードを著作する。型別の PREFIX・必須辺・
本文フォーマットは各エージェント側に残す。ここは **出力形態・slug 採番・サイドカー・辺記法** の共通部。

> 正本は `doc-system-v2/FORMAT.md`・`doc-system-v2/config.yml`・`doc-system-v2/schema/sidecar.schema.json`。
> 本ファイルはその著作向け要約。食い違ったら FORMAT.md を正とする。

## 1ノード = 2ファイル

v2 は 1ノード = **本文 `{slug}.md`（Markdown のみ）＋ サイドカー `{slug}.yaml`（属性）** の対。

- `{slug}.md` … **本文のみ**。属性・バッジ・`---`/`## ` 境界・YAML を一切書かない。
- `{slug}.yaml` … サイドカー。下記キーのみ（`schema/sidecar.schema.json`・未知キー禁止）。

## id / slug 採番（連番 id は廃止）

- **id = ファイル名 stem = slug = `slugify(title)`**。型 prefix ＋連番（`SPEC-15` 等）は**使わない**。
- slug は **唯一実装 `doc-system-v2/slugify.py` を再利用**して算出する（独自に正規化しない）：
  ```bash
  python3 -c "import sys; sys.path.insert(0,'doc-system-v2'); from slugify import slugify; print(slugify('ここにタイトル'))"
  ```
- グローバル一意はここで保証しない＝**reconciliation-validator が書込前に `dsv2 check-slug` で fail-close**
  判定する（DD-22・Sub-D）。著作側は衝突しにくい**識別的なタイトル**を付ける責務のみ。
- 階層（旧 `X-N` 親子）は **path でも id でも表さない**。親子関係は **同型間の無名依存辺**（子→親）で表す。

## サイドカー `{slug}.yaml` のキー（これ以外禁止）

```yaml
title: "読めるタイトル（末尾に condition マーカーを書かない）"
version: "0.1.0"        # MAJOR.MINOR.PATCH。新規は 0.1.0
condition: normal       # テスタブル型のみ。normal|boundary|empty|failure|error。非テスタブル(傘)は省略
labels: []
scheduled: "<current_phase 値>"  # 既定 = current_phase（config.yaml）。後送りはオーナー承認時のみ空/別値
suppress: []            # 抑制 RULE 番号のリスト。RULE-005/007 は抑制不可
suppress_reason: ""     # suppress 非空なら必須（理由は本文でなくこの属性・機械可読）
edges:
  - to: "参照先ノードの-slug"   # 無名依存辺。slug（path 非依存）を書く
    ref_version: "0.1"          # 参照時点の相手サイドカー version の x.y（2パート）
    note: "任意の補足"          # 任意
```

- **持たない**：`id`（=stem）・`type`（=path 第2階層）・`status`（=path 第3階層）＝二重管理回避。
- **edges は無名**：`kind`/`status` を書かない。`to` は **1辺1 slug**（リスト記法禁止・OR は複数辺）。
- **ref_version = 参照先サイドカーの `version` の x.y**（バッジではなく `{参照先slug}.yaml` の version 上2桁）。
- TR 専用: `result: PASS|FAIL` ＋ `log_ref`。設計要素の実現担体は `carrier`（値集合の SoT = `schema/sidecar.schema.json` enum: `skill`/`agent`/`command`/`instructions`/`hooks`/`code`）。
- **`scheduled` の既定 = `current_phase`**（config.yaml）。「無計画な空」は禁止。後フェーズへ回すのはオーナー承認時のみで、その旨を残す（空/別値）。post-mvp の大枠は `labels` で表す。

## 出力先（tmp のミラーレイアウト）

v2 は **corpus と同じ path を tmp 下にミラー**して対で置く：

```
tmp/<sprint>/<parent-id>/nodes/<stage>/<type>/[<status>/]{slug}.md
tmp/<sprint>/<parent-id>/nodes/<stage>/<type>/[<status>/]{slug}.yaml
```

- `<stage>/<type>` は `doc-system-v2/config.yml: layout` に従う（型→dir はそこが唯一の機械可読ソース）。
  例: SPEC → `02-what/spec`／P → `03-analysis/p`／MOD → `05-design/mod`／FND(open) → `04-verification/fnd/open`。
- lifecycle 型（fnd/q/dd/pend）は `[<status>/]` を必ず挟む（`config.yml: status_dirs`）。新規 FND は `fnd/open/`。
- このミラーにより **reconciliation-validator は `doc-system-v2/validate.py <tmp/.../parent-id>` を直接走らせて**
  schema＋path＋id 一貫性（stem == slugify(title)）を機械検証でき、**reconciliation は `nodes/**` 部分木を
  corpus へそのまま反映**できる（path から type/status が導出されるため配置先が一意）。
- 親ノードを更新する場合も、その `{parent-slug}.yaml`（＋必要なら `.md`）を同じミラー下に置く。

## sprint の取得

`sprint` 未指定なら `doc-system-v2/config.yml` の `current_stage` ではなく、運用の current phase
（従来どおり `docs/doc-system/config.yaml` の `current_phase`）を用いる。指示で渡されたら従う。

## 受け入れチェック（全型共通・書込前）

- [ ] 1ノード = `{slug}.md`＋`{slug}.yaml` の対で出力（本文に YAML/バッジを書いていない）
- [ ] `{slug}` = `slugify(title)`（doc-system-v2/slugify.py で算出・stem と一致）
- [ ] サイドカーに `id`/`type`/`status` を書いていない（path から導出）
- [ ] edges は無名（`kind`/`status` なし）・`to` は単数 slug・`ref_version` は参照先 version の x.y
- [ ] `to` の slug がすべて実在（RULE-007: always_error）／必須依存辺が存在（config `must_link_to`）
- [ ] `scheduled` が非空（既定 = current_phase・空はオーナー承認済み後送りのみ）／suppress 非空なら `suppress_reason` あり
- [ ] tmp のミラー path が `nodes/<stage>/<type>/[<status>/]` に一致（config.yml layout）
