<!-- generated-by: python3 -m guidance_sync render; edit-source-only -->
<!-- common-source: .ai/guidance/common.md; sha256: 32e1680c012a7f6bc6a2c6a80e85382b35aa4a5417117540a4bb09a20239db90 -->
<!-- platform-source: .ai/guidance/platforms/codex.md; sha256: 8abc296ee3cbb906812790bae7c49289c55624998e9ff93892d65a0713df723a -->

# プロジェクト共通 guidance

この文書は Claude Code、Codex、GitHub Copilot に共通する意味内容の Source of Truth である。PF 固有の loader、tools、model、hook、dispatch、worktree などの実行機構はここへ混ぜず、各 PF の設定・原稿に残す。

## 言語・対外記録

- すべての説明・報告・質問は、ユーザーが明示的に別言語を指定しない限り日本語で行う。main thread、subagent、レビュー報告、PR 本文・コメントも同様とする。
- AI が PR 本文、PR コメント、レビューコメント、merge コメントを投稿する場合は、本文冒頭または件名で利用した AI agent 由来であることを明記する。
- オーナー判断が必要な矛盾・スコープ判断・据え置き可否はチャットで報告する。PR コメントやノードは永続化のための副次記録であり、それだけで報告済みとはみなさない。

## 作業分離・判断境界

- main thread は作業分解、実行主体の選定、進行管理、ユーザー報告を担い、実装・レビュー・是正は利用可能な別コンテキストへ分離する。
- レビュー担当と修正担当を分け、修正後は元レビューと別の文脈で再レビューしてから完了判断する。レビュー finding は記録し、対応内容・検証・最終結果も追跡可能にする。
- 矛盾・情報不足・オーナー判断必須で停止するときは、事実、選択肢、メリット／デメリット、理由付き推奨を示す。空の停止や AI による独断的な「対応不要」は禁止する。
- スケジュールや後続スプリントへの繰越は、オーナーの明示指示なしに決めない。
- CI や外部サービスは無課金で実現できる方法を優先する。課金が避けられない場合は実装前にオーナーの明示認可を得る。
- 設計で仕様から一意に決まらない点は、論点・選択肢・推奨・暫定決定・影響範囲を判断記録へ残して前進する。
- 決定履歴・却下案・経緯・例外理由は rationale へ移設して保持し、現行手順・契約は古い記述を積み上げず現在の正しい内容へ更新する。
- rate limit や session 上限を理由に、model／reasoning effort／必要な役割分離を品質降格しない。同じ構成で再開する。
- 新しい AI 資産を作る前に既存資産の重複・競合を点検する。
- 実装設計では、module、interface、protocol、persistence、orchestration、prompt、log/version、test strategy の凍結セットを総点検してから実装へ進む。

## 仕様設計・点検の原則

- PR1 もので分ける：入出力は「もの（実体）＋発生源（外部アクター）」で分け、使い道や内部発生プロセスでは分けない。
- PR2 判定軸を混ぜない：機械判定できる機構と、人が妥当性を確認する運用ルールを分ける。
- PR3 系外は非イベント：システムを介さない変更はイベント化せず、必要な検査は処理時に行う。
- PR4 観測できないものは持たない：顛末を観測できない事象に対する機能は作らない。
- PR5 状態の要否：毎回作り直せる導出物は状態化せず、過去を覚えなければ成立しない情報だけを状態にする。
- PR6 価値経路を遮断しない：すべての入力をプロセスから価値ある出力まで連続させる。
- PR7 矛盾は停止して打ち上げる：勝手に解決せず、原案・比較・理由付き推奨を添える。
- PR8 フル論理設計に MVP 印を付ける：論理は完全に作り、MVP 外を削除せず印で残す。
- PR9 DFD レベリング：階層をまたいで上位と下位を直結しない。
- PR10 認識合わせ先行：重い作業ほど、手順・成果物・未決事項・停止条件を先に揃える。

## 正本・実装規約

- 本リポジトリには doc_system と review_system が同居する。doc_system の正本は `doc-system-v2/` と関連する方法論・AI 資産、review_system の仕様・設計の正本は `docs/`（`docs/doc-system/` を除く）であり、混同しない。
- corpus ノード（`doc-system-v2/nodes/**`）は対応する `*-author` が一時出力し、`reconciliation-validator` の read-only 検証後に `reconciliation` が反映する。主文脈や他ロールは直接編集しない。
- review_system 本体の実装は Python を使用し、原則として標準ライブラリだけに依存する。
- 共通 AI 資産の正本は `.ai/` 配下に置く。PF の実行入口は正本そのものではなく、公式 import または追跡対象の生成物として接続する。

# Codex 固有 guidance

- Codex 固有の設定・hook・custom agent は `.codex/` 配下に置く。
- Codex repo skill は `.agents/skills/` 配下に置く。
- 実装、commit、push、PR 作成、PR レビュー、修正は、Codex が利用可能な subagent に委譲する。
- shell 経由で GitHub 本文を投稿する場合は body file を優先し、バッククォートや `$()` の shell 展開を防ぐ。
- secondary worktree からの remote 操作後にローカル checkout／cleanup が競合した場合は、remote 状態を確認してから後処理する。

## Codex rate-limit recovery

- project-local Stop hook は rate-limit の兆候がある場合だけ `/status` を送り、cooldown で再帰を抑える。
- cloud／hosted／no-tmux／tmux-unavailable の no-op 経路では、状態ディレクトリ、payload、ログなどの永続副作用を起こさない。
- tmux pane 注入ガードの既定は `^codex$` とし、wrapper が必要な環境だけ明示的に上書きする。
- Codex 資産を `.claude/` に混ぜない。Codex hooks/config/custom agents は `.codex/`、repo skills は `.agents/skills/` に置く。
