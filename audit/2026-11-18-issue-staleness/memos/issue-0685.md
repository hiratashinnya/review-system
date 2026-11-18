# Issue #685「issue_start の後続工程 dispatch が dispatch 元 cwd の対象 branch 上 checkout を要求し、adopt-branch は branch の未 checkout を要求するため、1b 以降（change-planner・test-writer・issue-implementer）の dispatch が成立しない」

- URL: https://github.com/hiratashinnya/review-system/issues/685
- 状態: closed（2026-11-18取得）
- 本文: 9590文字/ 120行。全文: `../raw/issues-2026-10.jsonl`
- AC: 16件（未チェック: 16）
- Issue参照: #655, #650, #371, #426, #502, #662, #663, #652, #538, #559, #691
- PR参照: #650
- 主見出し: ## 目的・背景 | ## 現状と根拠 | ### 観測（#655 の工程 1b で実測。以下は呼び出し元（主文脈）の報告値で、本起票時に再実行していない） | ### 該当コード（起票時に読取り確認） | ### 因果の整理 | ### 未確認事項 | ### 意図的設計の確認 | ## Scope | ### 設計案の比較と推奨（原案） | ## Out of scope | ## Acceptance criteria | ## 関連観測（範囲外・別原因。別 Issue 化はオーナー判断）
- 暫定評価: Closed・歴史的記録

## 本文内の現状・前提・依存記述（要時点照合）
- | A4 | 現状維持 | 変更なし | 1b 以降の dispatch が成立しない。**却下** |
- - 関連：#652（初回実 dispatch の検証。FBK の uncertainty が予定した種類の欠陥。#655 の merge まで保留中）、#662（1a の是正を同一 branch で継続する契約。継続入口が非初回検査を再利用する設計なら本件の結論が前提になる。原因は別で、#662 はパイプライン内で設計・実装する Issue のため、本件が直るまで 1b 以降で止まる）、#663（1b 以降の契約の隙間。独立）、#538（`codex_wo
- - 正式な parent／sub-issue／blocked-by 関係は設定しない（事実として、#655・#662 など 1b 以降へ進むパイプライン内 Issue は本件が直るまで進められないが、既存 Issue を変更しないためここでは設定しない。必要ならオーナー判断で blocked-by を追加する）。
- - **調整論点（実装の運用上の前提）**：#691のtriager/Advisoryに直接のroot cause重複はないが、正規issue-pipelineによる子Issue実装・実dispatchは#685の後続工程branch/OID矛盾により妨げられ得る。#685の修正前にパイプライン全体のlive成功を宣言しない。
- - **責務境界**：#685の修正Scopeは拡張せず、#691の実装計画で前提として追跡する。
- - **実装時の扱い**：双方の最新仕様・機械ゲート・テストを突き合わせ、既存契約を覆す変更は理由とオーナー承認を記録する。正式なGitHub relation/blocked-by設定は、本追記とは別に確定する。

## 点検記録
本文全体の状態・AC・リンクを走査。歴史的叙述のみでは古いと断定しない。関連先の最新状態と実コードは横断照合で検証し、未実測ACは合格扱いしない。
