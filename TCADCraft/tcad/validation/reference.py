"""Explicit measured-trajectory comparison, including commercial references."""
from collections.abc import Mapping

import numpy as np

from .base import BaseValidationTest, ValidationResult, comparison_fields
from .cross_validation import _tolerance


class ReferenceComparisonTest(BaseValidationTest):
    """Compare zero-argument measurement runners with declared field budgets.

    Both runners return mappings/objects with actual finite fields and optional
    success flags. For trajectories provide matching ``times_s``; interpolation
    or extraction must happen explicitly in the runner. Each field is checked
    against atol[field] + rtol*peak(abs(reference[field])). This global signal
    scale is meaningful at zero crossings; it is not a pointwise relative bound.

    reference_source records caller-provided provenance, not an authenticity or
    material-validation claim. Reusing one runner is rejected. A reported pass
    verifies numerical agreement only. Framework's device_builder is unused.
    """
    def __init__(self, subject_runner, reference_runner, *, fields=('phi',),
                 rtol=1e-6, atol=None, reference_source):
        super().__init__('Measured Reference Comparison')
        if (not callable(subject_runner) or not callable(reference_runner) or
                subject_runner is reference_runner):
            raise ValueError('provide two distinct callable measurement runners')
        if (not isinstance(fields, (list, tuple)) or not fields or
                any(not isinstance(f, str) or not f.strip() for f in fields) or
                len(set(fields)) != len(fields)):
            raise ValueError('fields must list unique nonempty measurement names')
        if not isinstance(reference_source, str) or not reference_source.strip():
            raise ValueError('provide an explicit reference_source')
        self.rtol = _tolerance(rtol)
        if atol is None:
            atol = {field: 0. for field in fields}
        if not isinstance(atol, Mapping) or set(atol) != set(fields):
            raise ValueError('atol must specify exactly the compared fields')
        budgets = {}
        for field, value in atol.items():
            array = np.asarray(value)
            if (array.shape != () or array.dtype.kind not in 'iuf' or
                    not np.isfinite(array) or not np.isfinite(float(value)) or
                    float(value) < 0. or (float(value) == 0. and array != 0.)):
                raise ValueError('absolute budgets must be finite nonnegative real scalars')
            budgets[field] = float(value)
        self.fields = tuple(fields)
        self.atol = budgets
        self.subject_runner, self.reference_runner = subject_runner, reference_runner
        self.reference_source = reference_source

    def run(self, device_builder=None):
        details = dict(reference_source=self.reference_source, rtol=self.rtol,
                       atol=dict(self.atol), field_error_ratios={},
                       physical_validated=False, constitutive_equivalence_validated=False,
                       global_temporal_error_validated=False,
                       reference_authenticity_validated=False)
        try:
            actual, reference = self.subject_runner(), self.reference_runner()
            if actual is reference:
                raise ValueError('subject and reference must not alias the same result')
            ratios = details['field_error_ratios']
            for field in self.fields:
                a, b = comparison_fields(actual, reference, field)
                scale = float(max(np.max(np.abs(a)), np.max(np.abs(b)), self.atol[field]))
                if scale == 0.:
                    ratios[field] = 0.
                    continue
                with np.errstate(under='ignore', divide='ignore', over='ignore', invalid='ignore'):
                    error = float(np.max(np.abs(a/scale-b/scale)))
                    budget = self.atol[field]/scale+self.rtol*float(np.max(np.abs(b/scale)))
                    ratios[field] = error/budget if budget else (0. if error == 0. else float('inf'))
            passed = all(ratio <= 1. for ratio in ratios.values())
            details['numerical_agreement_validated'] = passed
            return ValidationResult(self.name, passed,
                f'max field error/budget: {max(ratios.values()):.3e}', details)
        except Exception as error:
            details['numerical_agreement_validated'] = False
            return ValidationResult(self.name, False, f'reference comparison unavailable/failed: {error}', details)
