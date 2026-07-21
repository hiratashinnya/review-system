**status: open**

**論点（1文）**: config.yml の `must_link_to: { node: src, target: [dm, port, orc] }` は SRC の張り先から **MOD を除外**しているが、設計層で Python モジュールの自然な対応先は MOD（18 ノード・最多）であり、#160 で dsv2/ の Python 実装を SRC 化する際に大半（cli.py・query.py・meta.py 等）が MOD 対応なのに辺を張れず、必須辺 `SRC→[dm,port,orc]` を満たせない／不自然な張り先を強いられる。SRC の張り先に MOD を含めるべきか。

**背景（Read で確認）**: config.yml の implementation 段 `- { node: src, target: [dm, port, orc], activate_stage: implementation, severity: error, reason: "SRCは設計ノードを実現（いずれか1つ以上）" }`。設計層で MOD は 18 ノードと最多だが、SRC の張り先は DM(6)/PORT(1)/ORC(2)＝計 9 ノードに限られる。#160 で実装を SRC 化する際、モジュール実体（cli.py 等）の自然対応先である MOD へ辺を張れないのは仕様の穴の可能性。

**選択肢（排他・トレードオフ）**:

- **① `src → [mod, dm, port, orc]` に拡張（推奨）**: Python モジュール＝MOD の自然対応を許容する。SRC↔設計層の対応が素直になり、既存の他辺（dm/port/orc）を壊さず張り先を広げるのみ。トレードオフ＝config の必須辺（OR ターゲット）を1型拡張するだけで済み、実装の大半を占めるモジュール実体に自然な realizes 先を与えられる。
- **② 現状維持（dm/port/orc のみ）**: MOD は P/D 経由でのみ実装に到達する設計思想（`mod→[p,d]`）を維持する。トレードオフ＝設計思想は一貫するが、SRC の張り先が痩せ、モジュール実体の SRC が dm/port/orc いずれかへ不自然に張るか、SRC 化を諦めることになる。
- **③ SRC を MOD 単位で著作し `src→mod` のみ許可（他は禁止）**: 実装＝モジュール実現に一本化する。トレードオフ＝realizes の対象が MOD に単純化されるが、既存の `src→[dm,port,orc]` を破棄する破壊的変更となり、型実装（DM）・ポート実装（PORT）・オーケストレーション（ORC）を直接 SRC で実現する経路を失う。

**推奨**: **①**。MOD は「プロセス実装またはデータ型実現（D）」の実体であり、SRC（実ファイル/識別子）が最も自然に対応するのは MOD である。①は既存の他辺を壊さず張り先を広げるのみで、実装の大半を占めるモジュール実体に自然な realizes 先を与える。② は SRC の張り先が痩せて不自然な紐づけを強いる、③ は既存経路を破棄する破壊的変更のため非推奨。ただし config 変更＝機械判定の正本の変更であり、**DD で記録してオーナー確定後に反映**する（本 Q は確定ではなく推奨提示に留める）。

**依存**: 本 Q の決定は #160（SRC 著作）の前提。**決定前に SRC を著作しない**（張り先規則が未確定のまま SRC を著作すると再著作が発生する）。

**指摘時 ref_version**: src-に-dm-port-orc-への必須辺欠如-rule-006 "0.1"（`src-に-dm-port-orc-への必須辺欠如-rule-006.yaml` v0.1.0 時点。本 Q の影響要素＝SRC→[dm,port,orc] 必須辺欠如を規定する在グラフ SPEC）。config.yml は out-of-graph（版なし・DD-8/FND-104）のため唯一の根拠にしない。
