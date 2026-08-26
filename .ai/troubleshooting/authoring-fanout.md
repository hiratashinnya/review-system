# authoring-fanout — 回復手順（非規範）

この文書は、[`.ai/agents/authoring-fanout.md`](../agents/authoring-fanout.md) の STOP 条件に該当したときだけ参照する。本文の target_key、retry_of、batch_id の契約を変更する手順ではない。

## nonce 取得不能・キー衝突

末尾8桁が数字でない場合は nonce を空として旧形式へ戻し、同じ author の hand-off が既にないことを確認する。存在する場合は新規 target として上書きせず STOP する。前回失敗 target の再試行は `retry_of` を付け、対応する hand-off が存在することと parent/kind/index の形を確認する。成功済み target を再投入する場合は、対象をバッチから外すか、明示的に retry として扱う。

## hand-off 欠落・target 不一致

author の hand-off が無い、status が error、tmp の md/yaml 対が欠ける、または返された key が dispatch key と違う場合は validator を呼ばない。失敗 target の key と errors を主文脈へ返し、呼び出し元に対象 author の再起動を依頼する。別 target の hand-off を推測で読み替えない。

## ROLLBACK / blocked

validator の ROLLBACK は reconciliation へ進めず、errors をそのまま報告する。reconciliation の hand-off で parent が欠ける、または blocked の場合もバッチを成功扱いにせず、tmp と既存 corpus の状態を保持したまま主文脈へ打ち上げる。
