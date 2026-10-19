---
id: TD-asset-parity-refactor-637
version: 1
condition: normal
---
# 目的
Issue #637 の先行分割で既存の asset_parity 公開 API・互換キーワード・出力を維持し、既存 baseline 負債を除く。

# 前提
main 92f7cc0 の既存テストを仕様回帰の基準とする。機能是正と型検査対象の拡張は後続 PR で行う。

# 手順
- 実装を commit した後、`python3 -m unittest discover -s tests/unit -p 'test_asset_parity*.py'` を実行する。
- `python3 -m maintainability_lint check` を実行し、baseline 差分が既存3モジュールと既存長コメントの削除だけであることを確認する。
- 新規モジュールの公開 API と旧 import 経路が同じオブジェクトを再 export することを回帰テストで確認する。

# 期待結果
既存 asset_parity テストと import 互換テストが全件成功し、lint は violations=0。新規・変更モジュールは100物理行以内。
