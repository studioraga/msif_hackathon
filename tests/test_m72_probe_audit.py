import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import m72_probe_audit as a

class AuditTest(unittest.TestCase):
    def test_existing_probe(self):
        probe=Path(__file__).resolve().parents[1]/'build/m72/formal-probe-v5-closure11a'
        if not (probe/'manifest.json').exists(): self.skipTest('Node1 evidence not packaged')
        r=a.audit(probe)
        self.assertEqual(set(r['variants']),set(a.VARIANTS))
        self.assertTrue(all(x['interpretation']=='INCONCLUSIVE_NOT_EQUIVALENCE_PROOF' for x in r['variants'].values()))
    def test_missing_architecture_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'manifest.json').write_text(json.dumps({'schema':'msif-m72-formal-diagnostic-v1','variants':{}}))
            with self.assertRaisesRegex(ValueError,'architecture'): a.audit(p)
    def test_tampered_log_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            records={}
            for v in a.VARIANTS:
                log=p/f'{v}.log'; log.write_text('123. Executing EQUIV_INDUCT pass.\n')
                records[v]={'status':'TIMEOUT_INCONCLUSIVE','log_sha256':a.sha(log),'log_bytes':log.stat().st_size}
            (p/'manifest.json').write_text(json.dumps({'schema':'msif-m72-formal-diagnostic-v1','variants':records}))
            (p/'fixed.log').write_text('tampered')
            with self.assertRaisesRegex(ValueError,'digest'):a.audit(p)
