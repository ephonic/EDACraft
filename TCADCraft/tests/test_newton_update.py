from pathlib import Path
import math
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tcad/validation'))
from newton_update import audit_newton_update_transition as audit


class NewtonUpdateTests(unittest.TestCase):
    def test_additive_transition_is_resolved(self):
        r = audit([1., -1.], [1.5, -1.5], [.5, -.5])
        self.assertTrue(r['valid'] and r['compatible'])
        self.assertEqual(r['resolved_consistent'], 2)
        self.assertFalse(r['chronology_proven'])
        self.assertFalse(r['convergence_qualified'])

    def test_opposite_sign_rejected(self):
        self.assertFalse(audit([1.], [1.5], [-.5])['compatible'])

    def test_previous_iteration_update_rejected(self):
        self.assertFalse(audit([1.], [1.5], [.25])['compatible'])

    def test_wrong_units_rejected(self):
        self.assertFalse(audit([1e10], [1e10+1e6], [1e12])['compatible'])

    def test_sub_resolution_update_preserved(self):
        r = audit([1.], [1.], [1e-20])
        self.assertTrue(r['compatible'])
        self.assertEqual(r['sub_resolution'], 1)
        self.assertEqual(r['resolved_consistent'], 0)

    def test_rounding_near_adjacent_node_values(self):
        value = math.nextafter(1., math.inf)
        r = audit([1.], [value], [math.ulp(1.)*.6])
        self.assertTrue(r['compatible'])
        self.assertEqual(r['sub_resolution'], 1)

    def test_large_small_mixed_magnitudes_no_context_loss(self):
        self.assertTrue(audit([1e300], [1e300], [math.ulp(0.)])['compatible'])

    def test_zero_and_subnormal_observations(self):
        small = math.ulp(0.)
        self.assertTrue(audit([0.], [small], [small])['compatible'])

    def test_invalid_shapes_and_types_fail_closed(self):
        for args in (([], [], []), ([1.], [1., 2.], [0.]), ('x','x','x'),
                     (None, [1.], [0.]), ([1], [1.], [0.]),
                     ([True], [1.], [0.])):
            with self.subTest(args=args):
                self.assertFalse(audit(*args)['valid'])

    def test_nonfinite_observations_fail_closed(self):
        for value in (float('nan'), float('inf'), -float('inf'), sys.float_info.max):
            with self.subTest(value=value):
                self.assertFalse(audit([1.], [value], [0.])['valid'])


if __name__ == '__main__':
    unittest.main()
