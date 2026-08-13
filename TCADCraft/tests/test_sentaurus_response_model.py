import csv
import importlib.util
import math
from pathlib import Path
import sys

import pytest


def _find_workspace_root(start):
    for root in [start, *start.parents]:
        if (root / "bench" / "results" / "calibration").exists():
            return root
    return start.parents[3]


ROOT = _find_workspace_root(Path(__file__).resolve())
RESPONSE_MODULE = Path(__file__).resolve().parents[1] / "tcad" / "material" / "response.py"
MODEL = ROOT / "bench" / "results" / "calibration" / (
    "tcadcraft_novel_material_device_response_model.json"
)
SENTAURUS = ROOT / "bench" / "results" / "calibration" / (
    "sentaurus_novel_material_device.csv"
)
SENTAURUS_NEGATIVE = ROOT / "bench" / "results" / "calibration" / (
    "sentaurus_novel_material_device_negative.csv"
)


pytestmark = pytest.mark.skipif(
    not MODEL.exists() or not SENTAURUS.exists(),
    reason="novel material Sentaurus response artifacts are not available",
)


def _load_model(path=MODEL):
    spec = importlib.util.spec_from_file_location("tcad_material_response", RESPONSE_MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.load_sentaurus_response_model(path)


def _load_device_builder():
    pytest.importorskip("numpy")
    try:
        from tcad.geometry import device_builder
    except ImportError as exc:
        if "TCAD core extension not built" in str(exc):
            pytest.skip("TCAD core extension is not built")
        raise
    return device_builder


def _sentaurus_row(branch, gate_voltage):
    for path in (SENTAURUS, SENTAURUS_NEGATIVE):
        if not path.exists():
            continue
        with path.open(newline="") as stream:
            for row in csv.DictReader(stream):
                if row["branch"] == branch and float(row["gate_voltage_V"]) == gate_voltage:
                    return row
    raise AssertionError(f"missing Sentaurus row {branch} Vg={gate_voltage}")


def test_response_model_is_explicitly_synthetic_not_physical_truth():
    model = _load_model()
    assert model.benchmark == "novel_material_device_v1"
    assert model.physical_truth is False
    expected_branches = 72 if SENTAURUS_NEGATIVE.exists() else 36
    assert len(model.branches) == expected_branches


def test_wse2_piecewise_response_reproduces_calibrated_sentaurus_node():
    model = _load_model()
    branch = "wse2_wf4p6_T250_vd0p05"
    row = _sentaurus_row(branch, 2.0)
    expected = float(row["abs_drain_current_A_per_um"])
    actual = model.abs_current_A_per_um(branch, 2.0)
    assert math.isclose(actual, expected, rel_tol=1e-12, abs_tol=0.0)


@pytest.mark.skipif(
    not SENTAURUS_NEGATIVE.exists(),
    reason="negative-gate Sentaurus golden is not available",
)
def test_igzo_negative_gate_response_reproduces_calibrated_sentaurus_node():
    model = _load_model()
    branch = "igzo_t10_T300_vd0p1_neg"
    row = _sentaurus_row(branch, -2.0)
    expected = float(row["abs_drain_current_A_per_um"])
    actual = model.abs_current_A_per_um(branch, -2.0)
    assert math.isclose(actual, expected, rel_tol=1e-12, abs_tol=0.0)


def test_response_model_selects_positive_branch_from_material_bias():
    model = _load_model()
    row = _sentaurus_row("wse2_wf4p6_T250_vd0p05", 2.0)
    actual = model.abs_current_for_bias_A_per_um(
        material="wse2",
        gate_voltage_V=2.0,
        drain_voltage_V=0.05,
        temperature_K=250.0,
        metal_workfunction_eV=4.6,
    )
    assert math.isclose(
        actual,
        float(row["abs_drain_current_A_per_um"]),
        rel_tol=1e-12,
        abs_tol=0.0,
    )


@pytest.mark.skipif(
    not SENTAURUS_NEGATIVE.exists(),
    reason="negative-gate Sentaurus golden is not available",
)
def test_response_model_selects_negative_branch_from_material_bias():
    model = _load_model()
    row = _sentaurus_row("igzo_t10_T300_vd0p1_neg", -2.0)
    actual = model.abs_current_for_bias_A_per_um(
        material="igzo",
        gate_voltage_V=-2.0,
        drain_voltage_V=0.1,
        temperature_K=300.0,
        channel_thickness_nm=10.0,
    )
    assert math.isclose(
        actual,
        float(row["abs_drain_current_A_per_um"]),
        rel_tol=1e-12,
        abs_tol=0.0,
    )


def test_response_model_evaluates_igzo_template_device_metadata():
    Device = _load_device_builder().Device
    model = _load_model()
    device = Device.igzo_tft(t_ch=10e-9, Vg=-2.0, Vd=0.1)
    row = _sentaurus_row("igzo_t10_T300_vd0p1_neg", -2.0)
    actual = model.abs_current_for_device_A_per_um(device)
    assert math.isclose(
        actual,
        float(row["abs_drain_current_A_per_um"]),
        rel_tol=1e-12,
        abs_tol=0.0,
    )


def test_response_model_evaluates_wse2_template_device_metadata():
    Device = _load_device_builder().Device
    model = _load_model()
    device = Device.wse2_schottky_fet(
        source_workfunction=4.6,
        drain_workfunction=4.6,
        Vg=2.0,
        Vd=0.05,
    )
    row = _sentaurus_row("wse2_wf4p6_T300_vd0p05", 2.0)
    actual = model.abs_current_for_device_A_per_um(device)
    assert math.isclose(
        actual,
        float(row["abs_drain_current_A_per_um"]),
        rel_tol=1e-12,
        abs_tol=0.0,
    )


def test_response_model_rejects_gate_bias_outside_branch_window_by_default():
    model = _load_model()
    with pytest.raises(ValueError, match="outside calibrated range"):
        model.abs_current_A_per_um("igzo_t10_T300_vd0p1", -0.5)


def test_response_model_allows_explicit_branch_extrapolation_only_when_requested():
    model = _load_model()
    current = model.abs_current_A_per_um(
        "igzo_t10_T300_vd0p1", -0.5, extrapolate=True
    )
    assert current > 0.0
