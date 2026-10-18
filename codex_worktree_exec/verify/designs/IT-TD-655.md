# IT-TD-655 codex_worktree_exec — 未追跡分類と集約診断の結合テスト設計

- 作成：ac-designer（Claude Code (AI)）／VD 葉：`codex_worktree_exec/verification_design/VD-655.toml`（ID `VD-655-codex-worktree-exec`）
- 対象境界：`source_snapshot`（列挙・分類・集約）↔ `compiled_cache`（cache 検証）↔ `artifact_binding`（識別子写像）↔ `cli`（stderr・終了コード）↔ 回復コマンド（P6）
- 記号 C0〜C8・P1〜P8 は [ST-TD-655](ST-TD-655.md) §2・§3 の定義。TC は [IT-TC-655](IT-TC-655.md)。

### IT-TD-655-CWE-01 例外型の互換
- 1b依存：なし
- 合格条件：集約した拒否は `ValueError`（またはその subclass）として送出される。`artifact_binding`・`issue_start.phase_dispatch`・`issue_start.pr_rereview` の既存 `except` 句が、句を変えずにその例外を捕捉して各識別子へ写像する。

### IT-TD-655-CWE-02 HEAD source 読取のまとめと非永続
- 1b依存：なし
- 合格条件：1つの source について optimization 0・1・2 の cache と別 tag の cache を同時に置いた1回の検査で、`committed_bytes` の呼出しは1回。続けてもう1回検査すると累計2回（検査をまたいだ cache を持たない）。集約によって分類ごとに読み直さない。

### IT-TD-655-CWE-03 cache の分類対応表
- 1b依存：P1・P2・P7
- 合格条件：CP が「source の状態 × cache の名前・tag × code bytes」から分類（許可・無視または C2・C3・C6・その他の拒否分類）への対応表を記録し、次の全組合せでその表どおりの分類になる。どの組合せでも、未分類の扱いや `ValueError` 以外の例外が出ない。
  - source の状態：HEAD と作業面で一致／作業面と HEAD の両方に無い／HEAD のみ／作業面に未追跡／作業面で改変
  - cache の名前・tag：現行 tag（opt 無し・opt-1・opt-2）／別 tag／tag の無い名前（`m.pyc`）
  - code bytes：現行 source の compile 結果と一致／不一致
- 判定順に依存する分類（例：別 tag でも source が無ければ C2）は、表に明記されている。

### IT-TD-655-CWE-04 artifact_binding の2つの呼出し位置
- 1b依存：P7
- 合格条件：初回 binding（`input_file` を持つ binding）の経路と、`expected` を持つ binding の経路（`verify_source_snapshot` 内の再検査）の両方で、`CODEX_EXEC_BINDING_INVALID` の detail に fixture の全分類識別子と件数が入る。

### IT-TD-655-CWE-05 CLI の拒否出力
- 1b依存：P4
- 合格条件：未追跡違反で拒否されたとき、終了コードは2、stderr は `codex_worktree_exec: CODEX_EXEC_BINDING_INVALID: ` で始まり、行数は P4 の契約と一致する。`codex exec` は起動されない（launcher の差し替えで呼出し0回）。

### IT-TD-655-CWE-06 回復コマンドと検査の結合
- 1b依存：P6
- 合格条件：C2（2B の場合）・C3・C6 と、削除してはならない対象（ST-TD-655-15 の2）を同時に置いた作業面で、回復コマンドを1回起動した後に検査すると、C2・C3・C6 が診断から消える。削除してはならない対象は bytes と存在が変わらない。回復コマンドは検査の結果（診断）を入力にせず、作業面を自分で列挙する。
