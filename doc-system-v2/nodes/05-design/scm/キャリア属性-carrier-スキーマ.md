設計層ノードのサイドカー（`{slug}.yaml`）が持てる `carrier`（実現担体）フィールドの型・値集合を定義する。設計要素を「どの担体で届けるか」を機械可読に表し、とりわけ各 skill PROMPT ノードが `skill`／`agent` のいずれの届け方かを判定できるようにする（本 issue の主対象は PROMPT だが、enum は設計層全般に適用される）。技術的制約は `doc-system-v2/schema/sidecar.schema.json` の `carrier` enum が機械可読 SoT として既に強制しており、本ノードはその事実を在グラフの自己記述として可視化する。

**フォーマット**: JSON Schema draft 2020-12 の `string` 型＋`enum` 制約（`doc-system-v2/schema/sidecar.schema.json` の `carrier` プロパティ）。1ノード1サイドカー YAML 上の任意（optional）・単数値フィールド。
**必須フィールド**:
- `carrier`（文字列・任意・単数値）: 設計要素の実現担体（realization carrier）。値は下記 enum のいずれか1つ。該当担体を持たない設計要素（純スキーマ等）では省略する。
  - enum = `skill` ｜ `agent` ｜ `command` ｜ `instructions` ｜ `hooks` ｜ `code`
  - `instructions` = CLAUDE.md 等の常駐コンテキスト、`code` = Python 実装。値集合の SoT は `sidecar.schema.json` の本 enum（v2 正準フィールド・オーナー承認 2026-07-03・enum 化＝Issue #93）。
