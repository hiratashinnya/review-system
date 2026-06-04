---
doc_type: code
scope: org
extends: null
version: 1
rules:
  - id: naming-convention
    title: 命名規則
    category: readability
    severity: error
    determinism: deterministic
    enabled: true
    override: open               # 命名は現場裁量に委ねる＝下位は緩めても可
  - id: dead-code
    title: 不要コード
    category: readability
    severity: warning
    determinism: deterministic
    enabled: true
    override: tighten-only       # 既定。下位は締める/追加のみ、緩め・無効化は不可
  - id: long-function
    title: 長すぎる関数
    category: maintainability
    severity: warning
    determinism: tradeoff
    enabled: true
    override: open
  - id: missing-test
    title: テスト不足
    category: quality
    severity: warning
    determinism: judgment
    enabled: true
    override: tighten-only       # 全社の品質下限。下位は無効化/格下げ不可
  - id: secret-in-code
    title: 機密情報のハードコード
    category: security
    severity: error
    determinism: judgment
    enabled: true
    override: locked
---

# コード評価基準（全社デフォルト）

社内のあらゆるコードに共通で適用する基準。チーム/プロジェクトで上書きできる。

## naming-convention — 命名規則

変数・関数・クラスの命名が、役割が名前から読み取れる形になっているかを評価する。

**チェック観点**
- 過度な省略をしていないか（`uc` ではなく `user_count`）
- ブール値は `is_` / `has_` などで意図が分かるか

**良い例**
```python
user_count = 0
is_active = True
```

**悪い例**
```python
uc = 0
flag = True
```

## dead-code — 不要コード

到達不能なコード・使われていない変数や import が残っていないかを評価する。

**チェック観点**
- コメントアウトされたまま放置されたコードブロックがないか
- 未使用の import / ローカル変数がないか

**良い例**
```python
def total(items):
    return sum(items)
```

**悪い例**
```python
def total(items):
    # old = items[0]   # 旧実装。消し忘れ
    import os           # 未使用
    return sum(items)
```

## long-function — 長すぎる関数

1つの関数が複数の責務を抱えて長大になっていないかを評価する。分割の仕方には幅があるため定石ベースで提案する。

**チェック観点**
- 1関数がおおむね50行を超えていないか
- 抽出できるまとまった処理（ループ本体・前処理）がないか

**良い例**
```python
def process(order):
    validated = validate(order)
    return persist(validated)
```

**悪い例**
```python
def process(order):
    # バリデーション・整形・永続化・通知を全部ここで...（80行）
    ...
```

## missing-test — テスト不足

変更・追加されたロジックに対応するテストがあるかを評価する。何をどこまでテストすべきかは判断が要る。

**チェック観点**
- 公開関数・分岐の多いロジックにテストがあるか
- 異常系・境界値が確認されているか

**良い例**
- `parse_date` の正常系・不正入力・境界値（うるう年）がテストされている。

**悪い例**
- 新規追加した決済ロジックにテストが1件もない。

## secret-in-code — 機密情報のハードコード

API キー・パスワード・トークン等がソースに直書きされていないかを評価する。検知は機械的だが、対処（ローテーション要否等）は人間判断が要る。

**チェック観点**
- 認証情報がリテラルで埋め込まれていないか
- 設定は環境変数 / シークレットストア経由か

**良い例**
```python
api_key = os.environ["API_KEY"]
```

**悪い例**
```python
api_key = "sk-live-1a2b3c4d5e6f"
```
