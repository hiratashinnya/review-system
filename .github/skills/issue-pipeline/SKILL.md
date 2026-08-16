---
name: issue-pipeline
description: Orchestrate open GitHub Issues end-to-end (implement→PR→review→merge→close) one by one, while keeping owner decisions and progress management in the main thread.
---

# Issue 処理パイプライン（implement → PR → review → merge → close）

複数のオープン Issue を 1件ずつ完結させるオーケストレータ。主文脈は順序決め・意思決定・進捗管理を担い、実装/レビューは専用エージェントへ委譲する。

## 基本フロー

0. バックログ棚卸しの契機（前回から1暦月経過／open が純増 +15・総数 70 超）に該当するか1行で判定し、該当時だけ棚卸しの実施をオーナーへ提案する。運用の実体は [docs/tools/backlog-triage.md](../../../docs/tools/backlog-triage.md)（ここでは再掲しない）。判断主体はオーナーのままで、起票の抑制ではない。
1. オープン Issue の依存関係を確認し、推奨処置順を作る。
2. オーナー合意後、Issue ごとに以下を直列で完了する。
   - 実装担当: 実装 → commit/push → PR
   - レビュー担当: レビュー → 必要なら差し戻し → clean 判定後マージ
3. `Closes #N` で閉じない場合は Issue を手動クローズする。
4. 1件が merge & close 完了してから次の Issue に進む。

## 運用ルール

- Copilot では `issue-implementer` / `pr-reviewer` の専用エージェントは未移植。ここでの「実装担当」「レビュー担当」は、利用可能な実行手段に置き換えて運用する。
- 曖昧・矛盾・情報不足は握りつぶさず STOP 報告し、前提/選択肢/推奨を添えてオーナー判断を仰ぐ。
- スコープ外対応は現 PR に混ぜず、別 Issue として切り出す。
- 先送り・繰り越し・対応不要の判断を AI が独断で決めない。
- レビュー指摘と対応内容は PR コメントに AI 対応である旨を明記して残す。

## done

- 推奨順の提示と合意が取れている。
- 各 Issue が implement→PR→review→merge→close を完走している。
- 先送り/据え置きはオーナー明示判断が残っている。
