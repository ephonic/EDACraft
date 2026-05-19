"""
skills.npu.models — NPU Behavioral Models

SIMD-like neural network accelerator behavioral model.
Supports configurable compute arrays, activation functions,
and memory hierarchy for NPU pipeline stages.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


# =====================================================================
# NPU State
# =====================================================================

@dataclass
class NPUState:
    """NPU global state."""
    # Compute array state
    tile_cnt: int = 0
    dpe_cnt: int = 0
    cycle_cnt: int = 0

    # VRF state
    vrf_mem: Dict[int, int] = field(default_factory=dict)

    # Pipeline state
    state: int = 0  # 0=IDLE, 1=RUNNING, 2=DONE

    # Tracking
    ops_executed: int = 0
    cycles_busy: int = 0
    cycles_idle: int = 0


# =====================================================================
# Activation Function Models
# =====================================================================

def relu(x: int, width: int = 32) -> int:
    """ReLU: max(0, x)."""
    return max(0, x) & ((1 << width) - 1)


def relu_quantized(x: int, ew: int = 8) -> int:
    """Quantized ReLU for INT8 element width."""
    return max(0, x) & ((1 << ew) - 1)


def sigmoid_approx(x: int, ew: int = 8) -> int:
    """Piecewise linear approximation of sigmoid for INT8."""
    if x < -64:
        return 0
    if x > 63:
        return (1 << ew) - 1
    # Linear region: map [-64, 63] → [0, 255]
    return ((x + 64) * ((1 << ew) - 1)) // 127


def tanh_approx(x: int, ew: int = 8) -> int:
    """Piecewise linear approximation of tanh for INT8."""
    if x < -64:
        return 0
    if x > 63:
        return (1 << ew) - 1
    return ((x + 64) * ((1 << ew) - 1)) // 127


_ACTIVATION_FUNCS: Dict[str, Callable] = {
    "relu": relu,
    "sigmoid": sigmoid_approx,
    "tanh": tanh_approx,
    "pass_through": lambda x, ew=8: x & ((1 << ew) - 1),
}


# =====================================================================
# MAC Array Model
# =====================================================================

class MACArrayModel:
    """Behavioral model for NTILE × NDPE MAC array.

    Simulates matrix-vector multiply:
      result[tile][dpe] = sum(weight[tile][dpe][k] * activation[k])

    Supports configurable element width, accumulator width,
    and dot-product width.
    """

    def __init__(
        self,
        ntile: int = 7,
        ndpe: int = 40,
        ew: int = 8,
        accw: int = 32,
        dotw: int = 40,
    ):
        self.ntile = ntile
        self.ndpe = ndpe
        self.ew = ew
        self.accw = accw
        self.dotw = dotw
        self.state = NPUState()
        self._weights: Dict[int, int] = {}
        self._results: Dict[int, int] = {}

    def load_weights(self, addr: int, data: int):
        self._weights[addr] = data

    def run_tile(
        self,
        activations: List[int],
        tile_id: int = 0,
    ) -> List[int]:
        """Run one tile of MAC operations.

        Returns list of accumulator results per DPE.
        """
        results = []
        for dpe in range(self.ndpe):
            acc = 0
            for k, act in enumerate(activations):
                w = self._weights.get(tile_id * self.ndpe + dpe, 0)
                # INT8 × INT8 → INT32 accumulate
                prod = self._to_signed(w, self.ew) * self._to_signed(act, self.ew)
                acc += prod
            results.append(acc & ((1 << self.accw) - 1))

        self.state.ops_executed += self.ndpe
        self.state.cycles_busy += 1
        self.state.tile_cnt += 1

        return results

    def run_all_tiles(
        self,
        activation_bank: List[int],
    ) -> Dict[int, List[int]]:
        """Run all tiles and return results."""
        all_results = {}
        for tile in range(self.ntile):
            all_results[tile] = self.run_tile(activation_bank, tile)
        return all_results

    def get_status(self) -> Dict[str, Any]:
        return {
            "ntile": self.ntile,
            "ndpe": self.ndpe,
            "ops_executed": self.state.ops_executed,
            "cycles_busy": self.state.cycles_busy,
            "tiles_done": self.state.tile_cnt,
        }

    @staticmethod
    def _to_signed(val: int, width: int) -> int:
        val = val & ((1 << width) - 1)
        if val & (1 << (width - 1)):
            val -= (1 << width)
        return val


# =====================================================================
# NPU Behavioral Model Container
# =====================================================================

class NPUModel:
    """NPU behavioral model container.

    Wraps compute array models and pipeline state for
    interaction with the RTLCraft ecosystem.

    Usage:
        npu = NPUModel("my_npu", ntile=7, ndpe=40, ew=8)
        npu.mac_array.load_weights(0, weight_data)
        results = npu.run_layer(activations)
        print(npu.get_status())
    """

    def __init__(
        self,
        name: str = "npu",
        ntile: int = 7,
        ndpe: int = 40,
        ew: int = 8,
        accw: int = 32,
        dotw: int = 40,
        nvrf: int = 12,
        vrf_depth: int = 512,
        num_mfu_funcs: int = 8,
    ):
        self.name = name
        self.ntile = ntile
        self.ndpe = ndpe
        self.ew = ew
        self.accw = accw
        self.dotw = dotw
        self.nvrf = nvrf
        self.vrf_depth = vrf_depth
        self.num_mfu_funcs = num_mfu_funcs

        self.mac_array = MACArrayModel(
            ntile=ntile, ndpe=ndpe,
            ew=ew, accw=accw, dotw=dotw,
        )
        self.state = NPUState()

    def run_layer(
        self,
        activations: List[int],
        activation_func: str = "pass_through",
    ) -> List[int]:
        """Run a full layer: MAC → activation function.

        Args:
            activations: Input activation values.
            activation_func: Post-MAC activation ("relu", "sigmoid", "tanh", "pass_through").

        Returns:
            Flattened list of output values.
        """
        results = self.mac_array.run_all_tiles(activations)

        flat = []
        func = _ACTIVATION_FUNCS.get(activation_func, lambda x, ew=8: x)
        for tile in range(self.ntile):
            for val in results[tile]:
                flat.append(func(val, self.ew))

        self.state.state = 2  # DONE
        return flat

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "ntile": self.ntile,
            "ndpe": self.ndpe,
            "ew": self.ew,
            "vrf_depth": self.vrf_depth,
            "mac_status": self.mac_array.get_status(),
            "pipeline_state": self.state.state,
        }

    def reset(self):
        self.state = NPUState()
        self.mac_array.state = NPUState()
