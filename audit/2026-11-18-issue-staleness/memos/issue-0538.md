# Issue #538「Codex supervisor スタックを撤去し codex exec の薄いラッパーへ置き換える」

- URL: https://github.com/hiratashinnya/review-system/issues/538
- 状態: closed（2026-11-18取得）
- 本文: 13937文字/ 185行。全文: `../raw/issues-2026-09.jsonl`
- AC: 14件（未チェック: 0）
- Issue参照: #452, #448, #449, #451, #565, #603, #453, #459, #462, #463, #475, #477, #506, #518, #520, #233, #576, #604, #589, #638, #625, #533
- PR参照: #448, #233, #604, #638, #625
- 主見出し: ## 目的・背景 | ## #452からの引き継ぎ（2026-10-09・オーナー承認） | ## 設計確定事項（2026-10-10・オーナー承認） | ## 現状と根拠（実測・2026-09-22） | ### main に入っている #452 の実装 | ### 撤去の切り口はきれいである | ### フック側の実測 | ## 採用する実現方式（オーナー案・2026-09-22） | ## Scope | ## Out of scope | ## 要設計（オーナー明示の持ち越し事項） | ## Acceptance criteria
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- **しかしこの制約は「Codex が主文脈である」ときにだけ効く。** 主文脈を Claude Code にすれば、implementer/fixer の隔離は Claude Code 側の `isolation: "worktree"` が与えるか、`codex exec -C <worktree>` の1引数で足りる。**supervisor は前提ごと不要になる。**
- - #452は方式撤回を理由に `not_planned` でcloseする。#538完了まで#452をOPENで保持する従来方針を変更する。#452のcloseはsupervisorの完成・撤去完了を意味しない。
- - **範囲**：ラッパーの `/issue-pipeline` への組み込みは本 Issue に含める。Codex 主文脈前提の資産の整理は #603 とする。
- ## 現状と根拠（実測・2026-09-22）
- - **`permissions` 系キーは project-local `.codex/config.toml` で無視されるキーの一覧に含まれていない**ため、プロファイル定義自体はリポジトリに版管理できる（無視されるのは `openai_base_url` / `chatgpt_base_url` / `apps_mcp_product_sku` / `model_provider` / `model_providers` / `notify` / 
- - Codex 主文脈前提の資産（`.codex/agents/issue-implementer.toml`・`issue-fixer.toml`、`.agents/skills/issue-pipeline`、`.codex/hooks.json` の `spawn_agent` 用 gate、`asset_parity` の関連例外）の整理。#603 で扱う（2026-10-10 追記）。
- 2. **project trust が前提になる。** project-local の `.codex/config.toml` と `.codex/hooks.json` は **プロジェクトを trust するまで読み込まれない**（[Hooks](https://learn.chatgpt.com/docs/hooks)）。trust していない状態では user / system 層のフックだけが動く。trust 済みか否かで権限境界が変わる構成
- - Related: #565（素の `codex exec` が `AGENTS.md` の委譲指示で停止する。PR-B の spike で影響を実測）／#576（公開前 remote 検証要件の引き渡し。行き先は gitgate 側）／#603（Codex 主文脈前提の資産整理。本 Issue 完了後に着手）（2026-10-10 追記）

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
