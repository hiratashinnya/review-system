# Issue #851：モデル層・推論予算の不整合の照合と決定案（非規範・未承認）

> **状態：オーナーによる A/B/C/D の選択待ち。** 本文の「導出候補」「提案」は現行設定の変更を意味しない。
> 2026-11-23 に GitHub `main` の各ファイルを読んで照合した第1弾の記録である。Issue-pipeline は実行していない。
> 対象 Issue：[#851](https://github.com/hiratashinnya/review-system/issues/851)。
> 発端：[#829](https://github.com/hiratashinnya/review-system/issues/829)／マージ済み [PR #847](https://github.com/hiratashinnya/review-system/pull/847)。

## 1. 定義と読取元

- **閾値表**：`.ai/skills/bloom-model-tier/SKILL.md`「閾値表（PF中立）」にある Bloom Lv × 軸2（網羅性／判断）の12セル。
- **現行ロール表**：`.ai/skills/issue-pipeline/SKILL.md`「層と推論予算」の9行。既定実行者は同文書の「既定実行者」で決まる。**この表は本 PR では変更しない**。
- **Claude 実設定**：`.claude/agents/<role>.md` の先頭 `model:`／`effort:`（9ファイルを個別に確認）。
- **Claude 写像**：`.claude/skills/bloom-model-tier/SKILL.md`（低位→haiku、中位→sonnet、最上位→opus；最小→low、小→medium、中→high、大・最大→xhigh）。
- **Codex 写像**：`.ai/model-policy.json`（低位→low、中位→mid、最上位→top；最小→low、小→medium、中→high、大→xhigh、最大→max）。tier の具体モデル ID は resolver が選ぶため固定しない。
- **切替契約**：`.ai/skills/issue-pipeline/SKILL.md`「Codex 実行者が上限で止まったときの切替」。**実際に Codex 実行者へ指定した抽象層・予算より低い Claude への切替は禁止**。モデル層と予算は別々に比較し、一方の過剰を他方の不足の埋め合わせにしない。
- **過去の根拠**：`.ai/rationale/issue-fixer.md`。古い `sonnet/high` の経緯は残し、現行閾値表との不一致は別注で明示する。

以下は「資料からの事実」と「軸2についての提案」を区別する。軸2は役割の主要な認知行為による評価案であり、機械的に確定した実行時設定ではない。

## 2. 選択肢（オーナー専権）

| 案 | 正とする基準 | 利点 | リスク／留意点 |
|---|---|---|---|
| A | 閾値表を正本にしてロール表と frontmatter を導出 | 意味と設定の対応が簡潔で自動検査向き | リスク引上げ等の意図的例外の置き場がなく、実設定を勝手に下げるおそれ |
| B | 現行 frontmatter を正としてロール表を合わせる | 実行時 model／effort の変更が少ない | 閾値表からの導出根拠が曖昧、`xhigh` から「大／最大」を逆算できない |
| C | 現行ロール表を正として閾値表と frontmatter を合わせる | ロール毎の表示が一意になる | 汎用閾値表を個別ロールに合わせて改変し、他の利用者へ影響する |
| **D（推奨・未承認）** | **閾値表を導出元とし、ロール表に採用値と、導出から逸脱する場合は理由を併記** | 導出と実運用上の引上げを区別でき、無断の実設定変更を避けられる | 逸脱の判断と根拠を維持する負担がある |

提案 D のもとでも **「逸脱が見える」ことと「逸脱を承認済みにする」ことは別**である。軸2・採用値・変更する frontmatter はオーナー決定後に確定する。現在はどの案も承認済みとして記録しない。

## 3. ロール別対応表：実際の値と導出候補

| ロール | 主な認知行為・軸2の提案 | Bloom | 閾値表からの導出候補（層／予算） | 現行ロール表 | 現行 Claude `model/effort` | 現時点の差分と判断待ち |
|---|---|---|---|---|---|---|
| issue-investigator | 原因・影響の照合／網羅性 | Lv4 | 中位／大 | 中位／大 | sonnet/xhigh | 一致 |
| ac-designer | AC の妥当性評価／判断 | Lv5 | 最上位／中 | 最上位／中 | opus/high | 一致 |
| change-planner | 計画の設計とトレードオフ／判断 | Lv6 | 最上位／大 | 最上位／大 | opus/xhigh | 一致 |
| plan-reviewer | 検証設計・計画の合否評価／判断 | Lv5 | 最上位／中 | 最上位／中 | opus/high | 一致 |
| test-writer | 境界・反例の網羅／網羅性 | Lv4 | **中位／大** | **中位／中** | **sonnet/high** | 両者とも導出候補より予算が低い |
| issue-implementer | 承認済み計画の適用／網羅性（対案：判断） | Lv3 | 中位／中（判断なら中位／大） | 中位／中 | sonnet/xhigh | frontmatter は中より大きい。軸2と引上げ理由は未決 |
| pr-reviewer | 実害・整合性の評価／判断（対案：網羅性） | Lv5 | **最上位／中**（網羅性なら中位／最大） | 最上位／中 | **sonnet/xhigh** | モデル層が導出候補より低い。予算の多さで補償不可 |
| issue-fixer | 根本原因と責任箇所の分析／網羅性 | Lv4 | **中位／大** | **中位／中** | **sonnet/high** | 両者とも導出候補より予算が低い。旧 rationale の表現も要注記 |
| adviser | 相談事項に応じて決定／相談内容依存 | 可変 | **最上位固定／該当 Lv・軸2の予算** | 最上位／相談内容で引く | opus/high | 最上位固定は2026-11-16決定。予算が大・最大なら dispatch で引上げが必要 |

**読み方**：`pr-reviewer` は「最上位／中」と「中位／最大」が異なるセルであり、`sonnet/xhigh` だけではどちらを意図したか確定できない。`issue-implementer` も同様に、`xhigh` は判断セルまたは安全側の引上げか判別できない。「同じ `xhigh`」だけで抽象予算が大・最大のどちらかを逆算しない。

## 4. Codex 既定5ロールの切替下限（D案採用時の候補）

次表は **閾値表からの導出候補を Codex 実行者へ指定した場合** の比較である。実際の dispatch でリスク引上げされた場合は、必ず**その実指定値**を下限として再判定する。既定実行者の割当て自体は #829 で決定済みであり変更しない。

| ロール | Codex 候補（抽象層／予算 → tier／effort） | Claude 既存値 | 候補下限を満たすか／必要な操作 |
|---|---|---|---|
| issue-investigator | 中位／大 → mid/xhigh | sonnet/xhigh | 満たす |
| test-writer | 中位／大 → mid/xhigh | sonnet/high | **不足**。切替時は少なくとも sonnet/xhigh へ引上げ（または STOP） |
| issue-implementer | 中位／中 → mid/high | sonnet/xhigh | 満たす（軸2が判断＝大でも満たす） |
| issue-fixer | 中位／大 → mid/xhigh | sonnet/high | **不足**。切替時は少なくとも sonnet/xhigh へ引上げ（または STOP） |
| adviser | 最上位／相談内容依存 → top／その予算 | opus/high | **条件付き**。相談に必要な予算が中以下なら満たす。大・最大なら opus/xhigh への引上げ（または STOP） |

Codex の「最大」は `max`、Claude の「大／最大」はどちらも `xhigh` に対応する。**PF 固有 effort 文字列の辞書順で優劣を判定しない。** 抽象予算を保持して比較し、Claude の写像で最後に変換する（#829 既存契約のまま）。

なお、この表の「満たす／不足」は **候補と静的 frontmatter の比較結果** であり、Codex の実行・Claude 再 dispatch の成功を実測したものではない。

## 5. 決定後の実装順と影響

1. オーナーが本 Issue に **A/B/C/D** を選択し、軸2の対案・逸脱を採用するかも決める。Dなら例外毎に理由を記録する。
2. 選択に基づき共通ロール表の9行と閾値表との関係を規範に反映する。汎用 Bloom 閾値表自体は D では変更しない。
3. 影響する `.claude/agents/*.md` の model/effort を明示承認の範囲で更新する。必要なら変更前後の値、変更理由、実行コストと層の変化を PR 本文に列挙する。
4. `.ai/rationale/issue-fixer.md` の旧判断は史実として残し、選定根拠の現行値と未承認値を区別する。
5. 選択後の切替下限と **実 dispatch の指定値** が異なる場合は、例外・上位指定を尊重して比較する。#829 の切替規範本文は矛盾が生じた場合だけ修正する。

`adviser` の最上位固定、Claude の写像表、`.ai/model-policy.json` の tier→model ID、既定実行者、切替の発動条件は #851 では変更しない。

### frontmatter 変更前後の事実

**第1弾では変更なし（9ロールすべて）**。上表は変更提案ではなく読取結果である。特に `test-writer`／`issue-fixer`／`pr-reviewer` は実行時モデル／予算を変えうるため、オーナー決定前に修正しない。

## 6. 機械検査の要否（提案・未承認）

**要：後続の別 Issue に分離することを推奨。** 層表と frontmatter と閾値表の3箇所が独立に編集されると再び不整合が生じうるため。反面、主要認知行為・軸2・例外理由は人間の判断を含み、単純な完全一致検査では誤検知や例外潰しが起きる。

対象にするなら、(a) 明示した Bloom Lv・軸2からの導出、(b) オーナー承認済みの採用値・例外理由、(c) 予算の `xhigh` 多対一写像、(d) 9ロール／Codex既定5ロールの欠落と下限比較、の**機械的な部分だけ**を検証する。機械検査の実装は本 Issue の Out of scope なので行わない。要否の最終決定もオーナー判断として記録する。

## 7. 検証記録と未達条件

- GitHub `main` の以下を個別に取得：`.ai/skills/bloom-model-tier/SKILL.md`、`.ai/skills/issue-pipeline/SKILL.md`、`.claude/skills/bloom-model-tier/SKILL.md`、`.ai/model-policy.json`、`.ai/rationale/issue-fixer.md`、9ロールの `.claude/agents/*.md` 先頭。表の値はこれらの直接読取から転記した。
- 比較方法：Bloom Lv と提案した軸2を12セルに当て、抽象層／予算を得る。Claude と Codex の写像は**別々に適用**し、静的 `model/effort` と両軸を比較した。役割の行為分類は提案であり未承認。
- 実行テスト、`asset_parity check`、`test_governance_sync.py`、`maintainability_lint check`、実 dispatch、独立レビューはいずれも **この照合時点では未実測**。PR の CI 成否を別途確認する。
- **未達 AC**：オーナー選択記録、選択に基づく本番規範・frontmatter の整合、最終実測、独立レビュー clean。未承認のまま合格へ進めない。
