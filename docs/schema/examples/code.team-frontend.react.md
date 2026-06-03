---
doc_type: code
scope: team:frontend
extends: org
version: 1
# 「観点・言語別の例を足したいだけ」のケース。
# 親ルールの本文を差し替えず（＝重い承認経路を踏まず）、新しい id を additive に union する。
# 同一 doc_type×scope のファイルは複数置けて、rules は id 単位で結合される。
rules:
  - id: react-component-naming
    title: React コンポーネント命名
    category: readability
    severity: warning
    determinism: deterministic
    enabled: true
    override: open
  - id: hooks-rules
    title: フック使用ルール
    category: quality
    severity: error
    determinism: deterministic
    enabled: true
    override: loosen-needs-approval
---

# コード評価基準（frontend / React 固有の追加観点）

org の `naming-convention`（言語非依存）を**上書きせず**、React 固有の観点を新しい id として足す。
これにより親の本文は無傷のまま、言語別の例だけを additive に積める。

## react-component-naming — React コンポーネント命名

コンポーネントは PascalCase、フックは `use` 始まりになっているかを評価する。

**良い例**
```tsx
function UserCard() { /* ... */ }
const useUserData = () => { /* ... */ };
```

**悪い例**
```tsx
function userCard() { /* ... */ }   // コンポーネントが camelCase
const getUserData = () => { /* ... */ };  // フックなのに use 始まりでない
```

## hooks-rules — フック使用ルール

フックを条件分岐やループの中で呼んでいないか（Rules of Hooks）を評価する。機械的に判定できる。

**良い例**
```tsx
const [open, setOpen] = useState(false);
if (open) doSomething();
```

**悪い例**
```tsx
if (cond) {
  const [open, setOpen] = useState(false);  // 条件分岐内でフック
}
```
