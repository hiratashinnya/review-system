# maintainability_lint

Issue #539 で採用済みの保守性原則のうち、意味解釈なしに判定できる3項目を検査する
標準ライブラリのみの read-only lint です。

- Python モジュールは100物理行以内。
- 連続した行コメントは3行以内。長い経緯・根拠は DD/ADR/方法文書へ移す。
- `@dataclass` と具体的なロジッククラスを同一ファイルに置かない。

命名が責務を一意に伝えるかは意味判断が必要なので、この lint は推測しません。
`.ai/agents/{issue-implementer,issue-fixer,pr-reviewer}.md` の役割契約で、作成時とレビュー時に確認します。

## Usage

```bash
python3 -m maintainability_lint check
python3 -m maintainability_lint baseline
```

`check` は違反があれば exit 1、baseline や Python source を解釈できなければ exit 2 です。
`baseline` は現在の違反集合を JSON として stdout に出すだけで、ファイルは変更しません。

## Scope

`source_files.py` は repository root 直下の Python file と、Python file を含む top-level directory を
自動検出します。`tests/`、`doc-system-v2/`、`dsv2/`、archive、仮想環境等は対象外として明示し、
新しい汎用開発ハーネスを allowlist への追記漏れで無言に除外しません。別 worktree、build 出力、
仮想環境、dependency cache は階層を問わず走査から除外します。

行数は空行・コメントを含む物理行です。コメント検査は `tokenize` が返す連続した full-line
comment を対象とし、inline comment と docstring は別の役割なので数えません。クラス分離検査は
トップレベル `@dataclass` と、実処理を持つトップレベル class の同居を検出します。例外型と
`pass` / `...` / `raise NotImplementedError` だけの抽象契約はロジッククラスに数えません。

## Existing-debt ratchet

Issue #539 着手時には対象137ファイル中、100行超が66ファイル、4行以上のコメントブロックが
66件（26ファイル）、データ／ロジック同居が5ファイルありました。この Issue で全件を分割すると
スコープを超えるため、`baseline.json` に既存集合だけを固定しています。

- 新しい違反は失敗します。
- 既存の長いモジュールは内容 fingerprint が変わると失敗します。
- 既存の長いコメントは本文 fingerprint が変わると失敗します。
- 既存の同居ファイルは内容 fingerprint が変わると失敗します。
- 負債を解消して baseline だけが残った場合も stale baseline として失敗します。

したがって baseline 更新は自動免除ではなく、負債を増やしてよいかを差分レビューへ露出させる
明示的な判断です。CI は `.github/workflows/tests.yml` で `check` を毎 PR 実行します。
