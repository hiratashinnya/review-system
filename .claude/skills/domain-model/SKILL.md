---
name: domain-model
description: Derive a type-safe, immutable in-code domain model from a SETTLED data dictionary / I/O ledger — wrap meaningful scalars as value objects (no primitive/tuple obsession), make closed vocabularies enums, prefer frozen dataclasses, choose constructor vs factory vs builder deliberately, and name everything self-explanatorily. Use AFTER the data dictionary is settled, when turning it into Python types/classes. Not for external file-format schemas (use schema-design) and not for producing the data dictionary itself (use structured-analysis).
---

# ドメインモデル設計（データ辞書 → 型安全なクラス）

**確定済みのデータディクショナリ／I/O 台帳を入力**として、システム内部のドメイン型（Python dataclass 中心）へ写像する。
外部ファイル形式の設計は `schema-design`、データ辞書そのものの生成は `structured-analysis`（DFD 分解）が担う。
本スキルはその**下流＝実装用の内部型設計**だけを担当する（DD 確定の**後**に使う）。

原則：[spec-principles](../spec-principles/SKILL.md)（PR1 もので分ける／PR5 導出は無状態＝イミュータブル化しやすい）。

## 手順
1. **語彙の棚卸し**：データ辞書で `|` で閉じた語彙＝**Enum 候補**、`{…}` の複合＝**値オブジェクト候補**として印を付ける。
2. **基本型・タプルを排す**：意味あるスカラ（id・パス・ハッシュ等）は生 `str`/`int` でなく**値オブジェクト**に。
   `(file, line)` のようなレコード代用タプルは**名前付き値オブジェクト**に（タプルは順序不変の集合用途のみ）。
3. **タイプセーフ化**：閉じた語彙は `Enum`（順序ありは `IntEnum`）。**失敗は例外でなく `Result` 型**で表す（fail-close を型で強制）。
4. **イミュータブル徹底**：導出物（1実行の産物）は `@dataclass(frozen=True, slots=True)`。可変は状態（永続ストア）を写す最小限だけ。
5. **生成方法を必ず比較検討**（コンストラクタ／ファクトリ／ビルダー）。下の既定に当て、昇格理由があるときだけ上げる。
6. **自己説明的命名**を全型に適用（§命名）。名前だけで「何の値か・何をするか」が分かること。
7. **トレーサビリティ**：データ辞書の各項 → クラス／型 → 生成方法 の対応表を残す。

## 生成方法の判断（機構＋既定・最終判断は設計レビューで＝PR2）
- **コンストラクタ（既定）**：全フィールドが同時に揃い、検証は `__post_init__` で足りる。
- **ファクトリ**：生成に**派生/検証/パース**が要る／**サブタイプ選択を隠す**（registry）／直和の安全構築。`from_*`/`of`/`resolve_*`/`make_*`。
- **ビルダー**：多数の任意要素を**複数ソースから段階的に**組む（順次構造）。内部は可変でも `build()` は **frozen な最終物を1つ返す**。

## 命名（自己説明的・必須）
- 型＝PascalCase のドメイン語・**略語禁止**。識別子値オブジェクトは**役割で命名**（`RuleId`/`FilePath`、✗`Str`/`Key`）。
- 真偽は `is_`/`has_`。ファクトリ `from_*`/`of`/`make_*`、ビルダー手順 `with_*`/`add_*`、述語は副作用なしの動詞句。
- 禁止：`manager`/`helper`/`util`/`data`/`info`/`tmp` 等の無情報語。

## done
- 閉じた語彙がすべて Enum か（生文字列比較が残っていないか）。
- 意味あるスカラ／レコード代用タプルが値オブジェクト化されているか。
- 導出物がすべて frozen か。可変なのは状態を写す型だけか。
- 各型の生成方法（constructor/factory/builder）に根拠があるか。
- データ辞書 → クラスの対応表があり、不変条件を**型で**保証できているか。

## doc-system ノード著作（DM / TERM）
ドメイン型を起こすこの段で、**設計静的層の型ノード**と**共有語彙**を著作する。共通手順・横断スパイン・RULE 全文・本文フォーマットは [07-authoring-guide.md](../../../docs/doc-system/07-authoring-guide.md)。スキーマ→[02-meta-schema.md](../../../docs/doc-system/02-meta-schema.md)、接続要否→[03-connection-matrix.md](../../../docs/doc-system/03-connection-matrix.md)。

| 型 | 必須辺 | 備考 |
|---|---|---|
| DM | → TERM (refines)、→ P (refines) | 型の不変条件は本文「制約」に |
| TERM | （被参照中心の共有語彙）| 接続要否は [03](../../../docs/doc-system/03-connection-matrix.md) を参照 |
</content>
