# pr-reviewer — 回復手順（非規範）

PR diff、checks、レビュー履歴を取得できない場合は clean や mergeable と判定せず STOP とする。finding の対象 commit と base が不明なら、既存 finding ID を再利用する判断も保留する。

レビュー投稿や merge の権限エラーは、権限を迂回せずエラー全文を主文脈へ返す。レビュー本文が途中で失敗した場合は重複コメントを推測で投稿せず、GitHub 上の既存コメントを確認してから再試行する。
