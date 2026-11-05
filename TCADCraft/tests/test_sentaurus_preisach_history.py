"""Native API replay of independently generated Sentaurus history traces."""

import json
from pathlib import Path

import numpy as np
import pytest

from tcad.core import PyDeviceSimulator


REFERENCE = json.loads((Path(__file__).parent / "data" /
                        "sentaurus_preisach_history.json").read_text())


def replay_case(case):
    count = 9
    sim = PyDeviceSimulator(count, 1, 1, REFERENCE["length_m"] / (count - 1), 1.0, 1.0)
    sim.set_permittivity(np.full(count, 8.854187817e-12 * 25.0))
    sim.set_mobility(np.zeros(count), np.zeros(count))
    sim.set_doping(np.zeros(count))
    sim.set_effective_dos(np.full(count, 2.8e25), np.full(count, 1.04e25))
    sim.set_bandgap(np.full(count, 5.8))
    sim.set_thermal_voltage(0.025852)
    sim.set_electron_bc({0: 0.0, count - 1: 0.0})
    sim.set_hole_bc({0: 0.0, count - 1: 0.0})
    sim.set_ferroelectric_enabled(True)
    sim.set_ferroelectric_params(np.ones(count, dtype=np.int8), -1e8, 1e18)
    sim.set_ferroelectric_model(3)
    scale = 2 * case["Ec"] / np.log((case["Ps"] + case["Pr"]) /
                                    (case["Ps"] - case["Pr"]))
    sim.set_ferroelectric_preisach(case["Ps"], case["Ec"], scale)
    sim.set_gummel_max_iter(20)
    sim.set_tolerance(1e-10)
    predicted = []
    for point in case["points"]:
        sim.set_dirichlet_potential({0: point["voltage_V"], count - 1: 0.0})
        result = sim.solve()
        assert result["converged"]
        predicted.append(float(result["P"][count // 2, 0]))
    return np.asarray(predicted)


@pytest.mark.parametrize("case", REFERENCE["cases"], ids=lambda case: case["name"])
def test_startup_and_nested_history_against_sentaurus(case):
    reference = np.asarray([p["polarization_C_per_m2"] for p in case["points"]])
    np.testing.assert_allclose(replay_case(case), reference, rtol=1e-6, atol=1e-9)
