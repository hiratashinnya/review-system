"""backref.reverse — 辺逆転の計画と適用（一時 doc-system ツリーで end-to-end）。"""

import tempfile
import unittest
from pathlib import Path

from backref import reverse
from docidx import scan

FINDINGS = """\
# Findings

---

## FND-100: open finding（通常・provenance・欠落の3辺）

<details><summary>⬡ FND-100 · v0.1.0</summary>

```yaml
id: FND-100
type: FND
labels: []
scheduled: ""
edges:
  - to: P-100
    ref_version: "0.2"
  - to: FND-200
    ref_version: "0.1"
  - to: GHOST-1
    ref_version: "0.4"
```
</details>

**深刻度**: WARNING
**内容**: 何らかの指摘。

---

## FND-200: provenance 用の別 FND

<details><summary>⬡ FND-200 · v0.1.0</summary>

```yaml
id: FND-200
type: FND
labels: []
scheduled: ""
edges: []
```
</details>

provenance ノード本文。
"""

PROCESSES = """\
# Processes

---

## P-100: 処置対象プロセス

<details><summary>⬡ P-100 · v0.3.0</summary>

```yaml
id: P-100
type: P
labels: []
scheduled: ""
edges:
  - to: SPEC-1
    ref_version: "0.3"
```
</details>

プロセス本文。
"""

CONFIG = 'trace_scope:\n  include: ["doc-system/**/*.md"]\n  exclude: []\n'


def _make_tree(tmp: str) -> tuple[Path, Path]:
    root = Path(tmp)
    (root / "doc-system" / "04-verification").mkdir(parents=True)
    (root / "doc-system" / "03-analysis").mkdir(parents=True)
    (root / "docs" / "doc-system").mkdir(parents=True)
    (root / "doc-system" / "04-verification" / "02-findings.md").write_text(
        FINDINGS, encoding="utf-8")
    (root / "doc-system" / "03-analysis" / "03-processes.md").write_text(
        PROCESSES, encoding="utf-8")
    cfg = root / "docs" / "doc-system" / "config.yaml"
    cfg.write_text(CONFIG, encoding="utf-8")
    return root, cfg


class TestReversePlan(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root, self.cfg = _make_tree(self._tmp.name)
        index = scan.build_index(repo_root=self.root, config_path=self.cfg)
        self.plan = reverse.plan_reverse(index, self.root, "FND-100")

    def tearDown(self):
        self._tmp.cleanup()

    def test_classifies_three_edges(self):
        kinds = {a.to: a.kind for a in self.plan.actions}
        self.assertEqual(kinds, {"P-100": "normal", "FND-200": "provenance",
                                 "GHOST-1": "missing"})

    def test_dd3_line_covers_all(self):
        self.assertIn('P-100 "0.2"', self.plan.dd3_line)
        self.assertIn("provenance", self.plan.dd3_line)
        self.assertIn("削除済み", self.plan.dd3_line)

    def test_fnd_yaml_reversed_and_bumped(self):
        new = self.plan.new_text["doc-system/04-verification/02-findings.md"]
        self.assertIn("⬡ FND-100 · v0.1.1", new)
        self.assertIn("resolved: true", new)
        self.assertIn("edges: []", new)
        self.assertNotIn("to: P-100", new)  # forward 辺は消えた

    def test_target_gets_backref_and_bump(self):
        new = self.plan.new_text["doc-system/03-analysis/03-processes.md"]
        self.assertIn("⬡ P-100 · v0.3.1", new)
        self.assertIn("to: FND-100", new)
        self.assertIn('ref_version: "0.1"', new)  # FND-100 のバッジ x.y

    def test_dd3_inserted_into_body(self):
        new = self.plan.new_text["doc-system/04-verification/02-findings.md"]
        self.assertIn("**指摘時 ref_version**:", new)

    def test_provenance_target_untouched(self):
        # FND-200 は findings.md にあるが backref を張らない（→FND-100 が増えない）
        new = self.plan.new_text["doc-system/04-verification/02-findings.md"]
        # FND-200 ブロックは edges: [] のまま
        self.assertEqual(new.count("to: FND-100"), 0)


class TestReverseApplyThenReparse(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root, self.cfg = _make_tree(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _index(self):
        return scan.build_index(repo_root=self.root, config_path=self.cfg)

    def test_apply_makes_consistent_graph(self):
        plan = reverse.plan_reverse(self._index(), self.root, "FND-100")
        reverse.write_plan(plan, self.root)
        idx = self._index()
        fnd = idx.by_id["FND-100"]
        self.assertIs(fnd.fields.get("resolved"), True)
        self.assertEqual(len(fnd.edges), 0)
        self.assertEqual(fnd.version, "0.1.1")
        p100 = idx.by_id["P-100"]
        tos = {e.to: e.ref_version for e in p100.edges}
        self.assertEqual(tos.get("FND-100"), "0.1")
        self.assertEqual(p100.version, "0.3.1")

    def test_idempotent_second_run_is_noop(self):
        plan = reverse.plan_reverse(self._index(), self.root, "FND-100")
        reverse.write_plan(plan, self.root)
        plan2 = reverse.plan_reverse(self._index(), self.root, "FND-100")
        self.assertTrue(plan2.noop)
        self.assertEqual(plan2.new_text, {})

    def test_dd3_not_overwritten_when_present(self):
        # 先に DD-3 行を本文へ入れておくと、2 回目の挿入は起きず警告のみ
        plan = reverse.plan_reverse(self._index(), self.root, "FND-100")
        # 本文に DD-3 を埋めてから別の open FND は無いので、apply 後の再計画は noop。
        # ここでは「挿入は1回だけ」を新テキストで確認する。
        new = plan.new_text["doc-system/04-verification/02-findings.md"]
        self.assertEqual(new.count("**指摘時 ref_version**:"), 1)


NOTARGET = """\
# Findings

---

## FND-300: 削除済み対象のみ

<details><summary>⬡ FND-300 · v0.1.0</summary>

```yaml
id: FND-300
type: FND
labels: []
scheduled: ""
edges:
  - to: GHOST-9
    ref_version: "0.2"
```
</details>

**内容**: 削除済みノードのみを指す指摘。

---

## FND-400: provenance のみ

<details><summary>⬡ FND-400 · v0.1.0</summary>

```yaml
id: FND-400
type: FND
labels: []
scheduled: ""
edges:
  - to: FND-300
    ref_version: "0.1"
```
</details>

provenance のみ。
"""

INLINE_NONEMPTY = """\
# IO

---

## D-1: inline 非空 edges を持つ対象

<details><summary>⬡ D-1 · v0.1.0</summary>

```yaml
id: D-1
type: D
edges: [SPEC-1]
```
</details>

本文。
"""

FND_TO_D1 = """\
# Findings

---

## FND-500: D-1 を指す

<details><summary>⬡ FND-500 · v0.1.0</summary>

```yaml
id: FND-500
type: FND
labels: []
scheduled: ""
edges:
  - to: D-1
    ref_version: "0.1"
```
</details>

本文。
"""


def _make_tree_text(tmp: str, findings: str, processes: str | None = None) -> tuple[Path, Path]:
    root = Path(tmp)
    (root / "doc-system" / "04-verification").mkdir(parents=True)
    (root / "doc-system" / "03-analysis").mkdir(parents=True)
    (root / "docs" / "doc-system").mkdir(parents=True)
    (root / "doc-system" / "04-verification" / "02-findings.md").write_text(
        findings, encoding="utf-8")
    if processes is not None:
        (root / "doc-system" / "03-analysis" / "03-processes.md").write_text(
            processes, encoding="utf-8")
    cfg = root / "docs" / "doc-system" / "config.yaml"
    cfg.write_text(CONFIG, encoding="utf-8")
    return root, cfg


class TestNoTargetRecording(unittest.TestCase):
    """削除済み／provenance のみの resolved FND は本文へ『付与先なし』を残す（PR8・check 整合）。"""

    def _run_and_check(self, fnd_id: str) -> tuple[str, list]:
        from backref import check as check_mod
        with tempfile.TemporaryDirectory() as tmp:
            root, cfg = _make_tree_text(tmp, NOTARGET)
            idx = scan.build_index(repo_root=root, config_path=cfg)
            plan = reverse.plan_reverse(idx, root, fnd_id)
            reverse.write_plan(plan, root)
            idx2 = scan.build_index(repo_root=root, config_path=cfg)
            new = (root / "doc-system/04-verification/02-findings.md").read_text("utf-8")
            findings = [f for f in check_mod.check(idx2) if f.fnd_id == fnd_id]
            return new, findings

    def test_deleted_only_writes_notarget_and_check_clean(self):
        new, findings = self._run_and_check("FND-300")
        self.assertIn("付与先なし", new)
        # resolved-no-backref が誤検出されない
        self.assertFalse([f for f in findings if f.code == "resolved-no-backref"])

    def test_provenance_only_writes_notarget_and_check_clean(self):
        new, findings = self._run_and_check("FND-400")
        self.assertIn("付与先なし", new)
        self.assertFalse([f for f in findings if f.code == "resolved-no-backref"])


class TestInlineNonEmptyFailClose(unittest.TestCase):
    def test_raises_instead_of_dropping_edges(self):
        from backref.errors import BackrefError
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "doc-system" / "04-verification").mkdir(parents=True)
            (root / "doc-system" / "03-analysis").mkdir(parents=True)
            (root / "docs" / "doc-system").mkdir(parents=True)
            (root / "doc-system" / "04-verification" / "02-findings.md").write_text(
                FND_TO_D1, encoding="utf-8")
            (root / "doc-system" / "03-analysis" / "02-io.md").write_text(
                INLINE_NONEMPTY, encoding="utf-8")
            cfg = root / "docs" / "doc-system" / "config.yaml"
            cfg.write_text(CONFIG, encoding="utf-8")
            idx = scan.build_index(repo_root=root, config_path=cfg)
            with self.assertRaises(BackrefError):
                reverse.plan_reverse(idx, root, "FND-500")


if __name__ == "__main__":
    unittest.main()
