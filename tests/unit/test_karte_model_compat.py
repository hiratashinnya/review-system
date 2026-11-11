"""karte.model の解析責務分割（Issue #746・K-01）で挙動が変わっていないことの比較テスト。

分割前の ``karte.model`` に同じ入力を通して記録した結果
（``tests/fixtures/karte/model_parse_golden.json``）と、現行実装の結果を突き合わせる。
入力は決定論的な変異（キー欠落・空値・重複・不正値・不正行）で生成する。
成功は出力の sha256、失敗は例外クラス名とメッセージ全文で比較し、失敗分類の同等性も固定する。
"""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from karte import model

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "karte" / "model_parse_golden.json"

VALID = """# Karte: issue-307
<!-- karte-format: 1 -->

## Findings

### F-307-01
status: open
harm: real
harm_detail: required 属性が消え必須入力が素通りする
severity: blocker
scope: in
disposition: deferred
deferred_to: #12
waived_by:
waived_reason:
locus: [a.py::f, b.toml::f]
summary: build_attrs が既存 attrs を破棄している
evidence: forms.py:120 を Read
expected: 既存 attrs を保つ
recheck: required を描画して確認
rounds: [1, 2]
resolved_round:

### F-307-02
status: resolved
harm: none
harm_detail: 表示が崩れる
severity: minor
scope: out
disposition:
deferred_to:
waived_by:
waived_reason:
locus:
summary: 別の指摘
evidence: x
expected: y
recheck: z
rounds: [1]
resolved_round: 2

## Attempts

### Attempt 1
round: 1
finding_ids: [F-307-01]
root_cause: attrs-overwrite
change_kind: logic
targets: [a.py::f]
diagnosis: dict リテラルで作り直している

### Result 1
attempt: 1
finding_ids: [F-307-01]
touched: [a.py, a.py::f]
outcome: partial
note: aria が欠ける
"""

REPORT = """# レビュー結果

総括の自由文。

### F-307-01
harm: real
harm_detail: required が消える
severity: major
scope: in
locus: a.py::f
summary: 要約
evidence: 根拠
expected: 期待
recheck: 再確認
status: resolved
distinct_from: [F-307-02]

### new
harm: none
harm_detail: 見た目だけ
severity: minor
scope: out
locus: [a.py::g, b.py::g]
summary: 新規
evidence: e
expected: x
recheck: r
disposition: waived
waived_by: owner
waived_reason: 軽微
"""


def run(fn, *args):
    try:
        return {"ok": fn(*args)}
    except Exception as exc:  # noqa: BLE001 - 失敗分類（型とメッセージ）を記録するため全捕捉
        return {"err": type(exc).__name__ + ": " + str(exc)}


def view_karte(text):
    return model.dumps(model.parse(text))


def view_review(text):
    return [
        {k: (list(v) if isinstance(v, tuple) else v) for k, v in vars(item).items()}
        for item in model.parse_review(text, 307)
    ]


def mutations(text):
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if ":" in line and not line.startswith(("#", "<!--")):
            key = line.split(":")[0]
            yield f"drop-{i}-{key}", lines[:i] + lines[i + 1:]
            yield f"empty-{i}-{key}", lines[:i] + [key + ":"] + lines[i + 1:]
            yield f"dup-{i}-{key}", lines[:i + 1] + [line] + lines[i + 1:]
            yield f"bogus-{i}-{key}", lines[:i] + [key + ": bogus-VALUE"] + lines[i + 1:]
            yield f"list-{i}-{key}", lines[:i] + [key + ": [x, y]"] + lines[i + 1:]
            yield f"nonint-{i}-{key}", lines[:i] + [key + ": [1x]"] + lines[i + 1:]
        yield f"garbage-{i}", lines[:i] + ["???"] + lines[i:]


def karte_extras():
    yield "empty-text", ""
    yield "no-header", "## Findings\n"
    yield "wrong-issue", VALID.replace("F-307-02", "F-308-02")
    yield "dup-finding", VALID.replace("### F-307-02", "### F-307-01")
    yield "dup-attempt", VALID + (
        "\n### Attempt 1\nround: 1\nfinding_ids: [F-307-01]\n"
        "root_cause: r\nchange_kind: logic\ntargets: [a]\n"
    )
    yield "orphan-result", VALID.replace("### Result 1\nattempt: 1", "### Result 2\nattempt: 2")
    yield "result-mismatch", VALID.replace(
        "attempt: 1\nfinding_ids: [F-307-01]\ntouched", "attempt: 3\nfinding_ids: [F-307-01]\ntouched"
    )
    yield "unknown-section", VALID + "\n## Notes\n\n### X\na: b\n"
    yield "bad-attempt-title", VALID.replace("### Attempt 1", "### Round 1")
    yield "comment-lines", VALID.replace("## Findings", "<!-- c -->\n## Findings")
    yield "bad-char-id", VALID.replace("F-307-01", "F-307-1")
    yield "slug-bad", VALID.replace("attrs-overwrite", "Bad Slug")
    yield "deferred-prose", VALID.replace("#12", "別 Issue で対応")
    yield "waived-missing", VALID.replace("disposition: deferred\ndeferred_to: #12", "disposition: waived")
    yield "extra-key", VALID.replace(
        "disposition: deferred\ndeferred_to: #12", "disposition: fix-here\ndeferred_to: #12"
    )
    yield "orphan-key", VALID.replace("disposition: deferred\ndeferred_to: #12", "disposition:\ndeferred_to: #12")
    yield "bigint", VALID.replace("rounds: [1, 2]", "rounds: [" + "9" * 40 + "]")
    yield "unicode-digit", VALID.replace("rounds: [1, 2]", "rounds: [１]")
    yield "no-scope", VALID.replace("scope: in\n", "")
    yield "bad-scope", VALID.replace("scope: in", "scope: maybe")
    yield "locus-comma", VALID.replace("locus: [a.py::f, b.toml::f]", "locus: a.py::f, b.toml::f")
    yield "nul", VALID.replace("a.py::f]", "a\x00.py]", 1)
    yield "heading-four-hashes", VALID.replace("### F-307-02", "#### F-307-02")
    yield "heading-no-space", VALID.replace("### F-307-02", "###F-307-02")


def review_extras():
    tail = REPORT.split("### new\n")[1]
    yield "empty", ""
    yield "preamble-only", "# t\n自由文\n"
    yield "preamble-keyline", "foo: bar\n### new\n" + tail
    yield "wrong-section", "## Other\n\n### new\n" + tail
    yield "findings-section", "## Findings\n\n### new\n" + tail
    yield "other-issue", REPORT.replace("F-307-01", "F-999-01")
    yield "bad-id", REPORT.replace("### F-307-01", "### F-x")
    yield "no-scope", REPORT.replace("scope: out\n", "")
    yield "bad-status", REPORT.replace("status: resolved", "status: resolve")
    yield "distinct-other-issue", REPORT.replace("[F-307-02]", "[F-999-02]")
    yield "distinct-bad", REPORT.replace("[F-307-02]", "[nope]")
    yield "distinct-scalar", REPORT.replace("[F-307-02]", "F-307-02")
    for term in ("対応不要", "別Issue", "別 issue", "Fix-Here", "オーナー確認済み", "スコープ外", "DEFERRED"):
        yield f"term-{term}", REPORT.replace("required が消える", f"required が消える {term}")
    yield "multi-errors", REPORT.replace("harm: real", "harm: huge").replace("severity: minor", "severity: tiny")
    yield "dispo-in-report", REPORT.replace("disposition: waived", "disposition: deferred")
    yield "continuation", REPORT.replace("summary: 要約", "summary: 要約\n折り返し行")
    yield "heading-four-hashes", REPORT.replace("### new\n", "#### new\n")
    yield "heading-no-space", REPORT.replace("### new\n", "###new\n")
    yield "title-new-finding", REPORT.replace("### new\n", "### new-finding\n")
    yield "title-upper-new", REPORT.replace("### new\n", "### NEW\n")


def helper_calls():
    for v in ["[a, b]", "[]", " x ", "[ ]", "[a,,b]", "abc]"]:
        yield "parse_value", (v,)
    for v in ["a.md::x", "", "  ", ["a", "b", "a"], ["a,b"], ["[x]"], "a, b", ["a\nb"]]:
        yield "normalize_locus", (v,)
    for v in ["F-1-01", "F-12-100", "F-0-01", "F-1-1", "x", "F-１-01"]:
        yield "parse_finding_id", (v,)
    for a in [(1, 1), (312, 3), (1, 100), (1, 0)]:
        yield "format_finding_id", a
    for v in ["ok-slug", "Bad", "", "a b", "-x"]:
        yield "validate_slug", (v, "root_cause")
    for v in ["logic", "doc", "nope", "", "revert"]:
        yield "validate_change_kind", (v,)
    for v in [["a"], [], ["a", "a"], "a"]:
        yield "validate_targets", (v,)
    for v in [["F-1-01"], [], ["bad"], ["F-1-01", "F-1-01"]]:
        yield "validate_finding_ids", (v,)
    for v in ["通常の実害", "対応不要です", "別Issue", "FIX-HERE", "本 PR で直す", "新規発生ではない"]:
        yield "find_harm_detail_terms", (v,)
    for v in ["a", "A  b\n", "別 Issue"]:
        yield "normalize_for_term_match", (v,)
    for v in [None, "a\nb", " x ", 5]:
        yield "check_scalar", (v, "w")
    for v in ["abc", "既存 attrs を破棄", "ＡＢＣ", ""]:
        yield "normalize_text", (v,)


def canonical(outcome):
    if "ok" not in outcome:
        return outcome["err"]
    blob = json.dumps(outcome["ok"], ensure_ascii=False, sort_keys=True, default=sorted)
    return "ok:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_outcomes():
    result = {}
    for label, text in [("base", VALID), *karte_extras()]:
        result[f"parse/{label}"] = canonical(run(view_karte, text))
    for label, lines in mutations(VALID):
        result[f"parse/{label}"] = canonical(run(view_karte, "\n".join(lines)))
    for label, text in [("base", REPORT), *review_extras()]:
        result[f"review/{label}"] = canonical(run(view_review, text))
    for label, lines in mutations(REPORT):
        result[f"review/{label}"] = canonical(run(view_review, "\n".join(lines)))
    for index, (name, args) in enumerate(helper_calls()):
        result[f"helper/{index:03d}-{name}"] = canonical(run(getattr(model, name), *args))
    return result


class TestModelBehaviourIsUnchangedBySplit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.golden = json.loads(GOLDEN.read_text(encoding="utf-8"))

    def test_every_recorded_outcome_is_reproduced(self):
        current = build_outcomes()
        self.assertEqual(sorted(current), sorted(self.golden["outcomes"]))
        diffs = [key for key in current if current[key] != self.golden["outcomes"][key]]
        self.assertEqual(diffs, [], f"分割前と結果が違う入力: {diffs[:10]}")

    def test_golden_covers_both_acceptance_and_rejection(self):
        values = list(self.golden["outcomes"].values())
        accepted = [v for v in values if v.startswith("ok:")]
        self.assertGreater(len(accepted), 5)
        self.assertGreater(len(values) - len(accepted), 100)

    def test_every_public_name_is_still_importable_from_model(self):
        missing = [name for name in self.golden["names"] if not hasattr(model, name)]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
