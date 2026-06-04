---
doc_type: code
scope: project:checkout
extends: team:frontend
version: 1
# team:frontend（さらに org を継承）からの差分だけを書く。
# 「厳しく/緩め」は合成済みの「直近の親（＝team の実効値）」を基準に測る。追加・厳しくは常に自由。
rules:
  # ① team が warning に緩めた naming を、決済画面なので error に戻す。
  #    team(warning) 基準で「厳しく」＝常に自由。
  #    （org→project で見ると元の error と同じだが、その比較は使わない。基準は直近の親）
  - id: naming-convention
    severity: error

  # ② missing-test を error に締める。team の無効化は org 権威で拒否済みなので、
  #    missing-test は org 既定（warning・有効）のまま。それを「厳しく」error へ＝自由。
  - id: missing-test
    severity: error

  # ③ プロジェクト固有の新ルールを追加（常に自由）。本文はこのファイルで与える。
  - id: money-no-float
    title: 金額の浮動小数点演算
    category: correctness
    severity: error
    determinism: deterministic
    enabled: true
    override: tighten-only

  # ④ secret-in-code は org が locked。project からは厳しく/緩めいずれも触れない
  #    （ここに書いても拒否）。org の error 設定がそのまま貫通する。
---

# コード評価基準（checkout プロジェクト差分）

frontend チーム基準（[code.team-frontend.md](code.team-frontend.md)）を継承し、決済というクリティカル領域に合わせて
**さらに締め直す（厳しくする）**差分を定義する。締め直し（厳しく）・追加は常に自由。

## money-no-float — 金額の浮動小数点演算

金額計算に `float`/`number` をそのまま使わず、整数（最小通貨単位）か Decimal 型を使っているかを評価する。
決済では丸め誤差が事故に直結するため error。

**チェック観点**
- 金額の加減算・乗算を浮動小数点で行っていないか
- 通貨をまたぐ計算で型・スケールが保たれているか

**良い例**
```ts
const totalCents = items.reduce((s, i) => s + i.priceCents, 0);
```

**悪い例**
```ts
const total = items.reduce((s, i) => s + i.price, 0); // 0.1 + 0.2 問題
```
