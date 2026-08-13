"""Sentaurus-calibrated response surfaces for emerging material benchmarks.

This module intentionally represents *software calibration surfaces*, not
physical material truth.  It is meant for reproducing a frozen Sentaurus
synthetic-golden deck while full drift-diffusion/contact implementations are
being developed.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class BranchResponse:
    """One calibrated ``log10(abs(Id))`` response branch."""

    name: str
    material: str
    form: str
    min_gate_voltage_V: float
    max_gate_voltage_V: float
    data: Mapping[str, Any]

    def _check_gate_voltage(self, gate_voltage_V: float, extrapolate: bool) -> None:
        if not math.isfinite(gate_voltage_V):
            raise ValueError("gate_voltage_V must be finite")
        if extrapolate:
            return
        if (
            gate_voltage_V < self.min_gate_voltage_V
            or gate_voltage_V > self.max_gate_voltage_V
        ):
            raise ValueError(
                f"gate_voltage_V={gate_voltage_V} is outside calibrated range "
                f"[{self.min_gate_voltage_V}, {self.max_gate_voltage_V}] for "
                f"branch '{self.name}'"
            )

    @staticmethod
    def _interp(xs: list[float], ys: list[float], x: float) -> float:
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        pos = bisect_left(xs, x)
        x0, x1 = xs[pos - 1], xs[pos]
        y0, y1 = ys[pos - 1], ys[pos]
        if x1 == x0:
            return y0
        return y0 + (x - x0) / (x1 - x0) * (y1 - y0)

    def log10_abs_current_A_per_um(
        self, gate_voltage_V: float, *, extrapolate: bool = False
    ) -> float:
        """Evaluate calibrated ``log10(abs(Id[A/um]))``.

        Extrapolation is disabled by default.  Branches generated from the
        positive- and negative-gate Sentaurus sweeps remain separate calibrated
        operating windows.
        """
        self._check_gate_voltage(gate_voltage_V, extrapolate)
        if self.form == "piecewise_log_linear":
            xs = [float(value) for value in self.data["gate_voltage_V"]]
            ys = [
                float(value)
                for value in self.data["log10_abs_current_A_per_um"]
            ]
            return self._interp(xs, ys, gate_voltage_V)
        if self.form == "polynomial":
            span = max(self.max_gate_voltage_V - self.min_gate_voltage_V, 1.0e-30)
            x = (gate_voltage_V - self.min_gate_voltage_V) / span
            coefficients = [
                float(value)
                for value in self.data["coefficients_log10_abs_current_A_per_um"]
            ]
            return sum(coef * x ** order for order, coef in enumerate(coefficients))
        raise ValueError(f"Unsupported response form '{self.form}'")

    def abs_current_A_per_um(
        self, gate_voltage_V: float, *, extrapolate: bool = False
    ) -> float:
        """Evaluate calibrated absolute drain current in A/um."""
        log_current = self.log10_abs_current_A_per_um(
            gate_voltage_V, extrapolate=extrapolate
        )
        return 10.0 ** min(max(log_current, -300.0), 300.0)


class SentaurusResponseModel:
    """Loaded Sentaurus synthetic-golden response model.

    ``physical_truth`` is deliberately always ``False``.  Callers that need a
    real material model should use measured/DFT/process-constrained parameters
    and a device solver rather than this interpolation layer.
    """

    physical_truth = False

    def __init__(self, payload: Mapping[str, Any]):
        self.payload = dict(payload)
        self.benchmark = str(payload.get("benchmark", ""))
        self.policy = str(payload.get("policy", ""))
        self.branches = {
            name: BranchResponse(
                name=name,
                material=str(branch["material"]),
                form=str(branch.get("response_form", "polynomial")),
                min_gate_voltage_V=float(branch["min_gate_voltage_V"]),
                max_gate_voltage_V=float(branch["max_gate_voltage_V"]),
                data=branch,
            )
            for name, branch in payload.get("branches", {}).items()
        }
        if not self.branches:
            raise ValueError("response model contains no branches")
        self._branch_index = self._build_branch_index(self.branches.values())

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        if value in (None, ""):
            return None
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("branch selector values must be finite")
        return result

    @staticmethod
    def _close(lhs: float | None, rhs: float | None, tolerance: float) -> bool:
        if lhs is None or rhs is None:
            return lhs is rhs
        return abs(lhs - rhs) <= tolerance

    @classmethod
    def _build_branch_index(
        cls, branches: Iterable[BranchResponse]
    ) -> dict[tuple[str, str, float | None, float | None, float | None, float | None], str]:
        index = {}
        for branch in branches:
            data = branch.data
            key = (
                branch.material.lower(),
                str(data.get("sweep_polarity", "unknown")).lower(),
                cls._optional_float(data.get("temperature_K")),
                cls._optional_float(data.get("drain_voltage_V")),
                cls._optional_float(data.get("channel_thickness_nm")),
                cls._optional_float(data.get("metal_workfunction_eV")),
            )
            index[key] = branch.name
        return index

    @classmethod
    def from_json(cls, path: str | Path) -> "SentaurusResponseModel":
        """Load a response model generated by the calibration pipeline."""
        with open(path, encoding="utf-8") as stream:
            return cls(json.load(stream))

    def branch(self, name: str) -> BranchResponse:
        """Return a calibrated branch by exact Sentaurus branch name."""
        try:
            return self.branches[name]
        except KeyError as exc:
            raise KeyError(f"Unknown response branch '{name}'") from exc

    def branch_for_bias(
        self,
        *,
        material: str,
        gate_voltage_V: float,
        drain_voltage_V: float,
        temperature_K: float,
        channel_thickness_nm: float | None = None,
        metal_workfunction_eV: float | None = None,
        tolerance: float = 1.0e-9,
    ) -> BranchResponse:
        """Return the calibrated branch matching material parameters and bias.

        Positive- and negative-gate Sentaurus sweeps are stored as separate
        branches.  The sign of ``gate_voltage_V`` selects the appropriate
        sweep polarity; zero bias is assigned to the positive branch when both
        windows exist.
        """
        sweep = "negative" if gate_voltage_V < 0.0 else "positive"
        selector = (
            material.lower(),
            sweep,
            self._optional_float(temperature_K),
            self._optional_float(drain_voltage_V),
            self._optional_float(channel_thickness_nm),
            self._optional_float(metal_workfunction_eV),
        )
        exact_name = self._branch_index.get(selector)
        if exact_name is not None:
            return self.branch(exact_name)

        matches = []
        for branch in self.branches.values():
            data = branch.data
            if branch.material.lower() != selector[0]:
                continue
            if str(data.get("sweep_polarity", "unknown")).lower() != sweep:
                continue
            if not self._close(
                self._optional_float(data.get("temperature_K")), selector[2], tolerance
            ):
                continue
            if not self._close(
                self._optional_float(data.get("drain_voltage_V")), selector[3], tolerance
            ):
                continue
            if not self._close(
                self._optional_float(data.get("channel_thickness_nm")),
                selector[4],
                tolerance,
            ):
                continue
            if not self._close(
                self._optional_float(data.get("metal_workfunction_eV")),
                selector[5],
                tolerance,
            ):
                continue
            matches.append(branch)
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise KeyError(
                "No calibrated Sentaurus response branch for "
                f"material={material!r}, sweep={sweep!r}, Vd={drain_voltage_V}, "
                f"T={temperature_K}, thickness_nm={channel_thickness_nm}, "
                f"metal_workfunction_eV={metal_workfunction_eV}"
            )
        raise ValueError(f"Ambiguous calibrated response branch selector: {selector}")

    def abs_current_A_per_um(
        self, branch: str, gate_voltage_V: float, *, extrapolate: bool = False
    ) -> float:
        """Evaluate a branch current with range checks enabled by default."""
        return self.branch(branch).abs_current_A_per_um(
            gate_voltage_V, extrapolate=extrapolate
        )

    def abs_current_for_bias_A_per_um(
        self,
        *,
        material: str,
        gate_voltage_V: float,
        drain_voltage_V: float,
        temperature_K: float,
        channel_thickness_nm: float | None = None,
        metal_workfunction_eV: float | None = None,
        extrapolate: bool = False,
    ) -> float:
        """Evaluate current by material parameters and bias, not branch name."""
        branch = self.branch_for_bias(
            material=material,
            gate_voltage_V=gate_voltage_V,
            drain_voltage_V=drain_voltage_V,
            temperature_K=temperature_K,
            channel_thickness_nm=channel_thickness_nm,
            metal_workfunction_eV=metal_workfunction_eV,
        )
        return branch.abs_current_A_per_um(gate_voltage_V, extrapolate=extrapolate)

    def abs_current_for_device_A_per_um(
        self,
        device: Any,
        *,
        gate_voltage_V: float | None = None,
        drain_voltage_V: float | None = None,
        temperature_K: float | None = None,
        extrapolate: bool = False,
    ) -> float:
        """Evaluate a calibrated current for a device template.

        The device must provide ``metadata["sentaurus_calibration"]`` as
        populated by the emerging-material template builders.  This is a stable
        adapter for the synthetic Sentaurus replay; it is deliberately separate
        from the physical drift-diffusion solve path.
        """
        metadata = getattr(device, "metadata", {}).get("sentaurus_calibration")
        if not isinstance(metadata, Mapping):
            raise ValueError(
                "device does not provide metadata['sentaurus_calibration']"
            )
        benchmark = str(metadata.get("benchmark", ""))
        if benchmark and benchmark != self.benchmark:
            raise ValueError(
                f"device calibration benchmark '{benchmark}' does not match "
                f"response model benchmark '{self.benchmark}'"
            )
        selected_gate = (
            float(metadata["gate_voltage_V"])
            if gate_voltage_V is None
            else float(gate_voltage_V)
        )
        selected_drain = (
            float(metadata["drain_voltage_V"])
            if drain_voltage_V is None
            else float(drain_voltage_V)
        )
        selected_temperature = (
            float(metadata.get("temperature_K", 300.0))
            if temperature_K is None
            else float(temperature_K)
        )
        return self.abs_current_for_bias_A_per_um(
            material=str(metadata["material"]),
            gate_voltage_V=selected_gate,
            drain_voltage_V=selected_drain,
            temperature_K=selected_temperature,
            channel_thickness_nm=metadata.get("channel_thickness_nm"),
            metal_workfunction_eV=metadata.get("metal_workfunction_eV"),
            extrapolate=extrapolate,
        )

    def log10_abs_current_A_per_um(
        self, branch: str, gate_voltage_V: float, *, extrapolate: bool = False
    ) -> float:
        """Evaluate branch log-current with range checks enabled by default."""
        return self.branch(branch).log10_abs_current_A_per_um(
            gate_voltage_V, extrapolate=extrapolate
        )


def load_sentaurus_response_model(path: str | Path) -> SentaurusResponseModel:
    """Load a Sentaurus-calibrated synthetic response model."""
    return SentaurusResponseModel.from_json(path)
