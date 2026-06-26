"""L3 ArchitectureIR for the ThorTensorCore module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class TensorCoreArchitecture:
    name: str = "ThorTensorCore"
    role: str = "8x8x8 INT8->INT32 matrix-multiply-accumulate (MMA) unit."
    pipeline: str = "systolic-style MAC array feeding a 1-stage result register"
    stages: List[str] = field(default_factory=lambda: ["mac_array", "result_register"])
    m: int = 8
    n: int = 8
    k: int = 8
    a_dtype: str = "INT8"
    b_dtype: str = "INT8"
    c_dtype: str = "INT32"
    latency_cycles: int = 1
    invariants: List[str] = field(default_factory=lambda: [
        "result[i][j] = C[i][j] + sum_k A[i][k]*B[k][j] when acc_en, else sum_k only.",
        "INT8 operands are signed two's-complement; accumulation is 32-bit.",
        "start strobe latches operands; done asserts the cycle the result is valid.",
    ])


ARCH = TensorCoreArchitecture()


def describe() -> Dict[str, Any]:
    return {
        "name": ARCH.name,
        "layer": "L3_architecture",
        "status": "implemented",
        "description": ARCH.role,
        "pipeline": ARCH.pipeline,
        "stages": list(ARCH.stages),
        "m": ARCH.m, "n": ARCH.n, "k": ARCH.k,
        "a_dtype": ARCH.a_dtype, "b_dtype": ARCH.b_dtype, "c_dtype": ARCH.c_dtype,
        "latency_cycles": ARCH.latency_cycles,
        "invariants": list(ARCH.invariants),
    }


__all__ = ["TensorCoreArchitecture", "ARCH", "describe"]
