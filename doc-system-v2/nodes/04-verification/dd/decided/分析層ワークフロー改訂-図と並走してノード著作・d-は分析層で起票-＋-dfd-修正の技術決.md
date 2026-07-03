**status: decided**（2026-06-13 反映完了）

**論点**: 分析層 DFD Level 1 のオーナーレビューで 5 点の指摘が出た。①P-6 の config 直読み、②D の起票タイミング、③プロセス間データの D 化、④P-7 の記載内容入力欠如、⑤分析層ワークフロー（ノードを先に作って図を後付けする順序）。①③④は FND-21/22/23 で処置。本 DD は②⑤のプロセス決定と、③④の D→SPEC 紐付け・新規 ID 採番という技術的選択を記録する。

**決定**:
- **②D の起票タイミング = 分析層（変更なしを確認）**: config.yaml の `must_link_to: D→SPEC / D→P` と `must_be_linked_from: D←P` は既に `activate_stage: analysis` で発火する。機械ルール上 D は分析層ノードとして正しく扱われており、config 変更は不要。欠けていたのは著作運用（D を分析層で起票する手順）であり、`.claude/agents/analysis-author.md`・`.claude/agents/structured-analysis.md` にプロセス間データの D 起票を明示する（資産更新で対応・新規機能 SPEC は起こさない）。
- **⑤分析層ワークフロー = 図と並走してノード著作**: コンテキスト図 → L1 DFD → L2 分解を描きながら、各 ACTOR/I/O/D/P/E ノードを同時に著作・整合させる（図を後付けで起こさない）。structured-analysis エージェントの手順にこの並走を明記する。
- **③D→SPEC 紐付け規約**: 各 D はその生成プロセスを規定する SPEC に紐づける（D-1→SPEC-24 の先例に倣う）。D-3→SPEC-21（設定読込）・D-4→SPEC-1（パース生成物）・D-5→SPEC-2（パース段違反）・D-6→SPEC-5（RULE 検査）・D-7→SPEC-14（カバレッジ）・D-8→SPEC-38（tmp 草案著作）。
- **④新規 ID 採番（退役 ID 不再利用）**: 退役済み ID は再利用しない（再利用すると過去の FND 経緯記述と衝突し追跡性を損なう＝ID 永続原則）。(a) ノード記載内容入力は I-8（FND-10 で「著作エージェント定義」として削除）を再利用せず **I-9** を採番。(b) 設定オブジェクト等の新規 D は D-2（FND-8 で「著作済みノードファイル」として削除・O-3 へ再定義）を再利用せず **D-3** から採番する。I-8・D-2 は欠番＝退役として残す。

**影響範囲（2026-06-13 反映完了）**:
- `doc-system/03-analysis/02-io.md`: D-3〜D-8・I-9 を起票。D-1 に →FND-22 付与。
- `doc-system/03-analysis/03-processes.md`: P-5（D-3 生成元）・P-6（I-5 削除・D-3 消費）・P-1/P-2-*/P-3-*（D-3/D-4 消費）・P-4（D-5/D-6/D-7 消費）・P-7-1（I-9 消費）・P-7-2（D-8 消費）を再配線。P-5/P-6/P-1/P-4/P-7-1/P-7-2 に →DD-7、P-6 に →FND-21、P-7-1 に →FND-23 付与。
- `doc-system/02-what/03-spec.md`: SPEC-54（FR-13・P-7 記載内容入力）新設。
- `doc-system/03-analysis/03-processes.md`: P-5 本文の設定オブジェクト消費先に P-6 を追記（①の経路是正は分析層プロセス設計の修正であり SPEC 変更は不要）。
- `doc-system/03-analysis/00-dfd.md`: Level 1/2 を D ノード経由（P-5→D-3→P-6 等）に再描画。
- `.claude/agents/analysis-author.md`・`.claude/agents/structured-analysis.md`: D の分析層起票・図との並走を明記。
- D-3・I-9 に →DD-7 バックリファレンス付与。
