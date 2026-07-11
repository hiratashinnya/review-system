---
name: doc-system-v2-authoring
description: 'Shared doc-system v2 authoring contract common to every `*-author` agent (requirements-author, spec-author, analysis-author, design-author, verification-author): output shape (1 node = `{slug}.md` body + `{slug}.yaml` sidecar pair), slug/id assignment, sidecar key schema, unnamed edge notation, tmp mirror layout, and the scheduled self-judgment prohibition. Type-specific PREFIX/required-edges/body-format rules stay with each `*-author` agent — this file covers only the shared part. NOT an invocable task agent by itself; it is a shared reference doc linked from the author agents.'
model: claude-sonnet-5
tools:
  - read_file
  - grep_search
  - file_search
---

> **正本 = `.claude/agents/doc-system-v2-authoring.md`**（doc-system v2）。本ファイルはその GitHub Copilot 版ミラー。食い違ったら正本と `doc-system-v2/FORMAT.md` に従う。

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

### `scheduled` 値決定の自己判定禁止（再発防止・Issue #185／PR #150）

新規ノード著作時に `scheduled` を既定 `current_phase` へ設定する上記の運用は確立済みの標準動作であり、この既定適用自体は自己判定に当たらない。しかし**既存ノードの `scheduled` を一括変更・backfill する著作**（新規作成に伴わない値の書き換え）で、書き込む具体的な値を指示元（Issue 本文・オーナーコメント・呼び出し元指示）が明示していない場合は次を厳守する：

- `current_phase` と一致する・件数が機械検算と合う・`validate.py`/`dsv2 drift` がクリーン等、いかに機械的に検証可能であっても、それを根拠に値の妥当性を自己判定して著作を進めてはならない（CLAUDE.md「スケジュール独断禁止」＝`scheduled` の値決定はオーナー専権。実インシデント：PR #150 で `scheduled: "sprint-1"` への558件一括backfillが、指示側の値明示が無いまま `current_phase` 一致を根拠に「許容範囲」と自己判定された）。
- **STOP しなくてよいケース**：指示元が具体的な値そのものを明示している場合（例：「`scheduled` を `sprint-1` に設定してください」「このノードは `sprint-2` へ繰り越してください」）。その明示指示を機械的に反映するだけなので自己判定には当たらず、通常どおり著作してよい。
- **STOP すべきケース**：値が指示に明示されておらず、著作エージェント側で妥当性を推測して補う必要がある場合。著作を中断し、呼び出し元へ対象 slug・件数・推測した値・推測根拠を明記して STOP し、オーナー確認を要請する。

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
- [ ] `scheduled` が非空（既定 = current_phase・空はオーナー承認済み後送りのみ）。**既存ノードの一括変更/backfill で値を自己判定していない**（上記「`scheduled` 値決定の自己判定禁止」参照・Issue #185）
- [ ] tmp のミラー path が `nodes/<stage>/<type>/[<status>/]` に一致（config.yml layout）
