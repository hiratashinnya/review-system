# Issue #594: PR base 取り込みのオーナー決定

対象: https://github.com/hiratashinnya/review-system/issues/594

## 確定した権限範囲

2026-10-09、オーナーは本 Issue の処置を依頼したチャットで次を承認した。

> issue-fixer のみ、base→PR ブランチの取り込みと衝突解消を許可する案です。解消後にテストし、判断できない衝突は停止で良い

- 対象ロールは `issue-fixer` のみ。
- 許可対象は OPEN PR の base から、その PR の head ブランチへの取り込み。
- fixer が衝突内容を編集して解消し、解消後にテストする。
- 仕様判断が必要など、判断できない衝突は報告して停止する。
- PR 自体の merge / auto-merge 禁止は維持する。

## 比較と判断理由

専用の取り込み経路なら、PR 自体をマージする権限を付与せず、衝突のために CI とレビューが止まる問題を処置できる。衝突時に常に人へ戻す案では発見元の人手依存が残る。implementer へも許可する案は権限範囲が広がるため、今回は fixer に限定する。

## 実装設計への制約

- 任意の ref、Git option、merge 戦略を渡す汎用 merge wrapper を作らない。
- live PR の repository、head、base と fresh fetch の exact OID、現在の worktree と branch を照合する。
- 開始前の dirty index/worktree、別操作の merge/rebase/cherry-pick、fork PR、同一 head/base を拒否する。
- 専用の未完了状態を task / role / attempt / worktree / 元 HEAD / base OID / MERGE_HEAD に束縛する。衝突を成功扱いにしない。
- continue は未解消 index を拒否し、確定コミットの全親列と tree を検証する。
- abort が解消作業の編集を失う範囲を明記し、無関係な変更を検出したら拒否するか事前に復旧成果物へ保存する。
- Codex の inner は共通 Git を read-only とする既存境界を維持する。取り込み・確定は host 側、衝突内容の編集と検証は fixer 側へ分ける。
- protected asset の衝突は承認済み patch 経路に束縛するか停止する。契約ファイルの更新を古い契約のまま無検査で継続しない。
- 衝突中は `git write-tree` が失敗するため、既存 publish snapshot の単純な流用を避ける。
- #533 の classifier 是正はこの Issue に混ぜない。

## 受入検証

実 Git repository で正常取り込み、既に取り込み済み、実衝突の編集→テスト→確定、中止を検証する。誤った role / PR / repository / branch / OID、API failure、dirty tree、別操作の状態、偽造 state / MERGE_HEAD、第二親のすり替えを拒否する。双方の PF で PR merge / auto-merge の拒否が継続することも確認する。

この文書はオーナー決定と設計制約の記録である。実装・テストの完了を示すものではない。

## 本 Issue の実行経路に関する運用例外

2026-10-09、正規 supervisor の起動が必須認証ファイル不足による `CODEX_SUPERVISOR_AUTH_SOURCE_INVALID` で停止した。オーナーは同チャットで次を明示承認した。

> はい、この Issue に限り、別コンテキストで実装し、独立レビューする運用例外を認めます

この承認は #594 の実装と独立レビューの起動経路に限定する。既存 supervisor の認証検査や恒常的な dispatch 契約は変更しない。PR merge 禁止、対象 role の限定、コード構築原則、実装・是正・レビューの役割分離は維持する。push・PR 公開は検証済み差分と本文をオーナーへ提示してから扱う。

実装は新規の権限境界設計を含むため Bloom Lv6 創造・判断ボトルネック、初回レビューは権限境界・共有資産の変更を評価するため高い推論予算を使用する。

## 初期凍結設計の routine 決定（履歴）

以下は初回実装時の判断を保存した履歴であり、旧 supervisor 接続については後続の「再レビュー後の実装範囲・引継ぎ決定」を優先する。

詳細の現行契約は `docs/tools/gitgate-base-integration.md`（policy 1.0）を正本とする。

- 汎用 merge wrapper ではなく、専用 verb 3種と trusted main ledger の operation WAL に分離した。
- Codex の既存 large supervisor module を変更して新しい baseline 免除を作る案に対し、責務が明確な100行以内のhost adapterから既存CAS helperを利用する案を採用した。専用経路の実stage/commitを `via=integrate-base` とoperation/全親列/base/tree/testで記録し、既存push/karte.closeまで実経路テストする。
- 衝突専用のsnapshotは全stage indexとtracked/untracked内容の長さ付きfingerprintを用いる。未解決indexにwrite-treeを要求しない。
- abortはAPI不要、全編集をprivate recovery tarへ保存後に自分のmergeだけを中止する。予約中のlive process/foreign publishは拒否する。専用stage後のtest failureでも回復でき、publish履歴はaborted状態へ移して保存する。
- protected/契約のincoming変更は衝突に限らず開始前にSTOPする。innerのread-only mountとlaunch contract digestを広げず、古い契約のまま編集継続しないための保守的決定である。
- 既存register targets外の衝突はhostがファイル一覧とSTOPを返す。通常のpre_publish schema/中央カルテ診断との整合を維持するため、targetsを黙って広げない。
- continueのtestは固定unittest経路だけとし、Git内容CASと非0件の成功結果を要求する。任意shell commandを入力させない。

実装経路のオーナー例外は担当起動だけに適用し、製品のhost authority/owner plan検査には例外を実装しない。

## 再レビュー後の実装範囲・引継ぎ決定

2026-10-09、#538 の既存決定「旧方式の修正・P4完遂は再開しない」との整合を確認し、主文脈は次の2点を提示した。

1. 今回追加した旧 Codex supervisor 接続を外す。
2. 既存の CLI 互換性エラーを #538 へ引き継ぐ。

オーナーの回答は次のとおり。

> はい、進めてください

#594 は共通 gitgate と Claude issue-fixer の経路で完成させる。上の初期設計に含まれた旧 supervisor 向け新規 adapter とその専用テスト・接続用コード・現行手順を除去する。恒常的な旧 supervisor 自体の修正・撤去、新しい Codex 接続の実装は #594 の対象にしない。新方式の Codex 接続は #538 の撤去・置換設計で扱う。

F-594-01・04 は問題のある新規 host 接続の除去によって本 Issue 内で処置する（fix-here）。これは共通テスト runner を sandbox 化したという判断ではない。除去後の経路と契約は新しい独立レビューで確認する。

F-594-06 は #538 へ申し送る（deferred）。既存 main でも再現した feature catalog 不整合は open のまま残し、PASS・resolved・supervisor 完成へ読み替えない。#538 の撤去・置換後の検証で残存を確認する。

初期の比較・実装・レビュー証跡は履歴として保全する。push・PR 公開は検証済みの最終差分と本文を提示してから扱う。

現行実装は通常 Claude の running dispatch だけを許可し、Codex supervisor と unknown platform を拒否する。共通 engine の origin 正規化は既存 `branch_source.policy._remote_repository` を再利用し、撤去予定の supervisor helper への import 依存を外した。共通 runner の権限や sandbox を拡張したという判断ではない。
