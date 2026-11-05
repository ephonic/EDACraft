"""Limiting-case audit tests that do not require loading the native solver."""
from pathlib import Path
import importlib
import sys
import types
import unittest
import numpy as np

# Load the actual standalone audit modules with their relative imports intact.
# This intentionally tests no tcad public-package/native-extension integration.
package = '_tcad_mobility_floor_audit'
if package not in sys.modules:
    module = types.ModuleType(package)
    module.__path__ = [str(Path(__file__).resolve().parents[1]/'tcad/postprocess')]
    sys.modules[package] = module
audit = importlib.import_module(package+'.native_thermal').audit_native_lattice_mobility


def case(temperature=300., doping=0., electron=.1417, hole=.04705, base_n=.01):
    result = dict(converged=True, temperature=[temperature], phi=[0.], n=[1e20], p=[1e20],
        thermal_ledger=dict(available=True, mobility_temperature_K=[temperature],
            mobility_n_m2_V_s=[electron], mobility_p_m2_V_s=[hole],
            mobility_feedback=False, carrier_reference_temperature_K=temperature,
            carrier_reference_VT_V=.02585))
    for c in 'np':
        for axis in 'xyz':
            result['J'+c+'_'+axis] = [0.]
    return audit(result, ([0.],[0.],[0.]), [base_n], [.005], [doping], 'arora',
                 temperature, .02585, fixed_point_atol_K=1e-7,
                 current_rtol=1e-12, current_atol_A_m2=0.)


class AroraFloorAuditTests(unittest.TestCase):
    def test_zero_doping_300K_recovers_declared_maxima(self):
        self.assertTrue(case()['valid'])

    def test_legacy_missing_minimum_cannot_certify_itself(self):
        result = case(electron=.13648, hole=.04206)
        self.assertFalse(result['valid'])
        self.assertFalse(result['mobility_valid'])
        self.assertTrue(result['edge_current_valid'])

    def test_each_carrier_missing_floor_is_rejected(self):
        for values in (dict(electron=.13648), dict(hole=.04206)):
            with self.subTest(values=values):
                self.assertFalse(case(**values)['mobility_valid'])

    def test_high_doping_limit_retains_minimum(self):
        self.assertTrue(case(doping=1e100, electron=.00522, hole=.00499)['valid'])

    def test_high_doping_cannot_collapse_to_zero(self):
        self.assertFalse(case(doping=1e100, electron=0., hole=0.)['mobility_valid'])

    def test_temperature_term_does_not_scale_minimum(self):
        self.assertTrue(case(temperature=600., electron=(52.2+1364.8*2**-.66)*1e-4,
                            hole=(49.9+420.6*2**-2.05)*1e-4)['valid'])

    def test_insulator_zero_base_is_preserved(self):
        self.assertTrue(case(base_n=0., electron=0.)['valid'])

    def test_doping_sign_uses_total_uncompensated_population(self):
        values = dict(electron=(52.2+1364.8/2)*1e-4,
                      hole=(49.9+420.6/(1+(9.68e16/2.23e17)**.72))*1e-4)
        self.assertTrue(case(doping=9.68e22, **values)['valid'])
        self.assertTrue(case(doping=-9.68e22, **values)['valid'])


if __name__ == '__main__':
    unittest.main()
