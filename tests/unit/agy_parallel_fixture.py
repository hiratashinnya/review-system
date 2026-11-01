"""通常reader/resolverを使う、同一許可root配下の2子fixture。"""

import json
from dataclasses import replace

from agy_delegate.cohort_paths import workspace_id
from agy_delegate.native_policy import expected_file_only_rules
from agy_delegate.permissions import expected_rules
from tests.unit.agy_runtime_cohort_fixture import RuntimeCohortFixture


class ParallelCohortFixture(RuntimeCohortFixture):
    def setUp(self):
        super().setUp()
        self.permission_root = self.workspace
        self.children = (self.workspace / "a", self.workspace / "b")
        for child in self.children:
            child.mkdir()
        self.roots = (self.permission_root, *self.children)
        logical = expected_rules(self.permission_root)
        logical["deny"] = [f"write_file({path}/doc-system-v2/nodes)" for path in self.roots]
        self.settings.write_text(json.dumps({"permissions": logical}))
        native = expected_file_only_rules(self.permission_root, corpus_roots=self.roots)
        self.files["global"].write_text(json.dumps({"permissions": native}))
        self.requests = []
        for child in self.children:
            self.workspace = child
            self.wid = workspace_id(child)
            self.request = replace(self.request, workspace=child, permission_root=self.permission_root)
            self.refresh_proof()
            self.requests.append(self.request)
