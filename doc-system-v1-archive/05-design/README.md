# 設計フェーズ index — 凍結セット（doc-system）

> spec-inspector 実装着手前に固める設計物。分析層（`03-analysis/`）の確定を前提とする。
> **設計フェーズ開始**: 2026-06-16（N2・analysis 確定済み）

## 凍結セット（着手順）

| # | 項目 | 成果物 | 状態 |
|---|---|---|---|
| A | モジュール/パッケージ構成・FileSystemPort | [01-modules](01-modules.md) | ✅ 改訂済み（MOD-1〜18, PORT-1）DD-13 v0.2 粒度改訂 |
| C | 永続層（DS1〜3・PRS1） | [02-persistence](02-persistence.md) | ✅ 著作済み（DS-1〜3, PRS-1） |
| ① | オーケストレーション（スイムレーン付きフローチャート） | [03-orchestration](03-orchestration.md) | ✅ 著作済み（ORC-1・ORC-2）DD-15 v0.1 ORC→E 変更 |
| ②' | スキーマ（ノード/config/出力フォーマット） | [05-static](05-static.md) | ✅ 著作済み（SCM-1〜3 系・計10。階層は -N 採番） |
| - | 設定インスタンス（config.yaml の各要素） | [05-static](05-static.md) | ✅ 著作済み（CFG-1＋CFG-1-1〜13・1要素1ノード） |
| ③ | プロンプト設計（著作支援＝LLM／skill＝LLM） | [05-static](05-static.md) | ✅ 著作済み。**著作エージェント軸**＝PROMPT-1〜7（`*-author`×5＋reconciliation＋reconciliation-validator・SPEC-27/FR-13・SPEC-39）。**skill 軸**＝PROMPT-8〜20（13 skill・FR-17／傘 SPEC-61・`carrier: skill`・DD-22・2026-07-01） |
| ④ | テスト戦略 | `tests/`（証跡・設計完成後に判断） | ⬜ 未着手 |
| D | ロギング規約 | 検査パイプライン stdout のみ・O-1/O-2/O-6 にて確定 | ⬜ 未着手 |

> **③プロンプトの訂正（2026-06-30）**: 旧「不要（LLM なし）・スキップ」は誤り。検査系（P-1〜6）は決定論的だが**著作支援（P-7-1 記載内容充填）は `*-author` LLM エージェント**であり、その規約は SPEC-27/FR-13（著作エージェントが外部参照なしに type/PREFIX/辺方向/本文4項目/RULE チェックリストを内包）に規定済み。これを実現する PROMPT ノードを著作（PROMPT-6＝reconciliation 書込・PROMPT-7＝reconciliation-validator 検証・ともに SPEC-39）。**PR#55 レビューで「1 LLM エージェント=1 PROMPT」粒度の取りこぼし（validator 欠落）を発見し PROMPT-7 を追補**＝LLM エージェント7つ（`*-author`×5＋reconciliation＋reconciliation-validator）に PROMPT を1対1対応させた。
> **③skill 軸の追加（2026-07-01・DD-22）**: skill も LLM プロンプト資産であるため PROMPT 設計ノード化（PROMPT-8〜20＝価値実現直結の 13 skill）。著作エージェント軸（SPEC-27/FR-13）とは別の**機能軸 FR-17／傘 SPEC-61**（SPEC-61-1 存在・SPEC-61-2 親辺・SPEC-61-3 キャリア属性）で束ねる。**skill｜agent は `carrier` 属性**で表し、将来の skill→agent 変換（①-C ハイブリッド）は carrier 属性＋版バンプで扱い要件軸の付け替えを起こさない。対象外4件（coverage-html/asset-lateral-deploy/agy-delegate/bloom-model-tier）は NFR-3/SPEC-46 検査対象のまま。残＝①-C の `.claude/` fan-out 実装。
> **② 外部アクタ IF**: CLI サブコマンドシグネチャ（`python -m spec_inspector [options]`）は ORC-1 本文に概要を記載。
> **判断ログ**: [DD-13/DD-14](../04-verification/04-decisions.md)（MOD 粒度 v0.2 改訂・FileSystemPort 粒度）

## 依存規則（1枚）

```
domain ← ports ← core（config / collector / parser / projector /
                        drift_checker / structure_checker / condition_checker / verification_checker /
                        filter / graph_coverage / spec_coverage / reporter / author / reconciler）
       ← adapters ← __main__（合成ルート）
```
- `core/*` は `domain.*` と `ports.*` だけに依存
- `adapters/*` が `ports.*` を実装（結線は `__main__` のみ）
