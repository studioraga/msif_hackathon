import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from m71_lq_audit import verify

class TestM71LQAudit(unittest.TestCase):
    def test_missing_evidence_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                verify(Path(tmp))

    def test_false_approval_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            build = Path(tmp)
            out = build / "m71_lq"
            out.mkdir()
            (out / "evidence.json").write_text(json.dumps({
                "schema": "msif-m71-lq-v1",
                "qualification": "bounded-mapped-gate-level-validation",
                "release_approval": "PASS",
                "full_formal_equivalence": "NOT_VERIFIED",
                "physical_ppa": "NOT_VERIFIED",
            }))
            with self.assertRaises(ValueError):
                verify(build)

    def test_missing_architectures_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            build = Path(tmp)
            out = build / "m71_lq"
            out.mkdir()
            (out / "evidence.json").write_text(json.dumps({
                "schema": "msif-m71-lq-v1",
                "qualification": "bounded-mapped-gate-level-validation",
                "release_approval": "NOT_VERIFIED",
                "full_formal_equivalence": "NOT_VERIFIED",
                "physical_ppa": "NOT_VERIFIED",
                "liberty_sha256": "a" * 64,
                "model_sha256": "b" * 64,
                "manifest_sha256": "c" * 64,
                "architectures": {},
            }))
            (build / "model.json").write_text("{}")
            with self.assertRaises(ValueError):
                verify(build)
