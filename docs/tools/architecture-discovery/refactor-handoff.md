# Issue #745 C06 対応・変更申し送り

[Issue #745 の共通 AC C06](https://github.com/hiratashinnya/review-system/issues/745) と [設計発掘の親 Issue #835](https://github.com/hiratashinnya/review-system/issues/835) の間で、各変更の追従内容と担当を照合する。調査基準・実装照合は `main` [`4866a525c5ce923992a62cab3b6458d31bbda9dc`](https://github.com/hiratashinnya/review-system/commit/4866a525c5ce923992a62cab3b6458d31bbda9dc)。C06 の状態はこの棚卸し時点の**発掘 Issue**の状態で、リファクタリングのマージ状態と別に読む。

## 26 子 Issue の対応

| リファクタリング Issue | 発掘・受入担当 | Discovery status | 対応・基準での確認 |
| --- | --- | --- | --- |
| [#746](https://github.com/hiratashinnya/review-system/issues/746) K-01 karte/model.pyの解析・検証責務を分離 | D1 [#838](https://github.com/hiratashinnya/review-system/issues/838) | `pending` | [PR #796](https://github.com/hiratashinnya/review-system/pull/796) を基準 main に反映済み。 |
| [#747](https://github.com/hiratashinnya/review-system/issues/747) K-02 karte/model.pyのreview・正規化・表示責務を分離して負債ゼロ | D1 [#838](https://github.com/hiratashinnya/review-system/issues/838) | `pending` | [PR #799](https://github.com/hiratashinnya/review-system/pull/799) を基準 main に反映済み。 |
| [#748](https://github.com/hiratashinnya/review-system/issues/748) K-03 karte CLIのrender/status・状態集計責務を分離 | D1 [#838](https://github.com/hiratashinnya/review-system/issues/838) | `pending` | [PR #806](https://github.com/hiratashinnya/review-system/pull/806) を基準 main に反映済み。 |
| [#749](https://github.com/hiratashinnya/review-system/issues/749) K-04 karte CLIの更新verb・引数解析を分離して負債ゼロ | D1 [#838](https://github.com/hiratashinnya/review-system/issues/838) | `pending` | [PR #807](https://github.com/hiratashinnya/review-system/pull/807) を基準 main に反映済み。 |
| [#750](https://github.com/hiratashinnya/review-system/issues/750) K-05 karte similarity/touchedを責務分離して負債ゼロ | D1 [#838](https://github.com/hiratashinnya/review-system/issues/838) | `pending` |  |
| [#751](https://github.com/hiratashinnya/review-system/issues/751) K-06 karte通知フックの入力検証・通知判断を分離して負債ゼロ | D1 [#838](https://github.com/hiratashinnya/review-system/issues/838) | `pending` |  |
| [#752](https://github.com/hiratashinnya/review-system/issues/752) I-01 SubagentStop判定・進行ポインタを分離 | D2 [#839](https://github.com/hiratashinnya/review-system/issues/839) | `pending` |  |
| [#753](https://github.com/hiratashinnya/review-system/issues/753) I-02 subagent bind・成果物回収・解放を分離 | D2 [#839](https://github.com/hiratashinnya/review-system/issues/839) | `pending` |  |
| [#754](https://github.com/hiratashinnya/review-system/issues/754) I-03 worktree ledgerの保存・排他制御を分離 | D2 [#839](https://github.com/hiratashinnya/review-system/issues/839) | `pending` |  |
| [#755](https://github.com/hiratashinnya/review-system/issues/755) I-04 worktree ledger状態遷移・残留検出を分離 | D2 [#839](https://github.com/hiratashinnya/review-system/issues/839) | `pending` |  |
| [#756](https://github.com/hiratashinnya/review-system/issues/756) I-05 durable_lockとSessionStartの小規模負債を解消 | D2 [#839](https://github.com/hiratashinnya/review-system/issues/839) | `pending` |  |
| [#757](https://github.com/hiratashinnya/review-system/issues/757) G-01 gitgate/worktreeの引数解析・安全パス検証を分離 | D3 [#840](https://github.com/hiratashinnya/review-system/issues/840) | `pending` | [PR #787](https://github.com/hiratashinnya/review-system/pull/787) を基準 main に反映済み。 |
| [#758](https://github.com/hiratashinnya/review-system/issues/758) G-02 worktree collect/release・handoffを分離 | D3 [#840](https://github.com/hiratashinnya/review-system/issues/840) | `pending` | [PR #788](https://github.com/hiratashinnya/review-system/pull/788) を基準 main に反映済み。 |
| [#759](https://github.com/hiratashinnya/review-system/issues/759) G-03 worktree sweep・残留判定を分離して負債ゼロ | D3 [#840](https://github.com/hiratashinnya/review-system/issues/840) | `pending` | [PR #789](https://github.com/hiratashinnya/review-system/pull/789) を基準 main に反映済み。 |
| [#760](https://github.com/hiratashinnya/review-system/issues/760) G-04 gitgate adoptとCLIを責務別に分離 | D3 [#840](https://github.com/hiratashinnya/review-system/issues/840) | `pending` | [PR #791](https://github.com/hiratashinnya/review-system/pull/791) を基準 main に反映済み。 |
| [#761](https://github.com/hiratashinnya/review-system/issues/761) G-05 branch_source/policy.pyを責務分離して負債ゼロ | D3 [#840](https://github.com/hiratashinnya/review-system/issues/840) | `pending` | [PR #794](https://github.com/hiratashinnya/review-system/pull/794) を基準 main に反映済み。 |
| [#762](https://github.com/hiratashinnya/review-system/issues/762) B-01 GitHub API取得・branch protection証跡生成を分離 | D5 [#842](https://github.com/hiratashinnya/review-system/issues/842) | `pending` |  |
| [#763](https://github.com/hiratashinnya/review-system/issues/763) B-02 GitHubCollectorの取得責務を分割完了し負債ゼロ | D5 [#842](https://github.com/hiratashinnya/review-system/issues/842) | `pending` |  |
| [#764](https://github.com/hiratashinnya/review-system/issues/764) B-03 blocker_gate resolverの検証・waiver・評価処理を分離 | D5 [#842](https://github.com/hiratashinnya/review-system/issues/842) | `pending` |  |
| [#765](https://github.com/hiratashinnya/review-system/issues/765) B-04 blocker_gate model・contract・evaluatorを責務分離 | D5 [#842](https://github.com/hiratashinnya/review-system/issues/842) | `pending` |  |
| [#766](https://github.com/hiratashinnya/review-system/issues/766) B-05 waiver/closing referenceの解析・検証を責務分離 | D5 [#842](https://github.com/hiratashinnya/review-system/issues/842) | `pending` |  |
| [#767](https://github.com/hiratashinnya/review-system/issues/767) B-06 blocker_gate snapshot/CLIを分離して領域負債ゼロ | D5 [#842](https://github.com/hiratashinnya/review-system/issues/842) | `pending` |  |
| [#768](https://github.com/hiratashinnya/review-system/issues/768) L-01 feedback_ledgerの検証と状態集計を分離 | D4 [#841](https://github.com/hiratashinnya/review-system/issues/841) | `pending` |  |
| [#769](https://github.com/hiratashinnya/review-system/issues/769) L-02 project_status_syncのCLI・GitHub・modelを分離 | D5 [#842](https://github.com/hiratashinnya/review-system/issues/842) | `pending` | snapshot 判定から Project API の apply まで範囲を追加。 |
| [#770](https://github.com/hiratashinnya/review-system/issues/770) L-03 review_system CLI・frontmatter・criteria処理の小規模負債を解消 | N/A | `out-of-scope` | `review_system/` の製品 CLI・frontmatter・criteria が対象。 |
| [#771](https://github.com/hiratashinnya/review-system/issues/771) L-04 Claude review MCP serverを責務分離して全件返済を完了 | D2 [#839](https://github.com/hiratashinnya/review-system/issues/839) | `pending` | MCP の read-only review 呼出・状態参照まで範囲を追加。 |

### 担当範囲の調整

- **#769 は D5 [#842](https://github.com/hiratashinnya/review-system/issues/842)** が受ける。D5 の範囲に `project_status_sync/` と `.github/workflows/project-status-sync.yml` を加え、snapshot の投影・検証、Project 状態の読取り、変更計画・apply、CLI の診断レポート生成と Actions の発行を追う。依存関係の判定根拠は blocker 側のデータとして追う。D2 は主文脈が実装工程の着手で `In progress`、通常 STOP で `Ready` を設定する境界を扱う。[Level 0 の工程と同期](level-0.md) · [同期契約](../../../project_status_sync/README.md) · [#769](https://github.com/hiratashinnya/review-system/issues/769)
- **#771 は D2 [#839](https://github.com/hiratashinnya/review-system/issues/839)** が受ける。D2 の範囲に `.codex/mcp/claude_review/` の実行境界を加え、request/response、workspace・モデル、外部 PR 読取、Claude 起動・失敗・cooldown を追う。D1 はカルテ受入・通知を扱う。既定の工程ルートから MCP が呼ばれるかは実際の呼出口で確認する。[MCP 契約](../../../.codex/mcp/claude_review/README.md) · [#771](https://github.com/hiratashinnya/review-system/issues/771)
- D2 と D5 は着手時に自分の Issue 本文「変更申し送り（受入キュー）」にある F0 の担当範囲調整を確認し、変更 PR の到着に先立って、上記の対象パス・入出力・担当を発掘範囲に含める。完了直前にも受入キューを照合する。新規移設先が担当範囲をまたぐ場合は取り込み責任と関係先を記録する。[F0 の担当決定](https://github.com/hiratashinnya/review-system/issues/836) · [D2 受入先](https://github.com/hiratashinnya/review-system/issues/839) · [D5 受入先](https://github.com/hiratashinnya/review-system/issues/842)

## Stack G と統合済み変更

PR メタデータの merge SHA が基準 `main` の祖先であることを Git 履歴で確認した。D3 はこの統合後の公開 facade と分割先から着手する。以下の変更は F0 の目録と Level 0 に反映済みで、D3 の詳細図・根拠への取り込みは D3 で追う。

| refactor PR | merge SHA（基準の祖先） | D3 の差分確認・受入の起点 |
| --- | --- | --- |
| [#787 worktree の引数・安全パス・Git 補助分離](https://github.com/hiratashinnya/review-system/pull/787) | [`cc104f5adb1d6cf618f703be852f06249033c5d6`](https://github.com/hiratashinnya/review-system/commit/cc104f5adb1d6cf618f703be852f06249033c5d6) | `worktree.py` → `worktree_arg_*.py`、`worktree_path_validation.py`、Git 補助。入口互換と操作前のパス検証を確認。[移設された経緯](../../../.ai/rationale/gitgate-worktree-safety.md) · [回帰テスト](../../../tests/unit/test_gitgate_worktree_split.py) |
| [#788 collect/release・handoff の分離](https://github.com/hiratashinnya/review-system/pull/788) | [`843731a13087aa30cc02a2a8730b83a0fc428fc3`](https://github.com/hiratashinnya/review-system/commit/843731a13087aa30cc02a2a8730b83a0fc428fc3) | `worktree_collect_*.py`、`worktree_release_*.py`、`worktree_handoff_*.py`。handoff 検証・保存→台帳→解放、先に保存・確認する順序を追う。[安全性の経緯](../../../.ai/rationale/gitgate-worktree-safety.md) · [回帰テスト](../../../tests/unit/test_gitgate_worktree_g02.py) |
| [#789 abandoned-worktree sweep の分離](https://github.com/hiratashinnya/review-system/pull/789) | [`f53f5541beafb2e771401b8c7ed380ed0d55a1eb`](https://github.com/hiratashinnya/review-system/commit/f53f5541beafb2e771401b8c7ed380ed0d55a1eb) | `worktree_sweep*.py`。回収要否、`collected_to`、`release_pending` と残留掃引の条件を追う。[安全性の経緯](../../../.ai/rationale/gitgate-worktree-safety.md) · [回帰テスト](../../../tests/unit/test_gitgate_worktree_g03.py) |
| [#791 adopt・CLI の分離](https://github.com/hiratashinnya/review-system/pull/791) | [`ccac759abb881db77328a990de56a5620d304273`](https://github.com/hiratashinnya/review-system/commit/ccac759abb881db77328a990de56a5620d304273) | `adopt.py` / `cli.py` → `adopt_*.py` / `cli_*.py`。`adopt-branch` の PR/head、同名 ref、worktree 保持者照会と checkout 前の拒否を追う。[移設された経緯](../../../.ai/rationale/gitgate-adopt.md) · [API/CLI テスト](../../../tests/unit/test_gitgate_refactor_g04.py) · [worktree CLI テスト](../../../tests/unit/test_gitgate_refactor_g04_worktree_cli.py) |
| [#794 branch_source の責務分離](https://github.com/hiratashinnya/review-system/pull/794) | [`ccac759abb881db77328a990de56a5620d304273`](https://github.com/hiratashinnya/review-system/commit/ccac759abb881db77328a990de56a5620d304273) | `policy.py` → `source_*.py`・`github_client.py`・`validation.py` 等。起点を照合し検証した OID で分岐する契約と再確認を追う。[移設された経緯](../../../.ai/rationale/branch-source-policy.md) · [回帰テスト](../../../tests/unit/test_branch_source_refactor_g05.py) |

#791 と #794 の GitHub 記録は同一 merge SHA を指し、最終 head はそれぞれ [`1f86ab57f78705104f6477be91d34518f3952d0e`](https://github.com/hiratashinnya/review-system/commit/1f86ab57f78705104f6477be91d34518f3952d0e) と [`5fe1ac7f1f751650e8539311c997890ce3b3ae14`](https://github.com/hiratashinnya/review-system/commit/5fe1ac7f1f751650e8539311c997890ce3b3ae14)。基準の first-parent 履歴には #794 の merge があり、第2親から #791 の最終 head に到達する。統合の確認には `git merge-base --is-ancestor <merge SHA> <調査基準SHA>` と `git diff <merge SHA>^1 <merge SHA>` を使う。#794 の統合差分には #791 も含まれるので、個別の変更範囲は各 PR を参照する。

親 #745 の着手前合流対象も基準履歴にある。karte [#696](https://github.com/hiratashinnya/review-system/pull/696)・[#697](https://github.com/hiratashinnya/review-system/pull/697) はそれぞれ `dd3c9596e2f2a5aab85ffa3d78355ee064d9b3f4`・`2d7585f10c0fa5157899028ecdb4f521ab3af388`。branch_source [#740](https://github.com/hiratashinnya/review-system/pull/740)・[#741](https://github.com/hiratashinnya/review-system/pull/741) は [`c29613fc68a66963dee069c7f44188d94a667bca`](https://github.com/hiratashinnya/review-system/commit/c29613fc68a66963dee069c7f44188d94a667bca) に統合されている。K-01〜04 は対応表の PR から分割後の実装を D1 が照合する。

## オープン PR の発掘候補

2026-11-24（UTC）にオープン・未マージを確認した関連 PR。観測 HEAD は発掘候補の根拠とし、現行実装と図の根拠には基準 `main` を使う。

| PR・関連 Issue | 観測 HEAD | 発掘担当 | 確認する境界 |
| --- | --- | --- | --- |
| [#846 レビュー 0 件の記録と AC 照合](https://github.com/hiratashinnya/review-system/pull/846)・[#801](https://github.com/hiratashinnya/review-system/issues/801) | [`f62c28b886a61c25860c5e45b3dce15940290186`](https://github.com/hiratashinnya/review-system/commit/f62c28b886a61c25860c5e45b3dce15940290186) | D1 [#838](https://github.com/hiratashinnya/review-system/issues/838) | 0 件レビューの受理、round・原本記録と AC 照合。レビュー呼出と主文脈による AC 更新の工程接続は D2 [#839](https://github.com/hiratashinnya/review-system/issues/839) が確認。 |
| [#862 STOP 時の介入試行](https://github.com/hiratashinnya/review-system/pull/862)・[#513](https://github.com/hiratashinnya/review-system/issues/513) | [`8e145618f03f112023896e3956163323d578f583`](https://github.com/hiratashinnya/review-system/commit/8e145618f03f112023896e3956163323d578f583) | D2 [#839](https://github.com/hiratashinnya/review-system/issues/839) | Karte の STOP に関わる出力を受けて介入する Claude フックとセッション状態。Karte の出力境界は D1 [#838](https://github.com/hiratashinnya/review-system/issues/838) が確認。 |
| [#865 工程ロールのモデル層・推論予算](https://github.com/hiratashinnya/review-system/pull/865)・[#851](https://github.com/hiratashinnya/review-system/issues/851) | [`059aaaf53a1b47c363521f0a2c5c0efe82d8b3fc`](https://github.com/hiratashinnya/review-system/commit/059aaaf53a1b47c363521f0a2c5c0efe82d8b3fc) | D2 [#839](https://github.com/hiratashinnya/review-system/issues/839) | 工程ロールのモデル層・推論予算の閾値、規範、agent 設定の対応。 |
| [#866 オーナー判断の FBK 記録](https://github.com/hiratashinnya/review-system/pull/866)・[#513](https://github.com/hiratashinnya/review-system/issues/513) | [`2843e9651c78cbab84db1a7c0e7ecb9c24d699bc`](https://github.com/hiratashinnya/review-system/commit/2843e9651c78cbab84db1a7c0e7ecb9c24d699bc) | D4 [#841](https://github.com/hiratashinnya/review-system/issues/841) | 差分は FBK エントリ 3 件の追加のみ。判断の正本と Issue・PR の出典参照を確認。 |

発掘担当は着手時に関連 PR の一覧・状態・HEAD と最新 `main` を再取得する。PR が未マージのままクローズされた場合や変更の中止・範囲変更があった場合は、候補の状態と担当・確認範囲を見直す。

関連 PR のマージ直前に、変更側は発掘の進捗と最新 `main` を照合し、追従担当を確認する。発掘の完了前にマージされた差分は、発掘担当がマージ後の `main` の SHA を確認し、完了前に図・設計概要・根拠索引へ必要な変更を取り込む。発掘完了後は変更側が、当該 PR または先にマージする文書 PR で必要な追従を行う。[#835 の双方向ドリフト防止](https://github.com/hiratashinnya/review-system/issues/835)

## 使用手順

1. リファクタリング担当は着手時・マージ直前に [#835](https://github.com/hiratashinnya/review-system/issues/835) と表の担当発掘 Issue、最新 `main`、設計資料の SHA を確認する。PR 本文に `Discovery status: completed / pending / out-of-scope`、担当 Issue、比較対象の SHA、追従または申し送り先と受入状況を記録する。
2. **`completed`** ならリファクタリング側で PFD/DFD・設計概要・ADR 索引を差分照合し、必要なら当該 PR か先にマージする文書 PR で追従する。影響なしも根拠を PR に記録する。新判断がある場合は [既存 ADR の正本規則](README.md#保存先命名参照) に従う。
3. **`pending`** ならリファクタリング側が、担当 D1〜D5 の Issue 本文「変更申し送り（受入キュー）」へ、PR 番号・タイトル、比較した変更 HEAD、変更ファイル・移設先、責務・IF・処理順・データ入出力/保存・状態遷移・安全不変条件、rationale 移設先、回帰テストを記録し、PR 本文から参照する。マージ直前に記録の存在と充足を確認し、その時点で発掘完了なら `completed` へ切り替える。マージ後は比較した変更 HEAD を保持し、merge SHA を同じ申し送りに追記する。
4. 発掘担当は着手・完了直前に最新 `main` と受入キューを突合する。D2 と D5 は着手時から [F0 の担当範囲の調整](#担当範囲の調整) を適用する。受入記録には追従先と反映済みの SHA を残す。未吸収の関連 merge は発掘側が完了前に処置し、完了後の merge に伴う追従はリファクタリング側が担当する。並走時は確定成果物と比較 SHA によって担当を切り替える。双方を相互の blocker にしない。
5. **`out-of-scope`** は範囲外の理由を PR 本文に明記して C06 を N/A とする。開発基盤で未割当の変更は同じ明細を [#836「変更申し送り」](https://github.com/hiratashinnya/review-system/issues/836) で受け、担当の確定、スコープ調整、受入 Issue への転記とリンクまで未処理として追跡する。
