# Issue #629 初回独立ローカルレビュー（Codex）

対象: base b72d94bd → 504868bc2fbe68f18c01d63d4c15188b69cf9a6c。
オーナー承認の #629 限定運用例外に基づく公開前レビュー。PR は未公開、PR CI は未実施。

## 1. 判定

要修正。F-629-01 は canonical ledger への新しい running entry が既存 Claude の worktree 自動束縛を妨げる退行である。

17 ファイルの git diff 全627行を1–100、101–200、201–300、301–400、401–500、501–600、601–627行として欠落なく末尾まで読んだ。生成 instructions、hook 両ミラー、policy 1.2、コード、テスト、設計、失敗ログを含む。共有コードの編集、ブランチ切替、commit/push、外部投稿は行っていない。仮説再現は一時 Git fixture 内のみ。

固定 argv/merge 戦略、引数 schema、非ゼロ unittest 成功判定、内容 CAS、全2親/tree、pending commit/push fence、登録の live PR/exact OID/clean 検証、認可 request/workspace/repository/branch/session の整合検査、再登録と予約の CAS、API 不要の abort/recovery を既存 engine との接続から確認した。fork/default branch/同一head-base/detached拒否も既存 live 検査を再利用する。Claude fixer-only、既存 Codex entry の拒否、登録 CLI の両 host 全role拒否、raw merge/PR merge 禁止のコード契約は維持される。Copilot の信頼操作者登録は host認証や OS sandbox を謳わず、限界を明記している。

新規 production module は68行で stdlib を利用し、baseline 差分はない。policy/正本/生成 asset は追随している。ローカル保存ログは target 43件 OK、asset_parity 0 MISSING（既存 heuristic staleness表示あり）、maintainability violations=0 accepted_debt=94、guidance_sync OK。全unitログはレビュー時に実行中で空だったため、その成功は評価していない。これらは PR CI 合格を示さない。

## 2. Finding

### F-629-01
harm: real
harm_detail: Copilot 登録を使った clone で後続 Claude subagent の差分検出による worktree 束縛が ambiguous-running となり、既存の自動実行経路が利用できなくなる。
severity: major
scope: in
locus: gitgate/base_copilot.py:37, issue_start/worktree_ledger.py::resolve_worktree_for_agent
summary: Copilot 認可を共有台帳の running dispatch として残すため、既存 Claude consumer が別 platform の認可を live Claude dispatch と誤認する。
evidence: 実 Copilot fixture で登録→start→continue が committed となっても entry.status は running、Claude候補1件と非一致agent_idで resolve_worktree_for_agent が (None, ambiguous-running) を返し、同entryをreleasedにした対照では候補/diffを返した。
expected: Copilot認可とoperation証跡を維持しながら、Claude dispatch がない場合の既存 worktree 差分束縛が Copilot entry の存在に左右されない。
recheck: 下記一時Git再現を実行し、Copilot登録中/pending中/committed後/aborted後のいずれでも単一Claude候補が既存条件どおりdiffで束縛され、実Claude running entryがある場合は拒否されることを確認する。
status: open

再現手順（レビュー時実行、共有コードは無変更）:

```python
from tests.unit.test_base_copilot import CopilotIntegrationTests
from issue_start import worktree_ledger
case = CopilotIntegrationTests('test_conflict_continue_two_parents')
try:
    case.setUp()
    case.start()
    case.resolve()
    case.continue_()
    (case.main / '.claude/worktrees/agent-visible').mkdir(parents=True)
    print('copilot state:', case.entry()['status'],
          case.entry()['base_integrations'][-1]['state'])
    print('fallback:', worktree_ledger.resolve_worktree_for_agent(
        case.main, agent_id='different'))
    case.mutate(lambda entry: entry.update(status='released'))
    print('control:', worktree_ledger.resolve_worktree_for_agent(
        case.main, agent_id='different'))
finally:
    case.doCleanups()
```

観測結果:

```text
copilot state: running committed
fallback: (None, 'ambiguous-running')
control: ('.claude/worktrees/agent-visible', 'diff')
```

## 3. 次の処置

F-629-01 を主文脈へ差し戻す。処置担当の推奨は権限境界・共有ledger判断を扱える高推論予算層。処置方針はオーナー専権とし、本 reviewer は是正を実行しない。是正後は別文脈による再レビューが必要。

## 4. Owner report / merge

clean ではないため owner report と手動 merge 判定への引渡しは未実施。公開前ローカルレビューであり、GitHub承認・CI合格・公開許可を意味しない。
