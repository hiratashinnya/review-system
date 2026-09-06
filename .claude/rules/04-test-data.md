## 時刻依存 test data の規律（再発防止・2026-08-10・Issue #344）
**test data に絶対日付・固定 epoch を使い、それが実行時の wall clock（`datetime.now()`/`time.time()`）と
比較される形にするときは、その wall clock 読み取りを必ず制御する**（`unittest.mock.patch` で対象モジュールの
`datetime`/`time` を固定する、`now=` のような明示引数でテスト値を注入する、あるいは freeze 系ライブラリで
凍結する）。コード変更なしに時間経過だけでテストが赤くなるのは、この規律違反の兆候であって仕様側の不具合ではない。

- **同一クラスの再発が2回起きている**：1度目＝#302（`test_codex_rate_limit_api.py` の固定 epoch が
  時間窓外になり失敗）。2度目＝#339（`tests/fixtures/blocker_gate/waiver_valid.yml` の
  `expires_at`。#302 の是正が当該ファイルの範囲に留まり、`blocker_gate/waiver.py` が
  `approved <= now < expires` で wall clock 比較する同種のフィクスチャは検査対象外のまま残った）。
  **「絶対日付・固定 epoch は書くな」ではない**——テストの再現性のためにこれらを使うこと自体は正当。
  問題は「wall clock と比較される形で使うのに、その wall clock を制御し忘れる」こと。
- **対象は上限・下限どちらの境界値も含む（向きではなく「反転しうるか」で決まる）**：
  `expires_at`/`valid_until`/`deadline`/`not_after`/`resets_at` のような期限・上限側だけでなく、
  `approved_at`/`not_before` のような窓の開始・下限側も本規律の対象。理由は上限/下限という
  向きではなく、「authoring 時点で値を wall clock の反対側に置いた場合、時間経過で比較結果が
  反転しうるか」で決まる——`approved <= now` 型の比較でも、`approved_at` を意図的に未来日にして
  「まだ承認されていない」を表す fixture を書けば、`expires_at` が過去に転じて壊れるのと対称に、
  時間経過で `False`→`True` に反転しうる（`blocker_gate/waiver.py:301` の
  `approved <= now < expires` が両側とも wall clock 比較の対象）。
  **対象外なのは、値が wall clock と一切比較されない場合に限る**：例えば `fetched_at`
  （過去の固定値）が同一スナップショット内の他の固定値（`completed_at` 等）とだけ比較される
  内部整合性チェックは、どちらも wall clock を読まないため時間経過で壊れる方向がない。
- **機械検査**：`time_fixture_lint`（`python3 -m time_fixture_lint check`）が
  `tests/fixtures/**`・`tests/unit/*.py` を対象フィールド語彙（期限・上限を示唆する語だけに絞り、
  `created_at`/`fetched_at` 等の inert な語は含めない——単純な日付 grep がもたらす大量誤検出を避ける
  ための絞り込み）でスキャンし、`unittest.mock.patch`/`now=` 注入等の保護マーカーが無いヒットを
  violation として報告する（詳細・設計判断は `time_fixture_lint/README.md`）。`.github/workflows/tests.yml`
  が `pull_request` ごとに実行する。避けられない/意図的な false positive は `time_fixture_lint/allowlist.py`
  に **理由付きで**登録する（`asset_parity/exceptions.py` と同じ「消さず理由を残す」運用）。
- **本節の記載先について**：`.claude/skills/test-strategy/SKILL.md`（review_system 固有の TD/TC/TR
  テーラリング資産）ではなく規約の正本側（`CLAUDE.md` から `@` import される本ファイル
  `.claude/rules/04-test-data.md`）に置く。理由＝この規律は review_system の TD/TC/TR 体系に
  留まらず、doc_system 側のハーネステスト（例：`test_codex_rate_limit_api.py`・`test_agent_command_gate.py`
  は dsv2/Issue 運用ハーネスのテストで review_system の TD/TC/TR 管理対象ではない）にも及ぶ、
  リポジトリ全体にまたがる横断規律のため。`time_fixture_lint` 自体は CI 定義と同じ「どちらの
  システムにも含有されない汎用開発ハーネス」区分（`.claude/rules/02-decision-process.md`
  「起票先はプロジェクト区分で決める（ハーネス開発は Issue 運用）」）。
