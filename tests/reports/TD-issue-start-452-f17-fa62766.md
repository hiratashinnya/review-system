---
id: TD-issue-start-452-f17
version: 1
condition: normal
result: FAIL
log_ref: tests/logs/TD-issue-start-452-f17-fa62766.txt
---

# 目的

F-452-17の診断proposal→host Attempt登録→同一thread resume→host push→Result close→finalを、
model/API非呼出のfake runnerと実Git fixtureで検証する。TD-issue-start-452 version 6のP3境界を維持する。

# 前提

- registered worktree、中央karteにround 2のopen finding、host ledgerを用意する。
- inner runnerはJSONL identity/terminalを返し、中央karteはhost bridgeだけが更新する。
- commit-before-testを守り、bootstrap検証を正規transportの実運用成功と扱わない。

# 手順・期待結果

1. 初回診断turnはworkspace read-only・proposal directory writeだけを許すcommandを生成する。
   active probeの診断phaseもworkspace write拒否、proposal write成功、auth/network拒否を要求する。
2. host生成identityとdigestを含むproposalを返し、turn.completed/exit 0の後にAttemptを1件登録する。
   診断中のコード差分、別identity/finding/digest、path traversal、symlink/hardlink、未登録handoffは拒否する。
3. 登録前・atomic replace後のcrashを注入し、同一proposalのretryでAttemptが1件に収束する。
   stale karte/proposal・登録後の差替えを拒否し、fresh run・別threadでは再開しない。
4. 登録済みAttemptの同一threadをresumeし、診断一致のhandoffだけを成功として受け付ける。
5. add→commit→pushの後もpre_publishのままとし、host close後にだけfinal fixedを生成する。
   closeの引数はhost記録から導出し、innerによるAttempt番号・base・outcome上書きを許さない。
6. push後、close前後、completed後、final前後のcrashで重複push/Resultがなく同じfinalへ収束する。
   schema-valid final置換、中央Result tamper、close順序違反はfail-closeする。
7. 既存supervisor/launch/karteのunit regressionとfull unittestを実行する。
   主文脈でuv経由coverage HTMLを生成し、数値と生成物pathを記録する。

# TC

`tests/unit/test_codex_karte_bridge.py`、`test_codex_supervisor.py`、`test_codex_supervisor_shrink.py`、
karte既存unit。installed CLIのmodel-free probeは環境依存skipを区別して記録する。

## 実測

- TD version: 1
- 実装commit: fa62766
- prompt雛形版 / 基準content_hash: N/A（host transactionのmodel-free unit）
- 実行日: 2026-09-15 Asia/Tokyo
- command: `python3 -m unittest tests.unit.test_codex_karte_bridge`
- 結果: 12 tests、failure 1。fresh-run拒否testのfixtureが既存protected planを渡さず、意図したRESUME_REQUIREDより手前のIMMUTABLE_MISMATCHに到達した。
- 対処: 同じspec.protected_pathsを用いるようfixtureを修正する。拒否をPASSへ読み替えず失敗ログを保持する。
