"""Analytic and adversarial controls; no native extension is required."""
from pathlib import Path
import math
import sys
import unittest
from decimal import Decimal, localcontext
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tcad/validation'))
from hfs_gqf import audit_hfs_gqf_face, binary64_rounding_cell


class FaceObservationAuditTests(unittest.TestCase):
    def case(self, **changes):
        args = dict(potential_left=0., potential_right=-0.00005,
                    carrier_left=1e16, carrier_right=1e16, carrier='n',
                    spacing='1e-6', thermal_voltage='.025', reference_density='4e16',
                    base_mobility='.001', saturation_velocity='200', beta=2,
                    cutoff='100', reported_below_cutoff=True, reported_mobility=.001)
        args.update(changes)
        return audit_hfs_gqf_face(**args)

    def contains(self, report, value):
        lo, hi = map(Decimal, report['force_V_m'])
        self.assertLessEqual(lo, value)
        self.assertGreaterEqual(hi, value)

    def test_asymmetric_power_of_two_rounding_cell(self):
        lo, hi = binary64_rounding_cell(1.)
        with localcontext() as ctx:
            ctx.prec = 1100
            self.assertEqual(1-lo, (hi-1)/2)
        self.assertLess(Decimal.from_float(math.nextafter(1., -math.inf)), lo)
        self.assertGreater(Decimal.from_float(math.nextafter(1., math.inf)), hi)

    def test_subnormal_rounding_cell_is_exact(self):
        value = math.ulp(0.)
        lo, hi = binary64_rounding_cell(value)
        with localcontext() as ctx:
            ctx.prec = 1100
            self.assertEqual(lo*2, Decimal.from_float(value))
            self.assertEqual(hi, lo*3)

    def test_uniform_drift_below(self):
        r = self.case(reported_force=50.)
        self.contains(r, Decimal(50))
        self.assertEqual(r['branch'], 'below')
        self.assertTrue(r['conditional_consistency'])

    def test_uniform_drift_active_both_beta_models(self):
        for beta in (1, 2):
            with self.subTest(beta=beta), localcontext() as ctx:
                ctx.prec = 100
                ratio = Decimal('.001')*200/200
                mu = Decimal('.001')/((1+ratio) if beta == 1 else (1+ratio*ratio).sqrt())
                r = self.case(potential_right=-.0002, beta=beta,
                              reported_below_cutoff=False, reported_mobility=float(mu))
                self.contains(r, Decimal(200))
                self.assertEqual(r['branch'], 'active')
                self.assertTrue(r['conditional_consistency'])

    def test_threshold_intersection_never_qualifies(self):
        for below in (True, False):
            r = self.case(potential_right=-.0001, reported_below_cutoff=below)
            self.contains(r, Decimal(100))
            self.assertEqual(r['branch'], 'indeterminate')
            self.assertIsNone(r['branch_consistent'])
            self.assertFalse(r['conditional_consistency'])

    def test_density_gradient_signs_and_reference(self):
        with localcontext() as ctx:
            ctx.prec = 120
            thermal = Decimal('.025') * (Decimal(6)/5).ln()
            for carrier, signed in (('n', -thermal), ('p', thermal)):
                force = signed.copy_abs()/Decimal('1e-6')
                ratio = Decimal('.001')*force/200
                mu = Decimal('.001')/(1+ratio*ratio).sqrt()
                r = self.case(potential_right=0., carrier_right=2e16, carrier=carrier,
                              reported_below_cutoff=False, reported_mobility=float(mu),
                              reported_force=float(force))
                self.contains(r, force)
                self.assertTrue(r['conditional_consistency'])
                # A nonzero potential distinguishes carrier signs.
                t = self.case(potential_right=-.00005, carrier_right=2e16, carrier=carrier)
                expected = (Decimal.from_float(-.00005)+signed).copy_abs()/Decimal('1e-6')
                self.contains(t, expected)

    def test_raw_vendor_units_scaled_after_observation(self):
        r = self.case(carrier_left=1e10, carrier_right=1e10, carrier_scale='1e6',
                      reported_mobility=10., mobility_scale='1e-4')
        self.contains(r, Decimal(50))
        self.assertTrue(r['conditional_consistency'])

    def test_swapped_sign_force_and_branch_are_rejected(self):
        self.assertFalse(self.case(reported_below_cutoff=False)['conditional_consistency'])
        r = self.case(reported_force=500.)
        self.assertFalse(r['reported_force_consistent'])
        self.assertFalse(r['conditional_consistency'])

    def test_bad_mobility_units_are_rejected(self):
        r = self.case(reported_mobility=10.)
        self.assertFalse(r['mobility_consistent'])
        self.assertFalse(r['conditional_consistency'])

    def test_refdens_omission_detected_with_same_frozen_observation(self):
        with localcontext() as ctx:
            ctx.prec = 100
            force = Decimal('.025')*(Decimal(6)/5).ln()/Decimal('1e-6')
            r = self.case(potential_right=0., carrier_right=2e16,
                          reference_density='0', reported_force=float(force))
            self.assertFalse(r['reported_force_consistent'])

    def test_nonfinite_boolean_and_wrong_observation_types_fail_closed(self):
        for value in (float('nan'), float('inf'), -float('inf'), True, 1, '1', sys.float_info.max):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.case(potential_left=value)

    def test_unsupported_or_invalid_physics_fail_closed(self):
        for changes in (dict(beta=3), dict(beta=True), dict(carrier='e'),
                        dict(spacing='0'), dict(thermal_voltage='-1'),
                        dict(reference_density='-1'), dict(carrier_scale='0'),
                        dict(reported_below_cutoff=None), dict(reported_mobility=0.),
                        dict(carrier_left=0.), dict(carrier_left=1., reference_density='0'),
                        dict(base_mobility='NaN'), dict(precision=28)):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.case(**changes)

    def test_precision_change_preserves_decisions(self):
        for phi in (-.00005, -.0001, -.0002):
            a = self.case(potential_right=phi, precision=80)
            b = self.case(potential_right=phi, precision=120)
            for key in ('branch', 'branch_consistent', 'mobility_consistent',
                        'reported_force_consistent', 'conditional_consistency'):
                self.assertEqual(a[key], b[key])


if __name__ == '__main__':
    unittest.main()
