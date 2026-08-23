**深刻度**: ERROR

**対応 Issue**: #338（`hiratashinnya/review-system`。PR #335 のレビュー中に `pr-reviewer`(AI) が発見し、オーナー指示で追跡）

**指摘**: `dsv2-lookup` エージェントの共通本文（`.ai/agents/dsv2-lookup.md`）「## 手順」節の 2 番目の手順が、候補ノードを絞り込む方法として `python3 -c "import json; ..."` を本文と唯一の worked example の双方で指示していた。この形は本リポジトリ自身の 2 系統の統制により **agent_type を問わず常に deny される**ため、`dsv2-lookup` は自分の中核手順を書かれたとおりに実行できない。

## 観測事実

### 1. 指摘対象の記述（PR #335 レビュー時点の `.ai/agents/dsv2-lookup.md`「## 手順」2）

```
2. **候補特定**：meta.json を `grep`（`title`/`id`/`labels` の文字列一致）や
   `python3 -c "import json; ..."` でフィルタし、関連ノードの `id`・`body_path` を絞り込む。
   - 例：`python3 -c "import json,sys; m=json.load(open('doc-system-v2/meta.json')); [print(n['id'], n['type'], n['status'], n['body_path']) for n in m['nodes'] if 'ドリフト' in n['title']]"`
   - 型で絞るなら `n['type']`（例 `FND`/`SPEC`/`FR`）、状態（open/resolved 等）で絞るなら `n['status']`。
```

`.claude/agents/dsv2-lookup.md` は本ファイルを参照する薄いラッパーであり、ラッパー側に該当記述は無い（＝欠陥は共通本文 1 か所に閉じる）。

### 2. deny する統制 ①：Claude Code 自身の権限機構

`.claude/settings.json` の `permissions.deny` にプレフィックスマッチのエントリが実在する（L159–160）：

```
"Bash(python3 -c *)",
"Bash(python -c *)",
```

### 3. deny する統制 ②：`agent-command-gate.sh` の全 agent_type 共通の危険コマンド層

`.claude/hooks/agent-command-gate.sh` の `segment_dangerous_command_token()`（L628）が、1 セグメント内に `-c` トークンとインタプリタ名トークンが**共存**すれば deny する（L650–655）：

```python
has_c = "-c" in segment_tokens
...
if has_c:
    for name in basenames:
        if name in SHELL_INTERPRETERS or name in PYTHON_HEAD_COMMANDS:
            return f"{name} -c"
```

`PYTHON_HEAD_COMMANDS = {"python", "python3"}`（L283）。この判定は `all_role_dangerous_command_token()`（L673）から呼ばれる**全 agent_type 共通層**であり、gated ロール（`issue-implementer`/`issue-fixer`/`pr-reviewer`）専用の層1〜3 とは別系統である。したがって `dsv2-lookup` 自身も対象になる。basename 正規化・非先頭トークン走査を行うため、`/usr/bin/python3 -c` や `timeout python3 -c` のような回避形も同様に deny される。

なお同層は `python3 -m <module>` を意図的に allow する（`-c` トークンを持たないため・L649 のコメントにオーナー確定として明記）。よって `dsv2-lookup` の手順 1・手順 4 が使う `python3 -m dsv2 index|deps|dependents` は影響を受けない。**壊れているのは手順 2 の `python3 -c` 形だけ**である。

### 4. 統制が CI で担保されていること

`tests/unit/test_agent_command_gate.py` の `UNIVERSAL_DANGEROUS_COMMANDS`（L222）に `"python3 -c 'x'"`・`"python -c 'x'"` が含まれ（L231–232）、全 agent_type に対して deny されることが Bash 経路（L344–349）と ctx 経路（`ctx_execute` L1248・`ctx_batch_execute` L1254）の双方で検証されている。すなわち本件は「たまたま現在 deny されている」のではなく、**deny され続けることがテストで固定されている**。

### 5. 検出経路が存在しないこと

エージェント本文中のコマンド文字列が統制と矛盾していないかを検査する機械検査は存在しない。`asset_parity` は 4 ツリー間の presence/absence のみを見る read-only ツールであり、本文の内容は見ない。`doc-system-v2/validate.py` はノードのスキーマ・path・辺を検査するもので、out-of-graph の agent 本文は対象外である。したがって人手のレビューでしか気づけない（現に PR #335 のレビューで初めて発見された）。

## 実害

1. **`dsv2-lookup` の中核手順が書かれたとおりには実行できない**。手順 2「候補特定」は meta.json から関連ノードを絞り込む段であり、本エージェントの存在理由（コンテキスト圧縮）そのものを担う。そこで提示される唯一の worked example が確実に deny される。
2. **失敗が確定的かつ反復的である**。「実行環境によっては失敗しうる」ではなく、`permissions.deny` と危険コマンド層の 2 系統が独立に、全 agent_type に対し、毎回 deny する。本文は毎回の呼び出しでエージェントに注入されるため、例に従うたびに同じ deny を踏む。
3. **deny 後の挙動が規定されていない**。同じ手順 2 は `grep` も併記しているため復帰の余地はあるが、本文はそれを「`python3 -c` が使えない場合の代替」として位置づけておらず、deny された `dsv2-lookup` が何をすべきかを定めていない。復帰は個々の LLM の即興に委ねられ、再現性が無い。
4. **リポジトリ自身の統制と正面から矛盾する指示を、統制対象のエージェント本文が保持していた**。統制の目的は任意コード実行の遮断であり、その統制下で動くエージェントの手順書が禁止形を規範例として提示している状態は、資産と統制のどちらが正かを読み手が判断できなくする。

## 深刻度の根拠

**ERROR** と判定する。

- **INFO にしない理由**：被覆・均一性のギャップ（検出が落ちる経路を持つだけで誤った成果物は出ない類型）ではない。指示に従えば必ず失敗する。
- **WARNING にしない理由 — 既存 WARNING 類型との差**：`fnd-深刻度の語彙が-05-verification.md・v2-テンプレート・実コーパスで三者不一致` が WARNING とされた根拠は「実現済みの実害はゼロ（124/124 が適合語彙で書かれており誤った成果物は 1 件も無い）」であった。本件は該当しない——欠陥が置かれているのは人間が随時読む out-of-graph の**テンプレート**ではなく、呼び出しのたびに機械（LLM）へ注入される**運用手順そのもの**であり、しかも当該手順の唯一の worked example が対象である。LLM は worked example を最も忠実に模倣するため、「誤った経路を選んだ場合にのみ失敗する」条件付きの欠陥ではなく、無条件の失敗である。
- **既存 ERROR 類型との整合**：`orc-検査パイプライン実行-が実在しない-cli-python-m-spec_inspector-を本文で参照している` は「本文が実行不能コマンドを提示している」ことのみ（同 FND の実害 1）では ERROR の根拠にせず、SRC との凍結矛盾（実害 2）を根拠に ERROR とした。本 FND はその先例を尊重し、**実害 1 相当だけを根拠にしていない**。ERROR の根拠は上記実害 2・3 の組（機械へ毎回注入される手順であること・確定的反復であること・deny 後の復帰が未規定であること）であり、ORC ノード（人間が随時読む設計記述で、読み手が実コマンドへ適応できる）とは消費者と反復性が異なる。
- **「機械検査が無いこと」は深刻度を下げる根拠にしない**（オーナー指示・2026-07-26）。上記観測事実 5 は検出経路の欠如を記録したものであって、深刻度の減算材料ではない。
- **オーナーが引き下げを判断する場合の材料**：同じ手順 2 が `grep` を先に併記しており価値経路は遮断まで至らない（degrade に留まる）と評価するなら WARNING が代替の判定となる。本 FND では上記理由で ERROR を採るが、この一点が判断の分岐であることを明示しておく。

## 指摘時 ref_version（DD-3）

**付与先なし（対象は in-graph ノードを持たない agent 資産のため）**。

- `doc-system-v2/nodes/05-design/prompt/` 配下の PROMPT ノード全 22 件を走査した結果、`.claude/agents/dsv2-lookup.md`／`.ai/agents/dsv2-lookup.md` を担体として参照するノード、および `dsv2-lookup` に言及するノードは存在しない（2026-08-23実測：`grep -rlF "dsv2-lookup" doc-system-v2/` はコーパス全体で0件。`00-dashboard.md` のissue #76行／resolved FND「著作テンプレートとプロンプトが識別子単位ノード・型別本文ポリシーに未追随」の2箇所はいずれも issue #173 でのリネーム前の旧名 `docidx-lookup` への言及であり、現行名 `dsv2-lookup` の言及ではない）。
- `carrier: "agent"` を持つ唯一の PROMPT ノードは `doc-system-config-operator-doc-system-config-操作エージェントプロンプト`（Codex custom agent・issue #140）であり、`dsv2-lookup` ではない。
- したがって forward 辺（`edges[].to`）を張れず、記録すべき `edges[].ref_version` も存在しない。解消時（`dsv2 reverse`）に backref を付与する先も無い。
- **`fnd_lifecycle.unresolved.must_link_to`（`config.yml`・`target: any`・severity error）との関係**：本ノードは open だが forward 辺を持たない。同ルールの `activate_stage` は `verification` であり現在の `current_stage` は `design` のため未発火であること、および `doc-system-v2/validate.py` は `fnd_lifecycle` ブロックを読み込む処理を持たない（同ファイルが施行するのは `exact_link_counts`／`must_link_to`／`must_be_linked_from` の 3 ブロックのみ）ことを確認済み。**辺の欠落は著作漏れではなく、張り先が実在しないことによる**。下記「選択肢」①を採れば張り先が生まれ、この状態は解消する。

## 本 FND のスコープ（1 アサーション）

「`.ai/agents/dsv2-lookup.md`「## 手順」2 が、リポジトリの統制により全 agent_type で常に deny される `python3 -c` 形を、本文および唯一の worked example として指示している」という単一命題に閉じる。

- **`.ai/agents/dsv2-lookup.md` 本文の是正作業自体は本 FND では行わない**（呼び出し元＝主文脈が直接 Edit する分業。Issue #338）。本 FND は指摘の記録と選択肢の提示に限る。
- 既存 open FND `fnd-深刻度の語彙が-05-verification.md・v2-テンプレート・実コーパスで三者不一致` とは対象・命題ともに無関係であり、統合も参照もしない。
- 統制側（`.claude/settings.json`・`agent-command-gate.sh`）の妥当性は論じない。両者は「どちらのシステムにも含有されない汎用開発ハーネス」区分であり、仮に統制側を変える論点が生じても起票先は Issue になる（`.claude/rules/02-decision-process.md`「起票先はプロジェクト区分で決める」）。本 FND は**含有されるハーネス側の資産**（`dsv2-lookup`）の本文に閉じた指摘である。

## 隣接観測（本 FND のアサーション対象外）

**同型の欠陥が `.ai/agents/doc-system-v2-authoring.md` にも存在する。** 同ファイル「## id / slug 採番」節が、slug の算出方法として次を指示している（L20–22）：

```bash
python3 -c "import sys; sys.path.insert(0,'doc-system-v2'); from slugify import slugify; print(slugify('ここにタイトル'))"
```

これは全 `*-author` エージェントが読む共通契約であり、しかも「slug は唯一実装 `doc-system-v2/slugify.py` を再利用して算出する（独自に正規化しない）」という規範の**唯一の実行手段**として提示されている。本 FND と統制・deny 経路は同一だが、**もの（資産ファイル）が異なり、影響範囲（`*-author` 7 ロール）と、代替手段の有無（こちらは `grep` のような併記された代替が無い）も異なる**。PR1「もの＋発生源で分ける」に従い本 FND には統合せず、ここに記録する。**処置要否・起票要否は呼び出し元／オーナーの判断事項**であり、本 FND では結論を出さない（「対応不要」を AI が独断で書かない）。

**`dsv2-lookup` に対応する PROMPT ノードが存在しない。** 上記「指摘時 ref_version」で確認したとおり、`dsv2-lookup` は `.claude/rules/02-decision-process.md` が「doc_system / review_system に含有されるハーネス」として明示列挙するロールでありながら、in-graph の担体を持たない（`prompt_coverage_targets` にも `dsv2-lookup` は無い）。そのため本件のように `dsv2-lookup` 本文へ指摘を起票しても forward 辺を張れず、解消時の backref も付与できない。これは本 FND のアサーションとは別命題であるが、本 FND の辺の欠落を直接もたらしている事実であるため記録する（処置は下記選択肢①）。

## 選択肢

**① `dsv2-lookup` の PROMPT ノードを在グラフ化した上で、本文の `python3 -c` 例を `grep` ベースへ差し替える。**

- `doc-system-v2/nodes/05-design/prompt/` に `carrier: "agent"` の PROMPT ノードを新設（`design-author` へ委譲）し、本 FND の forward 辺をそこへ張る。並行して `.ai/agents/dsv2-lookup.md` の手順 2 を、統制下で実行可能な `grep -A N` ベースの例へ書き換え、`python3 -c` を使わない旨と理由（deny される事実）を明記する。
- 利点：実害 1〜4 がすべて解消する。加えて `dsv2-lookup` が in-graph の担体を得るため、以後この資産に対する指摘が正規の辺を持てるようになり、`dsv2 reverse` による解消も機械実行できる（本 FND の辺の欠落＝隣接観測 2 も同時に解消）。`carrier` を持つ PROMPT ノード 15 件の既存モデルにそのまま乗る。
- 欠点：作業面積が最大。PROMPT ノードの新設は `design-author` への別委譲を要し、4 ツリー（`.claude`/`.github`/`.codex`/`.agents`）の資産整合（`asset_parity`）も併せて確認する必要がある。

**② 本文の `python3 -c` 例のみを `grep` ベースへ差し替える（PROMPT ノードは新設しない）。**

- `.ai/agents/dsv2-lookup.md` の手順 2 を書き換えるに留める。本 FND は forward 辺を持たないまま（「付与先なし」）運用する。
- 利点：実害 1〜4 は解消し、変更が 1 ファイルに閉じる。呼び出し元が既に予定している分業（主文脈が直接 Edit）とそのまま噛み合う。
- 欠点：`dsv2-lookup` は in-graph の担体を持たないままなので、`fnd_lifecycle` が `verification` ステージで発火した時点で本ノードが辺欠落として検出される（現在は未発火）。同資産への次の指摘でも同じ問題が再発する。

**③ 統制側に例外を設けて `python3 -c` を `dsv2-lookup` にだけ許可する。**

- `agent-command-gate.sh` の危険コマンド層に agent_type 例外を追加し、`.claude/settings.json` の `permissions.deny` からも外す。
- 利点：本文を変えずに済む。
- 欠点：**採らない**。全 agent_type 共通の任意コード実行遮断に穴を開ける変更であり、`.claude/rules/05-skills-agents.md`「静的検査で安全に扱えない（複数のサブプロセス起動 API・文字列結合・eval でトークン一致を自明に回避できる）ため、コードではなく言語そのものを allowlist で絞る」という確定方針と正面から衝突する。`tests/unit/test_agent_command_gate.py` の `UNIVERSAL_DANGEROUS_COMMANDS` も全 agent_type での deny を固定しており、その担保を崩す。統制を弱める側に倒す根拠が本件には存在しない（本件で失われている価値は「meta.json の絞り込み手段」であって、`grep` と `ctx_batch_execute` という代替が同じ手順内に既にある）。

**④ 現状維持＋注記のみ**（「`python3 -c` は環境によっては使えない」と注を足す）。

- 欠点：**推奨しない**。「環境によっては」は事実に反する（常に deny される）。実害 1〜3 は解消せず、誤った条件付き表現を新たに導入する分だけ状態が悪化する。

## 推奨

**② を即時実施し、① への格上げをオーナー判断に委ねる。**

根拠：

1. **②で実害はすべて止まる**。本件の欠陥は 1 ファイルの手順 2 に閉じており、同じ手順内に統制下で実行可能な代替（`grep`／`ctx_batch_execute`）が既に併記されている。書き換えは既存の記述を実行可能な側へ寄せるだけで、新たな設計判断を要さない。
2. **①の追加分（PROMPT ノード新設）は本 FND の実害ではなく構造の不足に対する処置**であり、性質が異なる。`dsv2-lookup` を在グラフ化するか否かは `prompt_coverage_targets` の対象集合をどう定めるかという別の決定に触れるため、本 FND の処置に抱き合わせて AI が確定させるべきではない。ただし①を採れば本ノードの辺欠落も同時に解消するため、オーナーが在グラフ化を選ぶなら同一バッチで実施するのが合理的。
3. **③は統制を弱める方向で、確定済みの方針と衝突する**。④は事実に反する注記を増やすだけで実害が残る。いずれも採らない。
4. **本 FND の解消手続きについて**：②を採る場合、`dsv2 reverse` の backref 付与先が存在しないため、解消時は本文の「付与先なし」記載をもって backref に代える（`.claude/rules/02-decision-process.md`「削除済みノードは FND 本文に「付与先なし」と明記」と同じ扱い。ただし理由は削除ではなく**未著作**である点が異なる）。①を採る場合は新設 PROMPT ノードへ通常どおり辺を張り、`dsv2 reverse` で機械実行できる。

処置要否・実施時期・①/②の別はオーナーが決定する。本 FND では「対応不要」の結論を出さない（PR7・独断禁止）。

## 対応状況

open（`scheduled: "sprint-1"`）。

**起票時点の作業ツリーの状態について**：本 FND の著作と同一バッチで、呼び出し元（主文脈）が Issue #338 の処置として `.ai/agents/dsv2-lookup.md` の手順 2 を既に書き換えている（`python3 -c` 例が `grep -A 20` ベースへ差し替えられ、`**`python3 -c` は使わない**` と deny の理由、および本 FND への参照が追記された状態を実測）。本 FND を `open` のまま起票するのは、**指摘の記録と、`fnd/open/`→`fnd/resolved/` の状態遷移を `dsv2 reverse` の機械実行に委ねる運用**（辺逆転・DD-3 凍結・z バンプ・`git mv` を手編集しない）に従うためであり、処置未着手を意味しない。解消の実行可否は上記「推奨」4 のとおり張り先の有無に依存するため、オーナー／主文脈の判断を要する。

## 接続規則変更の伝播チェック

本 FND の処置は `doc-system-v2/config.yml` の `must_link_to` / `must_be_linked_from` / `must_not_link_to` / `fnd_lifecycle` / `src_symbol_eligibility` のいずれも追加・変更・削除しない（対象は out-of-graph の agent 本文中のコマンド記述である）。したがって接続マトリクス（`docs/doc-system/03-connection-matrix.md`）・ドキュメント一覧（`docs/doc-system/01-document-items.md`）・各 author エージェント／スキルへの接続規則の伝播は**不要**である。

ただし選択肢①を採る場合は、接続規則ではなく **`prompt_coverage_targets` の対象集合**（`doc-system-v2/config.yml`）と 4 ツリー資産の整合（`python3 -m asset_parity check`）を併せて確認する必要がある。これは接続規則変更の伝播チェックとは別系統の確認であり、①の実施時に行う。
