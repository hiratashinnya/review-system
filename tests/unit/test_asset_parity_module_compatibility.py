"""Responsibility split retains the supported public import paths."""

import unittest

from asset_parity import inventory, report, staleness
from asset_parity.asset import Asset
from asset_parity.commit_epoch import git_last_commit_epoch
from asset_parity.report_builder import build_report
from asset_parity.report_json import render_json, to_jsonable
from asset_parity.report_model import AssetRow, Cell, Report
from asset_parity.report_text import render_text
from asset_parity.seed_scan import scan_parity_seeds
from asset_parity.stale_signal import StaleSignal


class TestModuleCompatibility(unittest.TestCase):
    def test_inventory_public_imports_are_preserved(self):
        self.assertIs(inventory.Asset, Asset)
        self.assertIs(inventory.scan_parity_seeds, scan_parity_seeds)

    def test_report_public_imports_are_preserved(self):
        for name, implementation in {
            'AssetRow': AssetRow, 'Cell': Cell, 'Report': Report,
            'build_report': build_report, 'to_jsonable': to_jsonable,
            'render_json': render_json, 'render_text': render_text,
        }.items():
            with self.subTest(name=name):
                self.assertIs(getattr(report, name), implementation)

    def test_staleness_public_imports_are_preserved(self):
        self.assertIs(staleness.StaleSignal, StaleSignal)
        self.assertIs(staleness.git_last_commit_epoch, git_last_commit_epoch)
