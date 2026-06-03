---
doc_type: code
scope: team:frontend
extends: org
version: 1
# org の各ルールに対する「差分」だけを書く。書かない id は org をそのまま継承。
rules:
  # ① 緩め方向（severity を下げる）＝リスク側 → 管理者承認が要る（override: loosen-needs-approval）
  - id: naming-convention
    severity: warning        # error → warning。本文は与えない＝org の観点をそのまま継承

  # ② 厳しく方向（severity を上げる）＝安全側 → 自由に適用（承認不要）
  - id: dead-code
    severity: error          # warning → error

  # ③ 無効化＝緩めの最たるもの → 承認が要る（missing-test の override は loosen-needs-approval）
  - id: missing-test
    enabled: false

  # ④ フロント固有の新ルールを「追加」＝安全側 → 自由。本文はこのファイルで与える
  - id: no-inline-style
    title: インラインスタイルの直書き
    category: maintainability
    severity: warning
    determinism: tradeoff
    enabled: true
    override: open

  # ⑤ secret-in-code を緩めようとしても override: locked のため機械的に拒否される。
  #    （ここに severity: warning と書いてもマージ時に reject。例として記載＝適用されない）
---

# コード評価基準（frontend チーム差分）

全社デフォルト（[code.org.md](code.org.md)）を継承し、フロント開発の実態に合わせて差分だけを定義する。
**緩め方向（① naming-convention の格下げ・③ missing-test の無効化）は管理者承認を経て初めて有効**になる。

## no-inline-style — インラインスタイルの直書き

JSX/HTML に `style={{...}}` や `style="..."` を直書きせず、CSS Modules / styled 等に寄せているかを評価する。
どこまで許容するかはチーム裁量のため `override: open`。

**チェック観点**
- 1〜2プロパティの暫定以外で、インラインに大量のスタイルを書いていないか
- デザイントークン（変数）を経由せず色・余白を直値で書いていないか

**良い例**
```tsx
<button className={styles.primary}>送信</button>
```

**悪い例**
```tsx
<button style={{ background: "#3b82f6", padding: "8px 16px" }}>送信</button>
```
