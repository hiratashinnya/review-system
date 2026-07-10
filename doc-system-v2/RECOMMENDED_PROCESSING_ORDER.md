# 推奨処理順序（2026-07-10 棚卸し・stage completion issue expansion 反映）

本ファイルは、識別子単位ノード・型別本文ポリシーの DD/FND 追加後に、open GitHub Issues と
doc-system-v2 open FND/Q/PEND の依存関係を踏まえて整理した推奨順序である。

## 前提

- #5 は親テーマ。コメントで「doc_system 構築完了 + review_system の doc_system 対応」が完了条件に更新済み。
- #127 は doc_system 完了の親。
- #108 は #127 の blocker と本文に明記されている。
- #94 はコメントで「backfill する」がオーナー確定済み。本文の「backfillしない推奨」は古い。
- #140/#141 は doc_system / review_system 用 config 操作エージェント。
- #142 は docidx archive 要否。dsv2 側の代替と `docidx.nodeyaml` の v2 共有利用を踏まえ、
  物理 archive へ移動しない判断で処理済み（**issue #172 で refine**：`nodeyaml.py` のみ `dsv2/` へ
  分離し、残りを `archive/docidx-v1/` へ archive）。
- #152 は scheduled 空欄対策。#94 は legacy backfill であり、今後の空欄流入防止・流出検出は別件として
  #141 後、#127 前に扱う。
- #154 は doc_system 完了物を配布・設定する installer。#127 で完了物の範囲を確定した後に扱う。
  GitHub Pages の更新設定は issue 本文どおりユーザー確認必須。
- #155 はエージェント・skills の PF 間同期。#128 後、#5 完了判断の前後で扱う。既存
  `asset-lateral-deploy` の手作業横展方針と自動同期案の整合監査を先に行う。
- #157〜#165 は #127 完了判定前に残っていた open Q/FND、Sprint 1 materialization、stage gate、
  `current_stage` advancement を分解した issue 群。Issue 起票と PR は分離し、本 PR では進捗管理ファイルだけを更新する。
- #4 は #140/#141 と重複気味。
- #6/#7/#11 は review_system 旧ドキュメント/テスト証跡側の負債で、#128 配下に寄せるのが自然。
- #127 は機械検証だけで閉じない。open FND 9 / open Q 1 / deferred PEND 1 が完了判定を妨げるか
  後続許容か、dsv2 の仕様外・設計外実装やテスト著作の範囲を認識合わせする必要がある。
- Sprint 1 完了対象は、Sprint 2 / post-mvp が明示されたもの、本文や dashboard で Sprint 2 以降 defer が
  明示されたもの、ユーザーが明示 defer したものを除く Q/FND とする。それ以外の Q/FND は Sprint 1 完了対象として close する。
- Q-2 は #157 で「傘 SPEC マップを維持し、実害が出た時点で細分化する」方針を DD-23 化して close 済み。
- Sprint 1 対象だけを完了対象にする判断は、SRC/TD/TC/TR materialization と `current_stage` gate の両方に適用する。
- 一時検証では `current_stage` を `implementation` / `verification` に上げても validate エラー 0 だが、これは
  `nodes/06-implementation/src` と `nodes/04-verification/{td,tc,tr}` が未存在で、validator が
  `must_link_to` / `must_be_linked_from` を stage gate として全面評価していないためであり、完了判定にはならない。

## 推奨順序

1. **識別子単位ノードの土台整備: FORMAT/dsv2 body policy**（完了: 2026-07-09）
   - 対象 FND: `FORMATとdsv2ツールが1ノード2ファイル固定でbodyless・shared-bodyノードを表現できない`
   - 理由: SRC/TD/TC の全作業の前提。先に FORMAT / notation / schema / validator / dsv2 meta/rename/viewer の本文ポリシーを確定する。
   - 反映: `config.yml: body_policy`、`body_ref.file` / `body_ref.anchor`、YAML 走査 validator、bodyless/shared-body 対応 meta/rename/viewer を追加し、対象 FND を resolved 化。

2. **SRC と TD/TC の実装設計・検証規則化**（完了: 2026-07-09 / PR #147）
   - 対象 FND:
     - `SRC実装層のlayout・schema・存在検査が未材化で識別子単位ノードを収容できない`
     - `TD共有本文とTC本文なし・TD-TC-1対1を検証層ルールが表現できない`
   - 理由: SRC は `source.*` と implementation layout、TD/TC は `body_ref`・`test.*`・TD-TC exactly-one RULE が中心。共通 schema が関わるため、body policy 後に扱う。
   - 反映: `06-implementation/src` layout、`source.*` / `test.*` サイドカー属性、TD-TC exact link count、SRC/TC 実体参照検査、対応 FORMAT/config/schema/validator/dsv2 検証規則を PR #147 で反映し、対象 FND 2件を resolved 化済み。

3. **著作テンプレート/プロンプト追随**（完了: 2026-07-09）
   - 対象 FND: `著作テンプレートとプロンプトが識別子単位ノード・型別本文ポリシーに未追随`
   - 理由: FORMAT/schema/validator が先。先に prompt を変えると、現行 validator が受け取れない形式を著作する恐れがある。
   - 反映: TD shared body・TC bodyless・SRC bodyless の v2 テンプレート、`test-strategy` skill、`verification-author`、共通 authoring 契約、reconciliation-validator/reconciliation、PROMPT ノード本文を body policy / `body_ref.*` / `test.*` / `source.*` / TD-TC 1:1 前提へ同期し、対象 FND を resolved 化。

4. **#108 dashboard 自動集計**（完了: 2026-07-09）
   - 理由: body policy 後の meta 形に合わせて実装する方が手戻りが少ない。#127 の blocker。
   - 反映: `python3 -m dsv2 dashboard --root doc-system-v2` を追加し、stage/type/status 件数と
     `fnd/open`・`q/open`・`dd/decided`・`pend/open|deferred` の Markdown スナップショットを
     標準出力へ生成可能にした。`00-dashboard.md` は手書き運用を継続し、機械集計で検算する。

5. **#94 scheduled backfill**（完了: 2026-07-10）
   - 理由: dashboard 自動集計後に、空 scheduled / legacy / backfill 済みの状態確認がしやすい。要否は owner 決定済みで、実施スプリントと方式が残る。
   - 反映: `MIGRATION_REPORT.md` の v1→v2 移行 585 slug を対象に、空 `scheduled` 558 件を `sprint-1` へ backfill。既存値あり 27 件（`sprint-2` 25 件・`post-mvp` 2 件）と移行後追加 18 件は #94 対象外として保持。

6. **#142 docidx archive 判断**（完了: 2026-07-10・**issue #172 で refine 済み**）
   - 理由: dsv2 index/dashboard/lookup が現行 v2 照会を担える一方、`docidx.nodeyaml` は
     `dsv2/meta.py` と `doc-system-v2/validate.py` の共有 YAML reader として現役のため、`docidx/`
     ごとの物理 archive は v2 実行系を壊す。
   - 反映: `docidx/README.md` に archive 判断を明記し、`docidx` skill と `dsv2/README.md` の参照境界を
     v1 archive CLI / v2 dsv2-native / 共有 `nodeyaml.py` に整理。`docidx/` は移動せず、現行コーパスの
     正本照会は `python3 -m dsv2` と通常のファイル検索へ寄せる。
   - **issue #172 での refine**（本ブロッカーの解消）: `nodeyaml.py`（`re`/`typing` のみ依存の自己完結
     モジュール・参照元 `dsv2/meta.py`・`doc-system-v2/validate.py` の2箇所のみ）だけを `dsv2/nodeyaml.py`
     へ切り出し、残り（`scan.py`/`cli.py`/`query.py`/`render.py`/`model.py`）を `archive/docidx-v1/` へ
     `git mv`（PR8「消さない」）。上記「`docidx/` は移動せず」の判断は本 issue で更新された。

7. **#140 → #141 config 操作エージェント**（前半 #140 完了: 2026-07-10 / 後半 #141 は次アクション）
   - 理由: doc_system 側を先に固め、その後 review_system 側へ横展開する。#4 は #140/#141 の親和的な元要求で、doc_system 側は #140 で吸収、review_system 側は #141 で扱う。
   - 反映（#140）: Codex custom agent `doc-system-config-operator` と repo skill `doc-system-config` を追加し、`doc-system-v2/config.yml` の作成・解説・変更時に FORMAT/config/schema/dsv2 と対応 SPEC/SCM/CFG/PROMPT ノードを照合する手順を明文化。PROMPT ノード `doc-system-config-operator doc-system config 操作エージェントプロンプト` で agent carrier を在グラフ化した。
   - 残り（#141）: review_system 側 config 操作エージェントへの横展開。doc-system 側資産をそのまま拡張せず、対象 config・検証・対応ノードを review_system 側の文脈で改めて切る。

8. **#152 scheduled 空欄対策**
   - 理由: #94 は v1→v2 移行 585 ノードの legacy backfill で完了済み。今後の空 `scheduled` の流入防止と流出検出は #127 完了判定の前に別件として閉じる。
   - 反映: `validate.py` と `schema/sidecar.schema.json` で `scheduled` を非空必須にし、`dsv2 index` 側も空欄・欠落を `MetaError` で fail-close。移行後追加の空欄 12 件は完了済み/解決済みノードとして `sprint-1` に整理済み。

9. **#157 Q-2 を傘 SPEC マップ維持方針で DD 化して close**（完了: 2026-07-10）
   - 理由: open Q 1 件をユーザー判断 1 で閉じ、#127 完了判定前の判断待ちを減らす。
   - 反映: DD-23 を新設し、傘 SPEC マップ維持を在グラフ化。Q-2 は closed 配下へ移動し、open 義務辺を解消して `→DD-23` の昇格辺を付与。

10. **#158 / #159 / #165 / #164 FND 解消群**
    - #158: 完了（2026-07-11）。本文 resolved 済み open FND 2 件（`_drift` z バンプ誤検出、`backref check` open-but-backref 判定トートロジー）を、既存 backref と out-of-graph 対象の扱いを確認した上で lifecycle 上も resolved へ整理した。
    - #159: Sprint 1 の SPEC 本文系 open FND を解消する。
    - #165: RULE 横断索引と dashboard 表記の open FND を解消する。
    - #164: out-of-graph 著作資産伝播 FND の backref 対象を在グラフ化して close する。
    - 理由: Sprint 1 完了対象の open FND を先に解消し、materialization と stage advancement の前提を整える。

11. **#163 current_stage に応じた implementation / verification 必須接続 gate**
    - 理由: `current_stage` を上げた時に `must_link_to` / `must_be_linked_from` が全面評価されない抜けを先に塞ぐ。
    - 留意: #152 の scheduled / current_phase semantics と矛盾させない。stage gate は空 `scheduled` 流入防止とは別責務として扱う。

12. **#160 Sprint 1 対象 SRC 実装ノード materialization**
    - 理由: stage gate 実装後に、Sprint 1 対象の実装ノードを `nodes/06-implementation/src` へ materialize する。
    - 留意: Sprint 2 / post-mvp / 明示 defer は完了対象に含めない。

13. **#161 Sprint 1 対象 TD/TC/TR 検証ノード materialization**
    - 理由: SRC materialization と同じ Sprint 1 境界で、検証設計・ケース・結果ノードを materialize する。
    - 留意: TD/TC/TR の完了対象もユーザー判断 2 に従い、Sprint 1 対象に限定する。

14. **#162 current_stage を implementation から verification へ進める**
    - 理由: Sprint 1 の open Q/FND 解消、stage gate 実装、SRC/TD/TC/TR materialization 後に stage を進める。
    - 留意: `current_stage` 単独更新で validate エラー 0 になることは完了判定ではない。#163 の gate と #160/#161 の materialization を揃えてから進める。

15. **#127 doc_system 完了判定**
    - 理由: #141、#152、#157〜#165 まで揃ってから doc_system 構築完了を判断する。
    - 認識合わせ: issue 本文は「テスト、実装含む全ノード著作完了が必須」「dsv2 が該当する想定」「仕様外実装や設計外実装が多数ある見込み」としている。validate / drift / prompt-coverage の機械検証だけでなく、Sprint 1 完了対象外として残す Sprint 2 / post-mvp / 明示 defer の扱いを確認する。

16. **#154 doc_system installer**
    - 理由: #127 で doc_system 完了物を確定した後、配布・初期設定・GitHub Pages 設定導線を installer として整える。
    - 留意: GitHub Pages はユーザー確認必須。自動実行、設定方法説明、設定しない、の選択肢を用意する。

17. **#128 review_system 文書の doc_system 対応**
    - 理由: #127 後に review_system 文書を doc_system 対応へ寄せる。#5 の完了条件にも関係する。

18. **#6/#7/#11 review_system 側の旧負債処理**
    - 理由: #128 配下で扱う。#11 の古いテスト名修正は #7 の UI 用語決定後が安全。

19. **#155 エージェント・skills の PF 間同期**
    - 理由: review_system 側の doc_system 対応後に、Claude Code / Codex CLI / GitHub Copilot 間の skill・エージェント・custom 指示・hook の同期方針を扱う。
    - 留意: 既存 `asset-lateral-deploy` は手作業横展を前提にするため、自動同期案との整合監査を先に行う。

20. **#5 親テーマの完了判断**
    - 理由: #5 の完了条件はコメントで「doc_system のシステム構築完了かつ review_system のドキュメントや実装を doc_system 対応に更新すること」と明記されている。#127 と #128 系の後続が揃ってから閉じる。

## 検証スナップショット

本順序の記録時点で以下を確認済み。

- `python3 -m dsv2 index --root doc-system-v2`: 604 ノード
- `python3 -m dsv2 dashboard --root doc-system-v2`: attention nodes 38 件（#94 対象 legacy の空 `scheduled` 0 件）
- `python3 doc-system-v2/validate.py`: 604 ノード / エラー 0 件
- `python3 -m dsv2 drift --root doc-system-v2`: ドリフトなし
- `python3 -m dsv2 prompt-coverage --root doc-system-v2`: PROMPT カバレッジ欠落なし

2026-07-10 の GitHub Issue 棚卸しで、#152/#154/#155 を新規 open issue として反映し、#127 の認識合わせ要素を追加した。
上記のノード数・検証実測は変えていない。

2026-07-10 の stage completion issue expansion で、#157〜#165 を新規 open issue として反映した。
この更新は進捗管理ファイルのみで、コーパスノードの lifecycle や `current_stage` は変更していない。
