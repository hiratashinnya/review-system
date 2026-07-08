**保存対象**: `docs/doc-system/config.yaml`（RULE 設定・必須接続ルール・ステージ状態・always_error fail-close・trace_scope など、検査パイプラインの挙動を決める全設定）。
**保存理由**: RULE 発火・activate_stage 判定・always_error による常時 ERROR 発火の単一ソース。P-5（config 読込・検証）がこのファイルを読んで検証し、下流の全プロセス（P-1〜P-4・P-6）の挙動を駆動する。
**ライフサイクル**: ACTOR-1（仕様著者）が config.yaml を作成・更新・管理する。spec-inspector は読み取り専用で、P-5 が実行のたびに読込・検証するのみ（書き込まない）。
