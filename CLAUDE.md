# CLAUDE.md — 作業規約

このリポジトリでの仕様策定・設計の進め方。手法の棚卸しは `docs/methods/method-inventory.md`、
スキル/エージェントの計画は `docs/methods/asset-plan.md`、実体は `.claude/`。

## 迷ったら原則に戻る
判断は **spec-principles（PR1–PR10）**（`.claude/skills/spec-principles/`）に従う。特に：
**もの＋発生源で分ける**／**機械判定と運用ルールを混ぜない**／**価値経路を遮断しない**／
**矛盾は停止して打ち上げ**／**系外＝非イベント**／**観測できないものは持たない**。

## 分析の姿勢（疑問を持つ・単一責務で分割）
- 現状の分析結果を鵜呑みにせず、**常に疑問を持ち、あるべき姿を追求する**。
- spec・プロセス・データ構造が**単一責務**となるよう分割できているかを検討した上で分析を進める（PR1「もの＋発生源で分ける」・機械判定と運用ルールの分離・DFD レベリングの徹底）。

## 決定ダッシュボード運用（A2）
- 未決は `docs/dashboard.md` に Q# として起票し、状態（未決/方針あり/確定/クローズ）を維持。
- 決定は「決定済み」へ。削除はクローズで**理由を残す**（消さない＝PR8）。
- 確定は本文（台帳/設計）に反映し、削除済み項目の生き残り参照を Grep で確認。

## 案出し（A3）
- 論点は1文化 → 2–4 の排他的選択肢＋トレードオフ → 推奨＋根拠 → Q# に記録。
- 運用ルール（PR2）は機構＋デフォルトに留め、設計で詰めない。

## 判断の仰ぎ方（フェーズ別・空で止めない＝PR7）
- **大原則**：矛盾・オーナー判断必須で止めるときも、**原案・比較・理由付き推奨/非推奨を必ず添える**（意見なき停止は禁止）。**矛盾は原案検討して提案、他のやれる所をやる、一通り終えたら整理して提示**。
- **起票してから止める（チャットで流さない）**：論点・矛盾・情報不足を見つけたら、**①ノード起票 → ②ダッシュボード更新（Q/FND いずれの場合も必須）→ ③選択肢＋推奨を添えて停止・質問** の順を必ず守る。チャットで指摘を述べるだけで**起票しないのは禁止**（後から「なぜ起票してない？」になる）。**②は省略不可**——ノードが明細、ダッシュボードが状態の要約で、両方を更新して初めて起票完了。
  - **起票先の使い分け**：未決の論点・**質問＝Q ノード**（`type: Q`・qa テンプレ・`verification-author` に委譲。決定したら DD へ昇格）／**既存ノードに対して発見した指摘・矛盾・原則違反＝FND ノード**（`doc-system-v2/nodes/04-verification/fnd/`（open/resolved の2状態は path で表現）・`verification-author` に委譲）。**質問はダッシュボードに直接書くのではなく Q ノードを起票し、ダッシュボードはその要約を更新する**。どちらも本文に内容・深刻度・推奨を書き、ID だけで投げず**本文で説明してから判断を仰ぐ**。
  - **処置したら必ずバックリファレンス**：FND を resolved にしたら処置対象ノードに `→FND-x` 辺を付与（削除済みノードは FND 本文に「付与先なし」と明記）。**辺逆転（forward 削除＋backward 付与＋DD-3 凍結＋z バンプ＋`fnd/open/`→`fnd/resolved/` の `git mv`）は手編集でなく `dsv2` ツールで機械実行する**＝`python3 -m dsv2 reverse <FND-slug> --root doc-system-v2`（既定 dry-run／`--apply` で書込・実装＝`dsv2/reverse.py`）。旧 `backref/`（v1専用）は `archive/backref-v1/` に retire 済み（issue #76）。
  - **FND 起票時は ref_version を本文にも記録**：FND 解消時に edges が逆転（FND→対象 → 対象→FND）するため指摘時の ref_version が辺情報から失われる。**FND 起票時に `edges[].ref_version` の値を本文に明記する**（`**指摘時 ref_version**: {ノードID} "{ref_version}"（{ファイル名} v{version} 時点）`・DD-3 制度化）。
- **要件定義フェーズ**：**暫定で進めない（危険）**。論点・矛盾・情報不足は**上記①〜③で止めて**選択肢＋推奨を出し、決定はオーナー。**他の決められる所を先に進める**（Q#/FND で起票・状態維持）。
- **設計フェーズ**：迷いは**推奨案で暫定決定**し、**判断ログ DD#**（論点→選択肢→推奨→暫定決定→影響範囲）に記録して前進。覆る場合の影響範囲を必ず併記。
- **DD# は Q# の設計フェーズ版**：未決の置き場が Q#（ダッシュボード）、暫定決定の記録が DD#（[design/decisions](docs/design/decisions.md)）。

## スケジュール独断禁止（再発防止・2026-06-14）
**FND/Q/DD で「次スプリント以降」「sprint-N 以降」等の実施スプリントを設定するとき、オーナー確認なしに独断で繰り越すことは厳禁。**

- **繰り越しはオーナー判断**：工数・優先度を理由にスプリントを後ろ倒しにする決定は、必ずオーナーに判断を仰いでから `scheduled: "sprint-N"` を設定する。
- **起票と判断要請を同時に行う**：FND/Q を起票したら、実施時期が未確定のうちは `scheduled: ""` のままにし、チャットで選択肢（今スプリント実施 vs 次スプリント繰り越し）＋推奨を添えてオーナーに確認する。
- **「影響なし・実害ゼロ・後でよい」は独断根拠にならない**：自分が軽微と判断しても、スプリント計画はオーナーが決める。軽微と思うなら「今すぐ実施できる。ただし影響 X が小さいため sprint-N 繰り越しも選択肢」と提示して判断を委ねる。
- **違反事例**（2026-06-14）：FND-35・FND-37 を「現時点実害ゼロ」「推奨のみ起票」として独断で `scheduled: sprint-2` に設定し、DD-8 の `ref_version` 移行・フロントマター廃止も「sprint-2 以降」に繰り越した。オーナー指示により即時実施に変更（DD-8 全実施・FND-37 resolved・FND-35 はオーナー明示承認で sprint-2 確定）。

## PR レビュー・GitHub コメント運用（明示・独断禁止）
- **Claude Code が実施したことを明示する**：PR でレビュー指摘への返信・コメントを投稿するときは、**AI（Claude Code）による対応であること**と、**実際に実施した処置（変更したファイル・コミット・判断の根拠）**をコメント本文に具体的に明記する。「誰が何をしたか」を後から取り違えないため、抽象的な要約だけで済ませず、処置内容を箇条書きで残す。
- **Codex が投稿する場合は Codex AI agent と明示する**：PR 本文、PR コメント、レビューコメント、merge コメントを Codex が投稿する場合は、ユーザーが明示的に別指示した場合を除き、本文冒頭または件名で **Codex AI agent** 由来であることを明記する。
- **レビューと修正の分離指示を守る**：ユーザーが「別コンテキスト」「subagent」「レビューと修正を分離」と指示した場合、レビュー担当 subagent と修正担当 subagent/主文脈を分ける。修正後は別文脈で再レビューし、所見・修正内容・検証・最終判断を PR コメントに残す。
- **「対応不要」を AI が独断で書かない**：指摘の処置要否・スプリント繰り越しは**オーナー判断**。AI が単独で「対応不要」「現時点不要」「将来検討でよい」等と結論づけてコメント・クローズしてはならない（過去に AI が独断で「対応不要」とコメントしオーナー指示に反した事例あり・2026-06-16）。指摘・矛盾を見つけたら **①ノード起票（FND/Q）→ ②ダッシュボード更新 → ③選択肢＋推奨を添えて打ち上げ**（PR7・意見なき停止禁止／独断禁止）。
- **指摘は処置完了まで追う**：レビュー指摘は原則として処置（起票→反映）まで完了させる。据え置くのは**オーナーが明示的に「不要/繰り越し」と判断した場合のみ**で、その旨と判断者をコメントに明記する。AI 同士のコメントを根拠に据え置かない。

## スキル/エージェント
- スキル（仕様）：`/align` `/value-trace` `/mvp-scope` `/schema-design` `/domain-model` `/spec-pipeline` `/asset-pipeline`
- スキル（実装設計）：`/architecture-design` `/orchestration-design` `/prompt-design` `/impl-design-pipeline`（凍結セット）・`/test-strategy`
- スキル（横展）：`/asset-lateral-deploy`（資産の別プラットフォーム展開）
- スキル（外部委譲）：`/agy-delegate`（Antigravity(agy)CLI への作業移譲の入口。疎通チェック必須・薄い起動口で実体は `agy-delegate` エージェント）
- スキル（Issue 運用）：`/issue-pipeline`（複数オープン Issue を implement→PR→review→merge→close で1件ずつ完結させる repo 運用オーケストレータ。主文脈は処置順の triage・進捗管理・オーナーとの意思決定に専念し、実装は `issue-implementer`・レビュー/マージは `pr-reviewer` へ委譲。model は bloom-model-tier＋リスク信号でルーブリック選定・再レビューは常に Sonnet・重い調査は agy-delegate。dev-tooling メタパイプラインで doc-system-v2 の ORC ノード化・prompt_coverage_targets 対象外＝agy-delegate と同区分）
- スキル（メタ・資産運用）：`/bloom-model-tier`（Bloom 認知分類でカスタムエージェントの `model:` ティアを選定。Lv1→haiku／Lv2-3→sonnet／Lv4+→opus）
- スキル（ノード検索・コンテキスト効率）：`/docidx`（**v1-archive 専用**。現行コーパスは doc-system-v2 のため対象外。実体＝`docidx/`＝`python -m docidx`・対象は `doc-system-v1-archive/`。read-only・drift は情報提示のみで判定はしない）。v2 コーパスの検索・読込は `docidx-lookup`（下記）が担う
- サブエージェント（点検・分析）：`spec-inspector`（仕様点検）・`structured-analysis`（DFD 分解）・`asset-auditor`（資産の重複/矛盾/競合監査・read-only）
- サブエージェント（ノード検索）：`docidx-lookup`（**dsv2-native**＝`python3 -m dsv2 index` の meta.json を grep/python でフィルタ→ `Read` で本文取得、辺は `dsv2 deps`/`dependents` で関連ノードのみ取得・ダイジェスト返却＝context 圧縮。ノード内容に対し read-only・`Bash` は `dsv2` CLI 実行のみ）
- サブエージェント（著作・調停）：`requirements-author`・`spec-author`・`analysis-author`・`design-author`・`verification-author`・`reconciliation-validator`（read-only 構造検証）・`reconciliation`（検証合格後の書込専任）
- サブエージェント（外部委譲）：`agy-delegate`（agy MCP 経由でタスクを Gemini に移譲。**移譲前に `mcp__agy__antigravity_status` で疎通必須・クラウドでは使用不可**。read-only 影響調査レポート・ノード素案作成は可だが、**正本（`docs/`/本ファイル）への書き込みと確定著作は移譲禁止**＝agy 産は素案/レポートにすぎず `*-author`(tmp)→`reconciliation-validator`(検証)→`reconciliation`(書込) を必ず通す）。
- サブエージェント（Issue 運用・`/issue-pipeline` のファンアウト先）：`issue-implementer`（1 Issue をブランチ→実装→テスト→commit→push→PR まで完結・**merge 不可**）／`pr-reviewer`（PR をレビュー→コメント→**merge 可・push 不可**）。**push/merge の非対称権限は `.claude/hooks/agent-command-gate.sh`（PreToolUse・agent_type ゲート）で機械的に拒否する**が、Bash 文字列の静的検査であり完全な sandbox ではない。プロンプト規律・レビュー分離・GitHub 側の保護と併用する（既知の限界は Issue #129）。両者は非対話（AskUserQuestion なし）＝曖昧は STOP 報告・対話判断は `/issue-pipeline` 主文脈が担う（DD-22）。
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

## 資産のテーラリング運用（A16）
- プロセスはスキル等で実現するため、**テーラリングの実体は `.claude/` に置く（docs ではない）**。
- 汎用標準は `.claude/standards/<name>/`（**非活性・auto-load されない**）、テーラリング済 active は `.claude/skills/<name>/`、対応は `.claude/tailoring-registry.md`。
- テーラリング時は**元（汎用標準）を `git mv` で `standards/` へ移動・非活性化**（消さない＝PR8）し、テーラリング版を `skills/` に置き、**registry に内容と実体パスを記録**。
- 初回適用＝`/test-strategy`（④ テスト戦略）。

## 実装設計フェーズ（凍結セット・判断ログ・A17–A20）
- 仕様確定後・実装着手前に **凍結セット**（モジュール／IF／プロトコル／永続／オーケストレーション／プロンプト／ログ・版／テスト戦略）を固める。索引＝`docs/design/README.md`。
- 手順は `/impl-design-pipeline`（`/architecture-design`→`/orchestration-design`→`/prompt-design`→`/test-strategy`）。**新規資産前に asset-auditor**（A14）。
- **判断ログ（DD#）**：仕様で一意に決まらない点は `docs/design/decisions.md` に `論点→選択肢→推奨→暫定決定→影響範囲` で記録（設計は暫定で前進・PR7）。
- **総点検（凍結セット規律）**：設計一式を **spec-inspector** に点検させ、G#（孤児/穴/分割違反/矛盾）を出して反映してから実装へ。
- **版は `MAJOR.MINOR`**（MAJOR=構造/型→対応ロジック改修・MINOR=内容のみ）。版↔対応ロジックを一目で追えること。

## このリポジトリ
- 現状ドキュメント中心（要件・設計フェーズ）。実装は **Python・原則標準ライブラリのみ**（Q5/Q5a：フロントマターも自前パーサ）。
- **`docs/` 配下は原則「壁打ちメモ＝非正本」**（オーナー方針・2026-06-29）：設計時の参考に閲覧してよいが**そっちありきにしない**。**正本は `doc-system-v2/`（ノードグラフ）＋ `.claude/`（資産・規約）＋本ファイル**。**例外＝`docs/doc-system/`**（config.yaml・templates・記法・接続マトリクス等＝doc-system の機械定義は正本の一部。`config.yaml` の `trace_scope` も `docs/**` を除外済み）。**docs/ プローズと doc-system ノードが食い違う場合は doc-system 側を正**とし、不足は doc-system 側に著作して埋める（docs/ は更新しない・古い記述は無視）。v1 `doc-system/` は issue #76（v1→v2 cutover）で `doc-system-v1-archive/` へ retire 済み（`git mv`・履歴保持・非正本）。
- MVP ターゲットは doc-system ノード（VAL/SR/FR ＋ `labels: post-mvp`）。運用ハブ＝`doc-system-v2/00-dashboard.md`（旧 `doc-system/00-dashboard.md`・`docs/dashboard.md`・`docs/requirements/12-mvp-scope.md` は非正本の壁打ち）。
- 実装設計のデータ辞書／ドメインモデルは doc-system の DM/TERM ノード（`doc-system-v2/nodes/05-design/dm/`・`doc-system-v2/nodes/03-analysis/term/`＝各ノード1ファイル）。`docs/design/00-data-dictionary.md`・`01-class-design.md` は非正本の参考。
- **実装前の凍結セット**：`doc-system-v2/nodes/05-design/` 配下（索引の考え方は `python3 -m dsv2 index` で meta.json 生成→grep/jq で参照。基盤＝`doc-system-v2/nodes/05-design/mod/`）。テスト戦略＝`/test-strategy`。`docs/design/*` プローズは非正本の参考。
- ノード検索/読み込みツール（md2idx 思想）：`docidx/`（**v1-legacy 専用・現行コーパスは対象外**。`python -m docidx`・標準ライブラリのみ・対象は `doc-system-v1-archive/`）。フォーマット依存マップ＝`docidx/README.md`。**v2 検索は `dsv2 index` ＋ grep/Read**（`docidx-lookup` 参照）。利用入口＝`/docidx`（`.claude/skills/docidx/SKILL.md`・v1-archive 専用と明記済み）・委譲先＝`docidx-lookup`（`.claude/agents/docidx-lookup.md`・dsv2-native）。各関数の `依存仕様:` docstring に依存 SPEC＋版を明記。
- FND 辺逆転（バックリファレンス）の機械実行：**v2 は `python3 -m dsv2 reverse`**（実装＝`dsv2/reverse.py`）。旧 v1 専用ツール `backref/` は issue #76 で `archive/backref-v1/` へ retire 済み（フォーマット依存マップは `archive/backref-v1/README.md` に保全・消さない＝PR8）。運用は `reconciliation` が `--apply`（旧 issue #48 の運用を dsv2 へ継承）。
- **依存仕様の参照原則（全スクリプト共通・再発防止）**：ツールの `依存仕様:`（docstring・README フォーマット依存マップ）は **in-graph の版付きノード（SPEC-x / DD-x ＋ vX.Y.Z）を一次アンカーに明記する**。`docs/doc-system/*`（04-notation・02-meta-schema・config.yaml）・`CLAUDE.md` は **out-of-graph で版を持たない**（ファイル frontmatter version は DD-8/FND-104 で廃止）ため**唯一の根拠にしない**——版が無いと仕様変更を取りこぼす。これらは補助ナビとしてのみ併記。版付きノードが未整備のフォーマット事実は不足を FND/Q で起票する。
