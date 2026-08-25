# Repository-managed hooks

このディレクトリの hook は clone 後に明示的に有効化する。

```console
chmod +x .githooks/pre-commit
git config core.hooksPath .githooks
```

`pre-commit` は `python3 -m guidance_sync staged-check` を実行し、`.ai/guidance/` の原稿変更に対応する Codex／Copilot 生成物が staged index に存在し、同じ index 上の原稿から得た期待値と一致することを fail-close に確認する。working tree の未 stage 内容は判定材料にせず、hook 自身は render も stage も行わない。

原稿を変更した場合は、明示的に次を実行して生成物を確認・stage する。

```console
python3 -m guidance_sync render
python3 -m guidance_sync check
git add -- .ai/guidance AGENTS.md .github/copilot-instructions.md
```

hook を導入していない clone／fork も GitHub Actions の `guidance-sync` workflow が同じ生成物整合性を検査する。
