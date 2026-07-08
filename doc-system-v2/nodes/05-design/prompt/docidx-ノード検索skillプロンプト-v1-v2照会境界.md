skill `docidx`（ノード検索/読み込み）を在グラフ化した skill 軸 PROMPT ノード。巨大な doc-system ノード群を必要最小限で検索・取得し、v1 は `docidx` CLI、v2 は `dsv2` CLI/通常のファイル検索へ使い分ける読み取り専用の照会プロンプト。実体＝`.agents/skills/docidx/SKILL.md`。決定元＝DD-22（SPEC-61 系）。
**バージョン**: 1.0
**目的**: doc-system ノードを ID・型・ラベル・キーワードから絞り込み、必要なノード本文と依存/被依存だけを取得させる。v1 コーパスでは `python -m docidx index/search/show/deps/dependents` を使い、doc-system-v2 では 1ノード=2ファイル構成と `python3 -m dsv2` の index/deps/dependents/orphans/drift/check-slug/prompt-coverage を使う境界を明確にする。
**入力変数**: 探索したいノード ID/型/ラベル/キーワード／対象コーパス（v1 `doc-system/` または v2 `doc-system-v2/`）／必要なグラフ照会（依存先・依存元・孤立・ドリフト等）。
**出力形式**: 目的に合う検索コマンドと取得結果の要約。必要に応じて対象ノードのファイル位置、本文抜粋、依存先/依存元、照会上の注意を返す。done＝大きなファイル全体を読まず、目的のノードまたは辺情報だけを取得できた状態。
**注意事項**: read-only。ノードの著作・編集・検証判定・FND 起票は行わず、著作は `*-author`→`reconciliation-validator`→`reconciliation`、検証は該当検査へ委譲する。v1/v2 を混同しない。v2 では `docidx` ではなく `dsv2` と通常のファイル検索を使う。carrier=skill（`.agents/skills/docidx/`・DD-22）。**辺の ref_version**: SPEC-61 "0.1"（02-what/03-spec.md v0.1.0 時点・DD-3）。
