import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from finding_triager.approved_materials import approved_materials


class ApprovedMaterialsTest(unittest.TestCase):
    def test_reads_only_receipt_bound_documents_and_rechecks_content(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            expected = {"issue": 783, "run_id": "run", "target_key": "key", "snapshot_oid": "a" * 40}
            (root / "binding.json").write_text(json.dumps({"expected": expected, "artifact_digest": "f" * 64}))
            rows = [("verification_design", "VerificationDesign", "vd.toml"),
                    ("solution_planning", "ChangePlan", "cp.toml")]
            receipts = []
            for phase, kind, path in rows:
                raw = ('artifact_type = "' + kind + '"\n').encode()
                (root / path).write_bytes(raw)
                receipts.append({"phase": phase, "artifact": path,
                                 "artifact_digest": hashlib.sha256(raw).hexdigest()})
            approval = {**expected, "context_id": "owner-approved", "reviews": receipts}
            marker = {"binding_file": "binding.json", "approval_file": "approval.json"}
            def normalize(doc):
                return {**doc, **expected}
            with patch('finding_triager.approved_materials.validate_phase_dispatch', return_value=approval) as validate, \
                 patch('finding_triager.approved_materials.read_committed_artifact', side_effect=lambda p, r: p.read_bytes()), \
                 patch('finding_triager.approved_materials.normalize', side_effect=normalize):
                result = approved_materials(root, marker)
                validate.assert_called_once_with(marker, "pr-reviewer", root)
                self.assertEqual(result['materials']['solution_planning']['path'], 'cp.toml')
                (root / 'cp.toml').write_text('artifact_type = "ChangePlan"\n# changed\n')
                with self.assertRaisesRegex(ValueError, 'digest changed'):
                    approved_materials(root, marker)

    def test_rejects_outside_path_even_if_native_verifier_misbehaves(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / 'binding.json').write_text(json.dumps({'expected': {}}))
            approval = {'reviews': [{'phase': 'verification_design', 'artifact': '../outside',
                                     'artifact_digest': '0' * 64}]}
            with patch('finding_triager.approved_materials.validate_phase_dispatch', return_value=approval):
                with self.assertRaisesRegex(ValueError, 'outside worktree'):
                    approved_materials(root, {'binding_file': 'binding.json'})
