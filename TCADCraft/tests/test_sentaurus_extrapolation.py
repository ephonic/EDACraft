from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tcad/validation'))
from sentaurus_extrapolation import audit_extrapolation_deck_pair as audit

BASE = ('File{Grid="mesh.tdr"} Physics{Temperature=300} '
        'Math{Digits=14 Extrapolate(Order=2)} '
        'Solve{Quasistationary(Goal{Name="right" Voltage=-.0001}){Coupled{Poisson Electron Hole}}}')
OFF = BASE.replace(' Extrapolate(Order=2)', '')


class ExtrapolationPairTests(unittest.TestCase):
    def test_only_global_directive_removed(self):
        r = audit(BASE, OFF)
        self.assertTrue(r['valid'])
        self.assertTrue(r['only_directive_removed'])
        self.assertFalse(r['solver_configuration_verified'])
        self.assertFalse(r['commercial_alignment_qualified'])

    def test_alternative_spacing_and_comments(self):
        baseline = BASE.replace('Extrapolate(Order=2)', 'Extrapolate /* note */ (Order = 2)')
        self.assertTrue(audit(baseline, OFF.replace('Digits=14', 'Digits = 14 // x\n'))['valid'])

    def test_commented_directives_do_not_count(self):
        self.assertTrue(audit('// Extrapolate(Order=1)\n'+BASE,
                              OFF+' /* Extrapolate(Order=2) */')['valid'])

    def test_quoted_directives_are_preserved_and_not_parsed(self):
        extra = 'File{Output="Extrapolate(Order=2) // literal"}'
        self.assertTrue(audit(extra+BASE, extra+OFF)['valid'])
        self.assertFalse(audit(extra+BASE, extra.replace('literal', 'changed')+OFF)['valid'])

    def test_escaped_quotes_do_not_hide_code(self):
        extra = 'File{Output="a\\\"Extrapolate(Order=2)"}'
        self.assertTrue(audit(extra+BASE, extra+OFF)['valid'])

    def test_physics_mesh_and_history_changes_rejected(self):
        for text in (OFF.replace('300', '301'), OFF.replace('mesh.tdr', 'mesh2.tdr'),
                     OFF.replace('-.0001', '-.0002'), OFF.replace('Digits=14', 'Digits=12')):
            with self.subTest(text=text):
                self.assertFalse(audit(BASE, text)['valid'])

    def test_missing_or_wrong_baseline_directive_rejected(self):
        for text in (OFF, BASE.replace('Order=2', 'Order=1'),
                     BASE.replace('Extrapolate(Order=2)', 'Extrapolate')):
            with self.subTest(text=text):
                self.assertFalse(audit(text, OFF)['valid'])

    def test_comparison_still_enabled_or_locally_overridden_rejected(self):
        for text in (BASE, OFF.replace('Digits=14', 'Digits=14 NoExtrapolate'),
                     OFF.replace('Coupled{', 'Coupled(Extrapolate){')):
            with self.subTest(text=text):
                self.assertFalse(audit(BASE, text)['valid'])

    def test_repeated_directive_or_math_block_rejected(self):
        for text in (BASE.replace('Digits=14', 'Digits=14 Extrapolate(Order=2)'),
                     BASE+' Math{Digits=14}'):
            with self.subTest(text=text):
                self.assertFalse(audit(text, OFF)['valid'])

    def test_local_baseline_directive_rejected(self):
        text = OFF.replace('Quasistationary(', 'Quasistationary(Extrapolate(Order=2) ')
        self.assertFalse(audit(text, OFF)['valid'])

    def test_malformed_comments_strings_and_braces_rejected(self):
        for suffix in (' /*', ' "unterminated', ' "x\\', ' {', ' }'):
            with self.subTest(suffix=suffix):
                self.assertFalse(audit(BASE+suffix, OFF)['valid'])
                self.assertFalse(audit(BASE, OFF+suffix)['valid'])

    def test_non_text_rejected(self):
        for value in (None, 1, BASE.encode()):
            self.assertFalse(audit(value, OFF)['valid'])


if __name__ == '__main__':
    unittest.main()
