# 推奨処理順序（2026-07-10 棚卸し反映）

本ファイルは、識別子単位ノード・型別本文ポリシーの DD/FND 追加後に、open GitHub Issues と
doc-system-v2 open FND/Q/PEND の依存関係を踏まえて整理した推奨順序である。

## 前提

- #5 は親テーマ。コメントで「doc_system 構築完了 + review_system の doc_system 対応」が完了条件に更新済み。
- #127 は doc_system 完了の親。
- #108 は #127 の blocker と本文に明記されている。
- #94 はコメントで「backfill する」がオーナー確定済み。本文の「backfillしない推奨」は古い。
- #140/#141 は doc_system / review_system 用 config 操作エージェント。
- #142 は docidx archive 要否。dsv2 側の代替と `docidx.nodeyaml` の v2 共有利用を踏まえ、
  物理 archive へ移動しない判断で処理済み。
- #152 は scheduled 空欄対策。#94 は legacy backfill であり、今後の空欄流入防止・流出検出は別件として
  #141 後、#127 前に扱う。
- #154 は doc_system 完了物を配布・設定する installer。#127 で完了物の範囲を確定した後に扱う。
  GitHub Pages の更新設定は issue 本文どおりユーザー確認必須。
- #155 はエージェント・skills の PF 間同期。#128 後、#5 完了判断の前後で扱う。既存
  `asset-lateral-deploy` の手作業横展方針と自動同期案の整合監査を先に行う。
- #4 は #140/#141 と重複気味。
- #6/#7/#11 は review_system 旧ドキュメント/テスト証跡側の負債で、#128 配下に寄せるのが自然。
- #127 は機械検証だけで閉じない。open FND 9 / open Q 1 / deferred PEND 1 が完了判定を妨げるか
  後続許容か、dsv2 の仕様外・設計外実装やテスト著作の範囲を認識合わせする必要がある。

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

6. **#142 docidx archive 判断**（完了: 2026-07-10）
   - 理由: dsv2 index/dashboard/lookup が現行 v2 照会を担える一方、`docidx.nodeyaml` は
     `dsv2/meta.py` と `doc-system-v2/validate.py` の共有 YAML reader として現役のため、`docidx/`
     ごとの物理 archive は v2 実行系を壊す。
   - 反映: `docidx/README.md` に archive 判断を明記し、`docidx` skill と `dsv2/README.md` の参照境界を
     v1 archive CLI / v2 dsv2-native / 共有 `nodeyaml.py` に整理。`docidx/` は移動せず、現行コーパスの
     正本照会は `python3 -m dsv2` と通常のファイル検索へ寄せる。

7. **#140 → #141 config 操作エージェント**（前半 #140 完了: 2026-07-10 / 後半 #141 は次アクション）
   - 理由: doc_system 側を先に固め、その後 review_system 側へ横展開する。#4 は #140/#141 の親和的な元要求で、doc_system 側は #140 で吸収、review_system 側は #141 で扱う。
   - 反映（#140）: Codex custom agent `doc-system-config-operator` と repo skill `doc-system-config` を追加し、`doc-system-v2/config.yml` の作成・解説・変更時に FORMAT/config/schema/dsv2 と対応 SPEC/SCM/CFG/PROMPT ノードを照合する手順を明文化。PROMPT ノード `doc-system-config-operator doc-system config 操作エージェントプロンプト` で agent carrier を在グラフ化した。
   - 残り（#141）: review_system 側 config 操作エージェントへの横展開。doc-system 側資産をそのまま拡張せず、対象 config・検証・対応ノードを review_system 側の文脈で改めて切る。

8. **#152 scheduled 空欄対策**
   - 理由: #94 は v1→v2 移行 585 ノードの legacy backfill で完了済み。今後の空 `scheduled` の流入防止と流出検出は #127 完了判定の前に別件として閉じる。
   - 留意: issue 本文は「空は許容しない。流入、流出両方への対策が必要」。既存 legacy 値の backfill と、新規・更新時の空欄対策を混同しない。

9. **#127 doc_system 完了判定**
   - 理由: #141 と #152 まで揃ってから doc_system 構築完了を判断する。
   - 認識合わせ: issue 本文は「テスト、実装含む全ノード著作完了が必須」「dsv2 が該当する想定」「仕様外実装や設計外実装が多数ある見込み」としている。validate / drift / prompt-coverage の機械検証だけでなく、open FND 9 / open Q 1 / deferred PEND 1 が完了阻害か後続許容か、dsv2 の仕様外・設計外実装やテスト著作の是正範囲を先に確定する。

10. **#154 doc_system installer**
    - 理由: #127 で doc_system 完了物を確定した後、配布・初期設定・GitHub Pages 設定導線を installer として整える。
    - 留意: GitHub Pages はユーザー確認必須。自動実行、設定方法説明、設定しない、の選択肢を用意する。

11. **#128 review_system 文書の doc_system 対応**
    - 理由: #127 後に review_system 文書を doc_system 対応へ寄せる。#5 の完了条件にも関係する。

12. **#6/#7/#11 review_system 側の旧負債処理**
    - 理由: #128 配下で扱う。#11 の古いテスト名修正は #7 の UI 用語決定後が安全。

13. **#155 エージェント・skills の PF 間同期**
    - 理由: review_system 側の doc_system 対応後に、Claude Code / Codex CLI / GitHub Copilot 間の skill・エージェント・custom 指示・hook の同期方針を扱う。
    - 留意: 既存 `asset-lateral-deploy` は手作業横展を前提にするため、自動同期案との整合監査を先に行う。

14. **#5 親テーマの完了判断**
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
