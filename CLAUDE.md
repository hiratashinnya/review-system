# CLAUDE.md — 作業規約

このリポジトリでの仕様策定・設計の進め方。手法の棚卸しは `docs/methods/method-inventory.md`、
スキル/エージェントの計画は `docs/methods/asset-plan.md`、実体は `.claude/`。

> **本リポジトリは doc_system と review_system の2プロジェクトが同居**（ファイル構成・「正本」の所在は文脈で変わる）。
> 詳細＝「[このリポジトリ＝2つのプロジェクトが同居（混同注意）](#このリポジトリ2つのプロジェクトが同居混同注意)」を参照。

> **本ファイルの中核規範は毎ターン注入される**（2026-07-28・context-mode 導入に伴う対策）。
> 実体＝`.claude/hooks/inject-governance.sh`（UserPromptSubmit）＋ `.claude/hooks/governance-directives.md`。
> **正本は本ファイル**で、`governance-directives.md` はその配送用の写し。**規約を変えたら写しも合わせる**
> （食い違ったら本ファイルを正とする）。**追従漏れは `.claude/hooks/check-governance-drift.sh`
> （PostToolUse）が機械的に検知する**——写しの `<!-- synced-from: CLAUDE.md@<sha> -->` と本ファイルの
> ハッシュを突き合わせ、食い違う間だけ警告する（反映後に sha を更新して解除）。
> subagent 側の対策は各 `.claude/agents/*.md` 末尾の
> 「注入ブロックへの優先規定」。背景と設計は `.claude/hooks/README.md`。

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
  - **ただし、どちらのシステムにも含有されない汎用ハーネスの開発は例外**（起票先が Issue になる。
    含有されるハーネスは従来どおりノード起票）＝後述「[起票先はプロジェクト区分で決める](#起票先はプロジェクト区分で決めるハーネス開発は-issue-運用)」。
    **打ち上げ義務そのものは変わらない**（起票せずチャットで流すのは依然として禁止）。
  - **起票先の使い分け**：未決の論点・**質問＝Q ノード**（`type: Q`・qa テンプレ・`verification-author` に委譲。決定したら DD へ昇格）／**既存ノードに対して発見した指摘・矛盾・原則違反＝FND ノード**（`doc-system-v2/nodes/04-verification/fnd/`（open/resolved の2状態は path で表現）・`verification-author` に委譲）。**質問はダッシュボードに直接書くのではなく Q ノードを起票し、ダッシュボードはその要約を更新する**。どちらも本文に内容・深刻度・推奨を書き、ID だけで投げず**本文で説明してから判断を仰ぐ**。
  - **処置したら必ずバックリファレンス**：FND を resolved にしたら処置対象ノードに `→FND-x` 辺を付与（削除済みノードは FND 本文に「付与先なし」と明記）。**辺逆転（forward 削除＋backward 付与＋DD-3 凍結＋z バンプ＋`fnd/open/`→`fnd/resolved/` の `git mv`）は手編集でなく `dsv2` ツールで機械実行する**＝`python3 -m dsv2 reverse <FND-slug> --root doc-system-v2`（既定 dry-run／`--apply` で書込・実装＝`dsv2/reverse.py`）。旧 `backref/`（v1専用）は `archive/backref-v1/` に retire 済み（issue #76）。
  - **FND 起票時は ref_version を本文にも記録**：FND 解消時に edges が逆転（FND→対象 → 対象→FND）するため指摘時の ref_version が辺情報から失われる。**FND 起票時に `edges[].ref_version` の値を本文に明記する**（`**指摘時 ref_version**: {ノードID} "{ref_version}"（{ファイル名} v{version} 時点）`・DD-3 制度化）。
- **要件定義フェーズ**：**暫定で進めない（危険）**。論点・矛盾・情報不足は**上記①〜③で止めて**選択肢＋推奨を出し、決定はオーナー。**他の決められる所を先に進める**（Q#/FND で起票・状態維持）。
- **設計フェーズ**：迷いは**推奨案で暫定決定**し、**判断ログ DD#**（論点→選択肢→推奨→暫定決定→影響範囲）に記録して前進。覆る場合の影響範囲を必ず併記。
- **DD# は Q# の設計フェーズ版**：未決の置き場が Q#（ダッシュボード）、暫定決定の記録が DD#（[design/decisions](docs/design/decisions.md)）。

## 起票先はプロジェクト区分で決める（ハーネス開発は Issue 運用）
**判定軸は「そのハーネスが doc_system / review_system に含有されるか」**（オーナー訂正・2026-08-02）。
旧判定軸「in-graph の観測可能成果物を持たない」は**事実に反するため廃止**——
`doc-system-v2/nodes/05-design/prompt/` に PROMPT ノードが22件実在し、うち15件が
`.claude/agents`/`.claude/skills` を参照して `carrier` を持ち在グラフモデル化されている
（14件が `carrier: "skill"`・1件が `carrier: "agent"`。著作エージェント系7件は `carrier` を持たない）
（オーナー確定 DD「skill を LLM プロンプト資産として在グラフの PROMPT 設計ノードにモデル化する」・
FR-17／傘 SPEC-61／PROMPT-8〜20）。**`.claude/` 全体をハーネス＝起票対象外と扱わない。**

- **doc_system / review_system に含有されるハーネス**（両システム自身の生産機構）→ 従来どおり
  **FND/Q/DD ノード起票 ＋ ダッシュボード更新**（doc_system の成果物＝`doc-system-v2/nodes/**` は
  `doc-system-v2/00-dashboard.md`、review_system の成果物＝`docs/` 配下は `docs/dashboard.md`・
  `docs/design/decisions.md`。`verification-author` に委譲）：
  - 著作・検証エージェント：`requirements-author`/`spec-author`/`analysis-author`/`design-author`/
    `verification-author`/`reconciliation`/`reconciliation-validator`/`spec-inspector`/
    `structured-analysis`/`dsv2-lookup`/`authoring-fanout`/`doc-system-v2-authoring`
  - 仕様策定・実装設計スキル：`doc-system-v2/config.yml` の `prompt_coverage_targets` に列挙された14件
    （`align`/`value-trace`/`mvp-scope`/`schema-design`/`domain-model`/`architecture-design`/
    `orchestration-design`/`prompt-design`/`test-strategy`/`spec-principles`/`spec-pipeline`/
    `impl-design-pipeline`/`asset-pipeline`/`docidx`）
  - コーパスを操作するツール：`dsv2`（doc-system-v2 のノードグラフを直接操作する）
  - review_system 本体の実装・テスト（`review_system/`・`tests/`）
- **どちらのシステムにも含有されない汎用開発ハーネス**（そのシステムの仕様グラフが記述する対象ではない）→
  **ノード起票もダッシュボード更新も行わない**。**`/gh-create-issue` で Issue を切って処置する**
  （`area:harness` ラベル）：
  - Issue 運用パイプライン：`issue-pipeline`/`issue-implementer`/`pr-reviewer`/`gitgate`
  - 実行環境の面倒を見るフック：`on-rate-limit.sh`/`resume-watcher.sh`/`install_pkgs`/
    `inject-governance.sh`/`check-governance-drift.sh`/`orchestrator-context.sh`/`agent-command-gate.sh`、
    `.claude/settings.json`
  - 外部委譲・モデル選定・横展・Issue 起票の補助：`agy-delegate`/`codex-review`/`bloom-model-tier`/
    `asset-lateral-deploy`/`coverage-html`/`gh-create-issue`/`asset_parity`
  - 是正ループ用ツール：`karte`
  - 点検・監査ツール（read-only）：`asset-auditor`（資産の重複/矛盾/競合監査。特定システムの仕様グラフが
    記述する対象ではなく資産全体を横断するため）
  - v1-legacy 退役ツール：`archive/docidx-v1`（v1 コーパス専用の検索ツール・実装対象は
    `doc-system-v1-archive/` のみで v2 コーパスは対象外・退役済み。**同名の skill `/docidx` を上記65行目の
    含有14件と混同しないこと**——`skill /docidx` は doc_system の仕様策定機構そのもの（PROMPT 設計ノード
    としてモデル化された対象）だから含有される側、`archive/docidx-v1/` はその skill が指す**v1 アーカイブ
    専用の退役ツール実装**で、v1 archive 化とともにどちらの現行システムの成果物でもなくなったため別物）・
    `archive/backref-v1`（v1 専用の辺逆転ツール・issue #76 で retire 済み・同じ理由で対象システムを失った）
  - CI 定義（`.github/workflows/`）

**根拠**：どちらに分類しても理由は同じ——**どちらのシステムの成果物でもない**（＝そのシステムの仕様
グラフが記述する対象ではない）ものだけを Issue 運用に回す。「ハーネスは in-graph の成果物を持たない」
という一般化はしない（含有されるハーネスは在グラフの成果物＝PROMPT ノード等を持つ）。

**本節は係属中の FND の帰趨を先取りしない**：`dsv2` 実装6モジュールに対応する設計ノード（MOD/P）の
過不足を指摘する open FND（severity ERROR・`scheduled: sprint-1`・対応 Issue #160）が別途係属中。
本節は `dsv2` の起票先（FND/Q/DD 側）を定めるだけで、その FND 自体の解消方法はオーナー判断を待つ。

**変わらないこと（弱めない）**：
- **意見なき停止は禁止（PR7）** — 起票先が Issue になるだけで、**原案・比較・理由付き推奨を添える**義務は同じ。
- **チャットで流して起票しないのは禁止** — ハーネスでも指摘・論点は必ず Issue に残す。
- **「対応不要」を AI が独断で書かない** — 処置要否・据え置きはオーナー判断。Issue のクローズも同様。

**迷ったら**：判定に迷う新規ハーネス・境界事例は、成果物側の規律（ノード起票・ダッシュボード）を
**満たした上で**Issue 化するか判断を仰ぐ（厳しい側に倒す）。

## スケジュール独断禁止（再発防止・2026-06-14）
**FND/Q/DD で「次スプリント以降」「sprint-N 以降」等の実施スプリントを設定するとき、オーナー確認なしに独断で繰り越すことは厳禁。**

- **既定は現行スプリント。確認は不要**（2026-07-26 オーナー指示で明確化）：新規に起票する FND/Q/DD/PEND の `scheduled` は、**オーナーから明示的な繰り越し指示がない限り、常に現行スプリントを設定する**。起票のたびに実施時期を問い合わせてはならない（`scheduled: ""` は `validate.py` と `dsv2 index` の双方で fail-close するため、空のまま置くこともできない＝issue #152）。
- **禁止されているのは「繰り越しの独断」であって「現行スプリントの設定」ではない**：工数・優先度・実害の小ささを理由にスプリントを**後ろ倒し**する決定だけがオーナー判断であり、必ずオーナーの明示指示を得てから `scheduled: "sprint-N"`（N > 現行）を設定する。
- **「影響なし・実害ゼロ・後でよい」は独断根拠にならない**：自分が軽微と判断しても、スプリント計画はオーナーが決める。軽微と思うなら「今すぐ実施できる。ただし影響 X が小さいため sprint-N 繰り越しも選択肢」と提示して判断を委ねる。
- **違反事例①・繰り越しの独断**（2026-06-14）：FND-35・FND-37 を「現時点実害ゼロ」「推奨のみ起票」として独断で `scheduled: sprint-2` に設定し、DD-8 の `ref_version` 移行・フロントマター廃止も「sprint-2 以降」に繰り越した。オーナー指示により即時実施に変更（DD-8 全実施・FND-37 resolved・FND-35 はオーナー明示承認で sprint-2 確定）。
- **違反事例②・過剰な確認**（2026-07-26）：FND 8 件・Q 1 件を起票した際、`scheduled` を現行スプリントに設定した上で「実施スプリントはオーナー判断」と毎回報告に添え、判断を仰ぎ続けた。オーナーより「明示的な繰り越し指示をしない限り現行スプリントに設定せよ。一々聞くな」と指示され、本節を上記のとおり改訂。**独断禁止は繰り越しにのみ掛かる**。

## PR レビュー・GitHub コメント運用（明示・独断禁止）
- **Claude Code が実施したことを明示する**：PR でレビュー指摘への返信・コメントを投稿するときは、**AI（Claude Code）による対応であること**と、**実際に実施した処置（変更したファイル・コミット・判断の根拠）**をコメント本文に具体的に明記する。「誰が何をしたか」を後から取り違えないため、抽象的な要約だけで済ませず、処置内容を箇条書きで残す。
- **Codex が投稿する場合は Codex AI agent と明示する**：PR 本文、PR コメント、レビューコメント、merge コメントを Codex が投稿する場合は、ユーザーが明示的に別指示した場合を除き、本文冒頭または件名で **Codex AI agent** 由来であることを明記する。
- **レビューと修正の分離指示を守る**：ユーザーが「別コンテキスト」「subagent」「レビューと修正を分離」と指示した場合、レビュー担当 subagent と修正担当 subagent/主文脈を分ける。修正後は別文脈で再レビューし、所見・修正内容・検証・最終判断を PR コメントに残す。
- **「対応不要」を AI が独断で書かない**：指摘の処置要否・スプリント繰り越しは**オーナー判断**。AI が単独で「対応不要」「現時点不要」「将来検討でよい」等と結論づけてコメント・クローズしてはならない（過去に AI が独断で「対応不要」とコメントしオーナー指示に反した事例あり・2026-06-16）。指摘・矛盾を見つけたら **①ノード起票（FND/Q）→ ②ダッシュボード更新 → ③選択肢＋推奨を添えて打ち上げ**（PR7・意見なき停止禁止／独断禁止）。
- **指摘は処置完了まで追う**：レビュー指摘は原則として処置（起票→反映）まで完了させる。据え置くのは**オーナーが明示的に「不要/繰り越し」と判断した場合のみ**で、その旨と判断者をコメントに明記する。AI 同士のコメントを根拠に据え置かない。

## CI/外部サービス連携のコスト方針（2026-07-11）
**CI連携や外部サービス連携を検討・実装するときは、常に無課金（無料）で実現できる方法を優先して検討する。課金が発生する構成でなければ実現できない場合は、実装前に必ずオーナーの明示的な認可を取る（独断厳禁）。**

- **判断材料を確認してから設計する**：例えば GitHub Actions は public リポジトリなら無料枠の制限自体がなく完全無料、private リポジトリは無料枠超過分から課金。実装前に対象リポジトリの可視性・課金体系を確認し、無料枠内に収まる設計（トリガー条件を絞る・軽量ジョブにする等）を優先する。
- **課金必須の場合は選択肢＋推奨を添えて認可を仰ぐ**：なぜ無課金での代替が不可能か・想定コスト規模を明記した上で、PR7の様式（選択肢＋推奨＋根拠）でオーナーに判断を仰ぐ。AI が独断で課金を伴う設定（有料プラン必須の機能・従量課金リソースの有効化等）を選んだり有効化したりしてはならない。

## レートリミット由来の品質降格の禁止（絶対規範・2026-08-03）
**サブエージェントがレートリミット／セッション上限で停止しても、モデル降格・effort 低下・
サブエージェントへの委譲の取りやめ（主文脈による代行）をしてはならない。**

- **禁止対象を明示**：①opus 指定のところを sonnet 等へ**モデル降格**する、②同じモデルのまま
  **effort（思考量）を下げる**、③サブエージェントへ委譲すべき作業を**主文脈が直接代行**する
  （委譲の取りやめ）——この3つはいずれも、レートリミット／セッション上限を理由にした品質低下であり禁止。
- **正しい対処＝同じ構成でそのまま再投入する**：モデル・effort を変えず、委譲もやめず
  （主文脈で代行せず）、停止前と同一の構成で再試行する。上限は再試行で解ける一時状態であり、
  構成を恒久的に下げてよい理由にはならない。
- **判断根拠：主文脈が動作している＝枠は回復している**。サブエージェントが上限で停止した時点で
  主文脈自身は動いている。主文脈が動けているということは、その時点でレートリミットは解除されている
  ということであり、「上限だから軽い構成で」は**回復済みの枠を使わずに品質だけ捨てる**、まったくの無駄。
- **モデル選定はリスク信号表に従う。実行環境の都合（レートリミット）では変えない**：
  `.claude/skills/issue-pipeline/SKILL.md` のリスク信号表は、model をブラストレディアス・変更規模・
  パターンの新規性・触る対象の性質・可逆性・仕様の明確さという**変更の性質**から機械的に引く
  （迷ったら opus 側に倒す）。「レートリミットに当たったから」はこの表のどの信号にも当たらず、
  選定根拠を実行環境の都合へ勝手に差し替える行為＝規約が定めた品質水準を AI の独断で下げることに当たる。
  選定根拠を1行残す規定があるため、降格すると記録上「リスクで選んだ」ように誤読されうる点も実害。
- **例外を作らない**：「急ぎだから」「軽微だから」は降格の根拠にならない。
  発端＝PR #319（Issue #315）で `pr-reviewer`（opus）がセッション上限停止した際、AI が独断で sonnet へ
  降格して再投入しようとしオーナーが停止させた事例（Issue #321）。
- **`codex-review`（別モデルファミリ）への切替は「降格」ではなく「追加の第二意見」**：`pr-reviewer` の同一構成での再投入が第一であり、`codex-review` はその再投入を置き換えるものではない。上限を理由に `pr-reviewer` を再投入せず `codex-review` だけで済ませるのは禁止される側に残る。再投入した**上で**別ファミリの第二意見も取ることは品質を下げる行為でなく、本規範に抵触しない（Issue #325 オーナー確定）。

## スキル/エージェント
- スキル（仕様）：`/align` `/value-trace` `/mvp-scope` `/schema-design` `/domain-model` `/spec-pipeline` `/asset-pipeline`
- スキル（実装設計）：`/architecture-design` `/orchestration-design` `/prompt-design` `/impl-design-pipeline`（凍結セット）・`/test-strategy`
- スキル（横展）：`/asset-lateral-deploy`（資産の別プラットフォーム展開）
- スキル（外部委譲）：`/agy-delegate`（Antigravity(agy)CLI への作業移譲の入口。疎通チェック必須・薄い起動口で実体は `agy-delegate` エージェント）
- スキル（外部委譲・第二意見レビュー）：`/codex-review`（Codex 公式 CLI `codex exec` への第二意見レビュー委譲の入口＝別モデルファミリ OpenAI。`agy-delegate`＝agy MCP/Gemini とは委譲先の機構が別・in-repo Claude レビュー→merge は `pr-reviewer`。cybersecurity フィルタで最終応答が `ERROR:flagged` に消える件の回避＝防御形式プロンプト＋`~/.codex/sessions/rollout-*.jsonl` フォールバックを規約化。Linux/WSL 専用・全外部ツリー非移植＝`asset_parity/exceptions.py` に登録済み。opus session 上限時の**追加の第二意見経路**として使える（`pr-reviewer` の同一構成での再投入を置き換えるものではなく、再投入した**上で**別ファミリの意見も取る用途））
- スキル（Issue 運用）：`/issue-pipeline`（複数オープン Issue を implement→PR→review→merge→close で1件ずつ完結させる repo 運用オーケストレータ。主文脈は処置順の triage・進捗管理・オーナーとの意思決定に専念し、実装は `issue-implementer`・レビュー/マージは `pr-reviewer` へ委譲。model は bloom-model-tier＋リスク信号でルーブリック選定・再レビューは常に Sonnet・重い調査は agy-delegate。dev-tooling メタパイプラインで doc-system-v2 の ORC ノード化・prompt_coverage_targets 対象外＝agy-delegate と同区分）
- スキル（メタ・資産運用）：`/bloom-model-tier`（Bloom 認知分類でカスタムエージェントの `model:` ティアを選定。Lv1→haiku／Lv2-3→sonnet／Lv4+→opus）
- スキル（ノード検索・コンテキスト効率）：`/docidx`（**v1-archive 専用**。現行コーパスは doc-system-v2 のため対象外。実体＝`archive/docidx-v1/`＝`python3 -m archive.docidx-v1`・対象は `doc-system-v1-archive/`。read-only・drift は情報提示のみで判定はしない。issue #172 で `docidx/` から `archive/docidx-v1/` へ退避、共有 YAML リーダ `nodeyaml.py` は `dsv2/nodeyaml.py` へ分離）。v2 コーパスの検索・読込は `dsv2-lookup`（下記）が担う
- サブエージェント（点検・分析）：`spec-inspector`（仕様点検）・`structured-analysis`（DFD 分解）・`asset-auditor`（資産の重複/矛盾/競合監査・read-only）
- サブエージェント（ノード検索）：`dsv2-lookup`（**dsv2-native**＝`python3 -m dsv2 index` の meta.json を grep/python でフィルタ→ `Read` で本文取得、辺は `dsv2 deps`/`dependents` で関連ノードのみ取得・ダイジェスト返却＝context 圧縮。ノード内容に対し read-only・`Bash` は `dsv2` CLI 実行のみ。旧名 `docidx-lookup`・v1 専用 `docidx` との混同を避けるため issue #173 で改名）
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

### 戻り値のハンドオフ規約（write 権限の有無で分ける・2026-07-28）
context-mode プラグイン（グローバル導入）が全 subagent 呼び出しに `<artifact_policy>`（成果物はファイルに書き、
パスと1行要約だけ返す）を注入する。**これを潰さず、受け渡し方を合わせる**方針で統一する。

- **write 権限があるエージェント（`*-author` / `structured-analysis` / `reconciliation` / `issue-implementer`）**
  → 呼び出し元へ返す項目を **`tmp/_handoff/<agent>--<key>.yaml`** に Write で書き、チャットには
  **`HANDOFF: <path>` ＋1行要約だけ**を返す。項目は従来の戻り値と同一（スキーマは各 agent.md の「ハンドオフ」節）。
  **呼び出し元は必ずこのファイルを Read して判断する**（1行要約だけで判断しない）。
  `tmp/` は gitignore 済み。`tmp/_handoff/` は `reconciliation` の tmp 掃除（`tmp/<sprint>/<parent-id>/`）の対象外
  （掃除は `python3 -m dsv2 clean-tmp <path> --apply` が保護名 `_handoff`・`_karte` を構成要素に
  含むパスを機械的に拒否する＝`dsv2/cleantmp.py` の `PROTECTED_DIRNAMES`。`_karte`＝是正ループの
  診断カルテ置き場（Issue #307）も同様に掃除対象外）。
  - **`<key>` は呼び出しごとに一意にする**：`authoring-fanout` は各 author へ `target_key`
    （**呼び出しごとの nonce**＋親＋型＋連番）を、`reconciliation` へ `batch_id`（sprint＋layer＋同じ nonce＋先頭親）を
    採番して渡す。親 ID だけをキーにすると、同一親の複数 target や `parent_id` 空の新規ルートが並列で走ったときに
    **同じファイルを上書きし、片方の結果が失われる**。nonce が無い決定論的採番だと、`(親, 型, 連番)` が偶然一致する
    **別バッチ**との衝突も同じ形で結果を失う（issue #278）。nonce は**バッチ内で共有する**（target ごとに振ると
    同一 target の二重ディスパッチ検査が効かなくなる）。
    **再試行の冪等性は nonce ではなく `retry_of` の明示で担保する**：失敗した target をやり直すときだけ、
    呼び出し元が `retry_of: <前回の target_key>` を渡して同じキーを再利用させる（新規著作では渡さない）。
  - **worktree をまたぐ場合は呼び出し元が絶対パスで渡す**（`issue-implementer` の `handoff_path`）。
    linked worktree 内では相対 `tmp/_handoff/` がその worktree 配下に解決され、呼び出し元から回収できない。
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
  - **付与先＝主文脈・`issue-implementer`・`pr-reviewer`・`dsv2-lookup`**（いずれも既に Bash を保有）。
    **Bash 非保有ロール（`spec-inspector` / `asset-auditor` / 各 `*-author` 等）には付与しない**——
    ゲートが効いても「シェル実行能力の新規付与＝権限昇格」は残るため。
  - **`language` は `shell` のみ許可**（ゲートが機械的に強制）。非 shell 言語は
    `<interpreter> -c <code>` と同値で、`permissions.deny` と危険コマンド層が全ロールに対し既に
    禁じている形。静的検査で安全に扱えない（複数のサブプロセス起動 API・文字列結合・eval で
    トークン一致を自明に回避できる）ため、コードではなく**言語そのものを allowlist で絞る**。
  - **gated 2ロール（`issue-implementer` / `pr-reviewer`）は層1〜3 が ctx 経路にもそのまま掛かる**——
    push/merge の非対称は維持され、**シェル記号（パイプ等）も deny される**。出力の絞り込みは
    シェル記号ではなく **`ctx_batch_execute` の `queries` / `ctx_execute` の `intent`** で行う。
    また gated 2ロールは **`cwd` の明示指定が deny**（省略時は context-mode がプロジェクトルートを補う）。
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
- **正本の所在**：`doc-system-v2/nodes/**`（ノードグラフ）＋ `.claude/`（資産・規約）＋ 本 `CLAUDE.md`。
  - **注意：「正本の所在」と「起票先」は別軸**。`.claude/` 配下の改修すべてが Issue 運用になるわけではない
    ——著作・検証エージェントや仕様策定スキル14件のように**両システムに含有されるハーネス**の改修は、
    従来どおりノード起票＋ダッシュボード更新の対象になる。Issue 運用（`/gh-create-issue`）に回るのは
    `issue-pipeline` 系・実行環境フック等の**どちらのシステムにも含有されない汎用開発ハーネス**の改修に限る。
    前掲「[起票先はプロジェクト区分で決める](#起票先はプロジェクト区分で決めるハーネス開発は-issue-運用)」参照。
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
- **資産ツリー間の presence/absence 検出（issue #155・検出半分）**：`.claude/skills|agents`（正本）↔ `.github/skills|prompts|agents`（Copilot）↔ `.codex/agents`（Codex CLI agent）↔ `.agents/skills`（Codex CLI skill）の4ツリーが揃っているかを **read-only** で機械検出するツール＝`asset_parity/`（`python3 -m asset_parity check`・標準ライブラリのみ・使い方は `asset_parity/README.md`）。**内容を書き換えるツールではない**（一括変換は 2026-06-15 に廃止済み・`asset-lateral-deploy` 参照）。意図的な非移植（`agy-delegate`／`issue-pipeline`＋`issue-implementer`／`pr-reviewer` の Copilot 非移植等）は `asset_parity/exceptions.py` に記録し、`.claude/tailoring-registry.md` の既存決定と同期させる（新規に非移植を決めたらまず tailoring-registry.md に記録してから exceptions.py に追記）。**CI 組み込み済み**（`.github/workflows/asset-parity.yml`・4ツリーいずれかを触る push/pull_request で自動起動・`MISSING` はビルド失敗／staleness はビルドを止めない・詳細は `asset_parity/README.md`）。
