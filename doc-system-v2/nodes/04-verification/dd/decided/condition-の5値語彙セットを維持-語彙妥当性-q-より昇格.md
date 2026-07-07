**status: decided**（2026-07-06 オーナー承認・選択肢A 採用）

> **辺の扱い**: 本 DD は decided だが、義務辺 `DD→X` は張らず `edges: []` とする。理由：本決定は**現状維持の追認**であり、in-graph／config.yml いずれにも反映すべき変更（未反映シグナル＝義務辺の対象）が存在しないため（vocab セット `normal / boundary / empty / failure / error` は不変）。被参照辺は昇格元 Q（`condition 5値語彙セットの妥当性 empty を boundary へ統合するか維持するか`）が処置側から `→<この DD の slug>` を張り返すことで確保され、RULE-005（完全孤立）は生じない。先例：DD-15〜DD-20 の Q 昇格 DD がいずれも `edges: []`。
> **指摘時 ref_version の記録（DD-3 制度）**: 本 DD は Q から昇格（DD であり FND でない）ため「指摘時 ref_version」の本文記録は不要（DD-16〜DD-20 と同扱い）。論点・現状の出所は昇格元 Q（指摘時 condition 属性なし・語彙外 SPEC "0.1"）である。

**論点**（condition 5値語彙セットの妥当性 empty を boundary へ統合するか維持するか より昇格・要約）: condition の5値セット `normal / boundary / empty / failure / error`（等価分割）は今も適切か。特に `empty`（空・ゼロ件・null）を `boundary` から独立させた経緯（FND-13・resolved）を踏まえ、独立を維持するか `boundary` へ統合（＝4値化）するか。

**現状**（Q で Read 確認済み）:
- `config.yml` の condition_vocab は `[normal, boundary, empty, failure, error]`。セマンティクスはコメント定義: normal=正常系 / boundary=境界値 / empty=空・ゼロ件・null / failure=仕様違反を正しく検出（sad-path）/ error=処理不能な異常入力（fail-close 対象）。
- `empty` は FND-13（v0.1.1・resolved）で追加された。指摘は「空集合・ゼロ件・null・未設定を表す独立クラスが無く、normal/boundary に混ぜると等価分割が崩れテスト設計の網羅穴になる」。in-graph アンカー SPEC-31（in-graph 0 件で RULE 評価を全スキップ）が `empty` を実使用し、SPEC-31 → FND-13 のバックリファレンス辺で紐づく（辺逆転完了済み）。
- したがって `empty` は既に実利用があり、単純削除はできない（削除には少なくとも SPEC-31 の condition 再割当が必要）。

**選択肢**（Q より要約・排他）:
- **選択肢A（5値維持・推奨）**: 現行セットを妥当と確定し変更しない。`empty` は FND-13 の根拠（空集合はゼロ件境界とは別の等価クラス。null/未設定/0件は境界値の「端」ではなく「集合そのものが空」で独立に扱うべき）で正当化される。トレードオフ＝5値の維持コスト（各 author・notation・テスト戦略が5値を列挙し続ける）。
- **選択肢B（empty を boundary へ統合し4値化）**: `empty` を廃し `boundary` に吸収、SPEC-31 等の empty 使用ノードを boundary へ再割当。トレードオフ＝FND-13 で解消した「空集合の網羅穴」が再発する懸念。FND-13 を意図的に覆す決定になるため覆す根拠が要る。
- **選択肢C（別軸で再編）**: 空集合が「正常なゼロ件」か「異常な欠落」かで意味が割れる点に着目し empty を用途で分割/再配置する。トレードオフ＝語彙が増える方向で複雑化し、等価分割の単純さを損なう。

**推奨**: 選択肢A（5値維持）。理由：(1) `empty` は FND-13 で「空集合＝境界とは別の等価クラス」という明確な根拠のもと追加され SPEC-31 で実利用がある意図的設計であり、覆すには FND-13 の根拠を否定する新たな根拠が必要だが現時点でそれは無い（CLAUDE.md「意図的設計の尊重」）。(2) B は解消済みの網羅穴を再発させるリスクがあり削減効果（5→4）に見合わない。(3) C は等価分割の単純さを損なう。

**決定**: **選択肢A を採用**（オーナー承認・2026-07-06）。condition の5値語彙セット `normal / boundary / empty / failure / error` を**そのまま維持**し、`empty` を `boundary` へ統合しない。5値の等価分割を追認する。

**根拠**:
- `empty` は FND-13（resolved）で「空集合＝境界とは別の等価クラス」という明確な根拠のもと追加され、SPEC-31 で実利用がある意図的設計であり、覆す新根拠がない（CLAUDE.md「意図的設計の尊重」）。
- 統合（選択肢B）すると FND-13 で解消済みの網羅穴が再発するリスクがある。
- 別軸再編（選択肢C）は等価分割の単純さを損なう。

**接続規則変更チェック（FND-99 パターン）**: 本 DD は **現状維持の追認**であり、`doc-system-v2/config.yml` の接続規則（`must_link_to` / `must_be_linked_from`）の追加・変更・削除を**含まない**。vocab セット自体も不変のため、接続マトリクス（`docs/doc-system/03-connection-matrix.md`）・ドキュメント一覧（`docs/doc-system/01-document-items.md`）・各 author エージェント／スキルへの規則伝播は**不要**（確認済み）。「変更なし」の確認自体を本チェックとして記録する。先例: DD-17/18/19/20 の同チェック（接続規則そのものに触れない変更は伝播不要）と同判定。

**影響範囲（A 採用時）**:

in-graph（今回 reconciliation で反映完了する対象）:
- 昇格元 Q（`condition 5値語彙セットの妥当性 empty を boundary へ統合するか維持するか`）を `q/open/` → `q/closed/` へ移動、`status: closed`（本 DD へ昇格）・`→<この DD の slug>`（ref_version "0.1"＝本 DD バッジ v0.1.0 の x.y）付与・MINOR バンプ v0.1.0→v0.2.0。

フォローアップ（本 PR では実装しない）:
- **無し**。本決定は現状維持の追認であり、vocab セットは不変のため `config.yml` の condition_vocab・coverage_rules（`fr.required_conditions` / `recommended_conditions`）・RULE-016（語彙外検査）・SPEC-31・各 author の語彙列挙のいずれにも変更は生じない（確認済み）。したがって先送りするフォローアップ実装事項は存在しない。

**覆る場合の影響範囲**: 選択肢B（empty を boundary へ統合し4値化）へ戻す場合、`config.yml` の condition_vocab から `empty` を除去、SPEC-31 等の empty 使用ノードを boundary へ再割当、RULE-016 の語彙集合・coverage_rules・各 author／notation／テスト戦略の語彙列挙を4値へ同期改訂し、FND-13（resolved）を再検討（意図的設計の逆転根拠を明示）する必要がある。影響は config.yml・SPEC-31・各 author 資産・FND-13 に及ぶ。
