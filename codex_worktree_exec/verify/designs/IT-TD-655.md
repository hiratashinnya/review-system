# IT-TD-655 codex_worktree_exec — 未追跡分類と集約診断の結合テスト設計

- 作成：ac-designer（Claude Code (AI)）／VD 葉：`codex_worktree_exec/verification_design/VD-655.toml`（ID `VD-655-codex-worktree-exec`）
- 対象境界：`source_snapshot`（列挙・分類・集約）↔ `compiled_cache`（cache 検証）↔ `artifact_binding`（識別子写像）↔ `cli`（stderr・終了コード）↔ 回復コマンド（P6）
- 記号 C0〜C8・R-PYC・M1〜M5・P1〜P8 は [ST-TD-655](ST-TD-655.md) §2・§3 の定義。TC は [IT-TC-655](IT-TC-655.md)。
- 「上位」欄は、対応する ST-TD（ST-TD 側の見出しに Issue AC がある）と、根拠の契約条項（snapshot `2fe2cd5` の path:行）を示す。

### IT-TD-655-CWE-01 例外型の互換
- 上位：ST-TD-655-12（1）／Issue AC12／`docs/methods/codex-workspace-binding.md:61-62`（検査不合格は終了コード2と識別子）
- 1b依存：なし
- 合格条件：集約した拒否は `ValueError`（またはその subclass）として送出される。`artifact_binding`・`issue_start.phase_dispatch`・`issue_start.pr_rereview` の既存 `except` 句が、句を変えずにその例外を捕捉して各識別子へ写像する。

### IT-TD-655-CWE-02 HEAD source 読取のまとめと非永続
- 上位：ST-TD-655-03・ST-TD-655-05／Issue AC3・AC5／`docs/methods/codex-workspace-binding.md:309`（source 毎に1回読み、次の検査で再読、永続 cache を作らない）
- 1b依存：なし
- 合格条件：1つの source について optimization 0・1・2 の cache と別 tag の cache を同時に置いた1回の検査で、`committed_bytes` の呼出しは1回。続けてもう1回検査すると累計2回（検査をまたいだ cache を持たない）。集約によって分類ごとに読み直さない。

### IT-TD-655-CWE-03 cache の分類対応表
- 上位：ST-TD-655-02・04・05・07／Issue AC2・AC4・AC5・AC7／`docs/methods/codex-workspace-binding.md:297-307`（生成元検証を通る cache の例外と、cache の source 一致・tag・code bytes 検証）
- 1b依存：P1・P2・P7
- 合格条件：CP が「source の状態 × cache の名前・tag × code bytes」から分類への対応表を記録し、次の全組合せでその表どおりの分類になる。分類先の値域は、生成元検証で通る（ST-TD-655 §2 の優先順位 0）、M1・M2 で通る、C0・C2・C3・C6・その他の拒否分類、のいずれかである。どの組合せでも、未分類の扱いや `ValueError` 以外の例外が出ない。
  - source の状態：HEAD と作業面で一致／作業面と HEAD の両方に無い／HEAD のみ／作業面に未追跡／作業面で改変
  - cache の名前・tag：現行 tag（opt 無し・opt-1・opt-2）／別 tag（`cpython-399`）／R-PYC に一致しない名前（`m.pyc`）／`__pycache__` 配下の `.pyo`（`m.<現行tag>.pyo`）
  - code bytes：現行 source の compile 結果と一致／不一致
- source が HEAD と作業面で一致 × 現行 tag（opt 無し・opt-1・opt-2）× code bytes 一致の3組合せは、生成元検証で通る（拒否分類に入らない）。
- R-PYC に一致しない名前（`m.pyc`）と `.pyo` は、生成元検証の path 条件（cache の path が `importlib.util.cache_from_source` の値に一致すること）を満たし得ないため、source の状態によらず C0 になる（ST-TD-655 §2 の優先順位 1）。
- stem が識別子でない現行 tag の cache は、R-PYC に一致しなくても生成元検証に合格すれば通る（ST-TD-655 §2 の優先順位 0 の (d)。R-PYC で狭めない）。`my-tool.py` を HEAD と作業面で一致させ、標準 compiler で作った `__pycache__/my-tool.<現行tag>.pyc`（code bytes 一致）は通る。同じ cache の code bytes が不一致なら、優先順位 1 により C0 として拒否される（base `2fe2cd5` でも拒否）。
- 判定順に依存する分類（例：別 tag でも source が無ければ C2。その根拠の記録は ST-TD-655-07 の 4）は、表に明記されている。

### IT-TD-655-CWE-04 artifact_binding の2つの呼出し位置
- 上位：ST-TD-655-12（1）／Issue AC12／`docs/methods/codex-workspace-binding.md:296`（全工程入力検査で拒否）・`287-290`（`expected.source_changes` の照合）
- 1b依存：P7
- 合格条件：初回 binding（`input_file` を持つ binding）の経路と、`expected` を持つ binding の経路（`verify_source_snapshot` 内の再検査）の両方で、`CODEX_EXEC_BINDING_INVALID` の detail に fixture の全分類識別子と件数が入る。

### IT-TD-655-CWE-05 CLI の拒否出力
- 上位：ST-TD-655-12（4）／Issue AC12／`docs/methods/codex-workspace-binding.md:61-62`（stderr の形式と終了コード）・`68`（検査に通らなければ起動しない）
- 1b依存：P4
- 合格条件：未追跡違反で拒否されたとき、終了コードは2、stderr は `codex_worktree_exec: CODEX_EXEC_BINDING_INVALID: ` で始まり、行数は P4 の契約と一致する。`codex exec` は起動されない（launcher の差し替えで呼出し0回）。

### IT-TD-655-CWE-06 回復コマンドと検査の結合
- 上位：ST-TD-655-09・11・15／Issue AC9・AC11・Scope 1（3B）／`docs/methods/codex-workspace-binding.md:307-308`（trusted caller が再生成・検査は read-only）
- 1b依存：P6
- 合格条件：C2（2B の場合）・C3・C6 と、削除してはならない対象（ST-TD-655-15 の2）を同時に置いた作業面で、回復コマンドを1回起動した後に検査すると、C2・C3・C6 が診断から消える。削除してはならない対象は bytes と存在が変わらない。回復コマンドは検査の結果（診断）を入力にせず、作業面を自分で列挙する。
