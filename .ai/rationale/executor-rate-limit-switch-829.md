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
- 通す範囲：
  - 同じ role を通すのは `test-writer` と `issue-implementer` だけ（`SWITCH_ROLES`）。change-planner は Claude 固定なので、同じ role の再 dispatch は従来どおり拒否する。issue-fixer は元から継続検査の対象外である。
  - 同じ Issue・branch の最新 owner であること、`released` と `closed_at`、`collected_to` の位置、receipt の sha256、remote exact OID の照合は、通常の継続と同じくすべて要求する。
  - 既存の `tests/unit/test_author_continuation.py` は変えずに全パスする。新しい許可条件は `tests/unit/test_author_continuation_limit_switch.py` で、通る場合（2 role・dispatch parser 層）と拒否される場合（Claude 固定 role、別 role、未回収・未解放、`stop_kind` 無し、`status` が stop でない、値違い、重複、字下げ内だけ、block scalar でない、`stop_reason` 無し、非 UTF-8、receipt 改変、より新しい owner）を固定した。
- 既知の限界：
  - `stop_kind` は role 自身の申告であり、上限で止まったことそのものを機械は確かめない。主文脈が逐語を確かめてから再 dispatch する規律と併用する。
  - Claude の role 自身が上限で止まったときの「同じ構成での再投入」は、同じ role の再 dispatch でも `stop_kind` を書かないので、従来どおり継続検査に拒否される。この PR では変えていない。
  - 実 dispatch の完走は未実測で、単体テストで確かめたのは継続検査と dispatch parser までである。
- 影響範囲：コードは `issue_start/author_continuation.py` と新規の `issue_start/executor_limit_receipt.py`。文書は `.ai/skills/issue-pipeline/SKILL.md`「作者間のbranch継承」「Codex 実行者が上限で止まったときの切替」、`.claude/skills/issue-pipeline/SKILL.md`、`.ai/troubleshooting/issue-pipeline.md`、`docs/tools/issue-start-and-branch-source.md`、3 role の共通契約と wrapper。A を覆す場合は、判別子の置き場に合わせてこれらと `executor_limit_receipt.py` を書き換える。
- 再 dispatch の入力：引き継ぎ commit で remote の OID が進むので、主文脈は `dispatch_target` と `expected_oid` をその OID で作り、引き継ぎ commit が変えた path を `binding.expected.source_changes` に加える（`codex_worktree_exec/source_snapshot.py` が承認外の path を拒否するため）。`context_id` と `handoff_path` は新しく採番する。

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
