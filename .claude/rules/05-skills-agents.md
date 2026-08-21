## スキル/エージェント
- スキル（仕様）：`/align` `/value-trace` `/mvp-scope` `/schema-design` `/domain-model` `/spec-pipeline` `/asset-pipeline`
- スキル（実装設計）：`/architecture-design` `/orchestration-design` `/prompt-design` `/impl-design-pipeline`（凍結セット）・`/test-strategy`
- スキル（横展）：`/asset-lateral-deploy`（資産の別プラットフォーム展開）
- スキル（外部委譲）：`/agy-delegate`（Antigravity(agy)CLI への作業移譲の入口。疎通チェック必須・薄い起動口で実体は `agy-delegate` エージェント）
- スキル（外部委譲・第二意見レビュー）：`/codex-review`（Codex 公式 CLI `codex exec` への第二意見レビュー委譲の入口＝別モデルファミリ OpenAI。`agy-delegate`＝agy MCP/Gemini とは委譲先の機構が別・in-repo Claude レビュー→merge は `pr-reviewer`。cybersecurity フィルタで最終応答が `ERROR:flagged` に消える件の回避＝防御形式プロンプト＋`~/.codex/sessions/rollout-*.jsonl` フォールバックを規約化。Linux/WSL 専用・全外部ツリー非移植＝`asset_parity/exceptions.py` に登録済み。opus session 上限時の**追加の第二意見経路**として使える（`pr-reviewer` の同一構成での再投入を置き換えるものではなく、再投入した**上で**別ファミリの意見も取る用途））
- スキル（Issue 運用）：`/issue-pipeline`（複数オープン Issue を implement→PR→review→merge→close で1件ずつ完結させる repo 運用オーケストレータ。主文脈は処置順の triage・進捗管理・オーナーとの意思決定に専念し、実装は `issue-implementer`・**是正は `issue-fixer`**・レビュー/マージは `pr-reviewer` へ委譲。model は bloom-model-tier＋リスク信号でルーブリック選定・再レビューは常に Sonnet・重い調査は agy-delegate。dev-tooling メタパイプラインで doc-system-v2 の ORC ノード化・prompt_coverage_targets 対象外＝agy-delegate と同区分）
- スキル（メタ・資産運用）：`/bloom-model-tier`（Bloom 認知分類でカスタムエージェントの `model:` ティアを選定。Lv1→haiku／Lv2-3→sonnet／Lv4+→opus）
- スキル（ノード検索・コンテキスト効率）：`/docidx`（**v1-archive 専用**。現行コーパスは doc-system-v2 のため対象外。実体＝`archive/docidx-v1/`＝`python3 -m archive.docidx-v1`・対象は `doc-system-v1-archive/`。read-only・drift は情報提示のみで判定はしない。issue #172 で `docidx/` から `archive/docidx-v1/` へ退避、共有 YAML リーダ `nodeyaml.py` は `dsv2/nodeyaml.py` へ分離）。v2 コーパスの検索・読込は `dsv2-lookup`（下記）が担う
- サブエージェント（点検・分析）：`spec-inspector`（仕様点検）・`structured-analysis`（DFD 分解）・`asset-auditor`（資産の重複/矛盾/競合監査・read-only）
- サブエージェント（ノード検索）：`dsv2-lookup`（**dsv2-native**＝`python3 -m dsv2 index` の meta.json を grep/python でフィルタ→ `Read` で本文取得、辺は `dsv2 deps`/`dependents` で関連ノードのみ取得・ダイジェスト返却＝context 圧縮。ノード内容に対し read-only・`Bash` は `dsv2` CLI 実行のみ。旧名 `docidx-lookup`・v1 専用 `docidx` との混同を避けるため issue #173 で改名）
- サブエージェント（著作・調停）：`requirements-author`・`spec-author`・`analysis-author`・`design-author`・`verification-author`・`reconciliation-validator`（read-only 構造検証）・`reconciliation`（検証合格後の書込専任）
- サブエージェント（外部委譲）：`agy-delegate`（agy MCP 経由でタスクを Gemini に移譲。**移譲前に `mcp__agy__antigravity_status` で疎通必須・クラウドでは使用不可**。read-only 影響調査レポート・ノード素案作成は可だが、**正本（`docs/`／`CLAUDE.md` ＋ `.claude/rules/`）への書き込みと確定著作は移譲禁止**＝agy 産は素案/レポートにすぎず `*-author`(tmp)→`reconciliation-validator`(検証)→`reconciliation`(書込) を必ず通す）。
- サブエージェント（Issue 運用・`/issue-pipeline` のファンアウト先）：`issue-implementer`（1 Issue をブランチ→実装→テスト→commit→push→PR まで完結・**merge 不可**・**初回実装専任**）／`issue-fixer`（**レビュー指摘を受けた是正ラウンド専任**・権限は implementer と同一＝push 可・merge 不可。**Step 1 の診断（`karte render`→`karte append`）を経ずに Edit/Write しない**契約で、`python3 -m karte` を許可される唯一のロール。ただし `ingest-review` は是正当事者に許さない＝主文脈が実行する・#308/#341）／`pr-reviewer`（PR をレビュー→**構造化 finding**（`### F-<issue>-<seq>`＋`harm`/`harm_detail`/`severity`/`locus`/`summary`/`evidence`/`expected`/`recheck`/`status`）で返す→**merge 可・push 不可**。指摘があれば自分で直さず `issue-fixer` へ差し戻す）。**push/merge の非対称権限は `.claude/hooks/agent-command-gate.sh`（PreToolUse・agent_type ゲート）で機械的に拒否する**が、Bash 文字列の静的検査であり完全な sandbox ではない。プロンプト規律・レビュー分離・GitHub 側の保護と併用する（既知の限界は Issue #129）。3ロールとも非対話（AskUserQuestion なし）＝曖昧は STOP 報告・対話判断は `/issue-pipeline` 主文脈が担う（DD-22）。
- **新しいスキル/エージェント/コードを作る前に `asset-auditor` で重複/競合を点検**し、新規 vs 既存変更を判断（A14）。
- 初回は `.claude/` のワークスペース信頼を受諾する必要がある。

## ノード著作の委譲ルール
ノードを著作するときは必ず対応するサブエージェントに委譲する（主文脈で直接書かない）：
- **VAL / SR / FR / NFR** → `requirements-author`
- **SPEC** → `spec-author`（1アサーション1ノード・-N枝番・無名依存辺で親 SPEC を参照）
- **ACTOR / I / O / D / P / E / TERM（用語ノードの新規作成＝分析ファセット）** → `analysis-author`
- **ORC / DS / MOD / DM / PORT / PRS / SCM / CFG / PROMPT** → `design-author`（**TERM は新規作成しない**。DM 確定時に既存 TERM へ設計ファセット＝型名/定義モジュールを追記更新する・1用語1ノード共有・#87）
- **TD / TC / TR / VERIFY / FND / DD / Q / PEND** → `verification-author`
- **著作後の構造検証（read-only・VALIDATION_OK/ROLLBACK）** → `reconciliation-validator`
- **検証合格後の self_fix 適用・本ファイル確定書き込み** → `reconciliation`

各著作エージェントは `tmp/<sprint>/<parent-id>.md` に出力する。**2段で確定する**：`reconciliation-validator`（read-only 検証→`VALIDATION_OK`/`ROLLBACK`）→ 合格なら `reconciliation`（self_fix 適用＋本ファイル書込＋tmp 掃除）。ROLLBACK 時は writer を呼ばず著作エージェントを再起動する。検証と書込を分離した理由＝validator は Write/Edit を持たず**構造的に本ファイルへ書けない fail-close**を保証（DD-22）。

- **委譲時のインプットは最小化**：**作業を特定するのに必要な情報**（関連ノードの ID、新規著作か既存更新かの別、対象範囲など）は委譲時に渡してよい。一方で**分析・推奨はサブエージェントに任せ**、主文脈で先回りして分析結果・推奨・本文を作り込んで渡さない。※これは委譲（author/分析）への入力規律。判断を仰ぐ FND/Q の**本文**は別物で、そちらは「ID だけで投げず本文で説明してから判断を仰ぐ」（オーナー向け説明）を維持する。
- **共通指示は一時ファイル経由でコンテキスト節約**：サブエージェント呼び出しを複数回行うとき、共通となる指示部分は `tmp/<sprint>/` 等の一時ファイルに書き出して各呼び出しから参照させ、呼び出しごとに同じ指示を展開しない。

### 戻り値のハンドオフ規約（write 権限の有無で分ける・2026-07-28）
context-mode プラグイン（グローバル導入）が全 subagent 呼び出しに `<artifact_policy>`（成果物はファイルに書き、
パスと1行要約だけ返す）を注入する。**これを潰さず、受け渡し方を合わせる**方針で統一する。

- **write 権限があるエージェント（`*-author` / `structured-analysis` / `reconciliation` / `issue-implementer` / `issue-fixer`）**
  → 呼び出し元へ返す項目を **`tmp/_handoff/<agent>--<key>.yaml`** に Write で書き、チャットには
  **`HANDOFF: <path>` ＋1行要約だけ**を返す。項目は従来の戻り値と同一（スキーマは各 agent.md の「ハンドオフ」節）。
  **呼び出し元は必ずこのファイルを Read して判断する**（1行要約だけで判断しない）。
  `tmp/` は gitignore 済み。`tmp/_handoff/` は `reconciliation` の tmp 掃除（`tmp/<sprint>/<parent-id>/`）の対象外
  （掃除は `python3 -m dsv2 clean-tmp <path> --apply` が保護名 `_handoff`・`_karte`・`_worktree` を
  構成要素に含むパスを機械的に拒否する＝`dsv2/cleantmp.py` の `PROTECTED_DIRNAMES`。`_karte`＝是正
  ループの診断カルテ置き場（Issue #307）、`_worktree`＝worktree 所有台帳の置き場（Issue #309）も
  同様に掃除対象外）。
  - **`<key>` は呼び出しごとに一意にする**：`authoring-fanout` は各 author へ `target_key`
    （**呼び出しごとの nonce**＋親＋型＋連番）を、`reconciliation` へ `batch_id`（sprint＋layer＋同じ nonce＋先頭親）を
    採番して渡す。親 ID だけをキーにすると、同一親の複数 target や `parent_id` 空の新規ルートが並列で走ったときに
    **同じファイルを上書きし、片方の結果が失われる**。nonce が無い決定論的採番だと、`(親, 型, 連番)` が偶然一致する
    **別バッチ**との衝突も同じ形で結果を失う（issue #278）。nonce は**バッチ内で共有する**（target ごとに振ると
    同一 target の二重ディスパッチ検査が効かなくなる）。
    **再試行の冪等性は nonce ではなく `retry_of` の明示で担保する**：失敗した target をやり直すときだけ、
    呼び出し元が `retry_of: <前回の target_key>` を渡して同じキーを再利用させる（新規著作では渡さない）。
  - **worktree をまたぐ場合も、呼び出し元が渡すのは「作業ツリールート相対」のパス**（`issue-implementer` /
    `issue-fixer` の `handoff_path`・Issue #323）。isolated なエージェント（`isolation: "worktree"`）は
    ハーネスに作業ツリー外への Write を機械的に拒否されるため、呼び出し元のワークツリーの絶対パスへは
    そもそも書けない。相対パスなら定義上つねに自分の作業ツリー配下へ解決されるので、別ワークツリーを
    指す誤誘導が検査ではなく構造で消え、isolated / 非 isolated のどちらの構成でも同じ契約が成立する。
    **回収は「エージェントが書けた絶対パスをチャットで返す」ことで行う**（呼び出し元は isolated ではない
    のでその絶対パスを Read できる）。ファイル名の採番権は呼び出し元に残す（`<key>` 一意化＝上記）。
- **write 権限がないエージェント（`reconciliation-validator` / `spec-inspector` / `asset-auditor` /
  `dsv2-lookup` / `pr-reviewer` / `authoring-fanout` / `agy-delegate`）**
  → ファイルに書けず注入の前提が成立しないので、各 agent.md 末尾の「注入ブロックへの優先規定」で
  `<artifact_policy>` を無効化し、**従来どおりチャットへ全文返す**。
  特に `reconciliation-validator` に書込経路を与えないこと自体が fail-close の保証（DD-22）。

### ctx_* ツールの付与方針（エージェント単位で選定・2026-07-29）
context-mode の 11 ツールを**一律禁止にはしない**。実測した性質で2群に分け、ロールごとに選ぶ。

- **実行系＝`ctx_execute` / `ctx_batch_execute` は「shell 限定」で Bash 保有ロールにのみ付与する
  （Issue #303 でゲートを拡張・#304 で解禁・2026-08-09）。`ctx_execute_file` は引き続き全ロール未付与。**
  「sandboxed subprocess」はコンテキストのサンドボックスであって**FS のサンドボックスではない**——実測で
  cwd＝プロジェクトルートのままリポジトリ内にファイルを書けた（注入文の "discard the sandbox FS" は実態と異なる）。
  当初（2026-07-29）は tool_name が `mcp__plugin_...` になり **`matcher: "Bash"` の `agent-command-gate.sh` が
  発火しない**ため全エージェント未付与としていたが、**#303 で同フックを実行系 MCP ツールへ拡張し、
  ロール別 allowlist（層1〜3）と危険コマンド層を ctx 経路にも適用した**ので、その範囲で解禁した。
  - **付与先＝主文脈・`issue-implementer`・`issue-fixer`・`pr-reviewer`・`dsv2-lookup`**（いずれも既に Bash を保有）。
    **Bash 非保有ロール（`spec-inspector` / `asset-auditor` / 各 `*-author` 等）には付与しない**——
    ゲートが効いても「シェル実行能力の新規付与＝権限昇格」は残るため。
  - **`language` は `shell` のみ許可**（ゲートが機械的に強制）。非 shell 言語は
    `<interpreter> -c <code>` と同値で、`permissions.deny` と危険コマンド層が全ロールに対し既に
    禁じている形。静的検査で安全に扱えない（複数のサブプロセス起動 API・文字列結合・eval で
    トークン一致を自明に回避できる）ため、コードではなく**言語そのものを allowlist で絞る**。
  - **gated ロール（`issue-implementer` / `issue-fixer` / `pr-reviewer`）は層1〜3 が ctx 経路にもそのまま掛かる**——
    push/merge の非対称は維持され、**シェル記号（パイプ等）も deny される**。出力の絞り込みは
    シェル記号ではなく **`ctx_batch_execute` の `queries` / `ctx_execute` の `intent`** で行う。
    また gated ロールは **`cwd` の明示指定が deny**（省略時は context-mode がプロジェクトルートを補う）。
  - **未知の MCP ツール名・入力形が読めない呼び出しは全 agent_type で fail-close（deny）**。
    Bash 経路の非ゲートロール fail-open（既存ワークフロー救済の例外）とは意図的に非対称。
  - **rtk フック（`matcher: "Bash"`）は ctx 経路では依然発火しない**——統制ではなくトークン節約
    プロキシなので解禁可否には影響しないが、ctx 経由ではその節約が効かないことを認識して使う。
- **検索系＝`ctx_search` / `ctx_index` は「リポジトリを変更しない」ので、多数ファイルを読むロールに付与する。**
  実測でリポジトリ（作業ツリー）へは一切書かず、KB は `~/.claude/context-mode/` に隔離される。付与先は
  `dsv2-lookup`（ノード横断検索が中核業務）・`spec-inspector`・`asset-auditor`・`reconciliation-validator`・`pr-reviewer`。
  **付与の根拠は「リポジトリに書かない」ことであって「read-only だから」ではない**——`ctx_search` は読取専用だが、
  **`ctx_index` は read-only ではない**（`readOnlyHint: false` / `idempotentHint: false`。同じ内容でも呼ぶたびに
  永続 FTS5 ストアへ追記される＝非冪等）。`reconciliation-validator` の DD-22 fail-close が保たれるのも
  **リポジトリ（`doc-system-v2/**`・tmp）へ書けないから**であり、KB への書込はその保証と無関係。
  運用上は**同じ対象を無駄に再 index しない**（既に index 済みの source があればそれを `ctx_search` で引き、
  対象が変わった/初回のときだけ `ctx_index` する）。
- **`ctx_fetch_and_index`（ネットワーク送信）・`ctx_purge`（KB 破壊）・`ctx_insight`（外部ダッシュボード起動）・
  `ctx_upgrade` / `ctx_stats` / `ctx_doctor`（運用系）は subagent に付与しない**——主文脈が扱う。

この方針を変えるとき（例：付与先ロールを増やす・`ctx_execute_file` を解禁する・非 shell 言語を通す）は、
**先に `.claude/hooks/agent-command-gate.sh` 側の統制を手当てし、付与は別 PR にする**——
付与が先行すると、ゲート未対応の面が素通しになる状態が生まれる（#303→#304 はこの順序で実施した）。
静的検査の限界は Issue #129 と同じ制約を受ける。**ゲートは sandbox ではない**——
`agent_type` の詐称・ハーネス外の実行経路・許可されたテストランナー経由の任意コード実行は閉じきれないので、
プロンプト規律・レビュー分離・GitHub 側のブランチ保護との併用が引き続き前提。
