---
id: TD-issue-start-452-f29-r25-4592fc0
version: 1
condition: normal
result: PASS
log_ref: tests/logs/TD-issue-start-452-f29-r25-4592fc0.txt
---

# F-452-29 round 25 verification result

実装 `4592fc0` で、未閉じ・不一致 quote を EOF まで消費せず、opener
直後の局所 endpoint（必ず1文字以上進む）へ復帰する lexer に変更した。
malformed word 内の候補はその literal を分類し、word 後の whitespace/newline
以降は scanner が再走査するため、候補自体が quote 内にある場合と後続 plain
candidate の双方を fail-close できる。

- focused: 40 PASS
- related issue-start/control/supervisor/assets: 206 PASS、skip 11
- asset parity: 9 PASS
- full unittest discover: 1880 PASS、skip 9
- Claude Code: 未使用

F25–28 の balanced fragment matrix、directory prose、canonical facts/path
exact-one は回帰なく PASS。通常 prose に候補がない場合は許可し、複数
malformed fragment も停止する。

coverage は uv の既定 cache が read-only、専用 `/tmp` cache は pypi.org の
DNS 到達不可だったため未実行。FAIL TR として別記録し、coverage PASS へは
読み替えない。
