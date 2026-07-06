**status: open**

**論点（Issue #78 論点4）**: condition 語彙の再設計（論点1〜3 の決定）が、既存の coverage/整合ルールと齟齬しないか。具体的には `coverage_rules`（RULE-017/018）・RULE-019（TD↔SPEC condition 一致）・RULE-016（condition 必須・語彙外検査）が、再設計後の語彙と整合する範囲・改訂すべき範囲を確定する。本 Q は論点1〜3 の決定を受ける**整合連動の制約**であり、単独では決められない（論点1/2/3 の結論に従属する）。

**現状（再設計語彙が触れる検査ルール）**:
- **RULE-016**（SPEC「condition 属性なし・語彙外」v0.1.0・condition failure）: condition が config の condition_vocab 外なら ERROR。**vocab セットの列挙（論点2）と傘の扱い（論点1）に直接依存**。
- **RULE-017**（SPEC「FR の SPEC 群に normal condition なし」v0.1.0）: `coverage_rules.fr.required_conditions = [normal]` を参照し WARNING。
- **RULE-018**（SPEC「FR の SPEC 群に failure/error condition なし」v0.1.0）: `coverage_rules.fr.recommended_conditions = [failure, error]` を参照し WARNING。**論点3 で always_error 系を failure/error のどちらに寄せるかが、この推奨集合の意味に波及**。
- **RULE-019**（SPEC「TD の condition が verifies 先 SPEC と不一致」v0.1.0）: TD↔SPEC の condition 値一致を検査。**論点1（傘は condition 省略）・論点3（SPEC-6/7 の値変更）で TD 側の追随が要る**。
- `coverage_rules` は現在 `required_conditions=[normal]` / `recommended_conditions=[failure,error]` で、`empty`（論点2）・`boundary` は coverage 要件に**含まれない**。

**選択肢**:
- **A（lockstep 同期改訂）** — 論点1〜3 のいずれかが vocab セット・値割当・傘扱いを変えたら、同一 DD の処置で RULE-016/017/018/019 の SPEC と config（condition_vocab / coverage_rules）を同時改訂し、out-of-graph 著作資産（接続マトリクス・各 author・notation・test-strategy）へも伝播する（**FND-99 パターンの再発防止**）。トレードオフ＝改訂範囲が広く一度の作業量が大きい。
- **B（後追い改訂・語彙先行）** — 語彙（論点2）を先に確定し、coverage/整合ルールは次の作業で追随改訂する。トレードオフ＝config と検査 SPEC・author 資産が一時的に不整合になり、その間に旧ルールで誤った condition を再生産する危険（FND-99 が起きた原因そのもの）。
- **C（整合ルール自体も再設計に含める）** — 論点4 を単なる追随でなく、この機会に coverage_rules の妥当性（empty/boundary を coverage 要件に含めるか、recommended を必須化するか等）も見直す。トレードオフ＝スコープ拡大。論点1〜3 の決定が固まる前に coverage を動かすと手戻りが増える。

**推奨**: **A（lockstep 同期改訂）**。理由：(1) config.yml（condition_vocab / coverage_rules）は機械判定の正本だが、同じ規則を人間/LLM 向けに表す out-of-graph 著作資産（接続マトリクス・各 author・notation・test-strategy）にも同期しないと、次回著作時に旧ルールで誤った辺・condition を再生産する（**FND-99 の実例**）。したがって語彙変更は検査 SPEC・config・著作資産を一括で動かすのが安全。(2) B は不整合ウィンドウが FND-99 の温床になるため非推奨。(3) C（coverage 自体の見直し）は有用だが論点1〜3 が固まってからの別 Q が適切で、本 Q に混ぜるとスコープが膨らむ（CLAUDE.md「スコープ拡大禁止」）。**改訂範囲の確定はオーナー判断**。

**依存関係（決定順序）**: 本 Q は論点1（傘→RULE-016/019）・論点2（vocab→RULE-016/017/018）・論点3（always_error→RULE-018/019）の決定に従属する。**論点1〜3 を先に決め、その結論を受けて本 Q で「どの検査 SPEC・config・著作資産を同期改訂するか」を確定する**のが自然な順序。論点1〜3 がすべて現状維持（追認）なら、本 Q の改訂は不要と確定できる。

**接続規則変更を伴う場合の伝播先（A 採用時のチェックリスト・CLAUDE.md / verification-author 契約）**: config.yml の接続規則や検査語彙を変える DD には、以下への同期を処置に含める — 接続マトリクス（`docs/doc-system/03-connection-matrix.md`）・ドキュメント一覧（`01-document-items.md`）・spec-author・analysis-author・design-author・verification-author・test-strategy スキル・notation。差分が無い資産も「確認済み」と記録する。

**ブロッカー**: coverage/整合ルールの改訂範囲・実施時期は**オーナー判断**（**独断でのスプリント繰越は禁止**・`scheduled` 空で判断を仰ぐ）。論点1〜3 の決定後に本 Q を DD へ昇格。

**指摘時 ref_version**: condition 属性なし・語彙外（RULE-016）"0.1"／FR の SPEC 群に normal condition なし（RULE-017）"0.1"／FR の SPEC 群に failure/error condition なし（RULE-018）"0.1"／TD の condition が verifies 先 SPEC と不一致（RULE-019）"0.1"（各 SPEC サイドカー v0.1.0 時点）／FR の condition 網羅 "0.2"（同 SPEC サイドカー v0.2.0 時点）
