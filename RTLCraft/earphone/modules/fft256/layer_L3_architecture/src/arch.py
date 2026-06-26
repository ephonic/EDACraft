"""L3 ArchitectureIR for the EarphoneFFT256 module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class FFT256Architecture:
    """Micro-architecture contract for the FFT wrapper."""

    name: str = "EarphoneFFT256"
    role: str = "Streaming 256-point FFT wrapper around the reusable FFT256Core datapath."
    pipeline: str = "streaming shell around a reusable FFT pipeline"
    stages: List[str] = field(default_factory=lambda: ["input_stream", "fft_core", "output_stream"])
    points: int = 256
    sample_width: int = 16
    numeric_format: str = "Q1.15 complex samples"
    throughput: str = "1 complex sample per cycle after pipeline fill"
    invariants: List[str] = field(default_factory=lambda: [
        "Transforms 256 complex input samples into 256 complex output samples.",
        "The wrapper preserves the streaming valid handshake on input and output.",
        "The reusable FFT256Core instance owns the butterfly pipeline state.",
    ])


ARCH = FFT256Architecture()


def describe() -> Dict[str, Any]:
    """Return architecture metadata for document generation."""
    return {
        "name": ARCH.name,
        "layer": "L3_architecture",
        "status": "implemented",
        "description": ARCH.role,
        "pipeline": ARCH.pipeline,
        "stages": list(ARCH.stages),
        "points": ARCH.points,
        "sample_width": ARCH.sample_width,
        "numeric_format": ARCH.numeric_format,
        "throughput": ARCH.throughput,
        "invariants": list(ARCH.invariants),
    }


__all__ = ["FFT256Architecture", "ARCH", "describe"]
