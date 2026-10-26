import copy
import json
import tempfile
import unittest
from pathlib import Path
from msif.core import inference
from msif.governance import validate_manifest
from msif.tensor_import import quantize_matrix, import_tensor, build_from_tensor

class TestM51(unittest.TestCase):
    def test_ties_to_even(self):
        self.assertEqual(quantize_matrix([[.5, 1.5, 2.5, -1.5, -2.5]], 1), [[0, 2, 2, -2, -2]])
    def test_reject_overflow_and_nonfinite(self):
        for matrix in ([[8.0]], [[float('nan')]], [[float('inf')]], [[0,1], [2]]):
            with self.assertRaises(ValueError): quantize_matrix(matrix, 1)
        for scale in (0, -1, float('nan')):
            with self.assertRaises(ValueError): quantize_matrix([[1.0]], scale)
    def test_pytorch_import_determinism_and_tamper(self):
        import torch
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint=Path(tmp)/'model.pt'
            torch.save({'layer.weight': torch.tensor([[0., 0.5, -0.5, 1.0], [-1., 0.25, -0.25, 0.0]],dtype=torch.float32)}, checkpoint)
            m1=import_tensor(checkpoint, 0.25, 'layer.weight')
            m2=import_tensor(checkpoint, 0.25, 'layer.weight')
            self.assertEqual(m1,m2)
            self.assertEqual(m1['weights'], [[0,2,-2,4],[-4,1,-1,0]])
            self.assertEqual(inference(m1,[127,-128,1,0]),[-258,-637])
            d=Path(tmp)/'out'; build_from_tensor(checkpoint, .25, d, 'layer.weight')
            self.assertTrue(validate_manifest(d))
            self.assertEqual(json.loads((d/'model.json').read_text())['provenance']['source_file_sha256'],m1['provenance']['source_file_sha256'])
            with (d/'msif_fixed.sv').open('a') as f:f.write(' //tampered')
            with self.assertRaises(ValueError):validate_manifest(d)
    def test_reject_unsupported_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'data.json';p.write_text('{}')
            with self.assertRaises(ValueError):import_tensor(p,1)
    def test_ambiguous_key_rejected(self):
        import torch
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'t.pt'; torch.save({'w':torch.zeros((2,2))},p)
            with self.assertRaises(ValueError):import_tensor(p,1)
