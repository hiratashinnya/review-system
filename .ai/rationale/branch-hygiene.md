# branch-hygiene — 設計経緯・却下案・既知の制約

Claude Code (AI) が新設。ローカルブランチ ref の棚卸し・分類・削除をオーナー確認つきで行う repo 運用スキル。共通本文の SoT は `.ai/skills/branch-hygiene/SKILL.md`。

## 発端

セッションで「マージ済みで用済みのローカルブランチと stale worktree を整理する」手順を実地で回し、その手順を資産化する依頼を受けた。実地でやったことは (a) worktree の棚卸しと削除、(b) ローカルブランチの棚卸しと削除、の2つ。`asset-auditor` の点検で (a) と (b) を分けて評価した結果、**責務が2つに割れている**（PR1：もの＋発生源で分ける）と判明した。もの＝「管理下 worktree の実体（発生源＝dispatch 機構）」と「ローカルブランチ ref（発生源＝主文脈／過去の PR 運用）」で別物、寿命の管理主体も別。

## 却下案

### 案C（原案そのまま）＝ worktree 棚卸し・削除も1スキルに含める — 却下

`git worktree remove` / `git worktree prune` の直接実行をスキルに書くと、既存の確定設計と正面衝突する：

1. **単一削除経路の破壊**。`gitgate/worktree.py` は「worktree 実体の削除経路はここだけ」を契約として宣言し（Issue #354 PR-2）、`_remove_worktree_dir()` に「消してよいパスか」の判定（symlink／脱出検査・`git worktree list --porcelain` 登録確認）を集約している。第2の削除経路ができると、`status: running`（live dispatch 所有）と `stopped`（未回収）の保護、および「handoff を回収できていないのに worktree を消さない」が**呼び出し順序で守られている構造**を迂回できる。害はディスク使用量ではなく、レビューアが古い作業ツリーを掴んでレビュー結果の信頼性が壊れること＋未回収 handoff の喪失。
2. **明文の禁止に抵触**。`.ai/troubleshooting/issue-pipeline.md` が「台帳の直接編集や `git worktree remove` の直接実行はしない」と規定済み。
3. **一度削除した散文の再導入**。`.ai/rationale/issue-pipeline.md` に、同種の手順（回収→remove→switch）を SKILL 散文から外して機構化した経緯が保全されている。スキルとして書き戻すのはこの決定の巻き戻し（規範11 区分2＝手順書は本文を書き換える、の逆行）。
4. **判定方式の差異**。`gitgate` は「TTL・経過時間による判定を設けない。判定は台帳 `status` と実在の突き合わせだけ」と宣言している。「HEAD が origin/main の祖先か」「Issue/PR が closed か」を worktree 削除の判定条件に昇格させるとこの設計方針と競合する。

→ 採用案では worktree 節は**手順を書かず** `gitgate` verb と `.ai/troubleshooting/issue-pipeline.md` への1行委譲に留めた（共通本文 §5）。

### 案B＝ `issue-pipeline` に「掃除」節を追加して EXTEND — 却下

`issue-pipeline` は「1 Issue のライフサイクル」であり、掃除は「リポジトリ全体の定期棚卸し」で発生源も周期も別（PR1）。かつ案C理由3と同じく rationale の逆行になる。スキルが肥大化し Issue 処理中に掃除が auto-invoke される事故面も増える。

## 採用（案A）

**新規スキル = ローカルブランチ衛生のみ。** ローカルブランチ ref は台帳 `branch_name` 以外を見る資産が皆無で、`asset-auditor` が「真の穴」と判定した領域。特に **squash-merged ブランチ ref は `gitgate` の `_cleanup_branch_ref` が使う `merge-base --is-ancestor` 検査で構造上必ず残留し、後で `adopt-branch` の `BRANCH_ADOPT_LOCAL_EXISTS` を誘発する**（`gitgate/worktree.py` docstring が実害として明記）。このスキルはその穴を、機械判定でなくオーナー確認つきの運用として埋める。

## 既知の制約

- **worktree は触らない**。`gitgate` の `collect-worktree` / `worktree-release` / `worktree-forget` と `.ai/troubleshooting/issue-pipeline.md` が正本。`.claude/worktrees/` 配下でない手動作成 worktree の扱いはオーナー確認に倒す。
- **origin／リモート ref は削除しない**。ローカル ref 限定。
- **削除の可否判定を機械ゲートにしない**（`gitgate` の設計方針と整合）。祖先マージ・PR MERGED は「削除可の候補」として提示し、実行の可否はオーナーが決める（独断禁止・規範3／実行前報告・規範12）。
- **`prompt_coverage_targets`（`doc-system-v2/config.yml`）対象外**。in-graph の観測可能成果物を持たない repo 運用ハーネスのため、`issue-pipeline` / `agy-delegate` / `bloom-model-tier` と同区分。

## 4ツリー移植

Claude（`.claude/skills/`）・Codex repo-skill（`.agents/skills/`）・Copilot（`.github/skills/`）に wrapper を配置。依存は `git` CLI と `gh` CLI とオーナー対話のみで、`issue-pipeline` の agent 版が Copilot 非移植になった理由（Claude hook／Task 委譲／`bloom-model-tier` 依存）に該当しないため、Copilot にも移植する。`asset_parity/exceptions.py` への追記は不要（全適用ツリーに実ファイルが存在）。SKILL 本文は `.ai/skills/` が SoT で各 wrapper は薄い参照。
