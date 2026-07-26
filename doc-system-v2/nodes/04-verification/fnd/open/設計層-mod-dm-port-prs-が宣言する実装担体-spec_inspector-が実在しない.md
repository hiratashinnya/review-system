**深刻度**: ERROR

**対応 Issue**: #160（Sprint 1 対象の SRC 実装ノードを materialize する）／関連 #127

**内容**: 設計層の MOD 18件・DM 6件・PORT 1件・PRS 1件（計26件）が宣言する実装担体 `spec_inspector/*` はリポジトリに実在せず、稼働している実装は別のモジュール分割（`dsv2/` ＋ `doc-system-v2/validate.py`）として存在する。設計ノードの担体宣言が事実と一致していないため、設計↔実装のトレースが成立しない。

観測事実:

- MOD 18件の本文はいずれも `**パス**: spec_inspector/*.py` を宣言するが、`spec_inspector/` パッケージは存在しない（`ls spec_inspector` → No such file or directory）。
- MOD 名（`parser` `collector` `filter` `domain` `config` `reporter` `projector` `reconciler` `author` `drift_checker` `condition_checker` `verification_checker` `structure_checker` `graph_coverage` `spec_coverage` `ports` `adapters/fs` `__main__`）に一致する `.py` はリポジトリ全体で1件も存在しない。
- DM 6件が宣言する型（`NodeRecord` / `EdgeRecord` / `ViolationRecord` / `ConfigSlice` / `CoverageReport` / `InspectionViews`）および PORT の `FileSystemPort` は、`grep --include=*.py` でヒット0件。実装は dict ＋ `pathlib` 直呼びで書かれており、値オブジェクト層・Port 抽象そのものが実装側に存在しない。
- PRS `tmp 草案ファイル書き出し` も、`prs: [class, function]`（`src_symbol_eligibility`）を満たす Python 担体を持たない（実体は著作エージェントの Write）。
- 実在する実装: `dsv2/{cli,meta,query,nodeyaml,viewer,rename,reverse,gitutil,yamledit,dashboard}.py` ＋ `doc-system-v2/{validate,slugify}.py`。
- 機械的帰結: `doc-system-v2/validate.py` の `_validate_identifier_ref()`（L456）は `source.file` の実在と Python AST 上の qualname 存在・kind 一致を ERROR で強制するため、**該当26件の SRC ノードは物理的に著作できない**。すなわち本件は #160（SRC materialize）の前提条件を塞いでいる。
- 現時点の `validate.py` live ERROR には現れない（`src` 系規則の `activate_stage: implementation`・現在 `current_stage: design`＝latent）が、設計ノード本文の担体宣言が事実と異なる点は現在時点で成立している欠陥であるため深刻度を ERROR とする。
- オーナー方針（2026-07-26）: 乖離は「未実装 / 設計変更 / 設計通り実装していない」のいずれかであり、**#160 のスコープ内で設計実装の整合を取る**（切り出さない）。

**本 FND のスコープ（1アサーション）**: 「設計層 MOD/DM/PORT/PRS の担体宣言先が実在しない」という単一命題に閉じる。担体適格性の規則側の不備（`src_symbol_eligibility: mod: [module]` が非 Python 担体を被覆しない／`cfg: [file]` の粒度不一致）は別 FND（Issue #256 系）の対象であり、本 FND では扱わない。実装は存在するが対応する設計ノードが無い逆方向（設計外実装）も別 FND（C2・同 #160）の対象。

## forward 辺の張り先と選定理由

**選定: 該当26件すべてに forward 辺を張る（代表ノード方式を採らない）。**

選定理由:

1. **処置の単位がノード単位だから**。是正は「26件それぞれの本文の担体宣言（`**パス**` / 公開 I/F / 型名）を実体に合わせて書き換える or ノード自体を統廃合する」という個別編集であり、26件すべてが処置対象になる。代表辺方式では残り25件が辺グラフ上「無指摘」に見える。
2. **解消時のバックリファレンスを全件に落とすため**（DD-16）。`dsv2 reverse --apply` は forward 辺の張り先にのみ backref を付与する。全件に張っておけば「どのノードが #160 で是正されたか」が辺グラフに残り、`dsv2 dependents` で機械的に追える。代表方式だと本文の箇条書きにしか証跡が残らない。
3. **対象集合の境界が機械的に確定しているから**。判定基準は「本文が `spec_inspector/*` を担体として宣言している」または「宣言する型・Protocol が実装コードに存在しない」の2つで、`grep -rn spec_inspector doc-system-v2/nodes/05-design/` および型名 grep（ヒット0件）で全数が一意に列挙できる。曖昧な周辺ノードを巻き込む余地がなく、全数辺が過剰被覆にならない。
4. **辺数増のコストが規則違反にならないことを確認済み**。`doc-system-v2/config.yml` および `validate.py` にハブ次数閾値ルールの実装は無く（`hub` 判定は validate.py に存在しない）、out-edge 26本が新たな違反・警告を誘発しない。1アサーション性は「宣言担体が実在しない」という単一命題で保たれており、辺の本数は指摘の数ではない。
5. コストとして、解消時に処置対象26件へ backref が付与され26件の z バンプが発生する。これは `dsv2 reverse --apply` による機械実行で処理でき、手編集は発生しない。

**辺の対象外だが同一原因の隣接観測**: ORC `検査パイプライン実行` も本文で `E-1（CLI 実行 python -m spec_inspector）` を宣言しており、同じ乖離を持つ。ただし本 FND の指摘対象は依頼スコープどおり MOD/DM/PORT/PRS の26件に限定しており、ORC は forward 辺に含めていない。#160 の是正作業では ORC も同時に整合させる必要があるため、対象追加の要否は主文脈／オーナーの判断を仰ぐ。

## 指摘時 ref_version（DD-3）

MOD（18件）:

- **指摘時 ref_version**: parser "0.2"（parser.yaml v0.2.0 時点）
- **指摘時 ref_version**: collector "0.1"（collector.yaml v0.1.0 時点）
- **指摘時 ref_version**: filter "0.2"（filter.yaml v0.2.1 時点）
- **指摘時 ref_version**: domain "0.3"（domain.yaml v0.3.1 時点）
- **指摘時 ref_version**: config "0.1"（config.yaml v0.1.0 時点）
- **指摘時 ref_version**: reporter "0.1"（reporter.yaml v0.1.0 時点）
- **指摘時 ref_version**: projector "0.1"（projector.yaml v0.1.0 時点）
- **指摘時 ref_version**: reconciler "0.1"（reconciler.yaml v0.1.0 時点）
- **指摘時 ref_version**: author "0.2"（author.yaml v0.2.0 時点）
- **指摘時 ref_version**: drift_checker "0.2"（drift_checker.yaml v0.2.0 時点）
- **指摘時 ref_version**: condition_checker "0.1"（condition_checker.yaml v0.1.0 時点）
- **指摘時 ref_version**: verification_checker "0.1"（verification_checker.yaml v0.1.0 時点）
- **指摘時 ref_version**: structure_checker "0.1"（structure_checker.yaml v0.1.0 時点）
- **指摘時 ref_version**: graph_coverage "0.2"（graph_coverage.yaml v0.2.0 時点）
- **指摘時 ref_version**: spec_coverage "0.1"（spec_coverage.yaml v0.1.0 時点）
- **指摘時 ref_version**: ports "0.1"（ports.yaml v0.1.0 時点）
- **指摘時 ref_version**: adapters-fs "0.1"（adapters-fs.yaml v0.1.0 時点）
- **指摘時 ref_version**: __main__ "0.1"（__main__.yaml v0.1.0 時点）

DM（6件）:

- **指摘時 ref_version**: noderecord型 "0.2"（noderecord型.yaml v0.2.1 時点）
- **指摘時 ref_version**: edgerecord型 "0.1"（edgerecord型.yaml v0.1.0 時点）
- **指摘時 ref_version**: violationrecord型 "0.3"（violationrecord型.yaml v0.3.0 時点）
- **指摘時 ref_version**: configslice型群 "0.1"（configslice型群.yaml v0.1.0 時点）
- **指摘時 ref_version**: coveragereport型 "0.1"（coveragereport型.yaml v0.1.0 時点）
- **指摘時 ref_version**: inspectionviews型群 "0.2"（inspectionviews型群.yaml v0.2.0 時点）

PORT（1件）／PRS（1件）:

- **指摘時 ref_version**: filesystemport "0.1"（filesystemport.yaml v0.1.0 時点）
- **指摘時 ref_version**: tmp-草案ファイル書き出し "0.1"（tmp-草案ファイル書き出し.yaml v0.1.0 時点）

## 選択肢

① **担体宣言のみ差し替え（名前合わせ）**: 26件の本文 `**パス**` を `dsv2/*.py` / `doc-system-v2/validate.py` の実ファイルへ書き換え、設計の分割（MOD 18分割・DM 6型・PORT 1）はそのまま維持する。
  - 利点: 変更量が小さく、SRC 著作の物理的ブロックは即座に解ける。
  - 欠点: 設計 MOD 18件と実装モジュール12本は1対1に対応しない（`parser`/`collector`/`filter` 等の責務境界が `dsv2/meta.py`・`query.py` に混在）ため、パスだけ合わせると「責務分割の嘘」が残り、次の乖離を再生産する。DM/PORT は宣言する型自体が実装に無いのでパス書き換えでは解決しない。

② **設計を実装の分割に合わせて再編**: 設計 MOD 集合を `dsv2/{cli,meta,query,nodeyaml,viewer,rename,reverse,gitutil,yamledit,dashboard}` ＋ `doc-system-v2/{validate,slugify}` の実分割へ対応付け直し、対応の付かない MOD は統合・削除（消さず post-mvp/廃止印で残す＝PR8）。DM は dict ベース実装の事実に合わせて型定義を再定義するか、DM の位置づけを「論理データ型」に限定する。PORT は `pathlib` 直呼びの事実に合わせて再定義または廃止印を付ける。
  - 利点: 設計が稼働実装の実体を記述するようになり、以後の SRC 著作・drift 検査が意味を持つ。
  - 欠点: 26件＋依存辺の広範な改訂となり、作業量が大きい。DM/PORT の廃止判断は設計思想（Ports & Adapters 採用可否）に踏み込む。

③ **実装を設計に合わせて作り直す**: `dsv2/` を `spec_inspector/` の分割へ再構成し、DM/PORT の型・Protocol を実装する。
  - 利点: 既存の設計記述をそのまま正とでき、レイヤ分離（domain / ports / adapters）が実装に入る。
  - 欠点: 稼働中でテスト済みの資産（`tests/unit/test_dsv2_*.py` 群）を破壊的に再構成する。#160 のスコープ（設計実装の整合を取る）に対して代償が過大で、価値経路を長期間止める（PR6）。

④ **担体宣言を設計ノードから外し SRC ノードへ一元化**: MOD/DM/PORT/PRS 本文からファイルパス宣言を撤去し、担体の事実は SRC ノード（`source.file` / `qualname` / `kind`）だけが持つ。設計ノードは論理設計（責務・I/F・依存方向）に専念する。
  - 利点: 担体情報の二重管理が消え、パスの陳腐化が構造的に起こらなくなる（機械検査は SRC ノードの `_validate_identifier_ref()` が担う）。
  - 欠点: ④単独では「設計の分割と実装の分割が違う」という本質は解消せず、SRC ノードを張る先の MOD が実体と対応しないままになる。

## 推奨

**②を基軸に、担体表現の方針として④を組み合わせる。**

根拠:

- 実装（dsv2）は稼働・テスト済みで、doc-system-v2 の運用（index / query / reverse / validate）を現に支えている。③は価値経路を止める代償が最も大きく、#160 の目的（整合を取る）に対して手段が過大。
- ①は SRC 著作のブロックを外す最短路だが、責務境界の不一致を温存するため同種の乖離が再発する。DM/PORT は型そのものが実装に無く、①では解決しない。
- ②の実施順として、まず **設計 MOD ↔ 実装モジュールの対応表**（1対1／1対多／対応なし の3分類）を作り、対応なしを「未実装として残す（post-mvp 印）」「設計変更として統廃合」「設計外実装として C2 側で新規著作」に振り分ける。この対応表が #160 の作業単位そのものになる。
- ④は②の副産物として同時に入れる。パス宣言を設計ノードに残す限り、実装リファクタのたびに26件の本文が陳腐化する（本 FND がまさにその発現）。担体は SRC ノードに一元化し、設計ノードは責務と I/F だけを持つのが二重管理回避（PR2 の「機械判定と運用ルールを混ぜない」に沿う）。
- DM/PORT の扱い（dataclass を導入するか、dict 実装を正として DM を論理型に留めるか）は設計思想の判断を含むため、対応表作成後に DD として記録して前進させる（設計フェーズは暫定決定で前進）。

## 対応状況

open（`scheduled: "sprint-1"`・#160 スコープ内で実施）。実施スプリントの変更（繰り越し）はオーナー判断を要する。

## 接続規則変更の伝播チェック

本 FND の処置は `doc-system-v2/config.yml` の `must_link_to` / `must_be_linked_from` / `src_symbol_eligibility` の**変更を含まない**（設計ノード本文の担体宣言と設計分割の是正のみ）。したがって author エージェント・スキル・接続マトリクス・ドキュメント一覧への伝播は不要と判断した。ただし②実施の過程で MOD/DM/PORT の型集合を再編し、その結果として接続規則の変更が必要になった場合は、その時点で伝播チェック（`docs/doc-system/03-connection-matrix.md`・`01-document-items.md`・`design-author` 等）を実施すること。
