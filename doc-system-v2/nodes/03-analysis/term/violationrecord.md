**もの**: RULE 検査が検出した違反 1 件の内部表現。検査結果の最小単位。
**用途**: 各 checker（MOD-5/6/14/15/16 等）が違反を検出するたびに 1 レコード生成し、filter（発火・重症度確定プロセス）を経て reporter（MOD-8）がレポート・G# 採番・終了コード決定の入力とする。
**Python 型名**: `ViolationRecord`
**保持要素**: `severity` / `file_ref` / `rule_id` / `node_id` / `message`
**定義モジュール**: `spec_inspector/domain.py`（MOD-1）
