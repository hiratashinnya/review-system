# Issue #851：モデル層・推論予算の不整合解消（D案の決定記録・非規範）

> **決定：2026-11-23、オーナーが D 案を選択。** `.ai/skills/bloom-model-tier/SKILL.md` の
> Bloom Lv × 軸2 の12セルから導出し、工程ロールの表には**導出値と採用値だけ**を記載する。差異の理由は本 rationale に記録する。
> 現行の運用規範は `.ai/skills/issue-pipeline/SKILL.md`「層と推論予算」を参照する。
> 本文は選択の経緯、実際の変更値・理由・未実測の限界を記録する**非規範の判断記録**である。
> [Issue #851](https://github.com/hiratashinnya/review-system/issues/851)／[PR #865](https://github.com/hiratashinnya/review-system/pull/865)。
> 発端は Issue #829／マージ済み PR #847。Issue-pipeline の工程実行と Copilot は使用していない。

## 1. 基準の比較とオーナー決定

| 案 | 統一方法 | 利点 | 不採用／採用理由 |
|---|---|---|---|
| A | 閾値表を正本にして他を一律導出 | 導出が明瞭 | ロール固有の引上げ理由を維持できない |
| B | 現行 Claude frontmatter を正本にして層表を合わせる | 既存実行時設定を変えずに済む | `xhigh` は「大」「最大」の両方になり、軸2・抽象値の根拠を逆算できない |
| C | 現行の工程ロール表を正本にして閾値表・frontmatterを従わせる | ロール表で一元管理できる | 個別ロールの都合で汎用の Bloom 12セルを改変してしまう |
| **D：採用** | **閾値表から導出し、採用値は Skill の表、逸脱理由・経緯は本 rationale に分離** | 演繹的な一貫性と、品質のための例外管理を両立 | 理由を記録・点検する運用が必要 |

Dを選んでも、**元の frontmatter が正解だったと遡及的に認めるわけではない**。
軸2は共通 `.ai/skills/bloom-model-tier/SKILL.md` の「主要認知行為」を基準として
以下に分類し、異なる採用値が必要ならその理由を別に評価する。
本表の「軸2」は作業のモデル選定の判断であり、レビュー finding の `scope` 等と混同しない。

### 規範と判断記録の責務分離（2026-11-25 修正）

Issue #851のD案における**正本の責務**は、実行に必要なルール・ロールの
Bloom Lv／軸2／導出値／採用値が `.ai/skills/issue-pipeline/SKILL.md`、
**導出との差が生じた判断理由・旧値との差・選択肢A〜D・変更経緯・
Codex 5ロールとClaudeの比較結果・検証の実施状況**が本 rationale である。

第一弾では「理由をロール表の同じ行に併記する」と誤って実装し、同じ理由と
比較の説明表をSkillに重複させた。オーナーの2026-11-25明示指示
「rationalに書くことをSkillに書くな」に従い、説明をSkillから除去して
本ファイルへ集約した。**層・推論予算・PF写像・切替下限の運用上の意味は変更しない。**
この区分の変更はD案の選択の経緯を否定せず、規範の可読性と責務分離を是正する。

## 2. 9ロール：判定・変更前後・根拠

**参照した正本**：Bloom 12セル `.ai/skills/bloom-model-tier/SKILL.md`、
変更前の9行 `.ai/skills/issue-pipeline/SKILL.md`、9ファイルの
`.claude/agents/<role>.md` frontmatter、Claude 写像
`.claude/skills/bloom-model-tier/SKILL.md`、Codex 写像 `.ai/model-policy.json`。
変えるのは**ロールの表と必要な Claude frontmatter**であり、閾値表と写像は変えない。

| ロール | 認知行為（Bloom Lv／軸2） | 閾値表から導出 | 採用層／予算 | Claude 変更前 → 変更後 | 判定・逸脱の根拠 |
|---|---|---|---|---|---|
| issue-investigator | 調査対象の因果照合（Lv4／網羅性） | 中位／大 | 中位／大 | `sonnet/xhigh` → 同左 | 漏れのない調査報告を行い、裁定は上位へ渡す |
| ac-designer | AC妥当性の評価（Lv5／判断） | 最上位／中 | 最上位／中 | `opus/high` → 同左 | 曖昧な受入条件の評価を担当 |
| change-planner | 変更計画の設計（Lv6／判断） | 最上位／大 | 最上位／大 | `opus/xhigh` → 同左 | 制約と依存関係を統合して新規計画を構成 |
| plan-reviewer | 設計適否の評価（Lv5／判断） | 最上位／中 | 最上位／中 | `opus/high` → 同左 | 検証条件を評価する |
| test-writer | 反例・境界の抽出（Lv4／網羅性） | **中位／大** | **中位／大** | **`sonnet/high` → `sonnet/xhigh`** | 旧設定の「中」は現行閾値より低いため補正 |
| issue-implementer | 承認済み計画の適用（Lv3／網羅性） | 中位／中 | **中位／大** | `sonnet/xhigh` → 同左 | **意図的な予算引上げ**：実装差分と既存 Red/Green・影響面の見落としを抑え、既存の大予算を下げない。モデル層を引上げず、Lv3/判断への根拠なき付替えもしない |
| pr-reviewer | 実害・契約適否の評価（Lv5／判断） | **最上位／中** | **最上位／大** | **`sonnet/xhigh` → `opus/xhigh`** | **意図的な予算引上げ**：全変更ファイル・対称箇所・権限/fail-closeの評価で既存の大予算を維持。従来の中位モデルは判断セルの最上位に不足するため昇格 |
| issue-fixer | findingの根本原因分析（Lv4／網羅性） | **中位／大** | **中位／大** | **`sonnet/high` → `sonnet/xhigh`** | 旧設定の「中」は現行閾値より低いため補正。歴史的な根拠は別文書に保存 |
| adviser | 相談ごとに主要行為を判定（Lv・軸2可変） | 該当セル／予算可変 | **最上位固定／相談ごとの予算** | `opus/high` → 同左 | **層のみ意図的な固定引上げ**（2026-11-16のオーナー決定）。`high` は静的初期値で、相談が大・最大なら dispatch で `xhigh` へ引上げ |

**変更した frontmatter：3ロール**。`test-writer` と `issue-fixer` は予算を
中→大（`high`→`xhigh`）にした。レビュー担当 `pr-reviewer` は中位→最上位
（`sonnet`→`opus`）とし、既存の大予算（`xhigh`）は維持した。
この3変更はモデル利用量・コストを増やす可能性がある。一方で**モデル層や推論予算の引下げはない**。
`issue-implementer` は既存 `xhigh` を残し、「Lv3判断セルだから」と誤って説明せず
採用値が導出値より大きい**意図的な引上げ**と説明する。

## 3. Codex 既定5ロール：切替後の下限

`.ai/model-policy.json` の Codex tiers は低位＝`low`、中位＝`mid`、最上位＝`top`。
Codex budgets は最小＝`low`、小＝`medium`、中＝`high`、
大＝`xhigh`、最大＝`max`。具体モデルIDは runtime resolver が選ぶ。
Claude の写像は低位＝`haiku`、中位＝`sonnet`、最上位＝`opus`、
最小＝`low`、小＝`medium`、中＝`high`、大・最大＝`xhigh`。
後者は多対一なので **Claude の `xhigh` だけから元の抽象予算を逆算できない**。

| Codex 既定ロール | 採用層／予算 → Codex tier/effort | 整合後の Claude frontmatter | Codexから切替する際の条件 |
|---|---|---|---|
| issue-investigator | 中位／大 → `mid/xhigh` | `sonnet/xhigh` | 通常基準を満たす |
| test-writer | 中位／大 → `mid/xhigh` | `sonnet/xhigh` | 通常基準を満たす |
| issue-implementer | 中位／大 → `mid/xhigh` | `sonnet/xhigh` | 通常基準を満たす |
| issue-fixer | 中位／大 → `mid/xhigh` | `sonnet/xhigh` | 通常基準を満たす |
| adviser | 最上位／相談毎 → `top/<算定結果>` | `opus/high` | 中以下では満たす。大・最大では `opus/xhigh` 以上に引上げ、不能なら STOP |

**#829 の切替規範を変更しない**：比較下限は上表の通常基準ではなく、
*実際に Codex 実行者へ指定した*層と抽象予算である。
安全上のリスク信号等で上位指定したら、切替後 Claude も同じ抽象層・予算以上にし、
実行モデルでそれを確保できない場合は STOP する。層の不足を予算の過剰で相殺しない。
Codex `max` と Claude `xhigh` も抽象段階を保持して既存写像で照合する。
実 dispatch の到達・完走は**未実測**である。

## 4. 旧記述と変更範囲

- `.ai/rationale/issue-fixer.md` の Issue #308 時点の `sonnet/high` を消さずに、
  新しい現行閾値 Lv4／大と D 採用後の `sonnet/xhigh` を後続節で区別する。
- `.ai/skills/issue-pipeline/SKILL.md` の9行には Bloom Lv・軸2、導出値・採用値だけを記載し、**理由は本ファイルだけ**に置く。
  `.ai/skills/bloom-model-tier/SKILL.md` の12セルを修正しない。
- `.ai/model-policy.json`、`.claude/skills/bloom-model-tier/SKILL.md` の写像、
  既定実行者の割当て、#829 の切替発動条件・継続検査は変更しない。
- `adviser` の最上位固定は従来のオーナー決定を尊重する。静的
  frontmatter を全ケースの下限保証と取り違えない。

## 5. 機械検査の是非

**要（別 Issue で扱う提案）。** 3つの資産が別々に更新されると同じ不一致が再発するため、
9ロールの欠落、固定値、Bloom Lv/軸2→導出値、採用値の逸脱理由、Claudeの多対一写像、
5ロールの Codex 切替下限の**機械的に決まる部分だけ**の検査を推奨する。
主要認知行為・軸2の妥当性や例外採用自体は人間の判断であり、
単なる YAML と閾値表の完全一致テストでは、D 案が認める正当な引上げを誤検出する。
**Issue #851 は機械検査を実装しない**。新規 Issue が必要かは別途判断する。

## 6. 点検方法・実測の範囲

1. GitHub の各原本を取得し、ロール毎の主要行為→Bloom Lv→軸2→
   閾値表セル→抽象層／予算を個別に導出。採用値が違えば理由を別に確認。
2. `.claude/agents/` の9件を別々に読み、frontmatter の `model` と
   `effort` を Claude の写像へ対応させ、ロール表の採用値と比較。
3. 5ロールの採用値を Codex の `tier/effort` へ写像し、Claude の frontmatter と
   **抽象層・予算**で比較。これらは**静的な照合**であり切替の実行テストではない。
4. Codex 独立レビューは第1弾の旧HEADに対して `completed`・findings なし
   だったが、D案を反映した新HEADは**別途独立再レビュー**を要する。
5. `python3 -m asset_parity check`（MISSING なし）、
   `python3 -m unittest tests.unit.test_governance_sync` と
   `python3 -m maintainability_lint check` をCIまたは実行環境で確かめる。
   ローカル checkout がないため、未実行のテストを成功と記録しない。

**残る完了条件**：最新HEADに対する CI・独立レビューを確認し、
未解決の実害 finding が0件であること。これは PR の merge 承認を意味しない。
