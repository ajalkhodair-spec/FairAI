import csv
import json
import unittest
from pathlib import Path

from scripts import (
    build_blocker_view,
    build_closure_evidence,
    build_reviewer_evidence_views,
)


ALLOWED_REVIEWER_STATUSES = {
    "experimentally_evaluated",
    "analytically_addressed",
    "bounded_as_limitation",
    "pending_author_or_external_action",
}


class ClosureEvidenceTests(unittest.TestCase):
    def test_reviewer_statuses_use_closure_vocabulary(self):
        with Path("docs/revision/REVIEWER_GAP_MATRIX.csv").open(
            newline=""
        ) as handle:
            rows = list(csv.DictReader(handle))
        self.assertTrue(rows)
        self.assertLessEqual(
            {row["status"] for row in rows}, ALLOWED_REVIEWER_STATUSES
        )

    def test_reviewer_secondary_views_are_current(self):
        data = build_reviewer_evidence_views.rows()
        self.assertEqual(
            build_reviewer_evidence_views.JSON_OUTPUT.read_text(),
            build_reviewer_evidence_views.render_json(data),
        )
        self.assertEqual(
            build_reviewer_evidence_views.CSV_OUTPUT.read_text(),
            build_reviewer_evidence_views.render_csv(data),
        )

    def test_blocker_secondary_view_is_current(self):
        data = build_blocker_view.rows()
        for path, content in build_blocker_view.expected_outputs().items():
            self.assertEqual(path.read_text(), content)
        self.assertEqual(data[-1]["id"], "BLK-005")

    def test_closure_manifest_and_freeze_are_current(self):
        checksum_text = build_closure_evidence.render_checksums()
        freeze_text = build_closure_evidence.render_freeze(checksum_text)
        self.assertEqual(
            build_closure_evidence.CHECKSUM_FILE.read_text(), checksum_text
        )
        self.assertEqual(build_closure_evidence.FREEZE_FILE.read_text(), freeze_text)
        freeze = json.loads(freeze_text)
        self.assertEqual(
            freeze["target_count"], len(build_closure_evidence.closure_targets())
        )
        self.assertEqual(
            freeze["source_baseline_commit"],
            build_closure_evidence.SOURCE_BASELINE_COMMIT,
        )

    def test_manuscript_package_excludes_build_products(self):
        targets = build_closure_evidence.manuscript_targets()
        self.assertIn(Path("manuscript/FairAI.tex"), targets)
        self.assertIn(Path("manuscript/Definitions/mdpi.cls"), targets)
        self.assertIn(Path("manuscript/Definitions/logo-orcid.pdf"), targets)
        self.assertNotIn(Path("manuscript/FairAI.pdf"), targets)
        self.assertFalse(any("synctex" in path.name for path in targets))
