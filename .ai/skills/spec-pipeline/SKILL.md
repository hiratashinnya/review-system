# 仕様設計パイプライン（オーケストレータ）

要件から MVP スコープまでを順に回す。**主文脈で実行**——**対話（オーナー判断・
Q/DD 起票・停止）が要る段を主文脈に残すため** skill にしている（①-C ハイブリッド・DD-22）。**非対話の並列著作 fan-out は
`authoring-fanout` エージェント（`author: requirements-author` / `author: spec-author`）へ委譲**する（下記 5）。
原則：[spec-principles](../spec-principles/SKILL.md)。

## ハイブリッド分担（DD-22 ①-C）
- **対話が要る段＝skill（主文脈）に残す**：`/align` のパラメータ確定、spec-inspector の矛盾停止、`/mvp-scope` の価値線引き。矛盾・オーナー判断は PR7 に従い**起票して止める**（Q/DD → オーナー）。
- **非対話の並列 fan-out＝エージェントへ委譲**：台帳/分析が「何を著作するか」を出したら、複数親ノードの要求層著作（VAL/SR/FR/NFR・SPEC）を `authoring-fanout`（`author: requirements-author` / `author: spec-author`）に一括ファンアウトさせる（著作→検証→書込を sub-tree 内で完結し、主文脈にはコンパクト要約だけ返る）。`authoring-fanout` は旧 `spec-authoring-fanout` を `author` パラメータで5著作者（requirements/spec/analysis/design/verification）に汎化した実装（issue #121）で、requirements/spec 系の挙動は従来と同一。

## 手順（順に・各段でチェックポイント）
1. `/align` — 段取りと確定パラメータ（**対話・skill**）。
2. **I/O 台帳＋イベントリスト＋カバレッジ** — 台帳とイベントリストを起こし、ACTOR/I/O/E ノードを **analysis-author** で著作する（2段確定：`reconciliation-validator`→`reconciliation`）。※旧 `/io-event-ledger` skill は 2026-06-11 に廃止され、著作規約は型別 `*-author` エージェントへ移管済み。
3. **spec-inspector** サブエージェント — 点検（gap/矛盾）。**矛盾は止めて確認**（対話・skill／PR7 起票→オーナー）。
4. **structured-analysis** サブエージェント — コンテキスト→DFD→単一責務→状態。
5. **要求層の並列著作 fan-out（非対話・エージェント委譲）** — 2・4 が「著作すべき親ノード群」を確定したら、**`authoring-fanout`** エージェントに委譲する：
   - まず `author: requirements-author`（VAL/SR/FR/NFR）を、独立親ごとに `targets` 配列で渡して**並列著作**させる。
   - 依存する SPEC は親 FR/SPEC 確定後、別バッチ `author: spec-author` で委譲する（依存対象は同バッチに混ぜない＝skill が分割）。
   - 単一対象しか無い段では fan-out せず `requirements-author` / `spec-author` を直接呼ぶ（fan-out はオーバースペック）。このとき戻りは `HANDOFF: tmp/_handoff/<author>--<parent-id>.yaml` ＋1行要約なので、**著作 slug 群・エラー・`update_slugs` は当該ファイルを Read して取る**。**直接呼びのときは主文脈が `update_slugs`（親サイドカー更新など既存ノードを更新した slug）を `reconciliation-validator` へ明示的に渡す**（集約役の fan-out を通さないため。渡し忘れると `dsv2 check-slug` が正当な更新を既存 id 衝突と判定して ROLLBACK する）。
   - 戻りが `FANOUT_DONE` なら次段へ。**`ROLLBACK`/`STOP`/矛盾報告が返ったら主文脈で受け止め**、該当 author の再起動 or PR7 起票（Q/DD → オーナー）を行う。委譲先は対話せず STOP を返し、オーケストレータ主文脈が呼び出し元の対話機構で判断を確定する。
   - **失敗した target を fan-out へ再投入するときは、その target に `retry_of:`（報告の `target_keys` に載っていた前回の `target_key`）と `error:`（差し戻し理由）を付けて渡す**（issue #278）。付けないと新しいキーが採番され、前回のハンドオフと対応付かなくなる。**新規 target には付けない**（付けないことで他バッチと衝突しないキーが採番される）。
   - **N 個中1個だけ失敗し、その1件だけを再試行する場合は fan-out に戻さない**（`targets` が1件のみだと Step 1-4 で
     オーバースペック STOP になる＝単一対象は該当 `*-author` を直接呼ぶ）。この直接呼び出しでは、入力の `target_key` に
     **前回の `target_key`（同じく前回 STOP 報告の `target_keys` の値）をそのまま渡す**（`error` も併せて渡す）。
     省略すると `parent_id` 単独キーにフォールバックし、前回の失敗ハンドオフと同じ場所に上書きされず、
     本 issue #278 の目的（同一 target のやり直し結果を一意に対応付ける）が満たされない。
6. `/value-trace` — イベント総点検（遮断検出）。
7. `/mvp-scope` — 価値ベースの線引き（**対話・skill**）。

各段の後に成果物を確認し、矛盾（PR7）が出たら停止して打ち上げる。必要なら spec-inspector を随時挟む。
