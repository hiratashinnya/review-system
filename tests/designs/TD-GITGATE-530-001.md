---
id: TD-GITGATE-530-001
version: 1
condition: failure
---
# PR 差分保存先と reviewer 契約の回帰

## 目的

`_save_diff` が書込み fd と返却パスの同一ファイル性を確認し、PR reviewer の差分取得契約が RTK を明示することを検証する。

## 前提

- Python 標準ライブラリの `unittest` を使う。
- 保存先は一時ディレクトリ内に作り、`os.stat` は必要なケースだけモックする。

## 手順

1. 一時作業ディレクトリで `_save_diff` を実行し、返却パスを実際の file descriptor と比較する。
2. `os.stat` が異なる `st_dev` / `st_ino` を返す状況を作り、保存処理が `PrDiffError` で失敗することを確認する。
3. 3つの PR reviewer 契約ファイルにある全ての `gh pr diff` 表記を走査し、それぞれ `rtk` を直前に持つことを確認する。

## 期待結果

- 正常保存では fd と返却パスの `st_dev` / `st_ino` が一致し、保存内容を読み戻せる。
- inode 不一致は `PrDiffError` となり、誤った返却パスを成功扱いしない。
- 契約の差分取得コマンドに bare の `gh pr diff` が残らない。
