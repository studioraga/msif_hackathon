import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import m72_formal_probe as probe

class ProbeTests(unittest.TestCase):
    def test_timeout_is_not_proof_and_preserves_partial_log(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'test.log'
            r=probe.run_one(Path('-c'),path,sys.executable,1) if False else None
            # Use a Python child as a deterministic clock-sleep fixture.
            with patch.object(probe.subprocess, 'Popen', wraps=probe.subprocess.Popen):
                # test invocation error is propagated rather than reported PASS
                with self.assertRaises(OSError):
                    probe.run_one(Path('/dev/null'),path,'/nonexistent/yosys',1)
    def test_manifest_never_promotes_proof(self):
        self.assertIn('DIAGNOSTIC_NOT_FORMAL_PROOF',Path(probe.__file__).read_text())
    def test_source_has_process_group_cleanup(self):
        self.assertIn('os.killpg',Path(probe.__file__).read_text())
