"""Diagnostic output must expose failures without making strict histories pass."""
from pathlib import Path
import sys
import unittest

# Also runs with stdlib Python on audit hosts without the simulation runtime.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tcad/validation'))
from sentaurus_log import audit_sentaurus_nonlinear_convergence
from sentaurus_newton import audit_sentaurus_newton_diagnostics as audit

HEADER = 'Iteration   |Rhs|      factor     |step|     error   #inner  #iterative  time\n----\n'
COMPLETE = 'Sentaurus Device simulation finished\nGood Bye !\n'
RHS_HEADER = '\nk_error_per_object:\nmax-norm : imax : l2-norm : inst : pde : imax-coords (um)\n'
CNORM = ('C-norm_equation max_error vertex coordinate [um] value\n'
         ' poisson: 1e-8 3 (0.25, -0.0) -0.003\n'
         ' electron: 1e-6 4 (0.5, 0.002) 1e10\n'
         ' hole: 1e-7 5 (0.75, 0.002) 2e10\n')


def rhs(scale):
    return RHS_HEADER + ''.join(f'{v} : {i} : {v} : : {eq} : ( 0.5 0.002 )\n'
                               for i, (v, eq) in enumerate(((scale * .01, 'Poisson'), (scale, 'Electron'), (scale * .1, 'Hole'))))


def sample(error='.5', termination='Error smaller than 1 ( .5 ).'):
    return HEADER + '0 1e-6 0.01\n' + rhs(1e-6) + CNORM + f'1 1e-32 1 1e-8 {error} 0 1 .1\n' + rhs(1e-32) + 'Finished, because...\n' + termination + '\n' + COMPLETE


class NewtonDiagnosticTests(unittest.TestCase):
    def assert_rejected(self, text):
        self.assertFalse(audit(text)['valid'])

    def test_real_format_and_locations(self):
        r = audit(sample())
        self.assertTrue(r['valid'])
        self.assertTrue(r['diagnostics_available'])
        self.assertEqual(r['records'][0]['rhs_per_equation']['electron']['imax'], 1)
        c = r['records'][0]['following_c_norm']['poisson']
        self.assertEqual(c['coordinates_um'], [.25, -0.0])
        self.assertEqual(c['reported_value'], -.003)
        self.assertFalse(r['root_cause_proven'])
        self.assertFalse(r['acceptance_criteria_changed'])
        self.assertFalse(r['physical_validated'])

    def test_legacy_plain_history_identical(self):
        text = HEADER + '0 1e-6 .0\n1 1e-30 1 1e-8 .5 0 1 .1\nFinished, because...\nError smaller than 1 ( .5 ).\n' + COMPLETE
        r = audit(text)
        self.assertEqual(r['history'], audit_sentaurus_nonlinear_convergence(text))
        self.assertTrue(r['valid'])
        self.assertFalse(r['diagnostics_available'])

    def test_failed_attempt_then_success_still_rejected(self):
        bad = sample('1e7', '#iterations larger than 1.').removesuffix(COMPLETE)
        r = audit(bad + sample())
        self.assertTrue(r['diagnostics_valid'])
        self.assertEqual(r['history']['rejected_table_indices'], [0])
        self.assertFalse(r['valid'])
        self.assertEqual(r['failures'][0]['tail_iterations'][-1]['iteration'], 1)

    def test_rhs_exit_does_not_override_large_update(self):
        self.assert_rejected(sample('1e7', '|RHS| less than 1e-5.'))

    def test_original_line_numbers_preserved(self):
        text = sample('1e7', '#iterations larger than 1.')
        self.assertEqual(audit(text)['history']['failure_diagnostics'][0]['line_number'], 1)
        r = audit(sample().removesuffix(COMPLETE) + text)
        self.assertEqual(r['history']['failure_diagnostics'][0]['line_number'], len(sample().removesuffix(COMPLETE).splitlines()) + 1)

    def test_truncated_simulation_rejected(self):
        self.assert_rejected(sample().removesuffix(COMPLETE))

    def test_unknown_text_not_silently_removed(self):
        self.assert_rejected(sample().replace(' poisson:', 'unknown diagnostic\n poisson:', 1))

    def test_unknown_equation_rejected(self):
        self.assert_rejected(sample().replace('Electron', 'ElectronTemperature'))

    def test_missing_equation_rejected(self):
        text = sample()
        self.assert_rejected('\n'.join(s for s in text.split('\n') if ': Hole :' not in s))

    def test_missing_all_rhs_rejected(self):
        self.assert_rejected(sample().replace(rhs(1e-6), '').replace(rhs(1e-32), ''))

    def test_duplicate_equation_rejected(self):
        self.assert_rejected(sample().replace('C-norm_equation', '1e-6 : 1 : 1e-6 : : Electron : ( .5 .002 )\nC-norm_equation', 1))

    def test_empty_block_rejected(self):
        self.assert_rejected(sample().replace(rhs(1e-6), RHS_HEADER))

    def test_bad_rhs_header_rejected(self):
        self.assert_rejected(sample().replace('l2-norm', 'l3-norm'))

    def test_bad_cnorm_header_rejected(self):
        self.assert_rejected(sample().replace('coordinate [um]', 'coordinate [m]'))

    def test_rhs_maximum_mismatch_rejected(self):
        self.assert_rejected(sample().replace('0 1e-6 0.01', '0 1e-3 0.01'))

    def test_invalid_numeric_diagnostics_rejected(self):
        for value in ('nan', 'inf', '-1e-6', '1e-9999'):
            with self.subTest(value=value):
                self.assert_rejected(sample().replace('electron: 1e-6', 'electron: ' + value))

    def test_negative_carrier_value_rejected(self):
        self.assert_rejected(sample().replace(') 1e10', ') -1e10'))

    def test_invalid_coordinate_rejected(self):
        for value in ('nan, .002', '.5', '.5, .002, .1, .2'):
            with self.subTest(value=value):
                self.assert_rejected(sample().replace('0.5, 0.002', value))

    def test_three_coordinates_and_fortran_exponents(self):
        text = sample().replace('( 0.5 0.002 )', '( 0.5 0.002 0 )').replace('(0.5, 0.002)', '(0.5, 0.002, 0)').replace('electron: 1e-6', 'electron: 1D-6')
        self.assertTrue(audit(text)['valid'])

    def test_zero_integer_rhs_diagnostic_is_not_an_iteration(self):
        text = sample().replace('0 1e-6 0.01', '0 0 0.01').replace(rhs(1e-6), rhs(0))
        text = text.replace('0.0 :', '0 :')
        self.assertTrue(audit(text)['valid'])

    def test_nontext_and_invalid_tolerance_raise(self):
        with self.assertRaises(ValueError):
            audit(None)
        with self.assertRaises(ValueError):
            audit(sample(), initial_rhs_tolerance=1e-30)


if __name__ == '__main__':
    unittest.main()
