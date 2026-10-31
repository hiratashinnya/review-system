# karte / feedback 台帳の deny に Write 専用エントリを置かない理由

## 経緯
- Issue #522 レビュー F-522-10 で、`.claude/settings.json` の `permissions.deny` に
  `Write(/tmp/_karte/**)` と `Write(/.ai/feedback/**)` を追加した。
- PR #688（2026-10-31）：Claude Code が "Deny rule Write(...) never matches · use Edit(...)"
  と警告したため、`Write` 専用エントリを削除した。`Edit` 規則が `Write` も覆う。

## 削除前の記述（移設元・文言は尊重して移設）

### `tests/unit/test_karte_cli.py` `TestKarteWritePathsAreDenied` の docstring（旧）
> Issue #522 レビュー F-522-10: カルテ台帳の deny が ``Edit`` と ``Write`` の**両方**あること。
>
> 是正前は ``Edit(/tmp/_karte/**)`` の1件だけで、``Write`` ツールによる**丸ごと上書き**の
> 経路が空いていた（実地確認で ``tmp/_karte/`` 配下へ新規ファイルを作成でき、既存カルテも
> 同じ経路で置き換えられる）。``Edit`` は既存文字列の一致を要求するぶん部分改変に留まるのに対し、
> ``Write`` は append-only を前提にした台帳そのものを差し替えられるため、塞ぐ必要性は
> むしろ ``Write`` の方が高い。``.ai/feedback/**`` 側が Edit/Write の両方を登録している
> （``tests/unit/test_feedback_ledger.py``）のに karte 側だけ片方、という非対称も消す。

### `karte/model.py` module docstring の該当段落（旧）
> **``Write`` の登録は Issue #522 レビュー F-522-10 で追加した**：**台帳の保護は実際には
> 二層で成立している**（同レビュー F-522-04／F-522-11 で判明）。非隔離で動く主文脈には
> ``permissions.deny`` が発火する（実測：メインチェックアウトの ``tmp/_karte/probe-pattern-522.md``
> への ``Write`` が "File is in a directory that is denied by your permission settings."
> で拒否された。当時 ``permissions.deny`` は ``Edit(/tmp/_karte/**)`` の1エントリのみで
> ``Write`` エントリは無かったが、それでも ``Write`` は素通りしなかった）。隔離ロール
> （是正・実装当事者）には worktree isolation が同じ書込みを構造的に拒否する（実測：隔離
> worktree からメインチェックアウトの同パスへの ``Write`` が "This agent is isolated in
> the worktree ... Edit the worktree copy of this file instead of the shared-checkout
> path." で拒否された。自分の worktree 内への ``Write``/``Edit`` は成功するが、そこは CLI
> が参照しない場所であり本物の台帳ではない）。``Write`` エントリを明示的に登録しているのは
> この実測でエントリ追加前に上書きが成功していたからではなく、パターンの錨（先頭 ``/`` の
> 解決基準）とツール経路の挙動が版に依存しうることへの明示的な備えである——``Edit``/``Write``
> のどちらか一方だけに依存せず、両方を宣言して同じ結論を二重に固定しておく。

## 旧記述どうしの食い違い
上記2つの旧記述は互いに矛盾していた。旧テスト docstring は「`Edit` 1件だけでは `Write` による
新規作成・上書きが通った（実地確認）」と述べ、旧 `model.py` は同じ状況（当時 `Edit` のみ）で
`Write` が拒否されたと述べていた。後者は F-522-04／F-522-11 の実測に基づく。
前者の観測は、隔離 worktree 内の自コピーへの書込み（`model.py` に「自分の worktree 内への
`Write`/`Edit` は成功する」とある）だった可能性があるが、**確認していない**。

## 現行の扱い
- deny は `Edit(/tmp/_karte/**)` と `Edit(/.ai/feedback/**)` のみ。
- `tests/unit/test_karte_cli.py` / `test_feedback_ledger.py` は `Write(...)` エントリの
  再混入を `assertNotIn` で防ぐ。
- 「Edit が Write も覆う」こと自体は実測記録と Claude Code の仕様に依拠し、テストでは
  機械検証できない。
