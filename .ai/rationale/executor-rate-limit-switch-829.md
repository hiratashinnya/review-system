# レートリミット時の規範の経緯（Issue #321 → Issue #829）

> **これは規範ではない。** 現行の規範は次の箇所にある。本書は、そこから移した経緯と、書き換えの根拠を保持する。
>
> - `.claude/rules/03-operational.md`「レートリミット時の品質降格の禁止と、委譲先 Codex 実行者の上限時の切替」
> - `.ai/skills/issue-pipeline/SKILL.md`「実行先、モデル、相談」
> - `.claude/skills/issue-pipeline/SKILL.md`「Codex 実行者経路」
>
> 移設は Claude Code (AI) が Issue #829 で行った（2026-11-15）。分離の方針は `.ai/rationale/README.md`。

## Issue #321 の規範の根拠と発端（移設元：`.claude/rules/03-operational.md`「レートリミット由来の品質降格の禁止（絶対規範・2026-08-03）」）

移設元の箇条書きのうち、理由と発端を述べる部分を移した。禁止対象と対処を述べる部分は移設元に残して書き換えた。

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

移設元の見出しは「絶対規範」を名乗り、上の箇条書きは「例外を作らない」と述べていた。

## Issue #321 のオーナー判定（出典：Issue #321 本文・オーナー指示 2026-08-03）

Issue #321 の本文が「オーナー判定」として引用している文をそのまま写す。

> レートリミットで停止した場合も sonnet に降格したり effort を下げたりサブエージェントに移譲することをやめたりしてはならない。**主文脈が動けているということは、すなわちレートリミットが解除されたということだ。**無駄なことをして品質を下げるな。

## Issue #829 で書き換えた理由

### オーナー決定（2026-11-15・出典：Issue #829 本文）

Issue #829 の本文は同日チャットの決定を結論だけ記録している。逐語はリポジトリ内に無い。

1. Claude 固定：ac-designer・change-planner・plan-reviewer・pr-reviewer。Codex 既定：issue-investigator・test-writer・issue-implementer・issue-fixer・adviser。
2. 委譲先がレートリミットのときは、同じロールの Claude サブエージェントへ同等以上の層で切り替えてよい。主文脈の直接代行と層の降格は禁止のまま。
3. agy は振り分け方針だけ定義し、有効化は #606 の解除契約に従う。
4. 工程に乗らない低難度作業の経路は別 Issue（#831）。

### 覆す根拠（AI の分析。オーナー決定は結論のみ）

Issue #321 の「同じ構成で再投入」の根拠は「主文脈が動いている＝枠は回復している」である。これは Claude 側の枠の話で、別提供者である Codex の枠が回復したことは示さない。主文脈（Claude）が動いていても、Codex 実行者の上限は続いていることがある。

このため書き換えは Issue #321 の根拠を否定していない。根拠が届かない範囲（委譲先の Codex 実行者の上限）だけを例外として切り出した。Claude ロール自身の上限には Issue #321 の根拠がそのまま当てはまるので、同一構成の再投入のまま残した。降格・effort 低下・主文脈による代行の禁止も残した。

### 採用した暫定決定（Issue #829「CP で決める論点（AI の推奨）」より）

- 切替の主体は主文脈とする。主文脈が同一ロールを Codex 実行者の指定なしで再 dispatch する。理由は、ロール自身は層を上げられず、選定根拠の記録は主文脈の責務だからである。
- 高リスク信号の実装も Codex 既定の例外にしない。Codex 側の層を引き上げる。理由は、Claude 固定の独立レビューが残るからである。

### 決めなかった点（Issue #829 の実装時点）

次の点は既存の規範とオーナー決定から一意に決まらなかった。規範本文には未決と書き、決まるまで STOP とした。

- adviser の相談を、難度を理由に Claude へ切り替えてよいか。
- Codex 実行者が途中で止まり、未 commit の部分変更が worktree に残ったときの扱い。
- agy の有効化後に、工程内の調査で Codex と agy のどちらを先に使うか。
- 上限の証拠となる出力の文字列・終了コード。Codex が上限時に返す出力の実測記録がリポジトリ内に無い。

### オーナー決定（2026-11-16・PR #847 の独立レビュー後）

上の4点のうち3点が次のとおり決まり、規範本文を書き換えた。決定は是正の依頼文に結論だけ記録されており、逐語はリポジトリ内に無い。

1. 未 commit の部分変更は「確かめて引き継ぐ」。ロールが差分とテストで確かめ、範囲内なら commit・push してから STOP し、切替後の Claude ロールが続きから行う。範囲外の変更が混じる場合と確かめられない場合は、既存規範から一意に決まらなかったので、commit せず STOP してオーナーへ打ち上げる側に倒した。
2. 上限の証拠は「逐語記録で暫定運用」。条件は Codex が上限到達を示した出力の逐語があることで、主文脈が逐語を記録して切り替える。初回に実測できた出力を定義へ追記する。
3. adviser は難度を理由に Claude へ切り替えない。難しい相談は Codex 側の層を引き上げる。層表の adviser の層は対応表で引ける語に直した。
4. Claude 固有の切替の例外は `.claude/rules/03-operational.md` にだけ置く。初回実装が `.ai/guidance/common.md` の降格禁止の1行へ足した例外の文は取り除き、PF 共通の内容へ戻した。

agy の有効化後に Codex と agy のどちらを先に使うかは、引き続き決めていない（#606 の解除時に決める）。

### オーナー決定（2026-11-16・是正ラウンド2）

是正ラウンド1で決めずに返した点に、次の決定が出た。決定は依頼文に結論だけ記録されており、逐語はリポジトリ内に無い。

1. Codex が残した変更が範囲内なら、テストが赤くても commit して引き継いでよい。意図して赤い commit（test-writer の Red テスト）なのか、途中停止の引き継ぎだから赤いのかが、コミットメッセージで分かるようにする。規範本文には書く内容（引き継ぎであること、未完了の赤と意図した Red の別）を定めた。決まった接頭辞などの固定書式は、既存文書にコミットメッセージの書式規約が無く一意に決まらないので定めていない。
2. adviser の層は最上位に固定する。上の決定3で書いた「難しい相談は Codex 側の層を引き上げる」「中位または最上位」は、この決定で置き換えた。
3. 層表の issue-fixer 行の推論予算は PR #847 では変えない。層表と bloom の表・frontmatter の食い違い（test-writer 行を含む）は別 Issue で扱う。

### オーナー決定（2026-11-16・是正ラウンド3）

再レビューの後、次の決定が出た。決定は依頼文に結論だけ記録されており、逐語はリポジトリ内に無い。

1. 引き継ぎ commit の書式を固定する。コミットメッセージ本文の末尾に `Handover: codex-limit` と、テストの状態を示す `Tests: red-unfinished`（途中停止の引き継ぎによる赤）／`Tests: red-intended`（意図した赤）／`Tests: green` を置く。引き継ぎではない意図的な赤の commit にも `Tests: red-intended` を書けば区別できる。是正ラウンド2の決定1で書いた「固定書式は定めていない」と、規範本文にあった「通常の commit にはこの記載を付けず、記載の有無で見分ける」は、この決定で置き換えた。
2. adviser の推論予算は「相談内容で引く」のまま変えない。

### 是正ラウンド3の暫定決定（AI の推奨。覆る場合の影響範囲を併記）

既存の規範、オーナー決定、コードの挙動から一意に決まらなかった点を、推奨案で暫定決定した。

#### 1. issue-fixer が引き継ぐときの karte の記録

- 論点：Codex が上限で止まった時点で、Step 1 で登録した Attempt は未クローズである。これをどう閉じ、切替後の issue-fixer がどう診断を登録するか。
- コードの挙動（PR #847 の head で読んだ範囲）：
  - `karte check`（`karte/verb_check.py`）は、未クローズの Attempt が1件でもあると失敗し、`SubagentStop` の停止ゲートが停止を1回拒否する。
  - `karte close-attempt`（`karte/verb_close_attempt.py`）は Attempt 1件に Result を1つだけ追記する。差分が空のとき受け付ける outcome は `no-change` だけである。
  - 類似判定（`karte/saturation_groups.py` の `priors_for`、`karte/similarity.py`）は、未解消 finding を共有する過去の Attempt をすべて比較対象にする。outcome も touched の有無も見ない。同種が2件あると3件目の `append` を `EXIT_SATURATED` で拒否する。
  - `ISSUE_FIX_BINDING_V1` の `round` は 1 以上の整数であることしか検査されない（`issue_start/gate_markers.py`）。
- 選択肢：
  - A：引き継ぎの Attempt を実測どおりクローズし（差分があれば `partial`、無ければ `no-change`）、切替後の issue-fixer は通常どおり `render` → `append` で新しい Attempt を登録する。
  - B：引き継ぎの Attempt を未クローズのまま残し、切替後の issue-fixer が同じ Attempt の下で続けて、最後にクローズする。
  - C：切替後の issue-fixer が root_cause の slug を変えて登録する。
- 暫定決定：A。
- 理由：B は停止ゲートの拒否を2回目の停止で通すことになり、「できる記録は必ず済ませてから停止する」の例外を増やす。切替が行われなかった場合（範囲外の変更でオーナーへ打ち上げた場合など）に未クローズの Attempt が残り、以後の `karte check` が失敗し続ける。C は「ラベルを付け替えて通そうとしない」に反する。A は手順とゲートを変えずに済み、記録が実測と一致する。
- 影響範囲：A では引き継ぎの Attempt が同種の試行1件に数えられるので、同じ root_cause での是正が飽和に達するのが1件早くなる。Codex が何も変更せずに止まった場合（`no-change`）も同じである。文書では避けられないので、`append` が拒否されたら付け替えずに STOP して主文脈へ返すと定めた。引き継ぎの Attempt を類似判定から外すには karte のコード変更が要り、PR #847 の範囲外である。B へ覆す場合は、`.ai/agents/issue-fixer.md`、`.claude/agents/issue-fixer.md`、`.claude/hooks/karte-protocol.md`「4. 停止できる条件」を書き換える。
- outcome の語彙：`partial` と `no-change` の使い分けは、既存の「是正の差分が無ければ `no-change`、あれば実測差分に応じた outcome」（`.ai/agents/issue-fixer.md`「取り込みとカルテ手順の順序」）に合わせた。引き継ぎは是正が途中なので、差分があるときは `partial` とした。
- 切替の再 dispatch の round：レビューを挟まないので同じ round とした。`karte check` は進行ポインタの round で診断の網羅を見るので、round を進めると未解消 finding がその round に属さず、検査の対象がずれる。無進捗検知（`karte/stall_detection.py`）は finding の連続未解消ラウンド数で数え、Attempt は見ないので、同じ round の再 dispatch は無進捗の計数を増やさない。所有台帳の起票（`issue_start/worktree_ledger.py` の `open_entry`）は、同じ issue・round の2回目を拒否しない。
- commit しなかった変更が未追跡の新規ファイルだけの場合：`close-attempt` の既定の測定は `git diff` で、未追跡ファイルを含まない。差分が空になり `partial` は拒否されるので、`no-change` でクローズして `--note` にパスを書くと定めた。

#### 1a. 引き継ぎの STOP と、既存の「STOP を返したらオーナーへ打ち上げる」

- 論点：共通本文は、是正担当が `status: stop` を返したとき、および実装担当が STOP を返したときに、主文脈がオーナーへ打ち上げると定める（実装担当は Project の `Status` を `Ready` へ戻す）。引き継ぎの STOP の後に主文脈が切替へ進む規定と食い違う。
- 選択肢：A：切替へ進む STOP を、この2つの規定の対象外と明記する。B：引き継ぎの STOP に `status: stop` 以外の値を使う。
- 暫定決定：A。
- 理由：ハンドオフの `status` の語彙を増やさずに済む。`.ai/troubleshooting/issue-pipeline.md` は `status: stop` の handoff を `stop_reason` とともにオーナーへ報告すると定めており、切替の事実を報告することとは両立する。
- 影響範囲：`.ai/skills/issue-pipeline/SKILL.md` の2か所。切替へ進む場合、Project の `Status` は `In progress` のまま変えない。

#### 2. issue-implementer が引き継ぐときの draft PR

- 論点：共通契約は「全パスを確認してから PR を開く」と定める。引き継ぎ commit を push した時点で draft PR を開くか。
- 選択肢：A：開かない（例外は commit・push だけ）。B：赤いまま draft PR を開く。
- 暫定決定：A。
- 理由：オーナー決定が認めたのは赤い状態での commit・push であり、PR を開くことは含まれていない。切替後の issue-implementer が全パスを確認してから開けば、既存の契約のまま読める。
- 影響範囲：切替後の再 dispatch まで PR が無い。B へ覆す場合は `.ai/agents/issue-implementer.md`「実装契約」と `.claude/agents/issue-implementer.md` を書き換える。

#### 3. 未完了の赤と意図した Red が同じ commit にあるときの `Tests:` 行

- 論点：オーナー決定は3つの値を定めたが、両方の赤が混在する commit の値は含まない。
- 選択肢：A：`Tests: red-unfinished` を1行だけ書き、内訳を本文に書く。B：`Tests:` 行を2行書く。C：4つ目の値を足す。
- 暫定決定：A。
- 理由：引き継ぎを受ける側が最初に知るべきなのは未完了の赤があるかどうかである。値を増やさず、1行で `git log` の検索に掛かる。
- 影響範囲：`.ai/skills/issue-pipeline/SKILL.md`「Codex 実行者が上限で止まったときの切替」の1文だけである。

#### 4. 引き継ぎではない Red commit の `Tests: red-intended`

- 論点：オーナー決定は「書けば区別できる」という趣旨で、test-writer の通常の Red commit に必ず書くかは明示していない。
- 選択肢：A：test-writer の Red commit には必ず書く。B：任意とする。
- 暫定決定：A。
- 理由：任意にすると、`Tests:` 行の無い赤い commit が意図した赤か書き忘れかを判別できない。
- 影響範囲：`.ai/agents/test-writer.md` と `.claude/agents/test-writer.md` に1文ずつ足した。機械検査は無い。B へ覆す場合はこの2文と共通本文の1文を直す。

#### 5. test-writer が Codex の上限で止まったときの記録先

- 論点：wrapper は「handoff に記録」、共通契約は「STOP でも artifact へ残す」と書いており、記録先が1つに決まらなかった。
- コードの挙動：TestDesign は `red_evidence` を1件以上と `ut_td`・`ut_tc` を要する（`issue_envelope/schema.py`）。途中で止まった時点では成立しないことがある。完了 receipt（`ISSUE_PHASE_BINDING_V1` の `handoff_path`）の内容は、回収した bytes の sha256 で束縛されるだけで、欄は機械検査されない。
- 選択肢：A：完了 receipt の `stop_reason`。B：TestDesign の `status = "stop"` と `stop_reason`。
- 暫定決定：A。
- 理由：途中停止でも必ず書ける。issue-implementer・issue-fixer と同じ欄になり、主文脈が逐語を探す場所が3ロールで揃う。作業ツリーの回収は自分の handoff があるときに行われるので、receipt はどのみち書く。
- 影響範囲：`.ai/agents/creation-stage-contract.md`「返却」に例外を1つ足した。receipt は commit されないので、逐語は主文脈が切替の記録へ写すまで `tmp/_handoff/` にしか無い。B へ覆す場合は、途中停止でも成立する TestDesign の形（`red_evidence` の下限）をコード側で決める必要がある。
- 後の変更：是正ラウンド4で receipt の様式を定め、`status`・`stop_kind`・`stop_reason` の3欄は継続検査が読むようになった（下記）。上の「欄は機械検査されない」は是正ラウンド3の時点の記述である。

### オーナー決定（2026-11-17・是正ラウンド4）

再々レビュー（new-16〜new-21）の後、次の決定が出た。決定は依頼文に結論だけ記録されており、逐語はリポジトリ内に無い。

1. new-16 は、この PR でコードを直す（再々レビューの選択肢 B）。test-writer と issue-implementer が Codex 上限で止まったあと、主文脈が同じ role を Codex 指定なしで再 dispatch する切替が、`issue_start/author_continuation.py` の継続検査（`PREDECESSORS`）に拒否されないようにする。
   - Issue #829 の Out of scope は `codex_worktree_exec` と gate／hook のコード変更を除外しているが、オーナーが明示的にこの PR での変更を決めた。この例外は new-16 に必要な最小のコード変更に限る。
   - 設計の条件（オーナー指示）：検査は緩める側にだけ変え、fail-close を保つ。通すのは、同じ Issue・同じ branch の最新 owner が同じ role で、その entry が上限による引き継ぎ STOP で回収・解放済みであると、台帳の事実から確かめられる場合に限る。
2. pd-4（test-writer の Red commit に `Tests: red-intended` を必ず書く）を維持する。
3. new-20・new-21 はこの PR では直さない。処置はオーナーが別途決める。

### 是正ラウンド4の暫定決定（AI の推奨。覆る場合の影響範囲を併記）

#### 6. 上限による STOP を継続検査がどう判別するか（new-16）

- 論点：継続検査は、最新 owner の `agent_type` が `PREDECESSORS[次の role]` と一致することを要求する。切替の再 dispatch では最新 owner は止まった同じ role なので拒否される。何を根拠に同じ role を通すか。
- コードの事実（PR #847 の head e7379a85 で読んだ範囲）：
  - 所有台帳の entry（`issue_start/worktree_ledger.py`）は `status`・`closed_at`・`collected_to`・`handoff_path` などを持つが、停止理由の欄は無い。`collect-worktree`（`gitgate/worktree_collect_handoff.py`）は handoff の bytes を `tmp/_handoff/collected/` へ写して sha256 を照合するだけで、内容を解釈しない。
  - 継続検査は `ISSUE_PHASE_PREDECESSOR_V1` の entry ID と receipt の sha256 で、回収済み receipt の bytes を台帳 entry に束縛している。したがって台帳から確かめられる「止まった理由」は、この bytes の中身だけである。
  - 上限の逐語は自由文で、上限を示す文字列・終了コードは未実測（逐語による暫定運用）なので、`stop_reason` の文面からは機械で判別できない。
  - handoff の欄を解析するコードは他に無い（`stop_reason` を読む Python は `issue_envelope` の artifact 用の schema だけ）。欄を足しても既存の経路は壊れない。
- 選択肢：
  - A：回収 receipt に機械可読の欄 `stop_kind: codex-limit` を足し、継続検査がそれを読む。
  - B：引き継ぎ commit の `Handover: codex-limit` 行を、remote exact OID の commit メッセージから読む。
  - C：主文脈の marker（`ISSUE_PHASE_PREDECESSOR_V1`）に「切替」を示す欄を足す。
  - D：台帳 entry に停止理由の欄を足し、SubagentStop か collect で書く。
- 暫定決定：A。
- 理由：
  - B は、未 commit の変更が無いまま止まった場合（引き継ぎ commit が無い）に使えない。
  - C は主文脈の自己申告であり、台帳の事実から確かめたことにならない。marker の exact field 検査（`{"entry_id","receipt_sha256"}`）も変わる。
  - D は台帳の schema と停止経路（hook）の変更になり、最小ではない。停止理由を書く主体が結局 role の handoff を読むことになる。
  - A は、既に台帳 entry と sha256 で束縛された bytes の中の1欄を読むだけで、台帳・marker・collect は変えない。3 role の handoff に同じ欄を置けるので、「3 role とも同じ欄」の規定とも揃う。
- 読み方（`issue_start/executor_limit_receipt.py`）：
  - top-level（字下げ無し）の `status`・`stop_kind`・`stop_reason` の行を数え、同じ欄が2行あれば拒否する。
  - `status: stop`、`stop_kind: codex-limit`、`stop_reason` が `|` または `|-` の block scalar の3つが揃わなければ拒否する。UTF-8 として読めなければ拒否する。
  - `stop_reason` を block scalar に限ったのは、逐語を字下げした行に閉じ込めるためである。逐語の中に `stop_kind: codex-limit` という行があっても、字下げされているので判定に入らない。既存の YAML リーダ（`dsv2/nodeyaml.py` はノード frontmatter 用）は block scalar と重複キーの扱いがこの用途に合わないので使わなかった。
  - 行は `\n` だけで分け、`\r\n` は先に `\n` へ正規化する。top-level の値の前後は空白とタブだけを除く。`stop_reason` の直後（空行か空白始まりの行が続く範囲）に、`str.isspace()` に当たらない文字を含む行が1行も無ければ拒否する（是正ラウンド6・下記10）。
- 通す範囲：
  - 同じ role を通すのは `test-writer` と `issue-implementer` だけ（`SWITCH_ROLES`）。change-planner は Claude 固定なので、同じ role の再 dispatch は従来どおり拒否する。issue-fixer は元から継続検査の対象外である。（後の変更：是正ラウンド8で、`claude-limit` の receipt なら change-planner を含む3 role の同じ role を通すようにした＝下記11。`codex-limit` の範囲は変えていない。）
  - 同じ Issue・branch の最新 owner であること、`released` と `closed_at`、`collected_to` の位置、receipt の sha256、remote exact OID の照合は、通常の継続と同じくすべて要求する。
  - 既存の `tests/unit/test_author_continuation.py` は変えずに全パスする。新しい許可条件は `tests/unit/test_author_continuation_limit_switch.py` で、通る場合（2 role・dispatch parser 層）と拒否される場合（Claude 固定 role、別 role、未回収・未解放、`stop_kind` 無し、`status` が stop でない、値違い、重複、字下げ内だけ、block scalar でない、`stop_reason` 無し、非 UTF-8、receipt 改変、より新しい owner）を固定した。是正ラウンド6で、`\n` 以外の行区切り文字による注入と空の `stop_reason` の拒否、`|-`・CRLF・逐語中の行区切り文字の受理を加えた（下記10）。
- 欄の意味：`stop_kind: codex-limit` は「上限で止まった」ではなく「上限で止まり、切替へ進める」STOP を示す。書くのは引き継ぎ commit を済ませたときと、未 commit の変更が無かったときだけで、範囲外の変更が混じる・確かめられないために commit しなかった STOP には書かない。理由は、オーナーの条件が「上限による引き継ぎ STOP」であり、引き継げなかった STOP は規範上オーナーへ打ち上げるので、その再 dispatch を継続検査が通してはならないためである。逐語はどちらの場合も `stop_reason` に残す。
- 既知の限界：
  - `stop_kind` は role 自身の申告であり、上限で止まったことそのものを機械は確かめない。主文脈が逐語を確かめてから再 dispatch する規律と併用する。
  - receipt の sha256 は主文脈が marker に渡す値なので、主文脈が回収 receipt に欄を書き足せば機械は止めない。主文脈は欄を書き足さず、3欄が揃わなければ打ち上げる、と規律で定めた。
  - Claude の role 自身が上限で止まったときの「同じ構成での再投入」は、同じ role の再 dispatch でも `stop_kind` を書かないので、従来どおり継続検査に拒否される。この PR では変えていない。
    （後の変更：是正ラウンド8で `stop_kind: claude-limit` を加え、この再投入も通すようにした＝下記11〜13。この項は是正ラウンド4の時点の記述である。）
  - 実 dispatch の完走は未実測で、単体テストで確かめたのは継続検査と dispatch parser までである。
- 影響範囲：コードは `issue_start/author_continuation.py` と新規の `issue_start/executor_limit_receipt.py`。文書は `.ai/skills/issue-pipeline/SKILL.md`「作者間のbranch継承」「Codex 実行者が上限で止まったときの切替」、`.claude/skills/issue-pipeline/SKILL.md`、`.ai/troubleshooting/issue-pipeline.md`、`docs/tools/issue-start-and-branch-source.md`、3 role の共通契約と wrapper。A を覆す場合は、判別子の置き場に合わせてこれらと `executor_limit_receipt.py` を書き換える。
- 再 dispatch の入力：引き継ぎ commit で remote の OID が進むので、主文脈は `dispatch_target` と `expected_oid` をその OID で作り、引き継ぎ commit が変えた path を `binding.expected.source_changes` に加える（`codex_worktree_exec/source_snapshot.py` が承認外の path を拒否するため）。`handoff_path` は新しく採番する。`context_id` も新しい dispatch のものにするが、コードは再利用を検査しない（規律）。

#### 7. test-writer の完了 receipt の様式（new-17）

- 論点：記録先は完了 receipt に決まったが、receipt のファイル名・形式・必須欄がどこにも無く、TestDesign の `status`／`stop_reason` と取り違えやすい。
- 暫定決定：`.ai/agents/test-writer.md`「出力とハンドオフ」に YAML の様式を置く。`status` は `done|stop` とし、TestDesign の `ready|stop` と値の語彙を分ける。欄は `schema_version`・`agent`・`status`・`issue`・`branch`・`work_unit`・`test_design`・`test_design_digest`・`commits`・`stop_kind`・`stop_reason`。
- 理由：receipt は「artifact path/digest の短い参照」（共通本文）なので、TestDesign 本体を転載しない最小の欄にした。`done` にしたのは、TestDesign の `ready` と同じ語だと、どちらの欄を読んでいるかを値から見分けられないためである。
- 影響範囲：receipt の欄を機械で読むのは継続検査の3欄だけで、他の欄は機械検査されない。`ready` に揃える場合は様式の1行だけを直す。

#### 8. 上限による STOP と「STOP はオーナーへ打ち上げる」の一般則（new-18）

- 論点：暫定決定 1a は共通本文の2か所に例外を足したが、troubleshooting の「`status: stop` の handoff はオーナーへ報告する」と、共通本文 ②-a の「STOP は主文脈が受けてオーナーへ打ち上げる」は例外の無い文のまま残り、test-writer・issue-investigator・adviser の STOP には例外の規定が無かった。
- 暫定決定：共通本文「Codex 実行者が上限で止まったときの切替」に、上限による STOP が打ち上げ規定の例外であること、対象（書込3 role の `stop_kind: codex-limit` と、read-only 2 role の入口出力の逐語）、報告は事実の通知で判断待ちではないことを1か所で書き、troubleshooting と ②-a の一般則の文からそこを指す。暫定決定 1a の2か所は残す。
- 影響範囲：暫定決定 1a の「影響範囲：2か所」は、この決定で一般則の文2か所と切替の節の1項が加わった。

#### 9. round の「単調増加」と切替の再 dispatch（new-19）

- 論点：`.ai/agents/issue-fixer.md` は round を「単調増加」とし、共通本文は切替の再 dispatch を同じ round で行うとしていた。new-16 で test-writer・issue-implementer の切替も実際に通るようになるので、`creation-stage-contract.md` の「roundは単調増加」も同じ問題を持つ。
- 暫定決定：「単調増加」を「レビューを挟むごとに進め、前の値より小さくしない」に書き換え、切替の再 dispatch はレビューを挟まないので同じ値を使う、と両方の共通契約に書く。共通本文の round の項は書込3 role に広げた。
- 理由：機械は round が 1 以上の整数であることしか検査しない（`issue_start/gate_markers.py`）。同じ値を許す読み方を明記すれば、2文が同じ値を指しても矛盾しない。
- 影響範囲：`.ai/agents/issue-fixer.md` の入力の1行、`.ai/agents/creation-stage-contract.md` の1文、共通本文と `.claude` 側 SKILL の round の項。

### 是正ラウンド6の暫定決定（AI の推奨。覆る場合の影響範囲を併記）

#### 10. receipt の行の分け方と空の `stop_reason`（new-22）

- 論点：`str.splitlines()` は `\x0b`・`\x0c`・`\x1c`〜`\x1e`・`\x85`・U+2028・U+2029 でも行を分ける。このため、字下げした逐語の中に `stop_kind: codex-limit` を置くと top-level の行として通っていた（再レビュー r4 の実測）。中身の無い `stop_reason: |` も通っていた。
- 選択肢：
  - A：`\n` だけで分ける（`\r\n` は正規化）。逐語の中のこれらの文字は字下げした行の内容として扱い、判定に入れない。
  - B：これらの文字を1つでも含む receipt を拒否する。
- 暫定決定：A。あわせて、`stop_reason` の直後に空白以外を含む字下げ行が無ければ拒否する。
- 理由：
  - 守りたいのは「逐語の中身が top-level の判定に入らない」ことで、A でそれが満たされる。
  - B は、上限の逐語（Codex の出力）に制御文字が混じるだけで、正しい切替の STOP まで拒否する。再レビューの harm_detail は、こうした誤った拒否も害に挙げている。
- YAML の読み方との差（是正ラウンド7で実測して書き直した・new-25）：
  - YAML 1.2 の行区切りは LF・CR・CRLF である。A は単独の `\r` で行を分けず、字下げ行の内容として扱う。このため `stop_reason: |\n  a\rstatus: ready\n` を gate は受理し、YAML として読むと top-level に `status` が増える。PyYAML 6.0.1 で読むと、`status` が `ready` に上書きされた（実測）。
  - PyYAML は YAML 1.1 の実装で、単独の `\r` に加えて `\x85`・U+2028・U+2029 でも行を分ける（実測）。`\x0b`・`\x0c`・`\x1c`〜`\x1e` を含む文書は ReaderError になる（実測）。
  - gate の受理が広がるわけではない。gate は自分の読み方で、top-level に `status: stop` と `stop_kind: codex-limit` を要求する。単独の `\r` で逐語から差し込んでも拒否される（実測）。差が出るのは、receipt を YAML として読む側が gate と違う値を見る場合に限る。本ラウンドの grep（`issue_start/subagent_hooks.py`・`gitgate/worktree_collect_handoff.py` など）では、receipt の `status` を YAML として読む機械側の箇所は見つからなかった（網羅はしていない）。主文脈が receipt を YAML として読んで判断するときは、この差を前提にする。
- 細目：
  - top-level の値は空白とタブだけを除く。`str.strip()` は `\x0c` なども除くので、`status: stop\x85` のような行も通してしまう。
  - 中身の有無は `str.strip()` で見る。空として扱うのは、`str.isspace()` に当たる文字（空白・タブ・`\x0b`・`\x0c`・`\x1c`〜`\x1f`・`\x85`・NBSP・U+3000・U+2028・U+2029 など）だけでできた行に限る。それ以外の制御文字（NUL・ESC・DEL・`\x85` 以外の C1 など、C0／C1 の 55 種）、ゼロ幅文字（U+200B・U+FEFF・U+200D・U+2060・U+00AD）、U+3164 だけの行は、中身として数えて受理する（是正ラウンド7で実測）。この検査は「逐語が残っていること」を確かめる補助にとどまる。逐語が壊れて見えない文字だけが残った receipt も通るので、主文脈が逐語を確かめる規律（「既知の限界」）と併用する。
  - タブで始まる行は block の中身に数えない。YAML では字下げに空白しか使えない。
  - 範囲は、次の「空でなく空白で始まらない行」の手前までとする。後ろに続く別の欄の block だけに中身がある場合は拒否する。
- 固定したテスト（`tests/unit/test_author_continuation_limit_switch.py`）：
  - 8文字それぞれによる注入の拒否。
  - 空 block の6形の拒否：EOF、直後に別の欄、空白だけの行、別の欄の block だけに中身、タブ始まり、空白扱いの制御文字（`\x0c`）だけ。
  - top-level の値の前後に空白とタブ以外の空白類（`\x0b`・`\x0c`・`\x1c`〜`\x1f`・`\x85`・U+2028・U+2029・NBSP・U+3000）がある行の拒否。対象は `status`・`stop_kind`・`stop_reason` の3欄（是正ラウンド7・new-26）。値を `str.strip()` で除く実装に戻すと Red になる。
  - 受理：`|-`、CRLF、先頭の空行、逐語の中の8文字。
- 範囲外として残したもの：コロンの後に空白の無い行（`status:stop`）と、`---` 以降の2つ目の文書は、引き続き受理される。どちらも書き手の様式から生じない形で、再レビューも指摘にしていない。
- 影響範囲：`issue_start/executor_limit_receipt.py`、同テスト、`docs/tools/issue-start-and-branch-source.md` の通過条件の文、本節の「読み方」。B に替える場合は、`_block_has_content` はそのままにして、分割の前に文字の検査を足し、受理テストの最後のケースを拒否側へ移す。

### オーナー決定（2026-11-17・是正ラウンド8）

再レビュー r4 の new-24（Claude の role 自身が上限で止まったとき、rules 03 の「同じ構成でそのまま再投入する」が継続検査に拒否される）について、次の決定が出た。決定は依頼文に結論だけ記録されており、逐語はリポジトリ内に無い。

1. `stop_kind: claude-limit` を足し、Claude の role 自身の上限による同じ role の再 dispatch を継続検査が通すようにする。
2. この PR の規範・文書には、止まったエージェントを別の経路で再開する手順を書かない（再 dispatch だけを手順とする）。
3. new-20・new-21 の処置方針は未決のまま触らない。

### 是正ラウンド8の暫定決定（AI の推奨。覆る場合の影響範囲を併記）

#### 11. `claude-limit` を通す role の範囲

- 論点：依頼は「`PREDECESSORS` の対象の4ロール（ac-designer・change-planner・test-writer・issue-implementer）」としていた。どこまでを通すか。
- コードの事実（head 09ec7b1c で読んだ範囲）：
  - `validate_author_continuation` は `ack.agent_type not in PREDECESSORS` のとき何も検査せずに返る。`PREDECESSORS` のキーは change-planner・test-writer・issue-implementer の3つで、ac-designer は値（change-planner の直前 role）としてだけ現れる。
  - ac-designer は manifest（`issue_start/managed-entrypoints-v2.json`）の managed 区分で、`issue_start/gate_dispatch.py` が `validate_phase_target(..., initial=True)`（base から新しい branch を作る初回著作）で検査する。継続検査は呼ばれない。
  - issue-fixer は isolation_only 区分だが `PREDECESSORS` に無いので、元から継続検査の対象外である。
- 選択肢：
  - A：`PREDECESSORS` のキー3つ（change-planner・test-writer・issue-implementer）すべてに `claude-limit` を通す。
  - B：A から change-planner を除く（Codex 既定の2 role だけ）。
  - C：ac-designer の再 dispatch も継続検査に載せる。
- 暫定決定：A。
- 理由：
  - Claude の role 自身の上限は、Claude 固定の change-planner でも、Codex 既定 role の Claude 側（dispatch された Claude サブエージェント自身）でも起きる。rules 03 の「同じ構成で再投入する」は role を限定していないので、継続検査が扱う role はすべて通す必要がある。B は change-planner について new-24 と同じ食い違いを残す。
  - C は ac-designer の検査経路（初回著作の managed 区分）を変える変更で、最小ではない。ac-designer の再 dispatch は元から継続検査に拒否されていないので、new-24 の食い違いは ac-designer には無い。
- `codex-limit` は従来どおり test-writer・issue-implementer（`SWITCH_ROLES`）だけに通し、change-planner の `codex-limit` は拒否する（Claude 固定の role に Codex 実行者は無いので、取り違えの receipt である）。
- 既知の限界：ac-designer が上限で止まった後の再 dispatch（初回著作の経路）が、止まる前に push 済みの branch がある状態で完走するかは確かめていない（継続検査の外の論点で、本ラウンドでは変えていない）。
- 影響範囲：`issue_start/author_continuation.py`（同じ role の判定から `SWITCH_ROLES` を外し、receipt の種別と role の組み合わせを `issue_start/executor_limit_receipt.py` の `require_limit_stop` で確かめる）。B へ覆す場合は `require_limit_stop` で `claude-limit` の role も `SWITCH_ROLES` に限る。

#### 12. Agent が上限で落ちて receipt が書かれなかったときの記録の作り方

- 論点：Claude の role 自身が上限で止まると、role は handoff を書けない（モデルの呼び出しそのものが失敗する）。主文脈が `worktree-release --force-uncollected` で解放すると `collected_to` が空になり、継続検査は「collected receipt path invalid」で拒否する。どう記録するか。
- コードの事実：
  - `gitgate collect-worktree`（`gitgate/worktree_collect_handoff.py`）は、台帳 entry の `handoff_path`（または `--handoff`）が指す、止まった role の作業ツリーの中のファイルを読み、`tmp/_handoff/collected/<entry-id>--<basename>` へ写して sha256 を照合し、entry を `collected` にして解放する。内容は解釈しない。対象は `stopped`・`stale` の entry で、`running`・`open` は拒否する（`gitgate/worktree_collect_target.py`）。
  - 解放は `git worktree remove --force` で、作業ツリーの未 commit 変更は消える（`gitgate/worktree_release_safety.py`）。
  - 継続検査は、回収 receipt の bytes を台帳 entry と marker の sha256 で束縛するだけで、誰が書いたかは見ない。
- 選択肢：
  - A：主文脈が、止まった role の作業ツリーの `handoff_path` に receipt を新しく書き（`status: stop`・`stop_kind: claude-limit`・Agent の結果に出た上限の逐語を入れた `stop_reason`）、既存の `collect-worktree` で回収・解放する。gitgate は変えない。
  - B：gitgate に、主文脈が書いた receipt を直接 `collected/` へ置いて束縛する verb を足す。
  - C：継続検査で、`collected_to` が空の entry を `claude-limit` 相当として通す。
- 暫定決定：A。
- 理由：
  - A は既存の collect・release の経路だけで実現でき、コードを変えない。B は gitgate の変更で最小ではない。C は「回収済みの bytes で止まった理由を確かめる」という継続検査の前提を外し、fail-close を弱める。
  - 既存の規律「主文脈は回収 receipt に欄を書き足さない」との関係：この規律が防ぐのは、role が書いた receipt に主文脈が `stop_kind` を足して、引き継げなかった STOP を通すことである。A では role が receipt を書けていないので、書き足す対象が無い。上限の証拠（Agent の結果の逐語）を受け取ったのも主文脈だけなので、記録を書く主体は主文脈になる。両者を両立させるため、主文脈が receipt を書くのは「role の handoff がその位置に無いとき」に限り、role の handoff があるときは書き足さず打ち上げる、と規律で分ける。
  - 主文脈が receipt を書くのは記録であって、委譲すべき作業の代行（rules 03 の禁止③）ではない。
- 条件（いずれかを満たさなければ書かずにオーナーへ打ち上げる）：
  - Agent の結果に上限（レート制限・セッション上限）を示す逐語がある。逐語の無い失敗は Codex 実行者の場合と同じく証拠にならない。
  - 止まった作業ツリーに未 commit の変更が無く、HEAD が remote の branch の OID と一致する（未 push の commit が無い）。解放が `--force` で変更を消すので、回収の前に確かめる。主文脈は commit・push を代行しない。
  - 止まった role の handoff が `handoff_path` に無い。
  - entry が `stopped` か `stale` である（`running` のままなら既存の troubleshooting の手順に従い、推測で回収しない）。
- 既知の限界：`claude-limit` の receipt は主文脈の記録であり、上限で止まったことそのものを機械は確かめない（`codex-limit` の「role 自身の申告」と同じ種類の限界）。主文脈が条件を確かめずに書いても機械は止めない。主文脈が止まった role の作業ツリーへ書けることと、この経路の実 dispatch の完走は未実測である。
- 影響範囲：`.ai/skills/issue-pipeline/SKILL.md`「Claude の role 自身が上限で止まったときの再投入」、`.claude/skills/issue-pipeline/SKILL.md`、`.ai/troubleshooting/issue-pipeline.md`、`docs/tools/issue-start-and-branch-source.md`。B へ覆す場合は gitgate の verb を足し、これらの手順をその verb に書き換える。

#### 13. `stop_kind` の2値の意味と、引き継ぎ commit の扱い

- 論点：`codex-limit` は「上限で止まり、切替へ進める STOP」で、引き継ぎ commit を済ませたか未 commit の変更が無かったときだけ書く。`claude-limit` はどう定義し、`Handover:`／`Tests:` の固定行をどう扱うか。
- 暫定決定：
  - `codex-limit`：委譲先の Codex 実行者が上限で止まり、role が引き継げた STOP。書くのは role。同じ role を Codex 実行者の指定なしで再 dispatch する（切替）。
  - `claude-limit`：Claude の role 自身が上限で止まり、作業ツリーに引き継ぐべき変更が無い STOP。書くのは主文脈（上の12）。同じ role を止まる前と同じ構成（Codex 実行者の指定の有無を含む）で再 dispatch する。
  - 両者に共通するのは「同じ role の再 dispatch へ進めてよい STOP」という意味で、`status: stop`・block scalar の `stop_reason` の要求と、逐語を `stop_reason` に置くことは同じ。
  - `claude-limit` には引き継ぎ commit が無い。role は止まった時点で commit できず、主文脈は代行しない。したがって `Handover:`／`Tests:` の固定行は使わない。作業ツリーに変更が残っていれば `claude-limit` を書かずにオーナーへ打ち上げる（`codex-limit` で「引き継げなかった STOP には書かない」としたのと同じ考え方）。role が止まる前に自分で commit・push した変更は、通常の commit として remote の OID に含まれ、再 dispatch はその OID から続ける。
- 理由：書く主体と「引き継げた／引き継ぐものが無い」の条件を2値で分けると、主文脈が receipt を読んで次の手（切替か同じ構成か）を一意に決められる。1値（`limit`）にまとめると、どちらの構成で再 dispatch するかを receipt から読めない。
- 既知の限界：台帳 entry には実行者（Codex か Claude か）の欄が無いので、継続検査が確かめられる取り違えは「Claude 固定の role の `codex-limit`」だけである。Codex 既定 role の `claude-limit` と `codex-limit` の取り違えは機械では見分けられず、主文脈が逐語を確かめる規律と併用する。
- 固定したテスト（`tests/unit/test_author_continuation_claude_limit.py`）：
  - 受理：3 role の `claude-limit`、change-planner の dispatch parser 層。
  - 拒否：change-planner の `codex-limit`、別 role（issue-implementer→test-writer、issue-fixer→issue-implementer、test-writer→change-planner）、未回収・未解放（`running`・`stopped`・`stale`・`collected`・`abandoned`、`closed_at` 無し、`collected_to` 無し・空）、`stop_kind` 無し、`status: ready`、`stop_kind` の重複（2値の組み合わせ両順）、逐語の中だけの `stop_kind`、block でない `stop_reason`、空の block、`stop_reason` 無し、値違い（`claude_limit`・`Claude-limit`・`limit`・2値の連結・引用符付き）、receipt の改変、remote OID の不一致。
  - 既存の `tests/unit/test_author_continuation_limit_switch.py` と `tests/unit/test_author_continuation.py` は変えずに全パスする。
- 影響範囲：`issue_start/executor_limit_receipt.py`（`require_executor_limit_stop` を、種別を返す `read_limit_stop_kind` と role との組み合わせを見る `require_limit_stop` に分けた。読み方は変えていない）、rules 03・`governance-directives.md` 項10、共通本文、各 role の共通契約の `stop_kind` の行。2値を1値にまとめる場合は、再 dispatch の構成を receipt 以外（切替の記録）から読む規律に書き換える。
