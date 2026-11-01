"""karte の判定を AI の要約を経ずにオーナーへ直送する通知フック（Issue #512）。

サブモジュール:
  * :mod:`karte_notify.trigger` — 通知の契機になる karte verb の実行を tool 呼び出しから検出する
    （検出対象 tool 名・コマンド抽出・トリガー検出・``--issue`` の抽出）。
  * :mod:`karte_notify.notify` — 通知要否の判定ロジック（純粋関数・既読スナップショットの
    パス解決・読み書き）。
  * :mod:`karte_notify.hook` — ``PostToolUse``（matcher ``Bash``）フックの実体
    （stdin JSON → ``karte status --json`` の起動 → ``systemMessage`` の出力）。

依存仕様: GitHub Issue #512。
"""
