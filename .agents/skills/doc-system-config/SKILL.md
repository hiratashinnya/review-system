---
name: doc-system-config
description: doc-system-v2/config.yml の作成・解説・変更を支援する。設定キーの責務、対応する SPEC/SCM/CFG/PROMPT ノード、dsv2 検証コマンド、#141 review_system 横展開との境界を扱う。
---

すべての説明・報告・質問は日本語で行う。ユーザーが明示的に別言語を指定した場合を除き、この skill の応答も日本語に統一する。

# doc-system-config

`doc-system-v2/config.yml` を触る前に、設定変更の根拠・影響・検証をそろえるための手順。

## いつ使うか

- doc-system v2 の config キーや接続規則を説明する。
- `must_link_to` / `must_be_linked_from` / `exact_link_counts` / `fnd_lifecycle` / `rule_activation` / `prompt_coverage_targets` / `trace_scope` などを変更する。
- config 変更に必要な SPEC/SCM/CFG/PROMPT ノードの有無を確認する。
- GitHub issue #140 の範囲で doc-system 側 config 操作を支援する。

## 使わない場合

- review_system 側の config 操作エージェント化。これは issue #141。
- 一般的な構造化 config スキーマ設計。新しい外部ファイル形式をゼロから設計する時は `schema-design` を使う。
- corpus ノードの直接著作。ノード作成・更新は AGENTS.md の authoring pipeline に委譲する。

## 手順

1. **現状を読む**
   - `doc-system-v2/config.yml`
   - `doc-system-v2/FORMAT.md`
   - `doc-system-v2/RECOMMENDED_PROCESSING_ORDER.md`
   - 変更対象に関係する `doc-system-v2/nodes/05-design/{cfg,scm,prompt}/**` と `nodes/02-what/spec/**`
2. **変更種別を分類する**
   - 値の説明だけか。
   - 既存キーの値を変えるだけか。
   - 新しい top-level key / enum / rule を増やすのか。
   - dsv2 / validate.py / schema の実装変更が必要か。
3. **根拠ノードを確認する**
   - `PROMPT` は SPEC への辺が必要。
   - `CFG` は SCM と SPEC への辺が必要。
   - `SCM` は SPEC への辺が必要。
   - 根拠が無ければ config だけを変更せず、必要ノードの著作を先に計画する。
4. **変更を最小化する**
   - issue #140 では doc-system 側だけを扱う。
   - #141 review_system 横展開に必要な差分は残作業として列挙し、この PR で実装しない。
   - #127 / #128 以降には進まない。
5. **検証する**
   ```bash
   python3 -m dsv2 index --root doc-system-v2
   python3 -m dsv2 dashboard --root doc-system-v2
   python3 doc-system-v2/validate.py
   python3 -m dsv2 drift --root doc-system-v2
   python3 -m dsv2 prompt-coverage --root doc-system-v2
   ```

## config キーの見方

- `layout` / `status_dirs`: path から type/status を導出する配置規約。
- `body_policy`: Markdown 本文の要否。TD/TC/SRC の bodyless/shared-body 判定に影響する。
- `must_link_to` / `must_be_linked_from`: RULE-006 系の接続規則。
- `exact_link_counts`: TD-TC 1:1 など、min-one より強い接続本数制約。
- `fnd_lifecycle`: open/resolved FND の辺方向と残留辺検査。
- `decision_spine`: DD/Q/PEND の義務辺。
- `rule_activation`: RULE ごとの発火開始 stage。
- `coverage_rules`: FR condition coverage などの網羅規則。
- `prompt_coverage_targets`: RULE-032 が PROMPT ノード欠落を検査する対象 skill 集合。
- `trace_scope`: dsv2 が in-graph として読むファイル集合。

## 完了条件

- [ ] 変更した config キーと理由を説明できる。
- [ ] 対応する SPEC/SCM/CFG/PROMPT ノードまたは「根拠未整備のため停止」を明示した。
- [ ] #140 の範囲に収まっており、#141 の横展開を実装していない。
- [ ] dsv2 index/dashboard/validate/drift/prompt-coverage が通っている。
