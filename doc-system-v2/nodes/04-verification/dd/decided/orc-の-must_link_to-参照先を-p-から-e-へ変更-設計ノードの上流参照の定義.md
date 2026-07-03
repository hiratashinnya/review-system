**status: decided**（2026-06-18 設計フェーズ）

**論点**: ORC（オーケストレーション）の `must_link_to` の参照先を P（プロセス）にするか E（イベント）にするか。設計ノードの上流参照をどう定義するかの問題。現行 config.yaml では `must_link_to: ORC → [P]`（「ORC はプロセスを実装」・MOD→P と同型）だが、ORC の識別子の本質は「何がパイプラインを起動するか」であり、MOD→P が捉える「モジュールがプロセスを実装」とは別の依存関係を表すべきではないか。

**選択肢**:
- **A（ORC→P）**: 「ORC はプロセスを実装」。設計→分析トレーサビリティを確保し、MOD→P と同型の参照とする。
- **B（ORC→E）**: 「ORC は起動イベントを参照」。ORC の識別子は "何がパイプラインを起動するか" であり、MOD→P とは別の依存関係（トリガ依存）を捉える。

**推奨**: **B**。

**根拠**:
- ORC の本質は「何をトリガに・どの順序でプロセスを走らせるか」の記述である。トリガ（E）への参照こそが必須であり、P への参照（実行段の列挙）は本文で表現できる。
- MOD→P で「モジュールがプロセスを実装」する関係は既にカバーされており、ORC→P は同じ軸の重複になる。
- ORC→E がなければ "何が起動するか" が RULE で保証されず、ORC が浮いた設計（トリガ未定義）になりえる。

**決定**: **B を採用**（2026-06-18）。`must_link_to: ORC → [E]` に変更し、ORC は起動イベントへの参照を必須とする。

**影響範囲**（本ファイル反映は別パス＝design-author→reconciliation。反映辺は reconciliation 時に X→DD-15 を付与）:
- `docs/doc-system/config.yaml`（out-of-graph）: `must_link_to` の ORC target を `P` → `E` に変更（reason を「ORC は起動イベントを参照する」に更新）。`must_be_linked_from` に `E ← [ORC]`（design ステージ・warning・「イベントは起動する ORC を持ちうる」）を追加。
- `doc-system/05-design/03-orchestration.md`: ORC-1 に `→E-1` 辺を追加（MINOR バンプ v0.1→v0.2）。`→DD-15` バックリファレンス付与。従来の P への参照は本文で実行段として表現する。
- `.claude/skills/architecture-design/SKILL.md`（out-of-graph）: `must_link_to` 表に `ORC → E(trigger)` を追記し、ORC→P が重複である旨を注記。

**覆る場合の影響範囲**: A（ORC→P）へ戻す場合、ORC-1 の E-1 辺を削除し P 辺を必須に戻す、config.yaml の `must_link_to` ORC target を E→P に戻し `must_be_linked_from: E←[ORC]` を撤回、SKILL.md の表を元に戻す（影響は設計層 orchestration と config・SKILL に限定・分析層 E ノードは不変）。
