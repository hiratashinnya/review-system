---
doc_type: code
scope: team:frontend
extends: org
version: 1
# org の各ルールに対する「差分」だけを書く。書かない id は org をそのまま継承。
# 既定は org 権威：下位は「追加」と「厳しく」だけ自由。緩め・無効化は org が open したルールのみ。
rules:
  # ① 緩め（severity を下げる）。naming-convention は org が override:open なので可
  - id: naming-convention
    severity: warning        # error → warning。本文は与えない＝org の観点をそのまま継承

  # ② 厳しく（severity を上げる）＝常に自由（org の下限を上げる方向）
  - id: dead-code
    severity: error          # warning → error

  # ③ フロント固有の新ルールを「追加」＝常に自由。本文はこのファイルで与える
  - id: no-inline-style
    title: インラインスタイルの直書き
    category: maintainability
    severity: warning
    determinism: tradeoff
    enabled: true
    override: open

  # ④ missing-test を無効化しようとしても override:tighten-only のため機械拒否される。
  #    （ここに enabled: false と書いてもマージ時に reject＝適用されない。緩め・無効化は org の open が要る）
  # ⑤ secret-in-code を緩めようとしても override:locked のため機械拒否される。
  #    （severity: warning と書いても reject）
---

# コード評価基準（frontend チーム差分）

全社デフォルト（[code.org.md](code.org.md)）を継承し、フロント開発の実態に合わせて差分だけを定義する。
**下位は「追加」と「厳しく」だけ自由**。①の naming 緩めは org が `open` 宣言しているから可能で、
④ missing-test の無効化・⑤ secret の緩めは org 権威（tighten-only / locked）で**機械拒否**される。

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
