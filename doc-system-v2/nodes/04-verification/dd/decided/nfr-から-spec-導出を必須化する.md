**status: decided**（2026-06-13 反映完了）

**論点**: 現状 NFR-1〜NFR-6 の全 6 件に SPEC 依存辺がゼロであり、NFR が達成されたかどうかを機械的に検証できない。FR → SPEC 導出は RULE-017/018 で強制されているが、NFR に同等のルールがなく、NFR は「制約として宣言するだけ」で終わる構造になっている。NFR をテスタブルな仕様として確実に達成可能な形にするには、NFR→SPEC 導出ルールを追加する必要がある。

**選択肢**:
- **A（RULE 追加）**: config.yaml に `must_link_to: NFR → [SPEC]` を追加し、NFR が少なくとも 1 本の SPEC 依存辺を持つことを必須化。NFR-1〜6 に各々 SPEC を導出して接続する。
- **B（suppress 許容）**: A に加えて、定量化困難な NFR（例: NFR-3「self-contained」）は `suppress: [RULE-xxx]` で個別免除を許容する。
- **C（現状維持）**: NFR は抽象制約として保持し、対応 SPEC は FR 側でカバーされているとみなす（検証の網羅穴は許容）。

**推奨**: A + B の組み合わせ。理由：NFR は「非機能」とはいえ機械検証可能な制約（例: NFR-1「プレーンテキスト形式」→ ファイルのバイナリ有無検査 SPEC、NFR-2「標準ライブラリのみ」→ import チェック SPEC）に落とせるものが多い。定量化が難しい NFR は suppress で免除するが理由コメント必須とする。C は検証穴を永続化するため不採用。

**決定**: A + B の組み合わせを採用（N6 処置・2026-06-13）。SPEC-44〜49（NFR-1〜6 各1件・normal）著作・config.yaml の `must_link_to` を `SPEC → [FR, NFR]` に変更・`must_be_linked_from: NFR ← [SPEC]` ルールを requirements ステージで追加・NFR-1〜6 に `→DD-5` バックリファレンス付与を実施した。

**影響範囲（2026-06-13 反映完了）**:
- `config.yaml`（out-of-graph）: `must_link_to` を `SPEC → [FR, NFR]` に変更（SPEC が NFR を直接親にできるよう拡張）。`must_be_linked_from` に `NFR ← [SPEC]`（requirements ステージ・warning）を追加。**番号付き RULE は新設せず config 駆動の被依存辺ルールで実装**（当初提案の「RULE-028 相当」は採らず・RULE-028 は別件のフィールドスキーマ検査に割当）。
- `doc-system/02-what/03-spec.md`: SPEC-44〜49（NFR-1〜6 各1件・normal）を著作。
- `doc-system/02-what/02-nfr.md`: NFR-1〜6 それぞれに `→DD-5` バックリファレンス付与。
- 残作業（未反映）: `.claude/agents/requirements-author.md`・`spec-author.md`・`docs/doc-system/07-authoring-guide.md` への「NFR の SPEC 導出必須」規約追記は今後（著作プロセスへの定着）。
