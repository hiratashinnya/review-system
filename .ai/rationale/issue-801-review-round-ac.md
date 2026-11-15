# Issue #801：0件レビュー・元Issue AC判定の設計判断と根拠

> 起源：Issue #801 本文から移設（2026-11-15）。Issue本文は現在の作業契約・AC・依存関係だけを残す。**このファイルは選択肢・検討経緯・現状調査・不採用案の保管場所であり、未決事項を自動承認しない。**
> 関連：Issue #375、#800、#801、#848、Draft PR #846。実装時点の記述と現在のコードが食い違う場合は、時点を区別して再検証する。

## 2026-11-15 更新：元 Issue の AC 充足判定を本 Issue へ統合（オーナー決定）

Claude Code (AI) が、オーナー決定（2026-11-15）に基づき本文を更新した。AC は追加のみで、既存7件の文言は変えていない。既存本文の記述は次の2点を訂正した（それ以外は追記のみ）：① `parse_review` の所在（`karte/model.py` → `karte/review_report.py`。「現状と根拠」の該当 bullet）、② 「#800 を blocked-by」の解消（#800 は 2026-11-11 に CLOSED、PR #697 は main へ merge 済み。「Dependencies / Related issues」）。

オーナー依頼：レビュー時に差分の検証だけでなく、元となった Issue の AC を充足できているか確認したうえで、Issue 本文のチェックを更新する（権限設計上 reviewer にできない場合は、主文脈の代行でもよい）。決定は次のとおり。

1. reviewer が AC ごとの充足判定と根拠を返す。未充足は `harm: real` の finding とする。
2. review が clean になった後の owner report 時に、主文脈が Issue 本文の AC チェックを代行更新し、事後報告する（事前確認は不要）。
3. チェック付与は「AC の更新」の事前確認の対象外と明記する。AC 文言の変更は従来どおり事前確認とする。

集約の根拠（`.ai/skills/gh-create-issue/SKILL.md` §3 軸2）。「0件の clean の取り込み拒否」と「元 Issue の AC 判定の置き場」は別の問題であり、同一視しない。ただし次の2条件を満たす。

- 対策の選択肢が重なる：AC 判定は finding 0件の clean でも返す必要があり、置き場は本 Issue が選ぶ 0件形式（(A)(B)(C)）に直接依存する。(C) を選ぶと、clean の AC 判定を載せる経路が無くなる。
- 部分最適の経路がある：別々に決めると、同じ review artifact に非互換な2形式ができる。

0件形式の各案は、従来の評価軸に加えて「clean でも AC 判定を載せられるか」でも比較する。

成果は2つになる（① 0件の clean の取り込み形式と round 記録、② 元 Issue の AC 充足判定とチェック更新）。オーナー決定により本 Issue へ統合した。着手時に1つの PR で満たせない規模と分かった場合は、オーナー方針（2026-11-10）に従い着手時に分割する。

## 目的・背景

指摘ゼロの clean な初回レビューが、Claude Code 直接経路・Codex 経路のどちらでも `ingest-reviewer` に拒否され、review run を完了扱いにできない。0件を表す正式な形式と、その round の記録方法を決め、reviewer 契約（`.ai/agents/pr-reviewer.md`）へ明記する。

本 Issue は #375（`type:tracking`）の子で、オーナー方針（2026-11-10）「Issue の一部しか実装しない PR はあってはならない。AC は1つの PR で満たすべき。Issue が大きければ着手時に分割する」に従い切り出した。PR #697（#800 の実装 PR）は 0件のレビューを扱わず、PR 本文の「未解決事項」に「対応方式とスコープはオーナー判断待ち」と記載している。

AC の出典：#375 の既存 AC に 0件は明示されていない。`O2`（#375「Acceptance criteria」2番目＝承認方式の実装で finding 全文が主文脈を通過しない）と、#375 冒頭「共通artifact envelopeとの接続」の「parse、保存、ingest、ID/round/digest 照合のいずれかが失敗したら review run を完了扱いにしない」が暗黙に前提とする「clean なレビューも同じ経路で完了できること」を、PR #697 本文の未解決事項（出典）に基づいて明文化したもの。

## 現状と根拠

検証基準は作業ツリー HEAD `4e82a9a`（PR #697 の head として #792 が記録した commit）の読解。以下は読解による事実で、再現コマンドの実行結果ではない。

- （2026-11-15 訂正・main `445fb0bf` で所在を確認。当初の記載は `karte/model.py`）`karte/review_report.py` の `parse_review`（`karte/model.py` は再エクスポート入口）は、`parse_blocks(text, allow_preamble=True)` の結果が空のとき `KarteFormatError`（「レビューレポートに finding ブロック（`### F-<issue>-<seq>` か `### new`）が無い」）を出す。docstring も「ブロックが1件も無いときは…finding ブロックが無いと報告する」と書いている。【読解で確認】
- `karte/ingest_review.py` の `ingest_locked` は `model.parse_review(report_text, issue)` をそのまま呼び、0件用の分岐を持たない。【読解で確認】
- 結果として、finding ブロックを持たないレポートは台帳にも進行ポインタの round にも記録されず、fail-close で拒否される。PR #697 本文によれば、Codex の trusted wrapper でも同じ理由で review run を完了できない。
- 0件と区別すべき失敗が別にある：Codex の空出力・非ゼロ終了・ポインタ不在は STOP（`.claude/agents/pr-reviewer.md`）であり、Write の途中打ち切りで本文が欠けた handoff も finding ブロックが無く見える可能性がある（未確認）。「0件の clean」と「出力が壊れた／欠けた」を同じ扱いにできない。
- round 2 以降の 0件は、前ラウンドの未解消 finding が残っていれば「再掲漏れ」（K-06・`ingest_checks.absent_open_ids`、保護モードでは `EXIT_INCOMPLETE`）と衝突する。「不在は解消ではない」ので、0件レポートを単純に clean とみなせない。
- カルテ issue-375 の `F-375-23`（open・PR #697 の `fix-here`）は、申告0件の原本作成テストが `policy.persist` を直接呼ぶだけで、実際の `ingest-reviewer` 経路で 0件レポートが受理されるか拒否されるか・原本が作られるかを検証していないと指摘している。本 Issue が決める形式に依存するため、PR #697 側のテストの扱いは #800 の側で整合させる。
- オーナー報告の観測（カルテ issue-375 の `F-375-25` として主文脈が記録する予定）。本起票時点の `tmp/_karte/issue-375.md` は `F-375-23` までで、`F-375-25` は未記載。

2026-11-15 の再確認（main `445fb0bf`・PR #697 merge 後の読解。`git rev-parse` が gate で拒否されたため `.git/refs/heads/main` から読んだ。実行結果ではない）。

- 上記の 0件拒否（`parse_review` と `ingest_locked`）は main でも変わっていない。前書きは無視され、finding ブロックが無いレポートは拒否される。したがって clean のレビューには、充足と判定した AC を載せる karte 経路がない（レビュー結果の PR コメントは主文脈が記録する別経路。`.ai/skills/issue-pipeline/SKILL.md` ②-b）。
- `.ai/agents/pr-reviewer.md`「レビュー契約」に、元 Issue の AC の充足判定はない。`.ai/skills/issue-pipeline/SKILL.md` の②-b・②-c・②-d にも、AC チェックを更新する担当と手順がない。
- `.claude/agents/pr-reviewer.md` の `gh` は `issue view` まで（`issue edit` は不可）で、`Write` は handoff の新規ファイルだけ（wrapper の記載。hook 表の機械 SSoT は未確認）。reviewer は元 Issue の AC を読めるが、本文を更新できない。Codex 経路は network 無効（`.ai/skills/issue-pipeline/SKILL.md` ②-c 手順4）で Issue を取得できず、AC は入力として渡す必要がある。
- `.ai/guidance/common.md`「作業分離・判断境界」は「Issue・PR のクローズと、それぞれの受け入れ基準（AC）の更新は…事前確認する」と定める。チェック付与がこの「AC の更新」に含まれるかは明記されていない。同趣旨が `.claude/hooks/governance-directives.md` 項12 と `.ai/skills/gh-create-issue/SKILL.md` §1・§3 にもある（網羅的な列挙は未実施で、AC に含める）。
- `.ai/skills/review-harm/SKILL.md` は「仕様・設計との不一致」を `harm: real` とする。AC 未充足を `harm: real` とすることは、この既存基準と整合する。
- 実例：#800 は 2026-11-11 に CLOSED で、「Acceptance criteria」節の checkbox 10件がすべて `- [ ]`（チェック済み0件）のままである（2026-11-15 に本文を取得して計測）。AC の充足有無は未確認で、ここでは「充足の記録が本文に残らない」事実だけを挙げる。

## Scope

- 0件を表す正式な形式の選択肢・トレードオフ・理由付き推奨をオーナーへ提示し、決定する（設計判断を含む）。着手時に現物を再確認して選択肢を確定する。起票時点の候補：
  - (A) 本文へ明示的な 0件マーカー（例：既存の `### new` と並ぶ「0件」を宣言する見出しや1行）を要求する。利点＝出力の欠落・打ち切りと機械的に区別できる。欠点＝reviewer 契約とパーサの両方の変更が要る。
  - (B) handoff ヘッダへ `findings=0` を載せ、本文は空を許す。利点＝本文を書き換えない。欠点＝ヘッダは宣言であって本文と照合できず、打ち切りで本文が空になった handoff との区別が弱い。
  - (C) 0件はそもそも取り込み対象にせず、「取り込み不要」を別経路（wrapper／reviewer の最終応答）で報告させる。利点＝karte を変えない。欠点＝round の記録が台帳に残らず、「そのラウンドをレビューした」事実が永続しない（現状の問題の再演になりうる）。
  - 暫定の推奨は (A)。理由＝失敗コストの非対称（0件を誤って clean と受理すると、実害ありの指摘を取りこぼしたまま通る失敗は merge 後まで気付けない）。出力欠落との区別を機械で担保できる形を優先する。着手時に現物を確認して確定する。
  - 評価軸の追加（2026-11-15）：「clean でも AC 判定を載せられるか」。(C) を選ぶ場合は、AC 判定の別経路を定める。
- 決定した形式での round の記録方法（台帳の round／進行ポインタ／原本のどこに 0件の round を残すか）を決め、実装する。
- 決定を reviewer 契約（`.ai/agents/pr-reviewer.md`）へ明記し、`.claude/agents/pr-reviewer.md`・`.ai/skills/issue-pipeline/SKILL.md` ②-b/②-c・`karte/README.md` を追従させる。
- （2026-11-15 追加）`.ai/agents/pr-reviewer.md` の 2b レビュー契約に、元 Issue の AC 全件の充足／未充足の判定と根拠を返す規定を追加する（finding 0件の clean でも返す）。
- （同）AC 未充足を、既存の finding 書式（9項目・スキーマ不変）の `harm: real` finding として返す規定を置く。
- （同）`.ai/skills/issue-pipeline/SKILL.md` の②-b・②-d に、clean 後の owner report 時に主文脈が Issue 本文の AC チェックを代行更新し、事後報告する手順を追加する。実行主体は主文脈とし、`pr-reviewer`・`issue-implementer`・`issue-fixer` には行わせない。
- （同）`.ai/guidance/common.md`「作業分離・判断境界」に、チェック付与は事前確認の対象外、AC 文言の変更は従来どおり事前確認、と明記する。「AC 更新は事前確認」と述べる全箇所を列挙し、整合させる。
- （同）Codex 経路（read-only・network 無効）へ、元 Issue の AC を入力として渡す方法を定める。

## 型別の補足（improvement）

- 利用者価値：clean なレビューも他のレビューと同じ経路で完了でき、「そのラウンドをレビューした」事実が永続する。AC を満たさない PR を merge 前に reviewer が検出でき、Issue 本文のチェックが充足の実態を表す。
- 提案挙動：上記 Scope のうちオーナーが選んだ形式。
- 互換性：finding が1件以上あるレポートの受理・拒否の結果（終了コード・標準出力の注記・台帳内容）を変えない。変える場合は理由とオーナー承認を残す。AC を持たない Issue の PR レビューを止めない。
- 代替案：上記 (A)(B)(C)。`pr-reviewer` に Issue 本文の更新権限（`gh issue edit` 相当）を付与する案は、権限分離（#803）に触れるため、オーナー決定により採らず、主文脈が代行する。

## 着手時に決める未決点（2026-11-15 追加・AC 判定分）

オーナー決定の範囲外であり、AI が独断で倒さない。着手時の1a/1bで、各点の原案・比較・理由付き推奨を添えてオーナー判断を仰ぐ。

1. PR 時点で観測できない AC（merge 後の実測が必要なものなど）の判定区分と、チェックの扱い。
2. AC 未充足の finding が `deferred`/`waived` で clean になった場合の、当該 AC のチェックの扱い。
3. チェック済みの AC が再レビューで未充足と判定された場合の扱い（取り外しの是非、事前確認の要否）。
4. AC の取得元（dispatch 時点の snapshot か live の本文か）、更新直前に AC 文言の一致を確認する方法、オーナーの編集との競合、Codex 経路への渡し方。
5. 充足した AC の記録先と形式（finding ではないため、前書き・新ブロック・PR コメントなど）を、0件形式（A）（B）（C）と一体で決める。AC を持たない Issue・checkbox 形式でない Issue・AC が子 Issue へ移った tracking Issue（#375 型）の扱い、owner report に載せる AC 充足状況の様式もここで決める。

## 2026-11-15：未決事項の追加調査と指摘

- **① AC結果の語彙**：`satisfied / not_met / unverified` はPR #846 の `karte/review_summary_ac.py` で追加された **AC判定専用の新規列挙**。既存 `karte/vocabulary.py` の `harm: real|none`、`status: open|resolved`、`disposition: fix-here|deferred|waived` と異なる判定軸。別コンポーネントの `unverified-evidence` は証拠の検証状態であってAC判定の既存規格ではない。新語彙を採用するなら互換性・SSoT・consumerを別途検証し、オーナー決定前は確定語彙として扱わない。
- **③ チェック済みACの後退**：`karte/ac_check_update.plan` は後退時に例外を送出するが、GitHub更新実行経路に強制結線されていない。呼び忘れを防止する機械的保証がなく、AIの注意力に依存する。owner-onlyの書込境界に整合性検査を結線するまで確実な停止とは主張しない。
- **独立レビュー F-801-06 / F-801-08 / F-801-09 / F-801-10**：最新PR #846の独立レビュー（HEAD 909122ef）で、snapshot無しのenvelopeフォールバック、複数行ACの見落とし、Codex起動互換テスト、CLI parser golden不整合を指摘。これらは未解消の実害findingであり、本件の完了条件に残る。

## ① AC判定語彙の背反点検（2026-11-15）

| 確認先 | 既存の意味・境界 | 新規 `unverified` との関係 |
|---|---|---|
| `karte/review_summary_ac.py` | `result` に `satisfied/not_met/unverified` を新設 | **AC判定専用の新規enum**。既存の正本語彙ではない |
| `karte/vocabulary.py` / `karte/status_verdict.py` | findingの `harm=real/none`、`status=open/resolved`、`disposition=fix-here/deferred/waived` | 異なる判定軸なので直接の値衝突はない。ただしACの評価不能とfindingの実害を直結する規定は追加判断 |
| `.ai/skills/review-harm/SKILL.md` | 実害は仕様違反・検証不能・トレーサビリティ断絶等を根拠とし、単なる推測を実害としない | 未観測の理由を示さず全件を `harm: real` とするのは、実害根拠の個別立証規則と衝突するおそれ。特にmerge後にしか観測できない条件は、意図した測定時期と失敗を区別する必要がある |
| `triage_policy/evaluator.py` / `.ai/rationale/triage-policy.md` | `unverified-evidence` は証拠の確認不足に対する owner-review 理由。AC違反のdeferred候補を自動提案しない | 同じ単語を用いるが**別語彙**。自動でdeferredを承認する機構ではない |
| `.ai/agents/pr-reviewer.md` と `.ai/skills/issue-pipeline/SKILL.md` | AC判定とfinding列の関係、処置はowner専権 | 現PRで `unverified` を新規導入しており、他の役割と互換性が確定したとは言えない |
| `karte/ac_check_update.py` | `unverified` でチェック付与しない | 呼び出したときだけ機能する。元Issue側との結線・書込境界が不十分 |

**結論：語彙新設である。既存の列挙値と同一データ項目で衝突する箇所は見当たらないが、semanticな背反は未解消**。推奨は、`unverified` を単なる「ACの未検証状態」として定義し、原因別に「レビュー時点で実測可能なのに未検証」「後工程を正当な測定時期とする」の区別を契約化すること。後者を自動 `harm: real` とするかはオーナー判断①へ戻す。これ以前に検証済みと宣言しない。

## ③ チェック済みAC後退の機械停止ギャップと必要な構成

現行 `karte/ac_check_update.plan` は `ac.checked is True` かつ `result != satisfied` なら `KarteUsageError` を送出し、単体テストが存在する。しかし**GitHub Issue本文の書込みは独立した `gh issue edit` / MCP経路から可能**であり、この関数を必須で通すようには配線されていない。よって**AIによる呼び忘れを機械的に防げない**。

さらに最新独立レビューの **F-801-08** は複数行ACの続きがsnapshot/digestから欠落し、続きのみが変化しても照合を通ると実証した。F-801-06はsnapshotを省略できる旧モードへの暗黙フォールバック。両者を塞ぐまで、`plan` 呼出し自体も十分な停止保証ではない。

必要な構成（③の正式なオーナー決定より前の**設計案**）：
1. 元IssueのAC全行（複数行継続・子項目も含む）をsnapshot化し、対象の本文・基点のrevisionを固定する。原本とレビューSummaryの整合がなければ書込不可。
2. **唯一のowner-only ACチェック更新入口**が、最新roundの原本・digest、全AC結果、`karte status` のverdict、snapshot/liveを照合。既存チェック済みACの後退、未検証、件数不整合、原本欠落はAPI呼出し前に機械停止。
3. managed operation内でraw `gh issue edit`／GitHub MCPの本文更新を直接実行できる経路をポリシーや権限で拒否し、上記入口への迂回を塞ぐ。**この封鎖がなければ完全な停止保証と報告しない**。
4. 同一Issueの同時編集はGitHub側の条件付き書込／revision整合の可否を検証し、非原子的なら read-backだけではTOCTOU完全保証ではないことを残差として明示する。
5. 「checked→unverified/not_met」「継続行だけのlive変更」「snapshotなし」「別Issue」「古いround」「read-back不一致」「直接書込迂回」を**write boundaryのE2E**でテストする。helper単体成功は代用しない。

この構成の採用と停止時のオーナー判断手順は未決③に属し、ここでは承認済みとは扱わない。
