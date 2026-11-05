"""PUND terminal extraction rejects ambiguous identifiers and bad normalization."""
import numpy as np
import pytest

from tcad.postprocess.terminal_trace import extract_pund_terminal_charge
from test_terminal_trace import pund_traces


@pytest.mark.parametrize("value", [True, "2e-14", [2e-14], 1j, np.nan, np.inf])
def test_pund_area_requires_finite_real_scalar(value):
    with pytest.raises(ValueError):
        extract_pund_terminal_charge(pund_traces(), terminal="gate",
                                     reference_terminal="body", electrode_area_m2=value)


@pytest.mark.parametrize("terminal,reference", [
    (True, "body"), ("", "body"), ("gate", True), ("gate", ""),
    ("gate", "missing"), ("gate", "gate"), (1, "body"),
])
def test_pund_requires_distinct_nonempty_string_terminals(terminal, reference):
    with pytest.raises(ValueError):
        extract_pund_terminal_charge(pund_traces(), terminal=terminal,
                                     reference_terminal=reference)


@pytest.mark.parametrize("value", [True, 1])
def test_pund_trace_labels_are_not_truthy_aliases(value):
    traces = pund_traces()
    traces[value] = traces.pop("P")
    with pytest.raises(ValueError):
        extract_pund_terminal_charge(traces, terminal="gate", reference_terminal="body")


def test_pund_charge_difference_cancellation_is_order_independent():
    traces = pund_traces(switching_charge=1e-300)
    out = extract_pund_terminal_charge(traces, terminal="gate", reference_terminal="body",
                                       electrode_area_m2=1e-14)
    assert np.isfinite(out["switching_charge_magnitude_C"])
    assert np.isfinite(out["switching_polarization_magnitude_C_per_m2"])


def test_pund_area_normalization_overflow_rejects_instead_of_inf_output():
    traces = pund_traces(switching_charge=1e308)
    with pytest.raises(ValueError):
        extract_pund_terminal_charge(traces, terminal="gate", reference_terminal="body",
                                     electrode_area_m2=1e-308)
