# Issue #318「karte: カルテ書込の symlink 再検査を原子的にする（O_NOFOLLOW で検査と open を1システムコールに畳む）」

- URL: https://github.com/hiratashinnya/review-system/issues/318
- 状態: closed（2026-11-18取得）
- 本文: 2763文字/ 56行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 6件（未チェック: 0）
- Issue参照: #314, #315, #307
- PR参照: #314
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ## Scope | ## Out of scope | ## Acceptance criteria | ## Dependencies / Related issues
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- **本 Issue は保証範囲を狭めるためのものではありません。** 現状を正確に表現し、処置が漏れないよう追跡することが目的です。並行して `karte/paths.py` の docstring を実情に合わせ、本 Issue で厳密化する旨を宣言します。
- `karte/paths.py` の `write_text_atomic` / `append_text` は、書込直前に `path.is_symlink()` で再検査してから `Path.write_text()` / `open("a")` を呼びます。docstring はこれを「TOCTOU 対策（`dsv2/cleantmp.py` の `_reverify_before_delete` と同じ defense-in-depth）」と説明し
- `Path.write_text()` と `open("a")` は**どちらも symlink を追跡する**ため、検査と open の間にパスが symlink へ差し替えられれば、書込はその symlink 先へ及びます。比較対象として挙げている `dsv2/cleantmp.py` の `_reverify_before_delete` は `shutil.rmtree` の直前に**同じガードを再実行**して window を詰めており、そちら
-   および `with path.open("a") as handle: ...`
- - `write_text_atomic` … 一時ファイルを `os.open(tmp, O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW)` で開く
-   （`O_EXCL` で既存を拒否し、`O_NOFOLLOW` で symlink を追跡しない＝**検査と open を1システムコールに畳む**）。
- - `append_text` … `os.open(path, O_WRONLY|O_APPEND|O_NOFOLLOW)` で開く。
-   （`os.open` の `O_NOFOLLOW` は最終要素にしか効かないため、親ディレクトリ側の差し替えは
-   ファイル名の完全一致）の変更。これらは現状のまま維持する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
