# Issue #315「karte: 実測信号の強制点・自動 resolved の fail-open ほかレビュー残指摘（PR #314 K-02/K-04〜K-07/K-09/K-11）」

- URL: https://github.com/hiratashinnya/review-system/issues/315
- 状態: closed（2026-11-18取得）
- 本文: 5754文字/ 127行。全文: `../raw/issues-2026-08a.jsonl`
- AC: 6件（未チェック: 6）
- Issue参照: #314, #307, #308, #309, #312
- PR参照: #314
- 主見出し: ## 背景 | ## 指摘一覧 | ### K-02 [major / harm: yes] 実測信号が `close-attempt` の任意実行に依存し、省略すれば無効化できる | ### K-06 [minor / harm: yes] 再掲されなかった未解消 finding を無条件 resolved にする | ### K-05 [minor / harm: yes] 再発番検出の偽陽性に逃げ道が無く `ingest-review` が全件失敗する | ### K-04 [minor / harm: no] `write_text_atomic` / `append_text` の symlink 再検査が非原子的 | ### K-07 [nit / harm: no] `normalize_text` の保持文字クラスが限定的 | ### K-09 [nit / harm: no] 飽和判定が `append` と `render`/`status` で別定義 | ### K-11 [nit / harm: no] `.claude/agents/reconciliation.md` の clean-tmp ガード説明が追従漏れ | ## Scope | ## Out of scope | ## Acceptance criteria
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- - CLAUDE.md「指摘は処置完了まで追う」「『対応不要』を AI が独断で書かない」と擦れる方向の **fail-open**。
- - 問題：`path.is_symlink()` / `tmp_path.is_symlink()` の検査後に `Path.write_text()`・`open("a")` を
-   使っており、両者は symlink を追跡する。検査と open の間に差し替えられれば追従する。
- - 推奨：`os.open(..., O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW)` / `os.open(..., O_WRONLY|O_APPEND|O_NOFOLLOW)`
-   で検査と open を1システムコールに畳む。据え置くなら docstring を
-   正規化結果が空になり `is_same_finding` が常に False（＝再発番を見逃す fail-open）。
-   対象文字を列挙しない方式にする。または docstring に適用範囲（ja/en 前提）を明記する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
