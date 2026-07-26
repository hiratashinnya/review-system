> **改訂理由（v0.1.0 → v0.2.0・MINOR）**: 被覆されない非 Python 担体の対象に **ORC `著作・反映パイプライン実行`** を追加し、指摘スコープを MOD / PRS から **MOD / PRS / ORC** へ拡大した（指摘の命題自体は不変＝「粒度1軸の適格性テーブルが担体の多様性を表現できない」）。**初版 v0.1.0 のスコープ（MOD / PRS）は網羅漏れだった**。原因は、影響対象を `src_symbol_eligibility` の全キー（mod / dm / port / orc / prs / prompt / cfg）に対して網羅確認せず、起票時点で既に把握していた MOD・PRS の事例だけでスコープを確定させたこと。本改訂では残る dm / port / prompt / cfg も併せて確認した（下記「全キーの網羅確認」）。forward 辺（`→ must_be_linked_from`）は変更しない＝欠陥は規則側にあり、影響を受ける設計ノードは本文に列挙する方式を踏襲する。

> **タイトルの是正（v0.2.1 で処置済み）**: v0.2.0 時点のタイトル `src_symbol_eligibility の mod: [module] が非 Python 担体の MOD/PRS を被覆しない` は ORC を含む拡大後スコープを表さず、かつ命題を MOD 起点で記述していた。主文脈が `python3 -m dsv2 rename --apply` で `src_symbol_eligibility-が担体軸を持たず非-python-担体の-mod-prs-orc-を被覆しない` へ改名し、`title` を `src_symbol_eligibility が担体軸を持たず非 Python 担体の MOD/PRS/ORC を被覆しない` へ同期した（referrer 0 件・`git mv` 2 対）。identity 操作のみで指摘内容・辺・深刻度に変更はないため **z バンプ v0.2.0 → v0.2.1**（DD-21 の「provenance/lifecycle 操作は z バンプ」に準ずる）。

**深刻度**: ERROR

**対応 Issue**: #256（必須辺検証ルールの見直し・修正 ④ implementation 段 src 系規則の対称化・担体/粒度適格性）

**指摘（1アサーション）**: `src_symbol_eligibility` はシンボルの粒度1軸（module / class / function / method / file）のみで適格性を定義しており、「全ての設計ノードは Python シンボルで実現される」ことを暗黙の前提としている。この前提が成立しない設計ノード（エージェント定義 Markdown・スキル・ツール呼び出し等の非 Python 担体で実現される MOD / PRS / ORC）は、implementation 段で必須辺 `mod←src` / `prs←src` / `orc←src` を**原理的に充足できない**。

## 観測事実

- 規則本体（`doc-system-v2/config.yml` L113–120）: `src_symbol_eligibility: mod: [module]` / `dm: [class]` / `port: [class]` / `orc: [function]` / `prs: [class, function]` / `prompt: [file]` / `cfg: [file]`。コメント（L109）は source.kind 語彙を `{module, class, function, method, file}` と宣言しており、**いずれも Python シンボル/ファイルの語彙**。
- 判定実装（out-of-graph）: `dsv2/query.py` の `_src_kind_ok()` が `node['source']['kind']` を許容 list と単純照合する。`source` / `kind` を持たないノードは不適格＝False（fail-close）。この照合は `must_link_to_gaps()` / `must_be_linked_from_gaps()` の両方から呼ばれるため、非 Python 担体は **出辺・入辺の双方で有効カウントされない**。
- 前提が成立しない設計ノードの実測:
  - MOD `author`（責務＝P-7-1 著作・tmp 出力）の実体は `.claude/agents/*-author.md`（エージェント定義 Markdown）。Python モジュールではない。
  - MOD `reconciler`（責務＝P-7-2 調停・本ファイル反映）の実体は `.claude/agents/reconciliation.md`。同上。
  - PRS `tmp-草案ファイル書き出し` の実体は著作エージェントの `Write` ツール呼び出し。クラスでも関数でもない。
  - **ORC `著作・反映パイプライン実行`（v0.1.0）**（本改訂で追加）: 記述する P-7-1（著作・tmp 出力）→ P-7-2（調停・本ファイル反映）の実体は **Claude サブエージェント**（`.claude/agents/*-author.md`・`.claude/agents/reconciliation.md`）であり、非 Python 担体。`dsv2/cli.py` のサブコマンドは index / deps / dependents / orphans / drift / prompt-coverage / dashboard / reverse / rename / check-slug / build-view のみで、**著作・反映のオーケストレーションを行う Python 関数は存在しない**（実測）。よって本 ORC は `orc: [function]` を満たす担体を持てず、SRC を著作できない。
  - MOD `filter`（責務＝P-2-5 抑制・発火フィルタ）は issue #118 の suppress 機構廃止により**機構自体が消滅**しており、担体の種別以前に対応実装が存在しない（原因が異なる＝本 FND の範囲外。後述）。
- **ORC が本 FND と同一の命題であることの確認**（別 FND との切り分け）: ORC `著作・反映パイプライン実行` が SRC を持てない原因は、「設計層 MOD/DM/PORT/PRS が宣言する実装担体 `spec_inspector/*` が実在しない」という**担体の不在**の命題ではない。担体（Claude サブエージェント）は実在し稼働しているが、**適格 kind（`function`）が非 Python 担体を許さない**ために充足できない。よって本 FND と同一アサーションであり、スコープに含める。
- **対比（対象外の ORC）**: もう一方の ORC `検査パイプライン実行`（v0.4.0）は `doc-system-v2/validate.py:main`（function・実在を確認）で `orc: [function]` を充足できるため、本件の対象外。同じ ORC 型でも担体の種類によって充足可否が分かれるという事実自体が、**粒度軸だけでは適格性を表現できない**ことの傍証になる。
- 既存資産（拡張の受け皿）: `doc-system-v2/schema/sidecar.schema.json` の `carrier` が enum `[skill, agent, command, instructions, hooks, code]` を持ち、「設計要素の実現担体（realization carrier）」として機械可読 SoT に定義済み（Issue #93 で enum 化・オーナー承認 2026-07-03）。in-graph の対応ノードは SCM `キャリア属性-carrier-スキーマ`。現在 PROMPT 15 件で使用実績がある。**MOD / PRS と同様に ORC もこの enum で判別可能**（`著作・反映パイプライン実行` = `agent` / `検査パイプライン実行` = `code`）であり、追加スコープに対しても新語彙の発明は不要。
- 前提の非対称: `src_symbol_eligibility` は「シンボルの粒度」の1軸しか持たず、「担体の種類」（code / agent / skill / …）の軸を持たない。`carrier` は既に後者を表現しているが、両者は接続されていない。

### 全キーの網羅確認（v0.2.0 で実施・初版の網羅漏れの再発防止）

| キー | 適格 kind | 非 Python 担体の実在事例 | 本 FND のスコープ |
|---|---|---|---|
| `mod` | `[module]` | MOD `author` / `reconciler`（agent 担体） | **対象** |
| `prs` | `[class, function]` | PRS `tmp-草案ファイル書き出し`（ツール呼び出し） | **対象** |
| `orc` | `[function]` | ORC `著作・反映パイプライン実行`（agent 担体） | **対象**（v0.2.0 で追加） |
| `dm` | `[class]` | 実在事例を確認できず（型定義は Python 側に閉じている） | 対象外（該当なし） |
| `port` | `[class]` | 同上 | 対象外（該当なし） |
| `prompt` | `[file]` | 担体は非 Python だが `file` 適格で充足可能 | 対象外（充足可） |
| `cfg` | `[file]` | 同上。ただし粒度不一致は別アサーション（A5） | 対象外（別 FND） |

## 深刻度の根拠（ERROR・実害で判定）

- **実害**: 該当する MOD / PRS / ORC は、`src_symbol_eligibility` を満たす SRC を**原理的に著作できない**。回避するには実体のない Python モジュール/関数を捏造して SRC を著作するしかなく、これは SRC ノードの意味（実装担体の宣言）を壊す＝トレーサビリティと検証の信頼性そのものを損なう。設計から実装への価値経路が該当ノードで遮断される（PR6 違反）。
- v0.2.0 で ORC が加わったことにより、影響は特定の型の局所事例ではなく、**本システムの主要な実装形態（Claude サブエージェント）で実現される設計要素全般**に及ぶことが確認された。
- **判定の根拠に機械検査の発火有無を用いない**: 本規則は `activate_stage: implementation` のため、`current_stage: design` の現時点では `validate.py` の ERROR 件数に現れない。しかしこれは**検査時期の問題であって実害の大小ではない**。実装着手時点で回避手段のない充足不能が確定しているため、latent であることを理由に深刻度を下げない。

## 選択肢

- **① kind 語彙の平坦拡張**: `src_symbol_eligibility` の値 list に非コード種別を直接追加する（例 `mod: [module, agent, skill]`、`prs: [class, function, agent]`、`orc: [function, agent]`）。`source.kind` 語彙を `carrier` enum 相当まで広げ、`_src_kind_ok()` はそのまま使う。
  - 利点: 変更量が最小（config.yml のリスト＋語彙定義のみ、判定実装は無改修）。
  - 欠点: 粒度軸と担体軸が同一 list に混ざるため、**Python モジュールの SRC が agent 担体の MOD を充足できてしまう**（逆も同様）。DD-10 の本来目的「MOD からしか張れないシンボルを関数/クラス流用で誤充足させない」と同種の誤充足を、担体軸で再発させる。ORC を加えたことでこの混同の影響範囲も広がる（`検査パイプライン実行` の function 担体と `著作・反映パイプライン実行` の agent 担体が相互に誤充足しうる）。
- **② carrier 軸を導入した2次元テーブル化**: 設計ノード側に `carrier`（既存 enum）を持たせ、`src_symbol_eligibility` を担体別テーブルへ構造変更する（例 `mod: { code: [module], agent: [file], skill: [file] }`、`orc: { code: [function], agent: [file] }`）。`_src_kind_ok()` は対象設計ノードの `carrier` で行を引いてから `source.kind` を照合する。
  - 利点: 粒度軸と担体軸が分離され、担体をまたぐ誤充足が起きない（PR2「判定の種類を混ぜない」に整合）。`carrier` enum という既存の機械可読 SoT を再利用でき、新語彙を作らない。同じ ORC 型で担体が分かれる実測事例（`著作・反映パイプライン実行` vs `検査パイプライン実行`）を、そのままテーブルの行で表現できる。
  - 欠点: config スキーマが1階層深くなり、判定実装（`_src_kind_ok()`）と `validate.py` の `load_src_symbol_eligibility()`（現在は「キー: フラット list」前提のパーサ）に改修が要る。`carrier` 未設定の設計ノード（現在 PROMPT 15 件以外は未設定）への既定値／移行が必要。
- **③ 非 Python 担体を規則の対象外にする**: `mod←src` / `prs←src` / `orc←src` に除外条件を導入し、`carrier != code` の設計ノードを規則対象から外す（機構は A1 で既存の `applies_when: condition_present` と同型＝`dsv2/query.py` に実装済みのパターン）。
  - 利点: 実装追随が軽く、既存の除外機構をそのまま流用できる。
  - 欠点: 非 Python 担体の設計要素が**トレーサビリティの網から落ちる**（実装との対応が機械検証されないまま残る）。エージェント定義は本システムの主要な実装形態であり、ORC（パイプライン全体の制御フロー）まで検証対象外にすると SRC 層の網羅性が実質的に大きく欠ける（PR6「価値経路を遮断しない」に反する方向）。

## 推奨

**②（carrier 軸を導入した2次元テーブル化）を推奨する。**

根拠:
- 本指摘の原因は「担体の多様性を粒度1軸で表そうとしている」ことであり、①はその混同を温存したまま値だけ増やす対症であって、DD-10 が排除した誤充足を担体軸で再生産する。
- 担体軸の語彙は既に `carrier` enum として機械可読 SoT に存在し（SCM `キャリア属性-carrier-スキーマ`）、新規に語彙を発明せずに済む。②は既存資産の接続であって新概念の導入ではない。ORC を加えた拡大後スコープでも、この受け皿はそのまま使える。
- ③は最も安価だが、`.claude/agents/*.md` を担体とする MOD・ORC が実在する以上、除外は「主要な実装形態を検証対象から外す」ことを意味し、SRC 層の存在意義を削る。

段階適用の余地: ② の完全実装（carrier 必須化＋パーサ改修）が sprint-1 の工数に収まらない場合、**①を暫定・②を最終形として DD に記録した上で①から入る**選択肢もある。ただしその段取り（暫定を挟むか一気に②へ行くか）および実施スプリントは**オーナー判断**を仰ぐ。

## 本 FND の範囲外（別処置へ送る事項・単一責務のため）

- MOD `filter` は「担体が非 Python」ではなく「機構が消滅して対応実装が存在しない」ケースであり、原因が異なる。設計ノードの retire／設計実装乖離の問題として #160 系（C1/C2）の処置対象に送る。本 FND では観測事実としてのみ記録する。
- 「設計層 MOD/DM/PORT/PRS が宣言する実装担体 `spec_inspector/*` が実在しない」（担体の不在）は別命題。本 FND は**担体は実在するが適格 kind が許さない**ケースのみを扱う。
- `must_link_to: src→[mod,dm,port,orc]` と `must_be_linked_from: X←src`（7型）の非対称は別アサーション（Issue #256 の A3・別 FND）。
- `cfg: [file]` の粒度不一致（キー単位 CFG vs ファイル単位 SRC）は別アサーション（Issue #256 の A5・別 FND）。`src_symbol_eligibility` に対応する CFG ノードが存在しない事実も A5 側で記録済み。
- 同じ `must_be_linked_from` を指摘対象とする `scm←cfg` の部分集団問題（Issue #253・A1）とは別アサーションである。

## 接続規則変更の伝播チェック（処置時に必須）

本 FND の処置は `config.yml` の `src_symbol_eligibility`（`must_link_to` / `must_be_linked_from` の充足判定を修飾する規則）の変更を伴うため、機械判定の正本だけでなく out-of-graph 著作資産への同期が必要になる。**v0.2.0 時点の確認結果**（初版から変更なし・ORC 追加による新たな差分も無し）:

- `.claude/` 配下（skills / agents）を `src_symbol_eligibility` および `source.kind` で全文検索した結果、**ヒット 0 件**。現時点で著作資産側にこの規則の記述は存在しない＝旧ルールの記述が残存している状態ではない。
- `docs/doc-system/03-connection-matrix.md` は `SRC --> MOD` / `DM` / `PORT` / `ORC`（L51–54）を mermaid で記載するのみで、**シンボル適格性・担体の条件は未記載**。
- 処置時に同期すべき候補: `docs/doc-system/03-connection-matrix.md`（適格性条件の追記）・`docs/doc-system/01-document-items.md`・`design-author`（MOD / PRS / **ORC** / PORT / DM の担体宣言に関わるため `.claude/agents/design-author.md` と `.github/agents/design-author.agent.md` の対）。②を採る場合は設計ノードへの `carrier` 付与ルールが著作規約に加わるため、design-author への同期は必須になる。ORC をスコープに加えたことで、同期対象の型に ORC が増える（同期先ファイルの集合は変わらない）。

## 処置対象（解消時の backref 付与先）

- `must_be_linked_from`（cfg）— 本 FND の forward 辺の張り先。解消時は `python3 -m dsv2 reverse <本FNDのslug> --apply` により辺を逆転し、当該ノードに backref を付与する。
- 影響を受ける設計ノード（MOD `author` / MOD `reconciler` / PRS `tmp-草案ファイル書き出し` / ORC `著作・反映パイプライン実行`）は**本 FND の forward 辺の張り先ではない**ため backref 付与先にならない（欠陥は規則側にあるため）。処置時の SRC 著作対象としてのみ参照する。
- 判定実装 `dsv2/query.py` の `_src_kind_ok()` および `doc-system-v2/validate.py` の `load_src_symbol_eligibility()` は out-of-graph（in-graph ノード不在）のため backref 付与先にならない。処置時に併せて改修すること。

**指摘時 ref_version**: must_be_linked_from "0.1"（must_be_linked_from.yaml v0.1.1 時点）
