# `.ai/feedback/` — オーナー判断の捕捉台帳（非活性・CLI 専用書込み）

オーナーが AI の推奨を曲げた判断を、一次情報のまま版管理下に蓄積する置き場（Issue #522）。
loader-facing asset ではない（`.ai/rationale/`・`.ai/troubleshooting/`・`.ai/schema/` と同じ
非活性レコード）。規範本文へ混入させず、PF tree へ複製しない。

| 種別 | 置き場 | id |
|---|---|---|
| 台帳エントリ | `ledger/FBK-<YYYYMMDD>-<slug>.toml` | `FBK-…` |
| 改訂案 | `queue/FBP-<YYYYMMDD>-<slug>.toml` | `FBP-…` |
| 週次棚卸し記録 | `triage/TRG-<YYYY>-W<NN>.toml` | `TRG-…` |

## 書込み経路は CLI だけ

人・エージェントによる直接の Write/Edit は `.claude/settings.json` の `permissions.deny`
（`Edit(/.ai/feedback/**)` / `Write(/.ai/feedback/**)`）で塞いである。下書きは版管理外の
`tmp/_feedback/` に自由に書き、`python3 -m feedback_ledger <verb> --from <draft>` が
検証・正規化して確定する。

```
python3 -m feedback_ledger new-entry --from tmp/_feedback/FBK-20260919-example.toml
python3 -m feedback_ledger check --canonical --require-base
python3 -m feedback_ledger status --now 2026-09-19
```

機械 lint の規則・設計判断・既知の限界は [`feedback_ledger/README.md`](../../feedback_ledger/README.md)。
形式契約は [`.ai/schema/feedback-ledger-v1.json`](../schema/feedback-ledger-v1.json) ほか2件。
