# 時刻依存テスト検査の設計根拠

wall clock と比較されうる時刻依存 test data を検査する（Issue #344 手当てB・#349 是正）。

背景・スコープの絞り込み方針
----------------------------
単純な絶対日付 grep は inert な `created_at`/`fetched_at`/`completed_at` 等を大量に
誤検出する。実測（Issue #344 起票時点）で `tests/` 配下の17 fixture・9 テストが絶対日付を
含むが、大半は無害 —— 例えば `blocker_gate/contract.py` の
``_date(result["fetched_at"]) > _date(result["completed_at"])`` は、fetched_at・completed_at
双方が同一スナップショット内の固定値同士の内部整合性チェックであり、どちらも wall clock
（``datetime.now()``/``time.time()``）と比較されない（安全 by construction）。

そこで本ツールは対象を「wall clock と直接比較されうる**境界値**の意味を持つフィールド名」
に絞る（:data:`SUSPICIOUS_FIELD_RE`：``expires_at``/``approved_at``/``resets_at`` (camelCase
``resetsAt`` も含む)/``expiry``/``deadline``/``valid_until``/``not_after``/``not_before``）。
``created_at``/``fetched_at``/``completed_at``/``id`` 等はこの語彙に含めない。

**上限（期限）側だけでなく下限（開始）側も対象**（PR #349 是正・F-344-02）：
``expires_at``/``valid_until``/``deadline``/``not_after``/``resets_at`` のような期限側だけでなく、
``approved_at``/``not_before`` のような窓の開始側も対象に含める。理由は向きではなく
「authoring 時点で値を『まだ現在時刻の反対側』に置いた場合、時間経過で比較結果が反転しうるか」
——``approved <= now`` 型の比較で ``approved_at`` を意図的に未来日にして「未承認」を表す
fixture を書けば、``expires_at`` が過去に転じて壊れるのと対称に、時間経過で ``False`` から
``True`` へ反転しうる。安全なのは、比較相手が wall clock ではなく同一スナップショット内の
他の固定値（fetched_at/completed_at 型）か、``time.time()`` 相対式（#302 パターン）の場合に限る。

2つの検出器:

* **fixture 検出器**（:func:`scan_fixtures`）―
  ``tests/fixtures/**/*.{yml,yaml,json}`` の1行1フィールド形（strict YAML / JSON 共通、
  シングル/ダブルクォート・裸値のいずれも可）を対象フィールド名でスキャンし、ヒットした
  フィクスチャを参照する ``tests/{unit,jev_hooks,time_fixture_lint}/test_*.py`` の**その参照箇所自身**が clock を制御している
  （``unittest.mock.patch``/``freeze_time``/``now=`` 注入等、:data:`PROTECTION_MARKER_RE`）ことを
  要求する。参照テストが1つも見つからない場合は「保護の有無を確認できない」として
  ``no_consumer`` を報告する（無視せず可視化する）。

* **python literal 検出器**（:func:`scan_python_literals`）―
  ``tests/{unit,jev_hooks,time_fixture_lint}/test_*.py`` 内の dict リテラル・定数代入から同じ語彙でヒットした行が、
  **その参照箇所自身のスコープ内**で clock 保護マーカーを持つか、``time.time()`` との
  相対式内にある（#302 で採用された安全パターン）ことを要求する。

保護判定のスコープ（PR #349 是正・F-344-01）
--------------------------------------------
旧実装は「参照テストファイル全文」を対象に :data:`PROTECTION_MARKER_RE` を検索しており、
clock と無関係な ``patch(...)`` が同じファイルのどこか別の場所にあるだけで「保護済み」と
誤判定していた（#339 と同クラスの再武装を検知できない false negative）。

本実装は :class:`_FileGraph` で各 python テストファイルを ``ast`` 解析し、フィクスチャ／
疑わしいリテラルの**参照行を直接囲む関数（メソッド）**を起点に、
(a) その関数自身のソース、
(b) 関数がクラスメソッドなら、そのクラスの ``setUp``/``setUpClass``（unittest が暗黙に
    呼ぶため、明示的な呼び出しが無くても保護スコープに含める）、
(c) 同一ファイル内のローカル関数呼び出し（``foo()``/``self.foo()`` を単純名で解決）で
    無向に連結する関数群（例：フィクスチャを読むヘルパー関数 A と、clock を patch する
    別のヘルパー関数 B を同じ test メソッドが両方呼ぶ構成で、A と B は「同じ test に
    呼ばれる」という一点で連結する）
の和集合をスコープとして :data:`PROTECTION_MARKER_RE` を検索する。
また ``patch(...)`` は**引数の対象文字列が clock 関連語（datetime/time/clock/freeze）を
含む場合のみ**保護マーカーとして数える——clock と無関係な対象への patch（例：
``patch("blocker_gate.cli.resolve_github_token")``）は、たとえ参照箇所と同じ関数内に
あっても保護とみなさない。

既知の残存限界（意図的に許容・Issue #129 と同水準の明記）：
モジュールレベル（関数の外）で参照される場合はスコープを狭められずファイル全文に
フォールバックする。また、同じヘルパー関数が「clock を保護する呼び出し元」と「保護
しない新しい呼び出し元」の両方から呼ばれる場合、無向連結成分は呼び出し元を区別しない
ため、新しい呼び出し元が誤って「保護済み」と判定されうる（fixture 共有ヘルパーの
呼び出し元ごとの区別は、静的解析の範囲を超えるデータフロー解析が必要なため未対応）。

誤検出（inert と判断した absolute date/epoch）は
:mod:`time_fixture_lint.allowlist` に (path, name) と理由を明記して登録する
（``asset_parity/exceptions.py` と同じ「消さず理由を残す」運用）。
