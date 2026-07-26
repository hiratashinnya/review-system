**深刻度**: WARNING（`activate_stage: implementation` のため現 `current_stage: design` では未発火＝latent。live ERROR は 0 件だが、#160 で CFG 向け SRC の著作に着手した時点で機械検証が空洞化する）

**対応 Issue**: #256（必須辺検証ルールの見直し・修正 ④ implementation 段 src 系規則の対称化・担体/粒度適格性）

**内容（1アサーション）**: `must_be_linked_from` の `{ node: cfg, source: [src] }` は、`src_symbol_eligibility: cfg: [file]` によって **ファイル単位の SRC** で充足される規則になっている。一方これを受ける CFG ノードは **`doc-system-v2/config.yml` のキー単位**で著作されており、規則が要求する実装担体の粒度（file）とノードの粒度（key）が一致しない。結果として「どの CFG がどの実装実体に対応するか」を機械判定できない。

**観測事実**:
- 規則（`must_be_linked_from`）: `{ node: cfg, source: [src], activate_stage: implementation, severity: error }`（DD-9 が追加した設計→実装の下流連続性 7 型のうちの 1 型）
- 適格性（`src_symbol_eligibility`・DD-10）: `cfg: [file]`。判定は `dsv2/query.py` の `_src_kind_ok()` が `node['source']['kind']` を許容 list と照合する。
- CFG 14 件はいずれも `doc-system-v2/config.yml` の**キー単位**ノード:
  `always_error` / `condition_vocab` / `config.yaml-設定インスタンス` / `coverage_rules` / `current_phase` / `current_stage` / `decision_spine` / `fnd_lifecycle` / `must_be_linked_from` / `must_link_to` / `phases` / `rule_activation` / `stages` / `trace_scope`
- `doc-system-v2/validate.py` の `_python_qualnames()`（L438）は `ast.parse` を用いる **Python AST 専用**であり、`_validate_identifier_ref()`（L456）も `ref_path.suffix == ".py"` のときだけ qualname 実在・kind 一致を検査する。**YAML キー単位の qualname を検証する機構は存在しない**。
- 併発観測（同一の粒度問題の傍証）: `config.yml` のキー `src_symbol_eligibility` **自体に対応する CFG ノードが存在しない**（上記 14 件に含まれない）。キー単位で CFG を著作する運用が現に採られている一方で、その被覆が全キーに及んでいない。
- 既存の保留: PEND `非-python-担体-prompt-cfg-の内容が当該資産である意味判定の完全機械化`（sprint-1 の file 適格性は「存在＋正規パス規約一致」まで。内容が当該資産であることの意味判定は保留）。

**帰結**:
1. CFG 14 件に SRC を著作すると、**14 件すべてが同一ファイル `doc-system-v2/config.yml` を `source.file` に持つ**。file 単位の適格性判定では 14 本の SRC が互いに区別されず、`X←src` のカウントは「同じ 1 ファイルを 14 回指す」ことで充足される。
2. `.yml` は `_validate_identifier_ref()` の Python 分岐に入らないため `source.qualname` は**検査されない**。誤った qualname・空 qualname でも ERROR にならず、誤充足（DD-10 が `mod: [module]` で排除しようとしたのと同種の問題）が CFG では機械的に防げない。
3. PEND-b が保留した「非 Python 担体の内容が当該資産である意味判定」は、cfg については **file 全体の意味判定ではなく該当キーの存否判定**に還元できる可能性があるが、現行の file 単位適格性ではその還元が使えない。

**選択肢**:
1. **YAML キーパス単位の qualname 検証機構を新設する** — `src_symbol_eligibility: cfg` に `key`（仮称）を許容し、`source.qualname` に YAML のキーパス（例 `must_be_linked_from`・ネストは `a.b`）を書かせる。`validate.py` に `_python_qualnames()` と対をなす YAML キーパス解決器を追加し、`.yml`/`.yaml` の `source.file` に対して qualname 実在を ERROR で検証する。既存 14 件のキー単位粒度を保ったまま 1 CFG = 1 キーの対応が機械判定になる。
2. **file 単位のまま許容し、同一ファイル共有を仕様として明記する** — `cfg: [file]` を維持し、「複数 CFG が同一 config ファイルを `source.file` に共有してよい」ことを `接続ルールスキーマ` と `must_be_linked_from` 本文に明記する。実装コストゼロだが、キー単位の対応関係は機械検証されず PR2 の「機械判定」側から運用ルール側へ落ちる（PEND-b の範囲が cfg 分だけ恒久化する）。
3. **CFG ノードの粒度をファイル単位に集約する** — キー単位 CFG 14 件を config ファイル単位の CFG へ統合し、規則側の file 粒度に合わせる。粒度は一致するが、既存 14 件が持つ被参照辺（SCM・SPEC 等からのトレース）を失い、PR1（もので分ける）・PR8（消さない）に反する。
4. **cfg を `X←src` の対象 7 型から外す** — DD-9 の 7 型から cfg を除外し、config の実現保証を別手段（例: `config.yaml-設定インスタンス` 1 件のみに SRC を要求）に委ねる。ERROR の発火自体を止められるが、設計→実装の下流連続性（PR6）を cfg については放棄する。

**推奨**: **選択肢①（YAML キーパス単位の qualname 検証機構を新設）**。根拠は 3 点。
- 既存 CFG 14 件の粒度は「config の 1 キー＝1 設定責務」であり PR1（もので分ける）に沿う。規則側を粒度に合わせる方が、ノード側を規則の都合で潰す③より整合が取れる。
- YAML キーパスの存否は決定論的に判定でき、PR2 の「機械判定」側に置ける。②④はいずれも機械判定を運用ルールへ降格させる。
- キー存否判定は PEND-b が保留した「内容が当該資産である意味判定」の cfg 部分を実質的に満たすため、保留範囲を prompt に絞り込める。

**副次論点（同一決定で併せて処置すべき事項）**: `src_symbol_eligibility` キーに対応する CFG ノードの欠落。①を採る場合、キーパス被覆の網羅性が前提になるため、当該 CFG ノードの著作要否を同じ決定で確定させる（本 FND のアサーション本体ではないため、処置は決定側に委ねる）。

**指摘時 ref_version**: must_be_linked_from "0.1"（must_be_linked_from.yaml v0.1.1 時点）

**接続規則変更の伝播チェック**: 本 FND は**起票時点では `doc-system-v2/config.yml` の接続規則を変更していない**（指摘と選択肢提示のみ）。したがって著作資産への同期は不要。ただし選択肢①③④のいずれかが決定された場合は `src_symbol_eligibility`／`must_be_linked_from` の変更となるため、決定側（DD）で以下への伝播を実施すること: `docs/doc-system/03-connection-matrix.md`（接続要否マトリクス）・`docs/doc-system/01-document-items.md`（上流参照列）・`.claude/agents/design-author.md` および `.github/agents/design-author.agent.md`（CFG の必須辺記述）・`doc-system-v2/schema/sidecar.schema.json`（①では `source.kind` の許容値追加）。なお **SRC 型を著作する専任エージェントは伝播対象表に存在しない**ため、SRC 著作規約（`source.file`/`qualname`/`kind` の書き方）の伝播先が未定である点を決定時に確認する必要がある。

**実施時期**: `scheduled: "sprint-1"`（起票時点＝current_phase）。実施 sprint の繰り越しは独断で行わずオーナー判断に委ねる。
