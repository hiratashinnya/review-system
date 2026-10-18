# IT-TC-655 codex_worktree_exec — 未追跡分類と集約診断の結合テストケース

- 作成：ac-designer（Claude Code (AI)）／TD：[IT-TD-655](IT-TD-655.md)。fixture F0 と別 tag の値は [ST-TC-655](ST-TC-655.md) の定義。
- 本書はケース仕様である。各ケースは、工程 2a（test_design）で test-writer が Red の実テストとして `tests/codex_worktree_exec/` に置く（一次記録は Issue #655 本文 Scope 1 のオーナー決定（2026-10-18）。test-writer の契約文言に対するオーナー承認の例外であることは [ST-TD-655](ST-TD-655.md) §1。配置は `.ai/agents/creation-stage-contract.md:44`）。

| TC | TD | 前提・手順 | 期待結果（合格条件） |
|---|---|---|---|
| IT-TC-655-CWE-01-1 | CWE-01 | F0 に C0 と C3 を置き、`verify_untracked_sources` を直接呼ぶ。同じ fixture で `verify_artifact_binding`（`unittest.mock` で後続検査を通す）を呼ぶ | 直接呼出しは `ValueError` の instance を送出。`verify_artifact_binding` は `CodexExecError`（`CODEX_EXEC_BINDING_INVALID`）を送出し、それ以外の例外が漏れない |
| IT-TC-655-CWE-02-1 | CWE-02 | F0 の `ordinary.py` に opt 無し・opt-1・opt-2 の現行 cache と別 tag の `ordinary.cpython-399.pyc` を置き、`committed_bytes` を wraps 付き patch して検査を2回呼ぶ | 1回目の後の呼出し回数1、2回目の後2 |
| IT-TC-655-CWE-03-1 | CWE-03 | source の状態5通り × cache の名前・tag 6通り（現行 opt 無し・opt-1・opt-2、`cpython-399`、`m.pyc`、`m.<現行tag>.pyo`）× code bytes 2通りの fixture を subTest で作り、検査する。存在し得ない組合せ（source が無く code bytes 比較ができない等）は CP の表の注記どおりに扱う。加えて、F0 に `my-tool.py` を commit し、`py_compile` で作った `__pycache__/my-tool.<現行tag>.pyc` だけを置いた fixture（a）と、その cache の code 部分を別内容の compile 結果に置き換えた fixture（b）で検査する | 各組合せの分類が CP の対応表と一致。source 一致 × 現行 tag 3通り × code bytes 一致は生成元検証で通り、その cache だけを置いた fixture で例外なし。`m.pyc` と `.pyo` はすべて C0。（a）は例外なし（base `2fe2cd5` と同じく通過）。（b）は拒否され、その cache が C0 として件数1。`ValueError` 以外の例外0件 |
| IT-TC-655-CWE-04-1 | CWE-04 | F0 に C0・C3・C6 を置き、(a) `input_file` を持つ初回 binding、(b) `expected` を持つ binding（承認済み artifact を commit して作る）で `verify_artifact_binding` を呼ぶ | (a)(b) とも `CODEX_EXEC_BINDING_INVALID`。detail に C0・C3・C6 の識別子と各件数 |
| IT-TC-655-CWE-05-1 | CWE-05 | CWE-04-1 の fixture で `codex_worktree_exec.cli.main` を呼ぶ。profile pin・trust 等の前段は既存テストの補助で通し、`run_codex` を呼出し記録つきの差し替えにする | 戻り値2。stderr が `codex_worktree_exec: CODEX_EXEC_BINDING_INVALID: ` で始まり、行数が P4 の契約と一致。差し替えた `run_codex` の呼出し0回 |
| IT-TC-655-CWE-06-1 | CWE-06 | 作業面に C3 を2件、C6 を1件、（2B の場合）C2 を1件と、ST-TC-655-15-1 の「削除しない対象」を置く。検査（拒否を確認）→ 回復コマンド1回 → 検査 | 2回目の検査の診断に C2・C3・C6 が無い（他に違反が無ければ例外なし）。削除しない対象の bytes と存在が不変 |
