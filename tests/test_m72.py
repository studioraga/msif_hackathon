"""M7.2 acceptance-boundary and constraint regression tests (no PDK assumed)."""
import importlib.util
import pathlib
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('m72_physical', ROOT / 'scripts/m72_physical.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class TestM72(unittest.TestCase):
    def test_common_sdc(self):
        a = mod.sdc(100, 5, 1, .01)
        self.assertIn('create_clock', a)
        self.assertIn('activations*', a)
        self.assertIn('rst_n', a)
        self.assertIn('set_output_delay', a)
        self.assertNotIn('set_false_path', a)
        self.assertEqual(a, mod.sdc(100, 5, 1, .01))

    def test_invalid_sdc_rejected(self):
        for c in (0, -1, 1, 1e99):
            with self.assertRaises(ValueError):
                mod.sdc(c, 5, 1, .01)
        with self.assertRaises(ValueError):
            mod.sdc(100, 99, 1, .01)
        with self.assertRaises(ValueError):
            mod.sdc(100, 5, 1, 0)

    def test_attestation_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'attest'):
            mod.preflight(pathlib.Path('.'), pathlib.Path('.'), pathlib.Path('.'))

    def test_missing_platform_fails(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(mod.shutil, 'which', return_value='/usr/bin/mock'), \
                 patch.object(mod, 'check_rtl', return_value={'shape':[2,4]}), \
                 patch.object(mod, 'audit_lq', return_value={'result':'PASS','vectors_per_architecture':[260]*3}):
                with self.assertRaises((ValueError, FileNotFoundError)):
                    mod.preflight(pathlib.Path(d), pathlib.Path(d), pathlib.Path(d) / 'out', acknowledge_license=True)

    def test_no_physical_claim_from_preflight(self):
        self.assertIn('NOT_VERIFIED', pathlib.Path(mod.__file__).read_text())
        self.assertIn('NOT_VERIFIED_ORFS_RESYNTHESIZES_RTL', pathlib.Path(mod.__file__).read_text())

    def test_dry_run_is_static_and_does_not_invoke_make(self):
        with tempfile.TemporaryDirectory() as td:
            out = pathlib.Path(td) / 'm72'
            flow = pathlib.Path(td) / 'orfs' / 'flow'
            flow.mkdir(parents=True)
            inputs = {}
            for v in mod.VARIANTS:
                d = out / v
                d.mkdir(parents=True)
                config = d / 'config.mk'
                constraint = d / 'constraint.sdc'
                config.write_text('export DESIGN_NAME = msif_' + v + '\n')
                constraint.write_text('create_clock -period 100 [get_ports clk]\n')
                inputs[v] = {'design_config': str(config), 'constraint_file': str(constraint)}
            with patch.object(mod.subprocess, 'run', side_effect=AssertionError('make invoked')):
                receipt = mod.run_flow({'variants': inputs}, out, flow.parent,
                                       execute=False, timeout=10)
            self.assertEqual(len(receipt['variants']), 3)
            for v in mod.VARIANTS:
                self.assertEqual(receipt['variants'][v]['status'], 'STATIC_PLAN_ONLY_NOT_EXECUTED')
                data = __import__('json').loads((out / v / 'orfs-plan.json').read_text())
                self.assertEqual(data['execution'], 'NOT_EXECUTED')
                self.assertEqual(data['physical_ppa'], 'NOT_VERIFIED')

    def test_dry_run_missing_sdc_fails(self):
        with tempfile.TemporaryDirectory() as td:
            out = pathlib.Path(td)
            config = out / 'config.mk'
            config.write_text('x')
            with self.assertRaisesRegex(ValueError, 'missing generated SDC'):
                mod.run_flow({'variants': {'programmable': {
                    'design_config': str(config),
                    'constraint_file': str(out / 'absent.sdc')} }},
                    out, out, execute=False, timeout=10)
