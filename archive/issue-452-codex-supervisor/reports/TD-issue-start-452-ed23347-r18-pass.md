---
id: TD-issue-start-452
version: 6
condition: normal
result: PASS
log_ref: tests/logs/TD-issue-start-452-ed23347-r18-pass.txt
---

# 目的

Issue #452のF-452-13是正後、pure launch-intent testsがhost executableへ漏れず本来の
canonical-state/live-Git assertionへ到達し、production security境界とfull unitを退行させないことを確認する。

# 前提・手順・期待結果

`tests/designs/TD-issue-start-452.md` version 6を適用し、実装commit `ed23347`に対して対象2件、
launch-intent/launch-control関連、direct executable security境界、full unitを実行する。
pure testだけが決定的evidence seamを使い、direct security testsはmockせず、full unitが成功すること。

## 実測

- ヘッダ: TD version 6 / 実装commit `ed23347` / prompt template version `managed-entrypoints-v2` / criteria content hash N/A / 2026-09-11 JST / local host Python 3.12
- 対象2件: PASS（2 tests、skip 0）。host executableへの直アクセスsentinelは発火せず、child側の自己申告actor排除とcanonical workspaceへのlive-Git照会assertionが双方成功した。
- 関連focused: PASS（128 tests、skip 9）。skipはinstalled executableのoperational観測であり、成功証拠に数えない。
- direct security境界: PASS（8 tests、skip 0）。owner/mode、digest/version、group/NSS、actual trust pathの検査をmockしていない。
- full unit: PASS（1789 tests、skip 9、122.774秒）。
- ログ: `tests/logs/TD-issue-start-452-ed23347-r18-pass.txt`
- sandbox内初回fullの別2FAILは、`$HOME`配下watcher.logへの書込み拒否でparser入力が空になった環境制約。対象コードとの差分0とsandbox外単独/full PASSを確認し、F-452-13の失敗や成功証拠には混ぜていない。
- GitHub Actionsの最終判定は本commitをpush後の新規runで確認する。
