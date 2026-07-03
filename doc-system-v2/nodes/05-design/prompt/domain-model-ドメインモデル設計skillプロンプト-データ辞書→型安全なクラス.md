skill `domain-model`（データ辞書 → 型安全なクラス）を在グラフ化した skill 軸 PROMPT ノード。確定済みデータディクショナリ／I/O 台帳を入力に、内部ドメイン型（Python dataclass 中心）へ写像するプロンプト。実体＝`.claude/skills/domain-model/SKILL.md`。決定元＝DD-22（SPEC-61 系）。
**バージョン**: 1.0
**目的**: 閉じた語彙（`|`）は Enum・複合（`{…}`）は値オブジェクトとして棚卸しし、基本型/レコード代用タプルを値オブジェクトへ、失敗は `Result` 型で表し、導出物は frozen dataclass に、生成方法（コンストラクタ／ファクトリ／ビルダー）を根拠付きで選び、自己説明的命名で型安全な内部ドメインモデルを設計させる（PR1 もので分ける・PR5 導出は無状態）。
**入力変数**: 確定済みデータディクショナリ／I/O 台帳（DD 確定の後に使う・上流＝structured-analysis）。
**出力形式**: ドメイン型定義（Enum／値オブジェクト／frozen dataclass）＋生成方法の判断＋データ辞書 → クラス／型 → 生成方法の対応表。
**注意事項**: 外部ファイル形式は schema-design、データ辞書生成は structured-analysis（本スキルは下流の内部型設計のみ）。生文字列比較を残さない・導出物は全て frozen・不変条件は型で保証。`manager`/`helper`/`util` 等の無情報語を禁止。carrier=skill（slash command `/domain-model`・DD-22）。**辺の ref_version**: SPEC-61 "0.1"（02-what/03-spec.md v0.1.0 時点・DD-3）。
