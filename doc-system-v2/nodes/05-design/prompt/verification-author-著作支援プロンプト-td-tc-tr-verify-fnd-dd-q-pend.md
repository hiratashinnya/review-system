検証層・意思決定ノード（TD / TC / TR / VERIFY / FND / DD / Q / PEND）の著作支援プロンプト。外部ファイル参照なしに type 値・id PREFIX・必須辺方向・追加属性・本文フォーマット・RULE チェックリストを内包する（SPEC-27 の実体＝`.claude/agents/verification-author.md`）。
**バージョン**: 1.0
**目的**: 指定された親ノード配下の検証・意思決定ノードを、type 値（自由記述不可）・id PREFIX（`TD-`/`TC-`/`TR-`/`VERIFY-`/`FND-`/`DD-`/`Q-`/`PEND-`）・必須依存辺方向（TD→SPEC・TC→TD・TR→TC・VERIFY→any・FND は状態で逆転・DD/Q/PEND→影響要素の義務辺）・追加属性（TD の condition＝SPEC と一致／TR の result・log_ref／FND の resolved）・RULE チェックリスト（RULE-016/019/020/021/001/002/022 とライフサイクル）を**プロンプト内に閉じて**提供する（SPEC-27-1〜5）。
**入力変数**: `parent_id`／`parent_body`／`sprint`／`context`／`error`。記載内容（I-9）＝各型本文＋メタ属性（TD＝condition、TR＝result/log_ref、FND＝resolved＋指摘時 ref_version の本文記録＝DD-3、DD/Q/PEND＝ライフサイクル状態を本文見出し/バッジに記載）。
**出力形式**: `tmp/<sprint>/<parent-id>.md` に子ノード群の Markdown を Write する＝tmp ノード草案（D-8）。本ファイルへは書かない。
**注意事項**: 辺は無名依存辺（kind/status なし・to は単数・ref_version 必須）。FND は状態で辺逆転（未解消＝forward `FND→対象`／resolved＝backward `対象→FND`＋forward 削除＋本文に指摘時 ref_version を凍結＝DD-3）。DD/Q/PEND の義務辺は反映後 `DD→X` を削除し `X→DD` に置換。接続規則変更を伴う DD/FND は対応 author/スキル/接続マトリクスへ同期（FND-99 パターン）。`scheduled: ""` 固定。`suppress` / `suppress_reason` は issue #118 で廃止済みのため出力しない。RULE-007 は always_error として常時 ERROR 発火する。
