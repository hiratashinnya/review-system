**status: decided**（2026-06-22 オーナー承認・案B 採用）

> **辺の扱い**（v0.1.1・FND-101 辺逆転是正に伴い整合更新）: 本 DD は decided。本決定の反映先は主に out-of-graph（`docs/doc-system/05-verification.md` の RULE 表・`docs/doc-system/config.yaml` の `fnd_lifecycle.resolved.must_not_link_to`）であり、in-graph の義務辺（DD→X）は反映済みのため張らない（DD-16 の `edges: []` と同方針）。本決定で resolved 化された FND-104 は当初 `FND-104→DD-17`（X→DD）を張っていたが、FND-101 辺逆転コホートの一括是正（DD-16・2026-06-25）で当該 provenance 辺を削除し、関連は FND-104 本文に記録した（→DD は付与せず provenance を本文に記す・DD-17 側に backref は付与しない＝DD-16 と同型）。処置成果の in-graph 代表である SPEC-59 が `→FND-104` バックリファレンス辺を持ち、FND-104 の resolved ルール（backward 必須）はこれで充足される。dedicated SPEC（SPEC-59）は RULE-030 を引くが、SPEC が RULE/DD への辺を張る慣行はないため `SPEC-59→DD-17` は不要。したがって本 DD の `edges: []`。先例: DD-9（RULE-029 新設・`→FND-78` 1 辺）・DD-16（`edges: []`・out-of-graph 反映＋provenance 本文記録）。
> **指摘時 ref_version の記録（DD-3 制度）**: 本 DD は FND-104 の指摘を受けて決定したものだが、DD であり FND でないため「指摘時 ref_version」の本文記録は不要（DD-16 と同扱い）。論点の出所は FND-104（findings.md v0.1 時点）である旨を論点欄に記す。

**論点**（FND-104 より昇格）: main の Q-4→DD-16 で `config.yaml` に正式化された `fnd_lifecycle.resolved.must_not_link_to`（target: any・severity warning・「resolved FND の元 forward 辺は削除済みであること」＝辺残留/禁止接続の存在の検出）に対し、それを検出・報告する RULE 番号が `docs/doc-system/05-verification.md` の RULE 一覧に存在しない（検出機構の定義そのものの空白）。既存 RULE は意味が合致しない:

- RULE-006（段階②・必須接続の**欠如**）は `must_link_to`/`must_be_linked_from` のみを対象とし、`must_not_link_to`（辺が**残ってはならない**）とは意味が逆。
- RULE-001/002/022（段階①・義務辺**残存**）は DD/Q/PEND の `decision_spine` **ノード型固有**ルールであり、config 駆動の汎用「辺残留」ルールではない。

結果として「config 駆動・任意型・辺が残留してはならない」検出を引ける RULE コードが空白で、検証ツール実装時に `must_not_link_to` 違反をどの RULE で報告するか決められず、FND-103 ②案の dedicated SPEC（resolved 系）も参照すべき RULE 番号を引けない。

**選択肢**:
- **案A（RULE-006 拡張）**: 既存 RULE-006 の定義を拡張し、config 駆動の `must_not_link_to`（辺残留・禁止接続の存在）も RULE-006 で報告する。RULE 番号を増やさず済むが、RULE-006 が「必須接続の欠如」と「禁止接続の残存」の**2責務**を持ち単一責務が緩む（欠如と残存は検出ロジックも逆・severity も error/warning で異なる）。
- **案B（新規 RULE-030 新設・推奨）**: 「config 駆動の禁止接続/辺残留の存在」を独立 RULE-030 として新設し、欠如（RULE-006）と残存（RULE-030）を責務分離する。RULE-001/022 が義務辺の残存を独立 RULE にしている先例と整合し、FND-103 ②案の dedicated SPEC（SPEC-59）はこの RULE-030 を引く。

**推奨**: 案B。理由: (1) RULE-006 の単一責務を守る（PR1「もの＋発生源で分ける」＝欠如と残存は検出ロジックも severity も別もの）。(2) RULE-001/022 が義務辺の残存を独立 RULE にしている既存先例と一貫する。(3) FND-103 の配置決定（辺欠如 vs 辺残留を別 SPEC に責務分離）と層が揃う。案A は RULE-006 を 2 責務化し、欠如（error）と残存（warning）という意味も severity も逆のロジックを 1 RULE に押し込むため非推奨。

**決定**: **案B を採用**（オーナー承認・2026-06-22）。RULE-030 を `docs/doc-system/05-verification.md` 段階①に新設し、config 駆動の禁止接続/辺残留（`fnd_lifecycle.resolved.must_not_link_to` を含む汎用の `must_not_link_to`）の存在を WARNING で報告する。FND-103 ②案で新設する dedicated SPEC（SPEC-59）は RULE-030 を引く。

**影響範囲（2026-06-22 反映状況）**:

機械判定の正本:
- `docs/doc-system/config.yaml`（out-of-graph）: **変更不要**。`fnd_lifecycle.resolved.must_not_link_to` 自体は DD-16 で既にコミット済み。RULE 番号（RULE-030）は config 側に持たず 05-verification.md 側でマップする（RULE-006 と同方式＝config が機構、05-verification.md が RULE 番号台帳）。✅ 変更なし

out-of-graph RULE 台帳:
- `docs/doc-system/05-verification.md`: 段階①に RULE-030（config 駆動の禁止接続/辺残留の存在＝`must_not_link_to` 違反・任意型・WARNING）を新設。本文注記で RULE-001/022（decision_spine のノード型固有残存）および RULE-006（必須接続の欠如・段階②）との責務分離を明記。✅ 反映済み（本セッション既了）

in-graph ノード（別ファイル差分で出力）:
- `doc-system/02-what/03-spec.md`: SPEC-59（fnd_lifecycle resolved 系 `must_not_link_to` の dedicated SPEC）の期待動作・例の参照 RULE を RULE-006→RULE-030 に差し替え、`→FND-103`・`→FND-104` バックリファレンスを付与（→ `tmp/sprint-1/SPEC-59.md`・reconciliation 反映）。
- `doc-system/04-verification/02-findings.md`: FND-104（v0.1→0.2 で resolved 化、その後 FND-101 辺逆転是正で v0.3）。当初は処置側から本 DD へ `FND-104→DD-17`（X→DD）を張り返していたが、FND-101 辺逆転コホート是正（DD-16・2026-06-25）で当該 provenance 辺を削除し関連は FND-104 本文に記録（→DD は付与せず provenance を本文に記す）。FND-104 の resolved backward は SPEC-59→FND-104 が充足する。FND-103 も ②案完了で resolved 化（同様に forward 辺を削除し本文 provenance 記録へ移行）。

**接続規則変更チェック（FND-99 パターン）**: 本 DD は **05-verification.md の RULE 台帳に RULE-030 を追加するのみ**で、`config.yaml` の接続規則（`must_link_to`/`must_be_linked_from`/`fnd_lifecycle` の `must_not_link_to`）の追加・変更・削除を**含まない**（`fnd_lifecycle.resolved.must_not_link_to` 規則自体は DD-16 で既にコミット済み・本 DD はその検出 RULE 番号を台帳に充てるのみ）。よって接続マトリクス・ドキュメント一覧・各 author エージェント／スキルへの規則伝播は**不要**。ただし RULE 台帳に番号が増えた事実（RULE 範囲 001〜030）は dashboard 参考の RULE 範囲記述に反映する（番号台帳の更新であって接続規則の変更ではない）。

**覆る場合の影響範囲**: RULE-030 を撤去し、SPEC-59 の参照 RULE を差し替える（案A へ回帰するなら RULE-006 拡張＋SPEC-59 を RULE-006 参照へ戻す）。
