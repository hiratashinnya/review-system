**深刻度**: WARNING

**改訂理由（z バンプ v0.2.0→v0.2.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い FND-101 辺逆転コホートの一括是正として辺逆転を完了。元 forward 辺 `→FND-103`（ref_version "0.2"・同根コホート）・`→DD-17`（ref_version "0.1"・決定ログ）を削除し `edges: []`・`resolved: true` を付与した。両辺とも DD/FND への provenance 辺のため、DD-16 と同型で辺を削除し関連は本文に記録する（→DD-17・→FND-103 ともに付与せず provenance を本文に記す・DD-17 側／FND-103 側に backref は付与しない）。処置成果の in-graph 代表である SPEC-59 から `→FND-104` の backward 辺を受けており、resolved ルール（backward 必須・forward 不在期待）を満たす。指摘時 ref_version は本文に記録済み（DD-3）。

> **reconciliation 申し送り（DD-17 本文との整合）**: 従来 FND-104 は決定スパイン慣行に従い `FND-104→DD-17`（X→DD）を張っていた。本是正で DD-16 の provenance 規則（→DD は削除し本文記録・DD 側に backref を付与しない）に従い当該辺を削除した。`decisions.md` の DD-17 本文に「処置側から本 DD へ FND-104→DD-17 を張り返す」と記載が残っているため、reconciliation で当該文を「provenance を本文記録に切替（DD-16）」へ整合させること。

**根拠（深刻度確定の理由）**: 実装層は 0 ノード（未実装）で現時点コードは壊れておらず実害はゼロのため、INFO も候補になる。しかし本指摘は FND-103（同根・INFO）とは性質が一段重い。FND-103 は「既に存在する RULE-006（必須辺欠如）の dedicated（テスタブル）SPEC が fnd_lifecycle resolved 系で不均一」という**被覆の均一化**論点であり、挙動は SPEC-8 一般則＋config 定義で既に規定済みだった。これに対し本 FND-104 は **config（`fnd_lifecycle.resolved.must_not_link_to`・辺残留検出・warning）にルールが定義されているのに、それを検出・報告する RULE 番号が 05-verification.md のどこにも存在しない**＝検出機構の定義そのものの空白である。具体的に：

- RULE-006（段階②・L78）は config の `must_link_to`/`must_be_linked_from` の必須接続**欠如**のみを対象とし、`must_not_link_to`（辺が**残ってはならない**＝禁止接続の存在）は列挙外で意味が逆。
- RULE-001/002/022（段階①・L35-37）は DD/Q/PEND の義務辺**残存**を検出するが、これは `decision_spine` の**ノード型固有**ルールであり、config 駆動の汎用「辺残留」ルールではない。

結果として「config 駆動・任意型・辺が残留してはならない」という検出を引ける RULE コードが空白で、検証ツール（spec-inspector・実装層 0 ノード・未実装）を実装する際に `must_not_link_to` 違反を**どの RULE コードで報告するか決められない**。FND-103 の dedicated SPEC（②案で新設予定の resolved 系 SPEC）も、その期待動作で参照すべき RULE 番号を引けない（暫定で RULE-006 と書かれたが RULE-006 は「欠如」で意味が逆転している）。「config にルールはあるが検出機構の RULE 定義が欠落」という**設計の完結性ギャップ**で、放置すると実装時に誤った RULE 番号で報告するか報告自体が落ちるため、現状の欠陥（定義不在）として **WARNING** とする。実害ゼロのため ERROR には上げない。

**対応状況**: resolved（2026-06-22・案B 採用／2026-06-25・DD-16 辺逆転完了）。オーナー決定により案B（新規 RULE-030 新設・欠如 RULE-006 と残存 RULE-030 を責務分離）を採用し、`docs/doc-system/05-verification.md` 段階①に **RULE-030**（config 駆動の禁止接続/辺残留の存在＝`must_not_link_to` 違反・任意型・WARNING）を新設して検出機構の空白を解消した。RULE-030 の本文注記で RULE-001/022（decision_spine のノード型固有残存）および RULE-006（必須接続の欠如・段階②）との責務分離を明記済み。FND-103 ②案の dedicated SPEC である **SPEC-59** がこの RULE-030 を引く（期待動作・例の参照 RULE を RULE-006→RULE-030 に差し替え済み）。決定記録は **DD-17**。処置成果の in-graph 代表である SPEC-59 から `→FND-104` のバックリファレンス辺を受ける。なお当初は決定スパイン慣行に従い処置側から決定ログへ `FND-104→DD-17` を張り返し、forward 辺 `→FND-103`（同根コホート）も baseline 慣行で保持していたが、本是正（2026-06-25・DD-16 辺逆転）で両 forward 辺を削除し `edges: []`・`resolved: true` を付与した（→DD-17・→FND-103 はいずれも provenance として本文記録に切替）。

### 内容

main の Q-4→DD-16 で `docs/doc-system/config.yaml` に正式化された FND ライフサイクルルール `fnd_lifecycle` は、resolved 系に2つの辺ルールを持つ。このうち `resolved.must_not_link_to`（target: any・severity warning・reason「resolved FND の元 forward 辺は削除済みであること（辺逆転ルール DD-3）」）は、**「辺が残留してはならない＝禁止接続が存在する」ことを検出する**汎用 config 駆動ルールである。

しかし `docs/doc-system/05-verification.md` の RULE 一覧には、この「禁止接続/辺残留の存在」を検出・報告する RULE 番号が存在しなかった。本処置で RULE-030 を新設し、この空白を解消した。

| 05-verification.md の RULE | 対象 | 性質 | `must_not_link_to` を被覆するか |
|---|---|---|---|
| RULE-006（段階②・L78） | config `must_link_to`/`must_be_linked_from` の必須接続**欠如** | 辺の**欠如** | × 意味が逆（欠如であって残留ではない） |
| RULE-001/002/022（段階①・L35-37） | DD/Q/PEND の義務辺（`X→Y`）が**存在** | 辺の**残存**だが**ノード型固有**（decision_spine） | × config 駆動の汎用辺残留ではない |
| **RULE-030（段階①・新設）** | **config 駆動・任意型・辺残留（`must_not_link_to`）** | **辺の残存（禁止接続の存在）・汎用** | **○（新設で被覆）** |

RULE-006 が「欠如」、RULE-001/022 が「残存（ノード型固有）」を担い、**config 駆動の汎用「辺残存（禁止接続の存在）」を検出する RULE が構造的に空白**になっていた。本処置で新設した RULE-030 がこの空白を埋め、`fnd_lifecycle.resolved.must_not_link_to` はじめ汎用 `must_not_link_to` 違反を引ける RULE が定義された。

影響（解消前）: 検証ツール（spec-inspector・実装層 0 ノード・未実装）を実装する際、`must_not_link_to` 違反をどの RULE コードで報告するか未定義。FND-103 ②案で新設する dedicated SPEC（resolved 系）の期待動作も、参照すべき RULE 番号を引けない（暫定で RULE-006 と記載されたが RULE-006 は「欠如」で意味が逆）。→ RULE-030 新設・SPEC-59 が RULE-030 を引くことで解消。

### 位置づけ（スコープ境界・FND-103 との層分離）

- これは FND-103（dedicated **SPEC** 被覆の不均一＝coverage 論点）とは**別層の RULE（検出機構）定義の不在**である。PR1「もの＋発生源で分ける」に従い、SPEC 被覆論点（FND-103）とは別ノードとして起票した。
- FND-101／Q-4 の**辺逆転コホート**（resolved FND の forward 削除・backward 付与）と同一系統。`must_not_link_to` は辺逆転後の resolved FND の構造（元 forward 辺が削除済みであること）を機械判定するルールである。
- 検出機構（RULE-030）が定義されて初めて、それを参照する dedicated SPEC（SPEC-59・FND-103 ②案）が RULE 番号を引ける。本 FND-104 の解消は FND-103 ②案の前提に位置づき、両者は本処置で同時に解消した。

### 推奨（オーナー提示用・2 案）

- **案A: RULE-006 の定義を拡張**して config 駆動の `must_not_link_to`（辺残留・禁止接続の存在）も RULE-006 で報告する。RULE 番号を増やさず済むが、RULE-006 が「必須接続の欠如」と「禁止接続の残存」の**2責務を持ち単一責務が緩む**（欠如と残存は検出ロジックも逆）。
- **案B（推奨）: 新規 RULE（例 RULE-030）を新設**し、「config 駆動の禁止接続/辺残留の存在」を独立 RULE として定義する。RULE-001/022 が義務辺の残存を独立 RULE にしている先例と整合し、**欠如（RULE-006）と残存（新 RULE）を責務分離**できる。FND-103 ②案の dedicated SPEC（resolved 系）はこの新 RULE を引く。

> 推奨は**案B**。FND-103 の配置決定（辺欠如 vs 辺残留を責務分離）と一貫し、RULE-001/022 が残存を独立 RULE にしている先例にも沿う。ただし RULE 新設は検証層設計（段階・suppress 機構・実装層 SPEC）に波及するため**オーナー確認必須**。現状実害ゼロ（実装層 0 ノード）のため独断で `scheduled` を設定しない（スケジュール独断禁止・CLAUDE.md）。AI が独断で「対応不要」「将来検討でよい」と結論づけない（PR7・独断禁止）。
>
> **決定: 案B 採用（DD-17）**（オーナー決定・2026-06-22）。RULE-030 を 05-verification.md 段階①に新設し、SPEC-59 が RULE-030 を引く dedicated SPEC として `must_not_link_to` を被覆する。決定記録は DD-17。

**指摘時 ref_version**: FND-103 "0.1"（doc-system/04-verification/02-findings.md の FND-103 ノードバッジ v0.1 時点・provenance＝同根コホート）／DD-17 "0.1"（doc-system/04-verification/04-decisions.md の DD-17 ノードバッジ v0.1 時点・provenance＝案B 決定ログ）。なお被指摘対象の検出機構ギャップは、(1) `docs/doc-system/config.yaml` の `fnd_lifecycle.resolved.must_not_link_to`（DD-16・Q-4 から昇格・main commit 由来でファイル version を持たないため参照箇所＝当該キーを明記）と、(2) `docs/doc-system/05-verification.md` の RULE 表（段階②・RULE-006〔L78〕／段階①・RULE-001/002/022〔L35-37〕）に所在するが、いずれもノード化されない out-of-graph 資産のため forward 辺は張れない（FND-103 が config.yaml を本文参照に留めたのと同じ扱い）。

### config.yaml 規則変更チェック（FND-99 パターン）

本 FND は **`fnd_lifecycle.resolved.must_not_link_to` を検出・報告する RULE が 05-verification.md に未定義であることを指摘するもので、`must_link_to`/`must_be_linked_from`/`fnd_lifecycle` 等の config 接続規則の追加・変更・削除を含まない**（`fnd_lifecycle` 規則自体は main の Q-4→DD-16 で既にコミット済み・本 FND はその検出機構 RULE の不在を起票するのみ）。処置（RULE-030 新設）も `docs/doc-system/05-verification.md` の RULE 番号台帳への追加に留まり、config.yaml の接続規則は変更していない。よって out-of-graph 著作資産（接続マトリクス・ドキュメント一覧・各 author エージェント／スキル）への規則伝播チェックは不要（RULE 台帳の番号追加＝RULE 範囲 001〜030 への更新は接続規則変更ではない）。SPEC-59 が RULE-030 を引く反映・05-verification.md の RULE 表更新は本処置の所掌内で完了済み。
