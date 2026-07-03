**status: decided**（2026-06-23 オーナー指摘「型検証を SPEC-60-3 として対象化」を受けた設計判断・案B 採用）

> **辺の扱い**: 本 DD は decided。本決定の反映先は主に out-of-graph（`docs/doc-system/05-verification.md` 段階0 の RULE 表に RULE-031 を追加）であり、in-graph の義務辺（DD→X）は反映済みのため張らない（DD-16/17 の `edges: []` と同方針）。本決定の in-graph 代表処置対象は FND-105（resolved・スコープ外撤回）であり、処置側（FND-105）から `→DD-18` のバックリファレンス辺を張り返す（FND-105 v0.2 で付与・X→DD 慣行）。dedicated SPEC（SPEC-60-3）は RULE-031 を引くが、SPEC が RULE/DD への辺を張る慣行はないため `SPEC-60-3→DD-18` は不要。したがって本 DD の `edges: []`。先例: DD-17（RULE-030 新設・`edges: []`・out-of-graph 反映＋処置側 FND-104 から張り返し）・DD-16（`edges: []`）。
> **指摘時 ref_version の記録（DD-3 制度）**: 本 DD は FND-105 のスコープ外撤回に伴い決定したものだが、DD であり FND でないため「指摘時 ref_version」の本文記録は不要（DD-16/17 と同扱い）。論点の出所は FND-105（findings.md v0.1 時点・当初「②案＝別軸」としてスコープ外化していた論点）である旨を論点欄に記す。

**論点**（FND-105 の②案より昇格）: `resolved` フィールドの入力空間を SPEC-60-1（`true`→resolved）／SPEC-60-2（boolean `false`・キー未設定→unresolved）／SPEC-60-3（boolean でない型不正）の3子 SPEC で完全分割するにあたり、SPEC-60-3 が要求する「`resolved` フィールドが存在するが boolean でない（文字列 `"true"`・数値 `1`・null 等）」の検出・報告をどの RULE で行うかが空白だった。FND-105 当初は型検証を「②案＝判定セマンティクス規定（①案）とは別軸」としてスコープ外に追い出していたが、オーナー指摘により撤回し SPEC-60-3 として SPEC-60 傘の対象に組み込む方針に変更した。既存 RULE は意味が合致しない:

- RULE-028（段階0・共通必須フィールドの存在と型）は `labels`/`scheduled`/`edges` 等の**全ノード共通必須フィールド**を fail-close で検証する。一方 `resolved` は **FND 固有の任意フィールド**であり、共通必須でも全ノード対象でもない。RULE-028 で拾うと「共通必須」と「FND 固有任意」の2責務を1 RULE が抱える。
- 非 boolean を黙って `false` 既定に解決すると（現行 SPEC-60-2 文言「`true` でないとき」は非 boolean まで拾う）、型不正の握り潰しになる。検出と報告を担う RULE が必要。

**選択肢**:
- **案A（RULE-028 拡張）**: 既存 RULE-028（共通必須フィールドの型検証）を拡張し、FND 固有の任意フィールド `resolved` の boolean 型検証も RULE-028 で行う。RULE 番号を増やさず済むが、(1) RULE-028 が「共通必須フィールドの型」＋「型別（FND 固有）任意フィールドの型」の**2責務**を持ち単一責務が緩む。(2) `resolved` は**任意**フィールドであり、RULE-028 の fail-close（必須欠如はノード単位で打ち切り）方針とも整合しない（任意フィールドの型不正は fail-close すべき性質ではない）。
- **案B（新規 RULE-031 新設・推奨）**: 「型別（FND 固有）任意フィールドの型検証」を独立 RULE-031 として新設し、共通必須フィールド型（RULE-028）と型別任意フィールド型（RULE-031）を責務分離する。`condition`→RULE-016・`result`→RULE-020 の既存「型別フィールドは専用 RULE」パターンと整合する。

**推奨**: 案B。理由: (1) RULE-028 の単一責務を守る（PR1「もの＋発生源で分ける」＝共通必須フィールドの型と型別任意フィールドの型は対象も発火条件も別もの）。(2) `condition`（FND/SPEC 等の型別フィールド）→RULE-016、`result`（TR の型別フィールド）→RULE-020 と同じく「型別フィールドは専用 RULE で検証する」既存パターンに揃う。(3) `resolved` は任意フィールドで非 fail-close（型不正でもノード処理を打ち切らず ERROR 報告のみ）にできるため、fail-close 前提の RULE-028 とロジックが異なる。案A は RULE-028 を 2 責務化し、必須/fail-close と任意/非 fail-close という性質の異なる検証を1 RULE に押し込むため非推奨。

**決定**: **案B を採用**（主文脈・2026-06-23）。オーナー指摘「型検証を SPEC-60-3 として対象化」を受け、RULE-031 を `docs/doc-system/05-verification.md` 段階0（スキーマ検証・RULE-023〜029 の節）に新設する。定義は「型が FND のノード YAML に `resolved` が存在するが boolean でない（型不正）」・深刻度 **ERROR**・**非 fail-close**。RULE-031 発火時は当該ノードの resolved 判定（SPEC-60-1/60-2）を適用せず型不正を報告する（非 boolean を黙って `false` 既定に解決しない）。SPEC-60-3 はこの RULE-031 を引く。なお RULE-028 拡張（案A）vs 新 RULE 新設（案B）の選択はオーナー override 可として本 DD に記録する。

**影響範囲（2026-06-23 反映状況）**:

機械判定の正本:
- `docs/doc-system/config.yaml`（out-of-graph）: **変更不要**。`fnd_lifecycle.resolved_field: resolved` は既コミット済みで、RULE 番号（RULE-031）は config 側に持たず 05-verification.md 側でマップする（RULE-006/030 と同方式＝config が機構、05-verification.md が RULE 番号台帳）。✅ 変更なし

out-of-graph RULE 台帳:
- `docs/doc-system/05-verification.md`: 段階0（スキーマ検証・RULE-023〜029 の節）に RULE-031（型が FND のノードに `resolved` が存在するが boolean でない＝型不正・ERROR・非 fail-close）を追加。本文注記で RULE-028（共通必須フィールドの型）との責務分離、および `condition`→RULE-016・`result`→RULE-020 の「型別フィールドは専用 RULE」パターンとの整合を明記。✅ 反映済み（主文脈で追加済み）

in-graph ノード（別ファイル差分で出力）:
- `doc-system/02-what/03-spec.md`: SPEC-60 傘の対象に SPEC-60-3（failure・`resolved` 型不正→RULE-031 ERROR）を追加、SPEC-60-2 の文言を「boolean の `false`／キー未設定」に限定修正（非 boolean を 60-3 の責務へ切り出し）。SPEC-60-1 は変更なし。SPEC-60 傘本文の「スコープ外」段落を 3 分割の説明へ書き換え（spec-author 所掌）。
- `doc-system/04-verification/02-findings.md`: FND-105（v0.1→0.2）の「スコープ外（明示）」「②案（別軸）」記述を撤回・書き換え（→ `tmp/sprint-1/FND-105.md`）。処置側から本 DD へ `FND-105→DD-18` を張り返す。

**接続規則変更チェック（FND-99 パターン）**: 本 DD は **05-verification.md の RULE 台帳に RULE-031 を追加するのみ**で、`config.yaml` の接続規則（`must_link_to`/`must_be_linked_from`/`fnd_lifecycle` の `must_not_link_to`/`resolved_field`）の追加・変更・削除を**含まない**（`resolved_field: resolved` 定義および省略時 false 既定の規約自体は main の Q-4→DD-16 で既にコミット済み・本 DD はその型妥当性検出 RULE 番号を台帳に充てるのみ）。よって接続マトリクス（`docs/doc-system/03-connection-matrix.md`）・ドキュメント一覧（`docs/doc-system/01-document-items.md`）・各 author エージェント／スキルへの規則伝播は**不要**（接続規則ではなく RULE 番号台帳の追加であり、DD-17 の RULE-030 新設と同じ判定）。ただし RULE 台帳に番号が増えた事実（RULE 範囲 001〜031）は dashboard 参考の RULE 範囲記述に反映する（番号台帳の更新であって接続規則の変更ではない）。

**覆る場合の影響範囲**: RULE-031 を撤去し、SPEC-60-3 の参照 RULE を差し替える（案A へ回帰するなら RULE-028 を拡張し、SPEC-60-3 を RULE-028 参照へ戻す）。SPEC-60-2 の文言限定修正（「boolean の `false`／キー未設定」）も巻き戻し、非 boolean を `false` 既定へ吸収する旧モデルへ戻す。
