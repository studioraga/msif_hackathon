"""P2b/P3-P5 fail-closed regression tests independent of EDA binaries."""
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import m72_exact_lq_import as p2b
import m72_report_review as physical

class TestM72Continuation(unittest.TestCase):
    def test_accepted_netlists_hash_pinned_and_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = p2b.prepare(ROOT, Path(tmp) / 'p2b')
            self.assertEqual(set(result), set(p2b.VARIANTS))
            for variant, entry in result.items():
                self.assertEqual(entry['raw_sha256'], entry['accepted_lq_sha256'])
                self.assertEqual(entry['normalization']['normalization_action'], 'NOOP_ALREADY_COMPATIBLE')
                self.assertEqual(entry['raw_sha256'], entry['normalized_sha256'])

    def test_missing_physical_reports_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = physical.collect(Path(tmp), 'normalized_v2')
            self.assertEqual(result['status'], 'BLOCKED_INCOMPLETE_REPORTS')
            self.assertEqual(result['physical_ppa_qualification'], 'NOT_VERIFIED')
            self.assertTrue(all(entry['missing'] for entry in result['variants'].values()))

    def test_timing_parser_missing_metrics_remain_unknown(self):
        entry = physical.parse_finish('finish report_worst_slack\nworst slack max 88.23\n')
        self.assertEqual(entry['worst_slack_max_ns'], 88.23)
        self.assertIsNone(entry['hold_violations'])
        self.assertIsNone(entry['wns_max_ns'])


class M72DocumentationBoundary(unittest.TestCase):
    """Reject accidental conversion of research receipts into release claims."""

    def test_canonical_docs_retain_release_blockers(self):
        architecture = (ROOT / 'docs' / 'Architecture.md').read_text()
        validation = (ROOT / 'docs' / 'Validation.md').read_text()
        self.assertIn('RELEASE_BLOCKED_REVIEW_REQUIRED', architecture)
        self.assertIn('NOT_VERIFIED', architecture)
        self.assertIn('MATCHED_BOUNDED_VCD_CAPTURED_NOT_POWER', validation)
        self.assertIn('release_authorized=false', validation)

    def test_python_version_matches_package_contract(self):
        package = (ROOT / 'pyproject.toml').read_text()
        prereq = (ROOT / 'docs' / 'Prerequisites.md').read_text()
        self.assertIn('requires-python = ">=3.12,<3.13"', package)
        self.assertIn('>=3.12,<3.13', prereq)
