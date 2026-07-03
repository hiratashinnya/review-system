**深刻度**: INFO

**改訂理由（z バンプ v0.2.0→v0.2.1・DD-16 辺逆転完了。辺逆転は downstream 無影響の provenance/lifecycle 操作のため z＝DD-8 §4「backref 追加＝z」準拠。当初 MINOR は誤りで Q-5/DD-21 により訂正）**:
DD-16（fnd_lifecycle 正式化）に伴い FND-101 辺逆転コホートの一括是正として辺逆転を完了。元 forward 辺 `→SPEC-60`（ref_version "0.2"・充足 SPEC）・`→DD-18`（ref_version "0.1"・型検証 RULE 決定ログ）を削除し `edges: []`・`resolved: true` を付与した（従来 baseline 慣行で保持していた forward 辺を本是正で削除）。処置成果の in-graph 代表である SPEC-60 から `→FND-105` の backward 辺を受けており、resolved ルール（backward 必須・forward 不在期待）を満たす。`→DD-18`（決定ログ・DD への provenance）は辺を削除し関連は本文に記録（DD-16 と同型：→DD は付与せず provenance を本文に記す・DD-18 側に backref は付与しない）。指摘時 ref_version は本文に記録済み（DD-3）。

**根拠（深刻度確定の理由）**: 本指摘は FND-103（同根・INFO）と性質が一致し、FND-104（WARNING）とは一段軽い。
- FND-104（WARNING）は **config にルール（`must_not_link_to`）が定義されているのに、それを検出・報告する RULE 番号が 05-verification.md のどこにも存在しない**＝検出機構そのものの構造的空白だった。「どの RULE コードで報告するか決められない」状態であり、放置すると実装時に誤った RULE 番号で報告するか報告が落ちるため WARNING とした。
- 本 FND-105 はこれと異なり、**`resolved` 状態の機械判定セマンティクス自体は out-of-graph の `docs/doc-system/config.yaml` で既に規定済み**である（`fnd_lifecycle.resolved_field: resolved`、コメントで「FND YAML の機械判定フィールド・省略時は false として扱う」＝`true`=resolved／未設定・`false`=unresolved／省略時 false 既定）。すなわち判定の挙動は config 定義で確定しており、状態依存ルール SPEC（SPEC-18-1＝unresolved 前提／SPEC-18-9＝resolved 前提／SPEC-59＝resolved 前提）はその判定結果を**前提**として正しく機能する。実装層は 0 ノード（未実装）で現時点コードは壊れておらず実害はゼロ。型検証（SPEC-60-3 で追加）も同層・同性質（実装層0ノード・被覆均一化の整備）であり深刻度は INFO 据置。
- 残る課題は「判定セマンティクスを規定した **dedicated（行固有・テスタブル）な in-graph SPEC が存在しない**」という被覆の不均一・完結性ギャップに留まる。これは FND-102（issue #30・標準必須辺 44 行を全 dedicated 化）／FND-103（fnd_lifecycle resolved 系2ルールの dedicated 化）が進めた「config 行→被覆 SPEC の 1:1 トレーサビリティ台帳」の延長線上にあり、`resolved_field` のセマンティクス（判定そのもの）が台帳から漏れていた論点である。FND-103（INFO）と決定の一貫性を保ち、現状欠陥ではなく被覆均一化の整備論点であるため **INFO** とする。

> なお「将来 config の `resolved_field` 定義や省略時既定を変更した際、in-graph SPEC が追従漏れする」リスクは WARNING 寄りだが、これは現状の欠陥ではなく将来の運用機構の話であり、本 FND を SPEC-60（傘＋SPEC-60-1/60-2/60-3）で充足（dedicated SPEC 化）することで吸収される（FND-102 の同種リスク評価と整合）。

**対応状況**: resolved（2026-06-22・SPEC-60 起票で充足／2026-06-23・型検証スコープ外を撤回し SPEC-60-3＋RULE-031 で完全被覆・v0.1→0.2／2026-06-25・DD-16 辺逆転完了）。オーナー決定により「FND（ギャップ起票）と SPEC（ギャップ充足）の両方を起票」する方針に従い、`resolved` フィールドの機械判定セマンティクス（`true`=resolved／未設定・`false`=unresolved／省略時 false 既定）を規定する dedicated behavior SPEC **SPEC-60** を FR-7 配下に新設して in-graph 被覆の空白を解消した。これにより、状態依存ルール SPEC（SPEC-18-1／SPEC-18-9／SPEC-59）が前提とする「resolved/unresolved の判定結果」が in-graph の dedicated SPEC で初めて規定され、config の `fnd_lifecycle.resolved_field` 定義と 1:1 で対応する台帳に組み込まれた。さらに 2026-06-23、当初スコープ外としていた `resolved` の boolean 型検証を撤回・対象化し、SPEC-60 傘を SPEC-60-1（`true`→resolved）／SPEC-60-2（boolean `false`・キー未設定→unresolved）／SPEC-60-3（boolean でない型不正→RULE-031 ERROR）の3子 SPEC で `resolved` 入力空間を完全分割した（型不正検出を含む resolved 判定セマンティクスを完全に in-graph 被覆）。

処置成果の in-graph 代表である SPEC-60 から `→FND-105` のバックリファレンス辺を受ける（SPEC 側で付与）。なお forward 辺 `→SPEC-60`（充足 SPEC を指す処置対象辺・FND-103 が `→SPEC-18-1` を持ったのと同型）および型検証 RULE 選定の決定ログ `→DD-18` は、当初 FND-101 辺逆転コホートの一括是正対象として保持していたが、本是正（2026-06-25・DD-16 辺逆転）で削除し `edges: []`・`resolved: true` を付与した（→DD-18 は provenance として本文記録に切替）。

### 内容

main の Q-4→DD-16（commit 52093ed）で `docs/doc-system/config.yaml` に正式化された FND ライフサイクルルール `fnd_lifecycle` は、`resolved` 状態の判定フィールドを `resolved_field: resolved` として定義し、コメントで解釈規約（`resolved: true`=resolved／`resolved: false`・未設定=unresolved／**省略時は false として扱う**）を規定している。この判定結果は次の状態依存ルール SPEC が**前提**として消費する:

| SPEC | 前提条件 | resolved 判定の扱い |
|---|---|---|
| SPEC-18-1 | 型が FND の**未解消**ノード（`resolved: false` / 未設定） | 判定**結果**を前提に使う |
| SPEC-18-9 | 型が FND の**解消済み**ノード（`resolved: true`） | 判定**結果**を前提に使う |
| SPEC-59 | 解消済み FND（`resolved: true`） | 判定**結果**を前提に使う |

しかし **「`resolved` フィールドをどう解釈して resolved/unresolved を判定するか」そのものを規定した in-graph SPEC が存在しなかった**。判定セマンティクスは out-of-graph の config コメントにのみ存在し、in-graph では各 SPEC が判定済みの結果（resolved か unresolved か）を所与として参照するだけだった。これは「config にセマンティクスはあるが、それを in-graph で dedicated に規定・テスト可能化する SPEC が欠落」という完結性ギャップである。

本処置で SPEC-60（FR-7 配下のトップレベル behavior SPEC）を新設し、`resolved` フィールドの解釈規約を in-graph で規定した。`resolved` フィールドの入力空間は次の3子 SPEC で完全分割する:

| 子 SPEC | condition | 入力 | 判定 |
|---|---|---|---|
| SPEC-60-1 | normal | `resolved: true`（boolean） | resolved |
| SPEC-60-2 | normal | boolean の `false`／キー未設定 | unresolved（省略時 false 既定） |
| SPEC-60-3 | failure | `resolved` が存在するが boolean でない（`"true"`・`1`・null 等） | 型不正として RULE-031 を ERROR 報告（黙って `false` 既定に解決しない） |

これにより SPEC-18-1／SPEC-18-9／SPEC-59 が前提とする判定が SPEC-60（傘）を上流に持つ形で根拠づけられ、config の `resolved_field` 定義との 1:1 トレーサビリティが成立し、かつ非 boolean 値の握り潰しを排した型妥当性検出まで in-graph 被覆した。

### 位置づけ（スコープ境界・FND-103/104 との層分離）

- **FND-104（検出機構＝RULE 番号の不在・WARNING）**とは別層。FND-104 は「`must_not_link_to` 違反をどの RULE で報告するか」という検出機構の空白だったのに対し、本 FND-105 は「`resolved` 判定セマンティクスを規定する **dedicated SPEC**（in-graph 被覆）の不在」という coverage 論点である。PR1「もの＋発生源で分ける」に従い別ノードとして起票した。
- **FND-103（dedicated SPEC 被覆の不均一・INFO）**と同層・同根。FND-103 が fnd_lifecycle の**必須辺ルール**（must_be_linked_from／must_not_link_to）の dedicated SPEC を新設したのに対し、本 FND-105 は同じ `fnd_lifecycle` ブロックの **`resolved_field` セマンティクス**（辺ルールが前提とする判定そのもの）の dedicated SPEC を補う。FND-103 が辺の向きを規定し、FND-105 がその向きを切り替える状態判定を規定する補完関係にある。
- **FND の `resolved` フィールドと DD/Q/PEND の非対称性**: SPEC-49 は DD/Q/PEND のライフサイクル状態が**ノード YAML に漏れていないこと**（本文バッジのみで保持）を検証する＝DD/Q/PEND は YAML に状態を持たない。一方 FND の `resolved` は **YAML フィールドとして持つ**＝両者は非対称である。この非対称（FND のみ機械判定フィールドを YAML に持つ）こそが、FND に固有の `resolved` 判定セマンティクス SPEC（SPEC-60）を必要とする理由であり、SPEC-60 はこの非対称性を in-graph で明示する位置づけを持つ。`resolved` を YAML フィールドとして持つ以上、その型（boolean）の妥当性検証（SPEC-60-3／RULE-031）も同非対称性に内包される論点である。
- FND-101／Q-4 の**辺逆転コホート**と同一系統。`resolved` の判定結果こそが「forward 辺を持つ（unresolved）か backward 辺を持つ（resolved）か」の辺逆転を駆動するため、SPEC-60 は辺逆転ルール群（SPEC-18-1/18-9/59）の判定基盤に当たる。

### 経緯（型検証スコープ外の撤回・PR8 経緯保全）

> **当初の誤り（撤回済み・記録のため残置）**: v0.1 時点の本 FND は、`resolved` の boolean 型検証（非 boolean 値の検出）を「②案＝判定セマンティクス規定（①案）とは**別軸**」と整理し、**本 FND のスコープ外**（必要なら別 FND/Q として起票すべき独立論点）として SPEC-60 の対象から追い出していた。すなわち SPEC-60 を SPEC-60-1／SPEC-60-2 の2子のみで構成し、型不正値の扱いは「オーナー判断に委ねる」として未対象化していた。
>
> **撤回理由（オーナー指摘・2026-06-23）**: オーナーより「勝手にスコープ外にするな。どう考えても SPEC-60-3 として対象にすべき」との指摘を受けた。AI（主文脈）が独断で型検証をスコープ外に追い出した判断は誤りであり、撤回する。`resolved` を YAML 機械判定フィールドとして持つ（上記非対称性）以上、その型妥当性は判定セマンティクスと不可分の同一被覆論点であり、別軸として切り離す根拠は弱かった。SPEC-60-2 の旧文言「`true` でないとき（明示 false、またはキー未設定）」が非 boolean 値まで黙って `false` 既定に拾う握り潰しを内包していた点も、型検証を対象化すべき根拠である。

撤回に伴い:
- `resolved` の boolean 型検証を SPEC-60-3（failure）として SPEC-60 傘の対象に組み込み、SPEC-60-2 の文言を「boolean の `false`／キー未設定」に限定修正して非 boolean を SPEC-60-3 の責務へ切り出した。
- 型不正の検出・報告を担う RULE-031 を新設した（型別＝FND 固有の任意フィールドの型検証・ERROR・非 fail-close）。RULE-028 拡張 vs 新規 RULE 新設の選定は **DD-18** に決定ログとして記録した（案B＝RULE-031 新設を採用・`condition`→RULE-016・`result`→RULE-020 の「型別フィールドは専用 RULE」パターンと整合）。

これにより本 FND は SPEC-60-1/60-2/60-3 ＋ RULE-031 新設（DD-18）で resolved 判定セマンティクス（型不正検出を含む）を完全に in-graph 被覆した。

### 推奨（オーナー提示用・履歴）

- **① SPEC-60 で behavior SPEC 化（採択済み）**: `resolved` フィールドの解釈規約を規定する dedicated behavior SPEC を FR-7 配下に新設し、config の `resolved_field` 定義と 1:1 対応させる。SPEC-18-1/18-9/59 が前提とする判定の根拠が in-graph で明示され、被覆が均一化する。FND-102/103 が進めた台帳化と整合する。
- **② `resolved` フィールドの boolean 型検証（採択済み・当初スコープ外を撤回）**: `resolved` に boolean 以外（文字列 `"true"`・数値 `1`・null 等）が入った場合に型不正として検出する。**v0.1 では本 FND のスコープ外（別軸）として切り出していたが、オーナー指摘により撤回し SPEC-60-3＋RULE-031（DD-18）として対象化**。SPEC-52-4（RULE-028）が共通必須フィールド型を担うのに対し、FND 固有の任意フィールド `resolved` の型検証は型別専用 RULE-031 が担う（責務分離）。

**指摘時 ref_version**:
- `→SPEC-60` "0.2"（doc-system/02-what/03-spec.md の SPEC-60 傘ノードバッジ・SPEC-60-3 追加で v0.1→0.2 へ追従後の版を指す。当初指摘時は v0.1）。
- `→DD-18` "0.1"（doc-system/04-verification/04-decisions.md の DD-18 ノードバッジ v0.1 時点＝型検証 RULE 決定ログの起票バッジ・provenance）。

なお親 FR は **FR-7「検証・指摘の完結性検証」**（v0.2・fnd_lifecycle 系 SPEC-18-1/18-9/59 と同じく FR-7 を親とする）だが、FR-7 への言及は本文参照に留め、forward 辺は処置対象である SPEC-60（充足 SPEC）と DD-18（型検証 RULE 決定ログ）のみとしていた（FR-7 への辺は不要＝FND は処置対象＝充足 SPEC を指せば十分で、親 FR への辺は FND-103 が SPEC-18-1 のみを指したのと同型）。本是正で両 forward 辺を削除済み。

被指摘対象の判定セマンティクス定義は `docs/doc-system/config.yaml` の `fnd_lifecycle.resolved_field`（DD-16・Q-4 から昇格・main commit 52093ed 由来でファイル version を持たないため参照キーを明記）に存在するが、config.yaml はノード化されない out-of-graph 資産のため forward 辺は張れない（FND-103 が config.yaml を本文参照に留めたのと同じ扱い）。被指摘の所在（config の `resolved_field` 定義の in-graph 未被覆）は本文で明記する。

### config.yaml 規則変更チェック（FND-99 パターン）

本 FND および本処置（SPEC-60-1/60-2/60-3 ＋ RULE-031 新設）は **`fnd_lifecycle.resolved_field` の判定セマンティクスおよびその型妥当性を規定する in-graph SPEC の不在を充足するもので、`must_link_to`/`must_be_linked_from`/`fnd_lifecycle` 等の config 接続規則の追加・変更・削除を含まない**（`resolved_field` 定義および省略時 false 既定の規約自体は main の Q-4→DD-16 で既にコミット済み・本 FND はその in-graph 被覆論点を起票・充足するのみ）。RULE-031 の新設は `docs/doc-system/05-verification.md` 段階0 の RULE 番号台帳への追加であり、config.yaml の接続規則・`fnd_lifecycle` 定義は変更していない（DD-18 影響範囲も同判定）。

よって out-of-graph 著作資産（接続マトリクス `docs/doc-system/03-connection-matrix.md`・ドキュメント一覧 `docs/doc-system/01-document-items.md`・各 author エージェント／スキル）への規則伝播チェックは不要（RULE 台帳・接続マトリクスへの伝播対象なし）。RULE 番号が増えた事実（RULE 範囲 001〜031）の dashboard 反映は DD-18 影響範囲に記録済み。SPEC-60（傘＋3子）が config の `resolved_field` 定義を引く反映は SPEC-60 系本文の入力/トリガで完了する（spec-author 所掌）。
