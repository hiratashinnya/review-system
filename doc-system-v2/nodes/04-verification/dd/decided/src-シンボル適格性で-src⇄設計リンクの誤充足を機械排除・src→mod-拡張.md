**status: decided**（2026-07-21 オーナー確定・本セッションの AskUserQuestion で全論点確定）

**論点**: SRC（実ファイル/識別子）と設計層ノード（MOD/DM/PORT/ORC 等）のリンク充足を、設計種別ごとに「張ってよいシンボル種別（source.kind）」で機械判定し、種別の食い違うシンボルによる誤充足（例: 関数シンボルで module 単位の MOD 辺を満たす）を排除するか。あわせて、DD-9 で `mod←src`（backward）を導入した以上、forward `src→[...]` に mod を含めないと module 実体の SRC が存在できず `mod←src` が恒常的に不充足になるため、forward target への mod 追加が必要になる。

**選択肢**:
- **A（現状維持・種別非照合）**: `src→[dm,port,orc]` のまま、辺の有無だけでリンク充足を判定する。トレードオフ＝実装は単純だが、任意の source.kind で任意の設計種別辺を満たせてしまい、モジュール実体を関数シンボルで代替する等の誤充足を機械的に排除できない。また mod が forward target に無いため DD-9 の `mod←src` が満たせない。
- **B（種別照合＋src→mod 拡張・採用）**: forward を `src→[mod,dm,port,orc]` に拡張し、設計種別×許容 source.kind のマップ（`src_symbol_eligibility`）で有効カウントを絞る。トレードオフ＝config・施行器（#163）に照合ロジックを要するが、誤充足を機械排除でき、DD-9 の `mod←src` と対称になる。

**推奨/根拠**: **B**。
- MOD はモジュール実体（cli.py 等）の自然な realizes 先であり、`src→mod` を許容しないと実装の大半（dsv2/ の 18 MOD 候補）が不自然な張り先を強いられる／SRC 化を諦めることになる（Q「SRC の必須辺が MOD を対象外…」の推奨①と一致）。
- 種別照合を入れないと「辺が在る＝充足」の緩い判定になり、module 単位の対応を関数シンボルで満たす等の誤充足を止められない。source.kind による有効カウント絞り込みで機械的に閉じる。

**決定（config 反映済み・inert／施行は #163）**:
1. `must_link_to: src→[mod,dm,port,orc]`（mod 追加・DD-9 の `mod←src` と対称）。
2. `src_symbol_eligibility` マップ: `mod=[module]` / `dm=[class]` / `port=[class]` / `orc=[function]` / `prs=[class,function]` / `prompt=[file]` / `cfg=[file]`。施行器（#163）は `src→X`・`X←src` のカウント時に SRC の `source.kind` を照合し、適格 kind のみ有効カウントする。
3. 論点1（sprint-1 スコープ）＝ kind 一致で確定（DM/PORT の `class` 重複は許容）。`class` 適格性の厳密化（Protocol/dataclass 判定）は **PEND-a** へ切り出す。
4. 論点2＝ file 適格性は「存在＋正規パス規約一致」（skill/agent は `.claude/skills/<name>/SKILL.md` 等の固定パス）まで機械判定する。中身が当該資産である意味判定の完全機械化は **PEND-b** へ切り出す。
5. `source.kind` 語彙を `{module, class, function, method, file}` へ拡張するのは施行器（#163・Phase B）実装で行う。

**影響範囲**（本 DD の在グラフ反映＝T2/T3→reconciliation 完了。反映後は義務辺 `DD→X` を `X→DD` に置換済み）:
- `doc-system-v2/config.yml`（out-of-graph・版なし）: **反映済み**（`must_link_to: src→[mod,dm,port,orc]`／`src_symbol_eligibility` マップ追加）。施行は #163 のため現状 inert。
- `doc-system-v2/nodes/05-design/scm/接続ルールスキーマ`（在グラフ）: `src_symbol_eligibility`（設計種別→許容 src.kind）のスキーマ記述と source.kind 語彙拡張の注記を追加済み（T2・z バンプ・backward 辺 `→DD-10` 付与済み）。
- `doc-system-v2/nodes/02-what/spec/src-に-dm-port-orc-への必須辺欠如-rule-006`（在グラフ）: forward target への mod 追加（`src→[mod,dm,port,orc]`・適格性 `src.kind=module` 条件付き）を本文追記済み（T3・z バンプ・backward 辺 `→DD-10` 付与済み・title/slug/scheduled/labels 不変）。
- Q「SRC の必須辺が MOD を対象外とし実装担体の自然な張り先が無い」: 本 DD で拡張①が確定したため **decided** へ移行済み（Q→DD 参照辺付与・git mv 実施済み）。

**接続規則変更の伝播チェック（FND-99 パターン防止）**: 本決定は config.yml の `must_link_to`（src target 拡張）と `src_symbol_eligibility` 追加を含む接続規則変更のため、機械判定の正本（config.yml）だけでなく人間/LLM 向け著作資産にも同期が要る。変更型＝SRC。確認結果:
- `doc-system-v2/config.yml`: 反映済み（機械正本）。
- SCM `接続ルールスキーマ`／SPEC `src-に-dm-port-orc…`: 本バッチ T2／T3 で同期済み（backward 辺で追跡）。
- **out-of-graph 著作資産＝本 DD-10 の PR 内で同期済み**（未同期のまま申し送らない・FND-99 型ドリフトを本 PR で回避）:
  - `docs/doc-system/03-connection-matrix.md`: mermaid に `SRC --> MOD` を追加し、§10 に src_symbol_eligibility（設計種別×許容 src.kind・種別照合で誤充足排除）の注記を追記済み。
  - `docs/doc-system/01-document-items.md`: SRC の直接先に MOD を追記し、src_symbol_eligibility による適格性（`src.kind` 照合で有効カウントを絞る）の注記を追記済み。
- **同期不要（SRC の張り先記述を持たない・grep 確認済み）**: 以下は SRC の `must_link_to`／適格性を表現する記述を含まないため、本規則変更の伝播対象にならない——
  - `.claude/agents/design-author.md`／`.github/agents/design-author.agent.md`: SRC の張り先・適格性を規定する記述なし。
  - `.claude/skills/architecture-design/SKILL.md`: `must_link_to` 表に SRC 行なし。
  以上により、SRC 接続規則を人間/LLM 向けに表現する out-of-graph 資産はすべて本 PR で config.yml と整合済みで、旧ルール（`src→[dm,port,orc]`・mod 欠落・種別適格性なし）とのドリフトは残っていない。

**スケジュール整合の申し送り（要オーナー判断・独断で変更しない）**: SRC forward 規則を規定する SPEC `src-に-dm-port-orc-への必須辺欠如-rule-006` は現状 `scheduled: sprint-2 / labels: post-mvp` である一方、DD-9 の backward `←src` 規則群および本 DD-10 は `sprint-1` である。forward（sprint-2/post-mvp）と backward/DD-10（sprint-1）の**実施時期が不一致**のまま残る。この不一致の是正（forward SPEC を sprint-1 へ前倒すか、backward/DD を sprint-2 に合わせるか、config 施行 #163 の実施時期）は**オーナー判断**であり、本 DD では SPEC の title/slug/scheduled/labels を独断変更しない（T3 も本文追記のみでスケジュール不変）。**実施時期はオーナー判断**として申し送る。

**覆る場合の影響範囲**: A（種別非照合・mod 非拡張）へ戻す場合、config.yml の `must_link_to` src target から mod を除去し `src_symbol_eligibility` を撤回、SCM `接続ルールスキーマ`・SPEC の追記を revert、DD-9 の `mod←src` も併せて見直し（module-SRC が存在できなくなるため）、PEND-a/PEND-b の前提（本適格性の存在）も失効する。影響は config・SCM・SPEC・DD-9・PEND-a/b と施行器 #163 に及ぶ。
