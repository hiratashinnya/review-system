"""Regression seams for the G-02 collect/release extraction."""

import inspect
import unittest
from unittest.mock import patch

from gitgate import worktree
from gitgate import worktree_branch_cleanup, worktree_release_flow, worktree_handoff_io
from gitgate import worktree_ledger_access, worktree_release_safety


class WorktreeG02FacadeTests(unittest.TestCase):
    def test_existing_private_and_public_entrypoints_remain_importable(self):
        self.assertIs(worktree.worktree_release, worktree_release_flow.worktree_release)
        self.assertIs(worktree._cleanup_branch_ref, worktree_branch_cleanup._cleanup_branch_ref)
        self.assertIs(worktree.find_entry, worktree_ledger_access.find_entry)
        self.assertIs(worktree._reason_note, worktree_release_safety._reason_note)
        self.assertIs(worktree._read_handoff, worktree_handoff_io._read_handoff)

    def test_collect_keeps_original_signature_and_writer_patch_seam(self):
        params = inspect.signature(worktree.collect_worktree).parameters
        self.assertEqual(list(params), [
            "repo_root", "entry_id", "worktree_path", "handoff_path", "into",
            "allow_missing_handoff", "reason", "now", "runner", "max_bytes", "release",
        ])
        writer = object()
        with patch.object(worktree, "_write_collected", writer):
            with patch.object(worktree, "_collect_worktree_flow") as flow:
                worktree.collect_worktree(".", now="injected")
                self.assertIs(flow.call_args.kwargs["write_collected"], writer)
                self.assertIs(flow.call_args.kwargs["release_fn"], worktree.worktree_release)
