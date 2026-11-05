"""Completed NewtonPlot messages are metadata; failures remain strict failures."""
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tcad/validation'))
from sentaurus_newton import audit_sentaurus_newton_diagnostics as audit
from test_sentaurus_newton import sample, COMPLETE

WRITE = 'writing newton_i0_s0.tdr (TDR format) ... done.\n'
PATTERN = r'^writing [^\s]+\.tdr \(TDR format\) \.\.\. done\.$'


class NewtonPlotTests(unittest.TestCase):
    def test_completed_message_preserves_history_and_line_numbers(self):
        baseline = sample()
        text = baseline.replace('C-norm_equation', WRITE + 'C-norm_equation', 1)
        before, after = audit(baseline), audit(text)
        self.assertTrue(after['valid'])
        self.assertEqual(before['history'], after['history'])
        record = after['records'][0]
        self.assertEqual(record['newtonplot_output'], dict(filename='newton_i0_s0.tdr',
                         line_number=text.splitlines().index(WRITE.rstrip()) + 1))
        c = record['following_c_norm']['hole']
        self.assertTrue(text.splitlines()[c['line_number'] - 1].startswith(' hole:'))

    def test_duplicate_incomplete_failed_and_unknown_output_rejected(self):
        for message in (WRITE + WRITE, WRITE.replace(' done.', ''),
                        WRITE.replace('done.', 'failed.'), WRITE + 'unknown diagnostic\n'):
            with self.subTest(message=message):
                self.assertFalse(audit(sample().replace('C-norm_equation', message + 'C-norm_equation', 1))['valid'])

    def test_output_before_initial_iteration_rejected(self):
        self.assertFalse(audit(sample().replace('0 1e-6 0.01', WRITE + '0 1e-6 0.01'))['valid'])

    def test_write_does_not_hide_missing_rhs_or_equation(self):
        text = sample().replace('C-norm_equation', WRITE + 'C-norm_equation', 1)
        self.assertFalse(audit('\n'.join(s for s in text.split('\n') if ': Hole :' not in s))['valid'])

    def test_failure_followed_by_success_still_rejected(self):
        bad = sample('1e7', '#iterations larger than 1.').removesuffix(COMPLETE)
        text = (bad + sample()).replace('C-norm_equation', WRITE + 'C-norm_equation', 1)
        self.assertFalse(audit(text)['valid'])
        self.assertEqual(audit(text)['history']['rejected_table_indices'], [0])

    def test_real_captured_success_and_iteration_limit(self):
        data = Path(__file__).with_name('data') / 'sentaurus_newtonplot'
        good = (data / 'table57.txt').read_text(encoding='utf-8')
        bad = (data / 'table58.txt').read_text(encoding='utf-8')
        for text, valid, rows, step in ((good, True, 4, 57), (bad, False, 301, 58)):
            with self.subTest(step=step):
                report = audit(text, initial_rhs_tolerance=1e-35)
                self.assertEqual(report['valid'], valid)
                self.assertTrue(report['diagnostics_valid'])
                self.assertEqual(len(report['records']), rows)
                for i, record in enumerate(report['records']):
                    self.assertEqual(record['newtonplot_output']['filename'], f'newton_i{i}_s{step}.tdr')
                # Blank output lines preserve original row numbers and failure diagnostics.
                plain = re.sub(PATTERN, '', text, flags=re.M)
                self.assertEqual(report['history'], audit(plain, initial_rhs_tolerance=1e-35)['history'])
        combined = bad[:bad.rfind('Sentaurus Device simulation finished')] + good
        report = audit(combined, initial_rhs_tolerance=1e-35)
        self.assertFalse(report['valid'])
        self.assertEqual(report['history']['rejected_table_indices'], [0])


if __name__ == '__main__':
    unittest.main()
