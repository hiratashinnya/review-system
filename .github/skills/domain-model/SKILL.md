---
name: domain-model
description: Derive a type-safe, immutable in-code domain model from a SETTLED data dictionary / I/O ledger — wrap meaningful scalars as value objects, make closed vocabularies enums, prefer frozen dataclasses, choose constructor vs factory vs builder deliberately. Use AFTER the data dictionary is settled. Not for external file-format schemas (use schema-design), not for producing the data dictionary itself (use structured-analysis).
---

# ドメインモデル設計（データ辞書 → 型安全なクラス）

確定済みのデータディクショナリ／I/O 台帳を入力として、システム内部のドメイン型（Python dataclass 中心）へ写像する。
原則：spec-principles（PR1 もので分ける／PR5 導出は無状態＝イミュータブル化しやすい）。

## 手順

1. **語彙の棚卸し**：`|` で閉じた語彙＝Enum 候補、`{…}` の複合＝値オブジェクト候補として印を付ける。
2. **基本型・タプルを排す**：意味あるスカラ（id・パス・ハッシュ等）は生 `str`/`int` でなく値オブジェクトに。
3. **タイプセーフ化**：閉じた語彙は `Enum`。失敗は例外でなく `Result` 型で表す。
4. **イミュータブル徹底**：導出物は `@dataclass(frozen=True, slots=True)`。可変は状態を写す最小限だけ。
5. **生成方法を比較検討**（コンストラクタ／ファクトリ／ビルダー）：
   - コンストラクタ（既定）：全フィールドが同時に揃う場合。
   - ファクトリ：生成に派生/検証/パースが要る場合。`from_*`/`of`/`make_*`。
   - ビルダー：多数の任意要素を複数ソースから段階的に組む場合。
6. **自己説明的命名**を全型に適用（略語禁止・`manager`/`helper`/`util` 等の無情報語禁止）。
7. **トレーサビリティ**：データ辞書 → クラス → 生成方法の対応表を残す。

## done

- 閉じた語彙がすべて Enum か（生文字列比較が残っていないか）。
- 意味あるスカラ／レコード代用タプルが値オブジェクト化されているか。
- 導出物がすべて frozen か。可変なのは状態を写す型だけか。
- データ辞書 → クラスの対応表があり、不変条件を型で保証できているか。
