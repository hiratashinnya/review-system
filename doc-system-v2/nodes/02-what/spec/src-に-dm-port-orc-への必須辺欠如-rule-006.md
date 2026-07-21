**前提条件**: 型が SRC のノードが存在する（implementation ステージが activate 済み）
**入力/トリガ**: SRC が DM・PORT・ORC のいずれにも依存辺を張っていない（config `must_link_to: SRC→[DM,PORT,ORC]`〔OR ターゲット〕・severity error）
**期待動作**: RULE-006 を ERROR で報告する。これは `@id` realizes 照合（SPEC-28-1/28-2）による設計漏れ・紐づけ漏れ検出とは別に、config の必須辺 `SRC→[DM,PORT,ORC]` の欠如を構造点検として検出するものである。
**例**: `SRC-4` が DM・PORT・ORC のいずれへも辺を持たない（3 ターゲットすべてに未接続）→ `ERROR|...|RULE-006|SRC-4|...`

**DD-10 反映（src→mod 拡張・v0.1.1 追記）**: DD-10（SRC シンボル適格性）で `must_link_to` の SRC forward ターゲットに **mod** を追加し、`src→[mod,dm,port,orc]` へ拡張した（config.yml 反映済み・施行は #163）。理由＝DD-9 で backward `mod←src` を導入したため、forward 側に mod を含めないと module-SRC が張り先を持てず `mod←src` が構造上不充足になる（forward/backward の対称性を保つ）。ただし mod ターゲットの充足は無条件ではなく、`src_symbol_eligibility`（mod=[module]）により **SRC の source.kind=module のときのみ有効カウント**する（関数流用等での誤充足を機械排除）。dm/port/orc の適格性は dm=[class] / port=[class] / orc=[function]。source.kind 語彙の {module, file 等} への拡張は施行器（#163・Phase B）で実装する。
**スケジュール整合の申し送り（要オーナー判断）**: 本 SPEC は現状 `scheduled: sprint-2 / labels: post-mvp` である一方、DD-9 の backward `←src` 規則群および DD-10 は sprint-1 である。forward（本 SPEC）と backward のスケジュールが不一致となるが、**実施時期の変更はオーナー判断領域のため本追記では slug/title/scheduled/labels を変更しない**（slug は connection-matrix §10 索引・他所から参照される安定 ID）。
