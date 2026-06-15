"""L4 StructuralIR for the EarphoneFFT256 module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SubBlock:
    name: str
    purpose: str
    interfaces: List[str] = field(default_factory=list)


@dataclass
class FFT256Structure:
    """Structural decomposition of the FFT wrapper."""

    name: str = "EarphoneFFT256"
    subblocks: List[SubBlock] = field(default_factory=lambda: [
        SubBlock(
            "input_adapter",
            "Normalize the incoming complex sample stream into the FFT core interface.",
            ["clk", "rst", "di_en", "di_re", "di_im"],
        ),
        SubBlock(
            "fft256_core",
            "Reusable FFTController instance that owns the butterfly pipeline and twiddle schedule.",
            ["clk", "rst", "di_en", "di_re", "di_im", "do_en", "do_re", "do_im"],
        ),
        SubBlock(
            "output_adapter",
            "Expose the FFT core outputs as the module-level streaming response.",
            ["do_en", "do_re", "do_im"],
        ),
    ])


STRUCTURE = FFT256Structure()


def describe() -> Dict[str, Any]:
    """Return structural metadata for document generation."""
    return {
        "name": STRUCTURE.name,
        "layer": "L4_structure",
        "status": "implemented",
        "description": "Structural wrapper around the FFT256Core streaming datapath.",
        "subblocks": [subblock.name for subblock in STRUCTURE.subblocks],
        "external_interfaces": ["streaming_input", "streaming_output"],
    }


__all__ = ["SubBlock", "FFT256Structure", "STRUCTURE", "describe"]
