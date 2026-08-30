# verification-author — 設計経緯・判断記録（非規範）

> これは規範ではない。現行契約は [`.ai/agents/verification-author.md`](../agents/verification-author.md) にある。

FND の open/resolved はサイドカーの boolean ではなく path と辺方向で表す。resolved で元の forward 辺を残すと、未解消と解消済みを同時に表してしまうため、reverse 操作で処置対象から FND への backref へ切り替える方式を採用した（DD-16）。

reverse 後は辺が「FND→対象」から「対象→FND」へ変わり、指摘時に対象のどの版を参照したかを元の辺から読めなくなる。そのため、FND 起票時の `edges[].ref_version` は本文にも保存する（DD-3）。

DD/FND が config の接続規則を変える場合に author 資産まで確認するのは、機械判定の正本と LLM 向けの説明が分岐すると、次の著作で旧辺を再生成するためである。接続規則変更の伝播記録は現行契約では必須チェックとして残し、その背景はここに分離した。
