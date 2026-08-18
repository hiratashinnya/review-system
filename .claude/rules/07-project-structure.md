## このリポジトリ＝2つのプロジェクトが同居（混同注意）

**本リポジトリには独立した2つのプロジェクトが同居している。ファイルツリーが両者にまたがって混在するため、
今どちらを触っているかを常に意識する。**「正本」「MVP」「凍結セット」等の語はどちらの文脈かで指す実体が変わる。

### ① doc_system（仕様策定支援ツール・メタ側＝本リポジトリの開発方法論そのもの）
「どう仕様を作り、どう検証し、どう資産化するか」を扱う自己言及的（ドッグフーディング）なツール群。**review_system の
ドメイン内容（要件/設計/スキーマ等）はここには実質存在しない**（`doc-system-v2/nodes/**` の VAL/SR/FR 等は
「グラフの図的可視化」「トレーサビリティ」「自動整合性検証」のように doc_system 自身の目的を記述したノードで、
`review_system`/`review-system` への言及は横断ツール文脈の4件のみ）。

- **ノードグラフ（正本）**：`doc-system-v2/`（`nodes/**`＝要件〜検証層ノード、`00-dashboard.md`＝doc_system 自身の進捗ハブ、`config.yml`）
- **v1 archive（非活性・履歴保持）**：`doc-system-v1-archive/`（旧 `doc-system/`。issue #76 で retire・`git mv`）
- **CLI/ツール実装**：`dsv2/`（v2ノード操作・index/query/reverse等）・`archive/docidx-v1/`（v1専用検索・`python3 -m archive.docidx-v1`）・`archive/backref-v1/`（v1専用辺逆転）・`asset_parity/`（4ツリー資産整合監査）
- **機械定義ドキュメント（例外的に正本の一部）**：`docs/doc-system/`（config.yaml・templates・記法・接続マトリクス等。`config.yaml` の `trace_scope` は `docs/**` を除外済み）
- **エージェント/スキル定義**：`.claude/skills/`・`.claude/agents/`（大半は doc_system 自身の著作・点検・パイプライン運用向け。横展開先＝`.codex/`・`.github/skills|prompts|agents`・`.agents/skills`）
- **テスト**：`tests/unit/test_dsv2_*.py`・`test_docidx_*.py`・`test_asset_parity_*.py`・`test_agent_command_gate.py`・`test_codex_*.py`・`test_claude_review_mcp.py`（`.codex/mcp/claude_review/server.py` 対象）等
- **正本の所在**：`doc-system-v2/nodes/**`（ノードグラフ）＋ `.claude/`（資産・規約。規約本体＝
  `CLAUDE.md` ＋ `.claude/rules/*.md`＝本ファイルもその1つ）。
  - **注意：「正本の所在」と「起票先」は別軸**。`.claude/` 配下の改修すべてが Issue 運用になるわけではない
    ——著作・検証エージェントや仕様策定スキル14件のように**両システムに含有されるハーネス**の改修は、
    従来どおりノード起票＋ダッシュボード更新の対象になる。Issue 運用（`/gh-create-issue`）に回るのは
    `issue-pipeline` 系・実行環境フック等の**どちらのシステムにも含有されない汎用開発ハーネス**の改修に限る。
    前掲「起票先はプロジェクト区分で決める（`.claude/rules/02-decision-process.md`）」参照。
- MVP ターゲットは doc-system ノード（VAL/SR/FR ＋ `labels: post-mvp`）＝**doc_system 自身**の MVP スコープ（review_system の MVP ではない）。運用ハブ＝`doc-system-v2/00-dashboard.md`。
- 実装設計のデータ辞書／ドメインモデルは doc-system の DM/TERM ノード（`doc-system-v2/nodes/05-design/dm/`・`doc-system-v2/nodes/03-analysis/term/`＝各ノード1ファイル）。
- **実装前の凍結セット**：`doc-system-v2/nodes/05-design/` 配下（索引の考え方は `python3 -m dsv2 index` で meta.json 生成→grep/jq で参照。基盤＝`doc-system-v2/nodes/05-design/mod/`）。テスト戦略＝`/test-strategy`。

### ② review_system（開発対象の製品本体＝AIレビューツール）
「文書を評価基準に沿って AI レビューし、指摘を仕分け・自動修正・revert する」実際のアプリケーション。

- **実装**：`review_system/`（`domain/`・`core/`・`ports/`・`adapters/`・`persistence/`・`parsing/`・`prompts/`・`io/`）。**Python・原則標準ライブラリのみ**（Q5/Q5a：フロントマターも自前パーサ）。
- **テスト**：`tests/unit/test_domain.py`・`test_parsing.py`・`test_triage.py`・`test_compose_intake.py`・`test_pipeline_e2e.py`・`test_criteria_repo.py`・`test_apply.py`・`test_workspace_git.py`・`test_guard.py`・`test_cli_e2e.py`・`test_cli_p2.py`・`test_pr_fixes.py`（いずれも `review_system.*` を import）＋ 成績書 `tests/cases/`・`tests/reports/`・`tests/logs/`（TD/TC/TR の3点セット・`/test-strategy` のテーラリング運用）
- **ドキュメント**：`docs/` 配下（`docs/doc-system/` を除く全て）＝ `docs/requirements/`・`docs/design/`・`docs/schema/`・`docs/process/`・`docs/methods/`・`docs/dashboard.md`・`docs/minutes/`
- **正本の所在**：**`docs/` 配下**。①の「正本は doc-system-v2」は doc_system 自身の記述についての規定で、doc-system-v2 コーパスに review_system 固有の要件/設計ノードが無い以上 review_system には適用されない。`docs/design/README.md`（凍結セット8項目）・`docs/design/decisions.md`（DD#）・`docs/dashboard.md`（進捗・Q#）が実質的な確定記録として機能する。
- MVP スコープは `docs/requirements/12-mvp-scope.md`＋`docs/dashboard.md`（①の doc-system ノード MVP とは別物）。データ辞書／ドメインモデルは `docs/design/00-data-dictionary.md`・`01-class-design.md`。

### 注意：`tests/unit/` は両プロジェクトのテストが同一ディレクトリに混在
`tests/cases/`・`tests/reports/`・`tests/logs/` は review_system 専用（TC/TR成績書）。一方 `tests/unit/` は
review_system と doc_system 両方のテストファイルが**物理的に同じディレクトリに同居**する。判別は import 先で行う：
`review_system.*` を import＝review_system 対象／`dsv2`・`archive.docidx_v1`・`asset_parity`・`.codex/*` を
import・exec＝doc_system 対象。

### doc_system の運用細則（②には適用されない・①専用）
- ノード検索/読み込みツール（md2idx 思想）：`archive/docidx-v1/`（**v1-legacy 専用・現行コーパスは対象外**。`python3 -m archive.docidx-v1`・標準ライブラリのみ・対象は `doc-system-v1-archive/`。issue #142 で `docidx/` からの物理移動を一旦保留していたが、issue #172 で共有 YAML リーダ `nodeyaml.py` を `dsv2/nodeyaml.py` へ分離した上で残りを `archive/docidx-v1/` へ `git mv`）。フォーマット依存マップ＝`archive/docidx-v1/README.md`。**v2 検索は `dsv2 index` ＋ grep/Read**（`dsv2-lookup` 参照）。利用入口＝`/docidx`（`.claude/skills/docidx/SKILL.md`・v1-archive 専用と明記済み）・委譲先＝`dsv2-lookup`（`.claude/agents/dsv2-lookup.md`・dsv2-native。旧名 `docidx-lookup`・issue #173 で改名）。各関数の `依存仕様:` docstring に依存 SPEC＋版を明記。
- FND 辺逆転（バックリファレンス）の機械実行：**v2 は `python3 -m dsv2 reverse`**（実装＝`dsv2/reverse.py`）。旧 v1 専用ツール `backref/` は issue #76 で `archive/backref-v1/` へ retire 済み（フォーマット依存マップは `archive/backref-v1/README.md` に保全・消さない＝PR8）。運用は `reconciliation` が `--apply`（旧 issue #48 の運用を dsv2 へ継承）。
- **依存仕様の参照原則（全スクリプト共通・再発防止）**：ツールの `依存仕様:`（docstring・README フォーマット依存マップ）は **in-graph の版付きノード（SPEC-x / DD-x ＋ vX.Y.Z）を一次アンカーに明記する**。`docs/doc-system/*`（04-notation・02-meta-schema・config.yaml）・`CLAUDE.md` は **out-of-graph で版を持たない**（ファイル frontmatter version は DD-8/FND-104 で廃止）ため**唯一の根拠にしない**——版が無いと仕様変更を取りこぼす。これらは補助ナビとしてのみ併記。版付きノードが未整備のフォーマット事実は不足を FND/Q で起票する
  （ただし起票先は前掲「起票先はプロジェクト区分で決める」の分類に従う——`dsv2` は両システムに含有される
  コーパス操作ツールのため FND/Q、`asset_parity`／`archive.docidx-v1` 等の**含有されない**汎用ハーネスで
  見つかった依存仕様アンカーの不足は Issue で起票する）。
- **資産ツリー間の presence/absence 検出（issue #155・検出半分）**：`.claude/skills|agents`（正本）↔ `.github/skills|prompts|agents`（Copilot）↔ `.codex/agents`（Codex CLI agent）↔ `.agents/skills`（Codex CLI skill）の4ツリーが揃っているかを **read-only** で機械検出するツール＝`asset_parity/`（`python3 -m asset_parity check`・標準ライブラリのみ・使い方は `asset_parity/README.md`）。**内容を書き換えるツールではない**（一括変換は 2026-06-15 に廃止済み・`asset-lateral-deploy` 参照）。意図的な非移植（`agy-delegate`／`issue-pipeline`＋`issue-implementer`／`issue-fixer`／`pr-reviewer` の Copilot 非移植等）は `asset_parity/exceptions.py` に記録し、`.claude/tailoring-registry.md` の既存決定と同期させる（新規に非移植を決めたらまず tailoring-registry.md に記録してから exceptions.py に追記）。**CI 組み込み済み**（`.github/workflows/asset-parity.yml`・4ツリーいずれかを触る push/pull_request で自動起動・`MISSING` はビルド失敗／staleness はビルドを止めない・詳細は `asset_parity/README.md`）。
