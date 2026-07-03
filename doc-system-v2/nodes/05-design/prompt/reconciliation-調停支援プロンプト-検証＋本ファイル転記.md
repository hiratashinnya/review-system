著作出力（tmp ノード草案）に対する**調停プロンプト**。草案スキーマの検証機能（P-7-2-1）に加え、検証合格後に草案を本ファイルへ転記する調停機能（P-7-2-2 本ファイル転記）を併せ持つため PROMPT 化する（オーナー指示）。SPEC-39 の実体＝`.claude/agents/reconciliation.md`。
**バージョン**: 1.0
**目的**: (1) 検証＝reconciliation-validator が返した VALIDATION_OK ブロック（validated・self_fix）を前提に、id 欠如・ref_version 不一致・残存 kind/status・to のリスト記法・resolved FND の元 forward 辺残存等の確定修正を tmp 上で適用する（検証ロジックは再実装せず validator 判定を信頼＝P-7-2-1）。(2) 調停＝self_fix 適用後の草案を `doc-system/` または `docs/` 配下の本ファイルへ Write/Edit で確定転記し、全書込完了後に tmp を掃除する（P-7-2-2 本ファイル転記）。id 欠如等の構造違反検出時は転記を中断し主文脈へ差し戻す（SPEC-39 系列・fail-close）。
**入力変数**: `sprint`（current_phase）／`validation_ok`（validator の VALIDATION_OK ブロック＝validated・self_fix。記載内容 I-9）。`validation_ok` 欠如・ROLLBACK 含みは書込せずエラー返却。
**出力形式**: 本ファイル（`doc-system/`・`docs/` 配下）への確定書き込み（D-8 草案の正本反映）＋ `tmp/<sprint>/` の掃除。完了報告は DONE ブロック（layer/sprint/written/applied_self_fix）。
**注意事項**: 検証前（validation_ok 無し）・ROLLBACK 含み・self_fix 適用不能のいずれも書込せず主文脈へ返す（fail-close）。Bash は `python3 -m docidx`（書込位置特定）と `python3 -m backref`（FND 辺逆転の機械実行）専用、それ以外の本文編集は Write/Edit のみ（場当たり sed/awk/echo 禁止）。検証ロジックは再実装しない（validator 専権・二重実装ドリフト防止）。
