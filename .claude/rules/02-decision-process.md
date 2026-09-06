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

## オーナーへの報告はチャットが正本（副次記録との分離・2026-08-20・Issue #379）
**オーナーへの報告・意思決定の仰ぎはチャット（main thread の直接出力）が正本である。**

- **判断事項はチャットに全文出す**：オーナーの判断を要する事項（PR7 の打ち上げ・据え置き可否・スコープ判断・矛盾など）は、チャットに「何を・なぜ・どうするか」が読み取れる粒度で全文を提示する。ID や 1 行要約だけで投げて「詳細はファイルを見てほしい」とするのは禁止。
- **PR コメント・カルテ・ファイルは永続化目的の副次記録**：PR レビューコメント、カルテ（`tmp/_karte/`）、ハンドオフ（`tmp/_handoff/`）、各種ノード（Q/FND/DD）は「永続化を目的とした副次的な記録」であり、そこに書いたことをもってオーナーへの報告・確認済みとはみなさない。
- **`<artifact_policy>` 等の要約規律の適用境界**：`<artifact_policy>` 等で注入される「長文出力を抑制しアーティファクト/ファイルへ逃がす」規約は **subagent → 呼び出し元（主文脈）** 間の通信規約であり、**主文脈 → オーナー** への報告・判断要請には適用しない。主文脈はオーナーに対してチャット上で判断材料を完結して提示する。
- **報告のタイミングは「実行前」（Issue #484）**：本節の他の項が定めるのは報告の**形式**（チャットが正本・副次記録では代替されない）であるのに対し、本項が定めるのは報告の**タイミング**である。**merge・push・force 系操作・外部への投稿など、取り消しにくい／共有状態に影響する操作は、実行してからまとめて報告するのではなく、実行前にチャットで報告して確認を得る。** 事後のまとめ報告は、たとえチャットで全文を出していても報告義務を果たしたことにならない（形式を満たしてもタイミングを満たしていないため）。clean 判定や過去に一度得た承認を、その後の実行の事前確認の代わりにしない。PF 共通の同趣旨の規定は `.ai/guidance/common.md`「作業分離・判断境界」にある。

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
  - Issue 運用パイプライン：`issue-pipeline`/`issue-implementer`/`issue-fixer`/`pr-reviewer`/`gitgate`
  - 実行環境の面倒を見るフック：`on-rate-limit.sh`/`resume-watcher.sh`/`install_pkgs`/
    `inject-governance.sh`/`check-governance-drift.sh`/`orchestrator-context.sh`/`agent-command-gate.sh`、
    `.claude/settings.json`
  - 外部委譲・モデル選定・横展・Issue 起票の補助：`agy-delegate`/`codex-review`/`bloom-model-tier`/
    `asset-lateral-deploy`/`coverage-html`/`gh-create-issue`/`asset_parity`
  - 是正ループ用ツール：`karte`
  - 点検・監査ツール（read-only）：`asset-auditor`（資産の重複/矛盾/競合監査。特定システムの仕様グラフが
    記述する対象ではなく資産全体を横断するため）
  - v1-legacy 退役ツール：`archive/docidx-v1`（v1 コーパス専用の検索ツール・実装対象は
    `doc-system-v1-archive/` のみで v2 コーパスは対象外・退役済み。**前掲「仕様策定・実装設計スキル」リストの
    含有14件と同名の skill `/docidx` を混同しないこと**——`skill /docidx` は doc_system の仕様策定機構そのもの（PROMPT 設計ノード
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
