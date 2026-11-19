# Issue #513 — 1回deny＋強いSTOP指示（試行版）

目的は、AIが工程停止を見落とす誤操作を低コストで減らすこと。解除まで全denyする強制機構ではなく、既存の権限・mergeゲートを緩和しない。

Claude PostToolUseでKarteのingest-review / ingest-reviewer / append / close-attempt / statusの**成功した結果に含まれるIssue番号**を検査し、Karteの既存状態からSTOP理由を取得する。共有active.jsonだけでは対象Issueを推測しない。
STOPではAIへ追加コンテキストで停止指示を届け、同じセッションの次の不適切なツール呼び出しをPreToolUse(*)で1回denyする。AskUserQuestion/todoが次の操作ならdenyせず、そのイベントは消費済みとする。2回目以降の許可をオーナー承認と扱ってはならない。

同じSTOP理由は再armしない。新しい理由または正常復帰後の再発は別イベント。セッションIDをハッシュしたローカルtmp/_karte/stop-once/*.jsonへ、理由・拒否数・次のツール名（最大8件、引数は保存しない）を記録する。state.pyのDENIALS_PER_EVENTを変更すると再試験時の拒否回数を増やせる。

試行指標：STOP後に正しくオーナー判断を仰いだ件数、警告を無視して作業を続行した件数、誤停止数。followup_toolsは行動の手掛かりであり、単独では違反と断定しない。

制約：実機Claude hookを未検証。既存のSTOPを新セッション開始時に自動検出しない。結果にIssue番号がないCLI、wrapper内での取り込み、自由文fixer STOP、Codex実行者、Hosted tool、別プロセスでの編集や並列ツールを全て捕捉するわけではない。hook障害時はstderrへ記録して継続するため、機械的fail-close保証にはならない。

実機で無視が観測されたら同じイベントのdeny回数を段階的に増やし、なお継続される操作だけに限定した持続ゲートを検討する。Issue #513の旧全deny契約と同一の保証水準を主張しない。
