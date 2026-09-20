"""`feedback_ledger`（Issue #522）の機械 lint・CLI・canonical 化のテスト。

時刻依存の判定（滞留）は**すべて ``--now`` / ``now=`` で wall clock を注入**して検証する
（`.claude/rules/04-test-data.md`「時刻依存 test data の規律」）。このファイルは
``datetime.date.today()`` を一切呼ばない。
"""

from __future__ import annotations

import datetime
import io
import json
import subprocess
import tempfile
import tomllib
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from feedback_ledger import allowlist as allowlist_module
from feedback_ledger import check as check_module
from feedback_ledger import routing as routing_module
from feedback_ledger import status as status_module
from feedback_ledger.cli import EXIT_ERROR, EXIT_NOT_FOUND, EXIT_OK, main
from feedback_ledger.model import ERROR, WARN
from feedback_ledger.schema import LEDGER_SPEC, PROPOSAL_SPEC, TRIAGE_SPEC
from feedback_ledger.store import load_store
from feedback_ledger.tomlwrite import TomlWriteError, dumps, render_value

NOW = datetime.date(2026, 9, 19)
OCCURRED = datetime.date(2026, 9, 1)
ENTRY_ID = "FBK-20260901-cli-only-writes"
PROPOSAL_ID = "FBP-20260919-tighten-contract"
TRIAGE_ID = "TRG-2026-W38"

NODE_ASSET = "docs/dashboard.md"
ISSUE_ASSET = "feedback_ledger/README.md"


def ledger_data(**overrides) -> dict:
    data = {
        "schema": LEDGER_SPEC.schema_const,
        "id": ENTRY_ID,
        "topic": "台帳への書込み経路を CLI に限定する判断",
        "occurred_at": OCCURRED,
        "decision_point": "implementation",
        "overridden_role": "main-thread",
        "divergence": "reversal",
        "confidence_of_inference": "medium",
        "recorded_by": "Claude Code (AI)",
        "affected_assets": [NODE_ASSET],
        "supersedes": "",
        "source": {"issue": 522, "pr": 0, "round": 0, "finding_ids": []},
        "narrative": {
            "background": "台帳の書込み経路をどう絞るかが論点になった。\n",
            "recommendation": "エージェントの直接編集を許し、lint で検出する。\n",
            "recommendation_reason": "実装が小さく、既存の運用を変えずに済むため。\n",
            "uncertainty": "",
            "owner_verbatim": "台帳へ書けるのは CLI だけにする。\n",
            "inferred_reason": "推測：検出では改ざんを止められないという判断。\n",
        },
    }
    for key, value in overrides.items():
        data[key] = value
    return data


def proposal_data(**overrides) -> dict:
    data = {
        "schema": PROPOSAL_SPEC.schema_const,
        "id": PROPOSAL_ID,
        "derived_from": [ENTRY_ID],
        "target_assets": [ISSUE_ASSET],
        "target_kind": "tooling",
        "routing": "issue",
        "status": "pending",
        "proposed_at": datetime.date(2026, 9, 19),
        "decided_in": "",
        "decided_by": "",
        "decided_at": "",
        "decision_reason": "",
        "issue_ref": "",
        "applied_pr": 0,
        "body": {
            "problem": "書込み経路の限定が README に書かれていない。\n",
            "proposed_change": "README に CLI 専用書込みの節を足す。\n",
            "rationale": "読み手が経路を誤らないようにするため。\n",
        },
    }
    for key, value in overrides.items():
        data[key] = value
    return data


def triage_data(**overrides) -> dict:
    data = {
        "schema": TRIAGE_SPEC.schema_const,
        "id": TRIAGE_ID,
        "period_start": datetime.date.fromisocalendar(2026, 38, 1),
        "period_end": datetime.date.fromisocalendar(2026, 38, 7),
        "reviewed": [ENTRY_ID],
        "outcomes": [{
            "entry": ENTRY_ID,
            "verdict": "no-change",
            "proposal": "",
            "merged_into": "",
            "reason": "既に契約として機能しているため変更しない。\n".strip(),
        }],
        "summary": {"notes": ""},
    }
    for key, value in overrides.items():
        data[key] = value
    return data


class FeedbackLedgerTestCase(unittest.TestCase):
    """各テストが独立した一時 repo-root で動く共通の足場。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        for relative in (
            ".ai/feedback/ledger", ".ai/feedback/queue", ".ai/feedback/triage",
            "tmp/_feedback", "docs", "feedback_ledger",
        ):
            (self.root / relative).mkdir(parents=True, exist_ok=True)
        (self.root / NODE_ASSET).write_text("dashboard\n", encoding="utf-8")
        (self.root / ISSUE_ASSET).write_text("readme\n", encoding="utf-8")

    # --- helpers ---------------------------------------------------------

    def write_draft(self, spec, data, name=None) -> str:
        path = self.root / "tmp/_feedback" / (name or f"{data['id']}.toml")
        path.write_text(dumps(spec, data), encoding="utf-8")
        return str(path.relative_to(self.root))

    def run_cli(self, *argv) -> tuple[int, str]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--root", str(self.root), *argv])
        return code, buffer.getvalue()

    def place(self, spec, data) -> Path:
        """CLI を通さず canonical ファイルを直接置く（bash 等での迂回書込みの再現）。

        CLI の preflight は不正な文書を**そもそも書かせない**ので、``check`` 側の検出力を
        検証するにはこの経路が要る（``permissions.deny`` を迂回した書込みを ``check`` が
        後段で捕まえる、という多層防御の2枚目を実際に踏むテスト）。
        """
        target = self.root / ".ai/feedback" / spec.subdir / f"{data['id']}.toml"
        target.write_text(dumps(spec, data), encoding="utf-8")
        return target

    def seed_entry(self, **overrides) -> str:
        draft = self.write_draft(LEDGER_SPEC, ledger_data(**overrides))
        code, _ = self.run_cli("new-entry", "--from", draft)
        self.assertEqual(code, EXIT_OK)
        return draft

    def seed_proposal(self, **overrides) -> str:
        draft = self.write_draft(PROPOSAL_SPEC, proposal_data(**overrides))
        code, _ = self.run_cli("propose", "--from", draft)
        self.assertEqual(code, EXIT_OK)
        return draft

    def seed_triage(self, **overrides) -> str:
        draft = self.write_draft(TRIAGE_SPEC, triage_data(**overrides))
        code, _ = self.run_cli("triage-close", "--from", draft)
        self.assertEqual(code, EXIT_OK)
        return draft

    def findings(self, *, canonical=True):
        return check_module.run_checks(self.root, canonical=canonical)

    def rules_with_errors(self, findings=None):
        findings = self.findings() if findings is None else findings
        return {f.rule for f in findings if f.level == ERROR}

    def stored(self, subdir, document_id) -> Path:
        return self.root / ".ai/feedback" / subdir / f"{document_id}.toml"


class CanonicalSerializerTests(FeedbackLedgerTestCase):
    def test_roundtrip_through_tomllib_preserves_every_value(self):
        for spec, data in (
            (LEDGER_SPEC, ledger_data()),
            (PROPOSAL_SPEC, proposal_data()),
            (TRIAGE_SPEC, triage_data()),
        ):
            with self.subTest(kind=spec.kind):
                text = dumps(spec, data)
                reloaded = tomllib.loads(text)
                self.assertEqual(reloaded["id"], data["id"])
                self.assertEqual(reloaded["schema"], spec.schema_const)
                # 再シリアライズしてバイト一致（canonical が冪等であること）
                self.assertEqual(dumps(spec, data), text)

    def test_written_documents_are_byte_identical_to_the_canonical_form(self):
        self.seed_entry()
        stored = self.stored("ledger", ENTRY_ID)
        self.assertEqual(stored.read_text(encoding="utf-8"), dumps(LEDGER_SPEC, ledger_data()))

    def test_multiline_values_are_literal_strings_and_keep_their_newlines(self):
        data = ledger_data()
        data["narrative"]["background"] = "1行目\n2行目\n"
        text = dumps(LEDGER_SPEC, data)
        self.assertIn("background = '''\n1行目\n2行目\n'''", text)
        self.assertEqual(tomllib.loads(text)["narrative"]["background"], "1行目\n2行目\n")

    def test_values_that_cannot_be_represented_are_refused(self):
        with self.assertRaises(TomlWriteError):
            render_value("text", "壊す''' マーカー\n")
        with self.assertRaises(TomlWriteError):
            render_value("line", "改行を\n含む")
        with self.assertRaises(TomlWriteError):
            render_value("date", "2026-09-19")


class L1KeyAndVocabularyTests(FeedbackLedgerTestCase):
    def test_missing_key_is_rejected(self):
        data = ledger_data()
        text = dumps(LEDGER_SPEC, data).replace('topic = "台帳への書込み経路を CLI に限定する判断"\n', "")
        draft = self.root / "tmp/_feedback/broken.toml"
        draft.write_text(text, encoding="utf-8")
        code, _ = self.run_cli("new-entry", "--from", "tmp/_feedback/broken.toml")
        self.assertEqual(code, EXIT_ERROR)

    def test_unknown_key_is_rejected(self):
        text = dumps(LEDGER_SPEC, ledger_data()) + '\nextra = "x"\n'
        (self.root / "tmp/_feedback/broken.toml").write_text(text, encoding="utf-8")
        code, _ = self.run_cli("new-entry", "--from", "tmp/_feedback/broken.toml")
        self.assertEqual(code, EXIT_ERROR)

    def test_enum_violation_is_rejected(self):
        draft = self.write_draft(LEDGER_SPEC, ledger_data(divergence="reversal"))
        text = (self.root / draft).read_text(encoding="utf-8").replace(
            'divergence = "reversal"', 'divergence = "u-turn"'
        )
        (self.root / draft).write_text(text, encoding="utf-8")
        code, _ = self.run_cli("new-entry", "--from", draft)
        self.assertEqual(code, EXIT_ERROR)

    def test_skill_scoped_overridden_role_is_accepted(self):
        self.seed_entry(overridden_role="skill:issue-pipeline")
        self.assertNotIn("L1", self.rules_with_errors())

    def test_id_must_match_the_filename(self):
        self.seed_entry()
        stored = self.stored("ledger", ENTRY_ID)
        stored.rename(stored.with_name("FBK-20260901-renamed.toml"))
        self.assertIn("L1", self.rules_with_errors())

    def test_slug_must_be_lowercase_and_hyphenated(self):
        data = ledger_data(id="FBK-20260901-Bad_Slug")
        draft = self.write_draft(LEDGER_SPEC, data, name="bad-slug.toml")
        code, _ = self.run_cli("new-entry", "--from", draft)
        self.assertEqual(code, EXIT_ERROR)

    def test_required_field_cannot_be_empty(self):
        data = ledger_data()
        data["narrative"]["recommendation"] = ""
        draft = self.write_draft(LEDGER_SPEC, data)
        code, _ = self.run_cli("new-entry", "--from", draft)
        self.assertEqual(code, EXIT_ERROR)


class L2AndL3ReferenceTests(FeedbackLedgerTestCase):
    def test_cli_refuses_to_record_an_unknown_asset_path(self):
        draft = self.write_draft(LEDGER_SPEC, ledger_data(affected_assets=["docs/nope.md"]))
        code, _ = self.run_cli("new-entry", "--from", draft)
        self.assertEqual(code, EXIT_ERROR)

    def test_missing_asset_path_is_reported(self):
        self.place(LEDGER_SPEC, ledger_data(affected_assets=["docs/does-not-exist.md"]))
        self.assertIn("L2", self.rules_with_errors())

    def test_traversal_in_asset_path_is_reported(self):
        self.place(LEDGER_SPEC, ledger_data(affected_assets=["../outside.md"]))
        self.assertIn("L2", self.rules_with_errors())

    def test_supersedes_must_point_at_an_existing_entry(self):
        self.place(LEDGER_SPEC, ledger_data(supersedes="FBK-20260101-nonexistent"))
        self.assertIn("L3", self.rules_with_errors())

    def test_supersedes_chain_between_existing_entries_passes(self):
        self.seed_entry()
        self.seed_entry(id="FBK-20260902-correction", supersedes=ENTRY_ID)
        self.assertNotIn("L3", self.rules_with_errors())


class L4AndL5NarrativeLintTests(FeedbackLedgerTestCase):
    def test_speculation_in_owner_verbatim_is_rejected(self):
        data = ledger_data()
        data["narrative"]["owner_verbatim"] = "おそらく CLI だけにしたいのだと思われる。\n"
        draft = self.write_draft(LEDGER_SPEC, data)
        code, _ = self.run_cli("new-entry", "--from", draft)
        self.assertEqual(code, EXIT_ERROR)

    def test_inferred_reason_requires_the_marker(self):
        data = ledger_data()
        data["narrative"]["inferred_reason"] = "検出では改ざんを止められないから。\n"
        draft = self.write_draft(LEDGER_SPEC, data)
        code, _ = self.run_cli("new-entry", "--from", draft)
        self.assertEqual(code, EXIT_ERROR)

    def test_assertion_vocabulary_in_inferred_reason_is_rejected(self):
        data = ledger_data()
        data["narrative"]["inferred_reason"] = "推測：オーナーは検出では不十分と述べた。\n"
        draft = self.write_draft(LEDGER_SPEC, data)
        code, _ = self.run_cli("new-entry", "--from", draft)
        self.assertEqual(code, EXIT_ERROR)

    def test_allowlist_entry_without_a_reason_fails_at_import_time(self):
        with self.assertRaises(ValueError):
            allowlist_module.AllowlistEntry(
                document_id=ENTRY_ID, rule="L4", term="おそらく",
                value="おそらくそうだ", reason="",
            )

    def test_allowlist_entry_rejects_an_unknown_rule(self):
        with self.assertRaises(ValueError):
            allowlist_module.AllowlistEntry(
                document_id=ENTRY_ID, rule="L9", term="おそらく",
                value="おそらくそうだ", reason="理由",
            )

    def test_allowlisted_wording_is_suppressed(self):
        verbatim = "おそらくこれで良い。\n"
        entry = allowlist_module.AllowlistEntry(
            document_id=ENTRY_ID, rule="L4", term="おそらく", value=verbatim,
            reason="オーナー自身が『おそらく』と言った逐語引用のため、語を外せない。",
        )
        original = allowlist_module.ALLOWLIST
        allowlist_module.ALLOWLIST = (entry,)
        self.addCleanup(setattr, allowlist_module, "ALLOWLIST", original)
        data = ledger_data()
        data["narrative"]["owner_verbatim"] = verbatim
        draft = self.write_draft(LEDGER_SPEC, data)
        code, _ = self.run_cli("new-entry", "--from", draft)
        self.assertEqual(code, EXIT_OK)


class L7CanonicalTests(FeedbackLedgerTestCase):
    def test_hand_edited_formatting_is_detected(self):
        self.seed_entry()
        stored = self.stored("ledger", ENTRY_ID)
        stored.write_text(
            stored.read_text(encoding="utf-8").replace(
                'recorded_by = "Claude Code (AI)"',
                'recorded_by   =   "Claude Code (AI)"',
            ),
            encoding="utf-8",
        )
        self.assertIn("L7", self.rules_with_errors())

    def test_canonical_is_skipped_without_the_flag(self):
        self.seed_entry()
        stored = self.stored("ledger", ENTRY_ID)
        stored.write_text(
            stored.read_text(encoding="utf-8").replace("topic =", "topic  ="),
            encoding="utf-8",
        )
        self.assertNotIn("L7", self.rules_with_errors(self.findings(canonical=False)))


class GitBackedImmutabilityTests(FeedbackLedgerTestCase):
    """L6（immutability）と P1（状態遷移）は merge base との比較なので実 git で検証する。"""

    def _git(self, *args):
        return subprocess.run(
            ["git", *args], cwd=str(self.root), capture_output=True, check=True
        )

    def setUp(self):
        super().setUp()
        try:
            self._git("init", "-b", "main")
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:  # pragma: no cover
            self.skipTest(f"git が使えない環境: {exc}")
        self._git("config", "user.email", "test@example.com")
        self._git("config", "user.name", "test")
        self.seed_entry()
        self.seed_proposal()
        self._git("add", "-A")
        self._git("commit", "-m", "seed")

    def test_modifying_a_committed_ledger_entry_is_rejected(self):
        stored = self.stored("ledger", ENTRY_ID)
        stored.write_text(
            stored.read_text(encoding="utf-8").replace("Claude Code (AI)", "someone else"),
            encoding="utf-8",
        )
        self.assertIn("L6", self.rules_with_errors())

    def test_deleting_a_committed_ledger_entry_is_rejected(self):
        self.stored("ledger", ENTRY_ID).unlink()
        self.assertIn("L6", self.rules_with_errors())

    def test_appending_a_new_entry_is_allowed(self):
        self.seed_entry(id="FBK-20260902-correction", supersedes=ENTRY_ID)
        self.assertNotIn("L6", self.rules_with_errors())

    def test_illegal_status_transition_is_rejected(self):
        stored = self.stored("queue", PROPOSAL_ID)
        stored.write_text(
            stored.read_text(encoding="utf-8").replace(
                'status = "pending"', 'status = "applied"'
            ),
            encoding="utf-8",
        )
        self.assertIn("P1", self.rules_with_errors())

    def test_base_ref_that_cannot_be_resolved_degrades_to_a_warning(self):
        findings = check_module.run_checks(self.root, canonical=True, base_ref="no-such-ref")
        skipped = [f for f in findings if f.rule in ("L6", "P1") and f.level == WARN]
        self.assertTrue(skipped)
        self.assertNotIn("L6", self.rules_with_errors(findings))

    # --- F-522-01: `*→superseded` は base 比較でも通る ---------------------

    DECIDED_FIELDS = {
        "decided_in": TRIAGE_ID,
        "decided_by": "owner",
        "decided_at": datetime.date(2026, 9, 19),
    }

    def _decided_variants(self) -> dict:
        """``superseded`` へ遷移しうる4つの出発状態と、その状態で P2 が要求する欄。"""
        return {
            "pending": {},
            "approved": dict(self.DECIDED_FIELDS),
            "rejected": {**self.DECIDED_FIELDS, "decision_reason": "既存の契約で足りるため"},
            "applied": {**self.DECIDED_FIELDS, "issue_ref": "#530", "applied_pr": 531},
        }

    def test_every_status_can_transition_to_superseded(self):
        """docstring と README が正規遷移と定める ``*→superseded`` が P1 を出さないこと。

        F-522-01 の回帰テスト。``ALLOWED_TRANSITIONS`` に
        ``(approved, superseded)`` 等が無いと、README「訂正シナリオ」の「承認の取り消し」が
        CLI では通るのに **merge base を解決できる CI でだけ**落ちる（CLI 自身の検証は
        base=None で遷移検査を飛ばすため、手元では再現しない）。
        """
        self.seed_triage()
        variants = self._decided_variants()
        for status, extra in variants.items():
            self.place(PROPOSAL_SPEC, proposal_data(
                id=f"FBP-20260920-from-{status}", status=status, **extra))
        self._git("add", "-A")
        self._git("commit", "-m", "decided proposals")
        self.assertNotIn("P1", self.rules_with_errors())  # base と一致＝当然通る

        for status, extra in variants.items():
            self.place(PROPOSAL_SPEC, proposal_data(
                id=f"FBP-20260920-from-{status}", status="superseded", **extra))
        findings = self.findings()
        self.assertNotIn("P1", self.rules_with_errors(findings))

    def test_reverse_and_revival_transitions_are_still_rejected(self):
        """逆行（``approved→pending``）と復活（``superseded→pending``）は依然 ERROR。

        F-522-01 の是正で ``*→superseded`` を通したことが、``→pending`` 方向まで
        緩めていないことを固定する（履歴を書き換えない不変条件）。
        """
        self.seed_triage()
        for status in ("approved", "superseded"):
            self.place(PROPOSAL_SPEC, proposal_data(
                id=f"FBP-20260920-{status}-then-back", status=status, **self.DECIDED_FIELDS))
        self._git("add", "-A")
        self._git("commit", "-m", "decided proposals")

        for status in ("approved", "superseded"):
            self.place(PROPOSAL_SPEC, proposal_data(
                id=f"FBP-20260920-{status}-then-back", status="pending", **self.DECIDED_FIELDS))
        findings = self.findings()
        self.assertIn("P1", self.rules_with_errors(findings))
        reverted = [f for f in findings if f.rule == "P1" and f.level == ERROR]
        self.assertEqual(len(reverted), 2)

    # --- F-522-02: base 未解決を CI では ERROR にできる ---------------------

    def test_require_base_promotes_the_skip_to_an_error(self):
        """``require_base=True`` のとき、base 未解決の L6・P1 skip が ERROR になる。

        F-522-02 の回帰テスト。`fetch-depth: 0` が失われた CI でも WARN のままだと、
        改ざん検知（L6）と状態遷移（P1）が無言で無効化されたままビルドが緑になる。
        """
        findings = check_module.run_checks(
            self.root, canonical=True, base_ref="no-such-ref", require_base=True)
        rules = self.rules_with_errors(findings)
        self.assertIn("L6", rules)
        self.assertIn("P1", rules)

    def test_require_base_is_silent_when_the_base_resolves(self):
        findings = check_module.run_checks(self.root, canonical=True, require_base=True)
        self.assertFalse(self.rules_with_errors(findings))
        self.assertFalse([f for f in findings if f.rule in ("L6", "P1")])

    def test_cli_require_base_exits_with_the_error_code(self):
        """CI が使う形（終了コード4）と、既定（WARN のまま 0）の両方を固定する。"""
        code, _ = self.run_cli("check", "--canonical", "--base-ref", "no-such-ref",
                               "--require-base")
        self.assertEqual(code, EXIT_ERROR)
        code, output = self.run_cli("check", "--canonical", "--base-ref", "no-such-ref")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("errors=0", output)


class ProposalRuleTests(FeedbackLedgerTestCase):
    def test_approved_requires_decider_and_date(self):
        self.seed_entry()
        self.seed_proposal()
        stored = self.stored("queue", PROPOSAL_ID)
        stored.write_text(
            stored.read_text(encoding="utf-8").replace(
                'status = "pending"', 'status = "approved"'
            ),
            encoding="utf-8",
        )
        self.assertIn("P2", self.rules_with_errors())

    def test_rejected_requires_a_reason(self):
        self.seed_entry()
        self.place(PROPOSAL_SPEC, proposal_data(
            status="rejected", decided_by="owner", decided_at=datetime.date(2026, 9, 19)))
        self.assertIn("P2", self.rules_with_errors())

    def test_applied_requires_issue_ref_and_pr(self):
        self.seed_entry()
        self.place(PROPOSAL_SPEC, proposal_data(
            status="applied", decided_by="owner", decided_in=TRIAGE_ID,
            decided_at=datetime.date(2026, 9, 19)))
        self.assertIn("P2", self.rules_with_errors())

    def test_derived_from_must_exist(self):
        self.place(PROPOSAL_SPEC, proposal_data())
        self.assertIn("P3", self.rules_with_errors())

    def test_cli_refuses_a_proposal_with_an_unknown_source_entry(self):
        draft = self.write_draft(PROPOSAL_SPEC, proposal_data())
        code, _ = self.run_cli("propose", "--from", draft)
        self.assertEqual(code, EXIT_ERROR)

    def test_routing_must_match_the_classification_table(self):
        self.seed_entry()
        self.place(PROPOSAL_SPEC, proposal_data(target_assets=[NODE_ASSET], routing="issue"))
        self.assertIn("P4", self.rules_with_errors())

    def test_routing_node_is_accepted_for_contained_assets(self):
        self.seed_entry()
        self.seed_proposal(target_assets=[NODE_ASSET], routing="node")
        self.assertNotIn("P4", self.rules_with_errors())

    def test_mixed_routing_targets_must_be_split(self):
        self.seed_entry()
        self.place(PROPOSAL_SPEC, proposal_data(
            target_assets=[NODE_ASSET, ISSUE_ASSET], routing="node"))
        self.assertIn("P4", self.rules_with_errors())

    def test_routing_table_classifies_harness_and_contained_assets(self):
        self.assertEqual(routing_module.route_for(".claude/skills/align/SKILL.md"), "node")
        self.assertEqual(routing_module.route_for(".ai/agents/spec-author.md"), "node")
        self.assertEqual(routing_module.route_for(".claude/hooks/agent-command-gate.sh"), "issue")
        self.assertEqual(routing_module.route_for(".ai/skills/issue-pipeline/SKILL.md"), "issue")
        self.assertEqual(routing_module.route_for("karte/model.py"), "issue")
        self.assertEqual(routing_module.route_for("dsv2/cli.py"), "node")


class TriageRuleTests(FeedbackLedgerTestCase):
    def test_reviewed_and_outcomes_must_agree(self):
        self.seed_entry()
        data = triage_data(reviewed=[ENTRY_ID, "FBK-20260902-other"])
        draft = self.write_draft(TRIAGE_SPEC, data)
        code, _ = self.run_cli("triage-close", "--from", draft)
        self.assertEqual(code, EXIT_ERROR)

    def test_proposed_verdict_requires_an_existing_proposal(self):
        self.seed_entry()
        data = triage_data(outcomes=[{
            "entry": ENTRY_ID, "verdict": "proposed", "proposal": PROPOSAL_ID,
            "merged_into": "", "reason": "",
        }])
        draft = self.write_draft(TRIAGE_SPEC, data)
        code, _ = self.run_cli("triage-close", "--from", draft)
        self.assertEqual(code, EXIT_ERROR)

    def test_no_change_verdict_requires_a_reason(self):
        self.seed_entry()
        data = triage_data(outcomes=[{
            "entry": ENTRY_ID, "verdict": "no-change", "proposal": "",
            "merged_into": "", "reason": "",
        }])
        draft = self.write_draft(TRIAGE_SPEC, data)
        code, _ = self.run_cli("triage-close", "--from", draft)
        self.assertEqual(code, EXIT_ERROR)

    def test_period_must_match_the_iso_week_in_the_id(self):
        self.seed_entry()
        data = triage_data(period_start=datetime.date(2026, 1, 5))
        draft = self.write_draft(TRIAGE_SPEC, data)
        code, _ = self.run_cli("triage-close", "--from", draft)
        self.assertEqual(code, EXIT_ERROR)

    def test_a_missing_week_is_reported_as_a_warning_not_an_error(self):
        self.seed_entry()
        self.seed_triage()
        later = triage_data(
            id="TRG-2026-W40",
            period_start=datetime.date.fromisocalendar(2026, 40, 1),
            period_end=datetime.date.fromisocalendar(2026, 40, 7),
            reviewed=[], outcomes=[],
        )
        self.seed_triage(**{key: later[key] for key in
                           ("id", "period_start", "period_end", "reviewed", "outcomes")})
        findings = self.findings()
        gaps = [f for f in findings if f.rule == "T1" and f.level == WARN]
        self.assertTrue(gaps)
        self.assertIn("TRG-2026-W39", gaps[0].message)
        self.assertNotIn("T1", self.rules_with_errors(findings))


class StatusTests(FeedbackLedgerTestCase):
    def test_untriaged_entry_becomes_stale_only_after_the_threshold(self):
        self.seed_entry()
        store = load_store(self.root)
        fresh = status_module.compute(store, OCCURRED + datetime.timedelta(days=3))
        aged = status_module.compute(store, OCCURRED + datetime.timedelta(days=30))
        self.assertEqual(fresh[0].state, status_module.UNTRIAGED)
        self.assertFalse(fresh[0].stale)
        self.assertTrue(aged[0].stale)
        self.assertEqual(aged[0].age_days, 30)

    def test_states_follow_the_proposal_lifecycle(self):
        self.seed_entry()
        self.seed_proposal()
        self.seed_triage(outcomes=[{
            "entry": ENTRY_ID, "verdict": "proposed", "proposal": PROPOSAL_ID,
            "merged_into": "", "reason": "",
        }])
        store = load_store(self.root)
        self.assertEqual(status_module.compute(store, NOW)[0].state, status_module.PROPOSED)

        code, _ = self.run_cli("approve", "--proposal", PROPOSAL_ID, "--triage", TRIAGE_ID,
                               "--by", "owner", "--now", "2026-09-19")
        self.assertEqual(code, EXIT_OK)
        store = load_store(self.root)
        self.assertEqual(status_module.compute(store, NOW)[0].state, status_module.APPROVED)

        code, _ = self.run_cli("apply-done", "--proposal", PROPOSAL_ID,
                               "--issue-ref", "#530", "--applied-pr", "531")
        self.assertEqual(code, EXIT_OK)
        store = load_store(self.root)
        self.assertEqual(status_module.compute(store, NOW)[0].state, status_module.APPLIED)

    def test_triage_verdicts_produce_carried_and_closed(self):
        self.seed_entry()
        self.seed_triage()
        store = load_store(self.root)
        self.assertEqual(status_module.compute(store, NOW)[0].state, status_module.CLOSED)

    def test_status_json_uses_the_injected_now(self):
        self.seed_entry()
        code, output = self.run_cli("status", "--now", "2026-09-19", "--json")
        self.assertEqual(code, EXIT_OK)
        payload = json.loads(output)
        self.assertEqual(payload["now"], "2026-09-19")
        self.assertEqual(payload["entries"][0]["state"], status_module.UNTRIAGED)
        self.assertEqual(payload["entries"][0]["age_days"], 18)
        self.assertTrue(payload["entries"][0]["stale"])

    def test_status_reports_not_found_for_an_unknown_entry(self):
        code, _ = self.run_cli("status", "--now", "2026-09-19", "--entry", "FBK-20200101-none")
        self.assertEqual(code, EXIT_NOT_FOUND)


class CliWorkflowTests(FeedbackLedgerTestCase):
    def test_check_exit_codes(self):
        code, output = self.run_cli("check", "--canonical")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("errors=0", output)
        self.place(LEDGER_SPEC, ledger_data(affected_assets=["docs/missing.md"]))
        code, _ = self.run_cli("check", "--canonical")
        self.assertEqual(code, EXIT_ERROR)

    def test_index_reports_not_found_when_empty(self):
        code, _ = self.run_cli("index")
        self.assertEqual(code, EXIT_NOT_FOUND)
        self.seed_entry()
        code, output = self.run_cli("index")
        self.assertEqual(code, EXIT_OK)
        self.assertIn(ENTRY_ID, output)

    def test_triage_open_writes_a_draft_listing_untriaged_entries(self):
        self.seed_entry()
        code, output = self.run_cli("triage-open", "--week", "2026-W38", "--now", "2026-09-19")
        self.assertEqual(code, EXIT_OK)
        draft = self.root / "tmp/_feedback/TRG-2026-W38.toml"
        self.assertTrue(draft.is_file())
        parsed = tomllib.loads(draft.read_text(encoding="utf-8"))
        self.assertEqual(parsed["reviewed"], [ENTRY_ID])
        self.assertEqual(parsed["outcomes"][0]["verdict"], "need-more-evidence")
        self.assertIn("棚卸し対象 1 件", output)

    def test_correction_scenario_1_entry_typo_needs_a_superseding_entry(self):
        self.seed_entry()
        draft = self.write_draft(LEDGER_SPEC, ledger_data(), name="again.toml")
        code, _ = self.run_cli("new-entry", "--from", draft)
        self.assertEqual(code, EXIT_ERROR)  # 既存エントリは CLI からも書き換えられない
        self.seed_entry(id="FBK-20260902-correction", supersedes=ENTRY_ID,
                        topic="誤記を訂正した記録")
        self.assertFalse(self.rules_with_errors())

    def test_correction_scenario_2_amend_a_pending_proposal(self):
        self.seed_entry()
        self.seed_proposal()
        amended = proposal_data()
        amended["body"]["proposed_change"] = "README に加えて .ai/README.md も直す。\n"
        draft = self.write_draft(PROPOSAL_SPEC, amended, name="amend.toml")
        code, _ = self.run_cli("amend-proposal", "--from", draft)
        self.assertEqual(code, EXIT_OK)
        stored = tomllib.loads(self.stored("queue", PROPOSAL_ID).read_text(encoding="utf-8"))
        self.assertIn(".ai/README.md", stored["body"]["proposed_change"])
        self.assertFalse(self.rules_with_errors())

    def test_correction_scenario_3_cancel_an_approval_by_superseding(self):
        self.seed_entry()
        self.seed_proposal()
        self.seed_triage(outcomes=[{
            "entry": ENTRY_ID, "verdict": "proposed", "proposal": PROPOSAL_ID,
            "merged_into": "", "reason": "",
        }])
        code, _ = self.run_cli("approve", "--proposal", PROPOSAL_ID, "--triage", TRIAGE_ID,
                               "--by", "owner", "--now", "2026-09-19")
        self.assertEqual(code, EXIT_OK)
        # 承認済みは amend できない（逆行遷移を作らない）
        code, _ = self.run_cli("amend-proposal", "--from",
                               self.write_draft(PROPOSAL_SPEC, proposal_data(), name="x.toml"))
        self.assertEqual(code, EXIT_ERROR)
        replacement = proposal_data(id="FBP-20260920-replacement")
        code, _ = self.run_cli("propose", "--from",
                               self.write_draft(PROPOSAL_SPEC, replacement),
                               "--supersede", PROPOSAL_ID)
        self.assertEqual(code, EXIT_OK)
        old = tomllib.loads(self.stored("queue", PROPOSAL_ID).read_text(encoding="utf-8"))
        self.assertEqual(old["status"], "superseded")
        self.assertFalse(self.rules_with_errors())

    def test_correction_scenario_4_reopen_and_extend_a_triage_record(self):
        self.seed_entry()
        self.seed_triage()
        extended = triage_data(summary={"notes": "棚卸し後に補足を追記した。\n"})
        draft = self.write_draft(TRIAGE_SPEC, extended, name="extend.toml")
        code, _ = self.run_cli("triage-close", "--from", draft)
        self.assertEqual(code, EXIT_OK)
        stored = tomllib.loads(self.stored("triage", TRIAGE_ID).read_text(encoding="utf-8"))
        self.assertIn("補足", stored["summary"]["notes"])
        self.assertFalse(self.rules_with_errors())

    def test_reject_records_the_decider_and_reason(self):
        self.seed_entry()
        self.seed_proposal()
        code, _ = self.run_cli("reject", "--proposal", PROPOSAL_ID, "--by", "owner",
                               "--reason", "既存の契約で足りるため", "--now", "2026-09-19")
        self.assertEqual(code, EXIT_OK)
        stored = tomllib.loads(self.stored("queue", PROPOSAL_ID).read_text(encoding="utf-8"))
        self.assertEqual(stored["status"], "rejected")
        self.assertEqual(stored["decided_by"], "owner")
        self.assertFalse(self.rules_with_errors())

    def test_apply_done_requires_an_approved_proposal(self):
        self.seed_entry()
        self.seed_proposal()
        code, _ = self.run_cli("apply-done", "--proposal", PROPOSAL_ID,
                               "--issue-ref", "#530", "--applied-pr", "531")
        self.assertEqual(code, EXIT_ERROR)

    def test_unknown_proposal_is_not_found(self):
        code, _ = self.run_cli("reject", "--proposal", "FBP-20200101-none", "--by", "owner",
                               "--reason", "x")
        self.assertEqual(code, EXIT_NOT_FOUND)

    def test_draft_outside_the_repo_root_is_refused(self):
        code, _ = self.run_cli("new-entry", "--from", "../escape.toml")
        self.assertEqual(code, EXIT_ERROR)


class RepositorySmokeTests(unittest.TestCase):
    """CI が実行するのと同じ形（リポジトリ実体に対する ``check --canonical``）を1本通す。"""

    REPO_ROOT = Path(__file__).resolve().parents[2]

    def test_repository_feedback_tree_has_no_lint_errors(self):
        findings = check_module.run_checks(self.REPO_ROOT, canonical=True)
        errors = [finding.render() for finding in findings if finding.level == ERROR]
        self.assertEqual(errors, [])

    def test_the_three_document_directories_are_version_controlled(self):
        for relative in ("ledger", "queue", "triage"):
            with self.subTest(relative=relative):
                directory = self.REPO_ROOT / ".ai/feedback" / relative
                self.assertTrue(directory.is_dir())
                self.assertTrue((directory / ".gitkeep").is_file())

    def test_write_paths_are_denied_for_the_edit_and_write_tools(self):
        """書込み経路が CLI だけであることの一方の担保（もう一方は agent-command-gate）。"""
        settings = json.loads(
            (self.REPO_ROOT / ".claude/settings.json").read_text(encoding="utf-8")
        )
        deny = settings["permissions"]["deny"]
        self.assertIn("Edit(/.ai/feedback/**)", deny)
        self.assertIn("Write(/.ai/feedback/**)", deny)


class SharedSchemaCorrespondenceTests(unittest.TestCase):
    """`.ai/schema/feedback-*-v1.json` が手書き検証器と同じ契約を宣言していること。"""

    REPO_ROOT = Path(__file__).resolve().parents[2]

    def _schema(self, name):
        return json.loads(
            (self.REPO_ROOT / ".ai/schema" / name).read_text(encoding="utf-8")
        )

    def test_schema_constants_match(self):
        for name, spec in (
            ("feedback-ledger-v1.json", LEDGER_SPEC),
            ("feedback-proposal-v1.json", PROPOSAL_SPEC),
            ("feedback-triage-v1.json", TRIAGE_SPEC),
        ):
            with self.subTest(name=name):
                schema = self._schema(name)
                self.assertEqual(schema["properties"]["schema"]["const"], spec.schema_const)
                self.assertFalse(schema["additionalProperties"])

    def test_required_keys_match_the_declared_field_sets(self):
        for name, spec in (
            ("feedback-ledger-v1.json", LEDGER_SPEC),
            ("feedback-proposal-v1.json", PROPOSAL_SPEC),
            ("feedback-triage-v1.json", TRIAGE_SPEC),
        ):
            with self.subTest(name=name):
                schema = self._schema(name)
                declared = set()
                for table in spec.tables:
                    if table.name:
                        declared.add(table.name)
                    else:
                        declared.update(field.name for field in table.fields)
                self.assertEqual(set(schema["required"]), declared)
                self.assertEqual(set(schema["properties"]), declared)

    def test_enumerations_match(self):
        ledger = self._schema("feedback-ledger-v1.json")["properties"]
        from feedback_ledger.schema import (
            CONFIDENCES, DECISION_POINTS, DIVERGENCES, PROPOSAL_STATUSES,
            ROUTINGS, TARGET_KINDS, VERDICTS,
        )
        self.assertEqual(set(ledger["decision_point"]["enum"]), set(DECISION_POINTS))
        self.assertEqual(set(ledger["divergence"]["enum"]), set(DIVERGENCES))
        self.assertEqual(set(ledger["confidence_of_inference"]["enum"]), set(CONFIDENCES))
        proposal = self._schema("feedback-proposal-v1.json")["properties"]
        self.assertEqual(set(proposal["status"]["enum"]), set(PROPOSAL_STATUSES))
        self.assertEqual(set(proposal["routing"]["enum"]), set(ROUTINGS))
        self.assertEqual(set(proposal["target_kind"]["enum"]), set(TARGET_KINDS))
        triage = self._schema("feedback-triage-v1.json")
        outcome = triage["$defs"]["outcome"]["properties"]
        self.assertEqual(set(outcome["verdict"]["enum"]), set(VERDICTS))

    def test_no_jsonschema_dependency_is_introduced(self):
        sources = [
            path for path in (self.REPO_ROOT / "feedback_ledger").glob("*.py")
        ]
        self.assertTrue(sources)
        for path in sources:
            with self.subTest(path=path.name):
                self.assertNotIn("import jsonschema", path.read_text(encoding="utf-8"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
