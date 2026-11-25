# Issue #513 — 1回deny＋強いSTOP指示

目的は、AIが工程停止を見落とす誤操作を低コストで減らすこと。解除まで全denyする強制機構ではなく、既存の権限・mergeゲートを緩和しない。1回denyは持続的なfail-closeの保証ではなく、Issue #513の旧全deny契約と同一の保証水準を主張しない。

## 動作

Claude PostToolUseでKarteのingest-review / ingest-reviewer / append / close-attempt / decide / statusの**成功した結果に含まれるIssue番号**を検査し、Karteの既存状態からSTOP理由を取得する。Bashのstdout・文字列結果、MCPのcontentテキスト配列、status --json、decideのfinding IDを扱い、エラー結果・不一致・複数Issue混在は判定不能としてスキップする。共有active.jsonだけでは対象Issueを推測しない。

STOPではAIへ追加コンテキストで停止指示を届け、同じセッションの次のツール呼び出しをPreToolUse(*)で1回denyする。2回目以降の許可をオーナー承認と扱ってはならない。

- 同じIssueの同じSTOP理由は再armしない。当該Issue自身が正常復帰した後の再発、または別の理由のSTOPは別イベントとして再びarmし、1回deny する。
- Karteの状態の読取と記録の更新は同じロックの中で行い、並列のPostToolUseで古い読取が新しい記録を上書きしない。
- 状態はセッションIDをハッシュしたローカル`tmp/_karte/stop-once/*.json`に置く。別セッションへは影響しない。記録するのは理由・拒否数・次のツール名（最大8件、引数は保存しない）。
- `state.py`の`DENIALS_PER_EVENT`は拒否回数の調整点（現行は1）。

## 仕様として維持する挙動（オーナー判断・2026-11-24）

次の挙動は仕様として維持する。実機検証で確認したのはAskUserQuestionの通過とToolSearchが1回分を使うことで、todo系ツールの通過とロックの保持は単体テストでの確認のみ。

- **AskUserQuestionは通す。** オーナーへ判断を仰ぐ正しい次手のため、denyせず、そのイベントの拒否を使い切ったものとする。
- **todo系ツール（TodoWrite/TaskCreate/TaskUpdate/TaskList/TaskGet）は通すが、拒否の権利は使い切らない。** 通過後の不適切なツールは1回denyされる。単体テスト`test_todo_tools_pass_and_keep_the_denial`で確認している。
- **ToolSearchは1回分を消費する。** todo系ツールは使用前にToolSearchでの読込が必要で、STOP武装後はそのToolSearchが先にdenyされ1回分を消費する。todo更新は不要な操作なので、これで問題ない。
- **denyはIssueを区別せずセッション単位で働く。** STOPは最後にarmされたIssueについて保持され、そのセッション内では別Issueの最初の操作も1回denyされる。同一セッションで複数Issueを扱うこと自体が不適切であり、別Issueの操作が止まるのはその是正になる。

## 実機検証の結果

PR #862のコメント（[#862-VERIFY-1]・[#862-VERIFY-2]・[#862-ASKQ-RESULT-1]）に記録。次を実測で確認した。

- STOP後の次のツール呼び出しが1回denyされる。同じ理由では再denyされない。
- 別の理由、または解消後の再発では再denyされる。
- 別セッションには漏れない。誤停止は0件。
- AskUserQuestionは通過する。
- hook障害時はstderrへ記録して継続する（fail-open）。状態JSONの構造不正、モジュールの読み込みと引数取得の失敗を含む全ての例外が対象で、終了コードは0。起動役の`.claude/hooks/karte-stop-once.sh`も、Pythonの起動失敗（非0終了）をstderrへ記録して終了コード0で継続する。フックが標準出力へ出した拒否・注入のJSONはそのまま通す。記録の検証は`digest`・`denied`（0以上の整数）・`followup_tools`・`issue`（整数）・`reasons`（コードと項目リストの並び）に及び、欠落・型違いは不正な記録として扱い、拒否回数は増やさない。記録ファイル（`tmp/_karte/stop-once/`の状態ファイル）はこのプログラムが書いたものとみなす。他の者が書き換えた場合への検証（型の検査など）は最善努力にとどめ、キーと記録内の`issue`の一致のような、書き換えへの網羅的な検証はしない。
- 並列に発行されたツール呼び出しはdenyをすり抜けうる。

## 試行指標

STOP後に正しくオーナー判断を仰いだ件数、警告を無視して作業を続行した件数、誤停止数。`followup_tools`は行動の手掛かりであり、単独では違反と断定しない。

## 捕捉範囲外

次は捕捉しない。結果にIssue番号がないCLI、reviewer wrapper内での取り込み、自由文のfixer STOP、Codex実行者、Hosted tool、別プロセスでの編集、並列ツール、新セッション開始時に既に存在するSTOP（自動検出しない）。hook障害時は継続するため、機械的fail-close保証にはならない。また、ツールに渡された文字列にコマンド名が含まれ、その応答にKarteの結果の見出しもあるとき、実際にKarteを実行していなくても記録しうる（オーナー判断でこのPRでは直さない。影響は1回の拒否と1回の再実行）。

実機で警告の無視が観測されたら、同じイベントのdeny回数を段階的に増やし、なお継続される操作だけに限定した持続ゲートを検討する。
