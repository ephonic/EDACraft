"""L3 ArchitectureIR contract for the Earphone top-level SoC."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class TopModule:
    instance: str
    module: str
    role: str


@dataclass(frozen=True)
class APBSlot:
    slot: int
    base_offset: int
    region: str
    integrated: bool


@dataclass
class TopLevelArchitecture:
    """Architecture contract for EarphoneTop integration."""

    name: str = "EarphoneTop"
    dsl_object_name: str = "earphone_top"
    verilog_module_name: str = "EarphoneTop"
    verilog_file_name: str = "earphone_top.v"
    clock_domain: str = "clk"
    reset: str = "rst_n"
    apb_decode_field: str = "m_paddr[29:22]"
    apb_slot_size_bytes: int = 4 * 1024 * 1024
    modules: List[TopModule] = field(default_factory=lambda: [
        TopModule("cpu", "EarphoneRV32", "RV32IM control processor"),
        TopModule("simd16", "EarphoneSIMD16", "16-lane vector/audio accelerator"),
        TopModule("fft256", "EarphoneFFT256", "Streaming FFT accelerator"),
        TopModule("qspi", "EarphoneQSPI", "External flash XIP controller"),
        TopModule("apb_bridge", "EarphoneAPBBridge", "APB4 decode and response mux"),
        TopModule("sram", "EarphoneSRAM256K", "256 KB APB SRAM"),
        TopModule("i2c", "EarphoneI2C", "APB I2C master"),
    ])
    apb_slots: List[APBSlot] = field(default_factory=lambda: [
        APBSlot(0, 0x00000000, "QSPI", False),
        APBSlot(1, 0x00400000, "SRAM", True),
        APBSlot(2, 0x00800000, "SPI", False),
        APBSlot(3, 0x00C00000, "UART", False),
        APBSlot(4, 0x01000000, "I2C", True),
        APBSlot(5, 0x01400000, "I2S", False),
        APBSlot(6, 0x01800000, "BTLE", False),
        APBSlot(7, 0x01C00000, "SIMD16", False),
    ])
    external_interfaces: List[str] = field(default_factory=lambda: [
        "clock_reset",
        "imem_bus",
        "dmem_bus",
        "apb_debug",
        "qspi_pads",
        "i2c_pads",
    ])
    invariants: List[str] = field(default_factory=lambda: [
        "Every integrated APB slave has an assigned APB slot.",
        "APB SRAM and I2C responses are muxed back to the external APB debug port.",
        "QSPI and I2C pad interfaces remain top-level ports.",
        "Top-level SoC closure is gated by module approvals and CP1_SOC approval.",
    ])


TOP_ARCH = TopLevelArchitecture()


def describe() -> Dict[str, Any]:
    """Return architecture metadata for document generation and tests."""
    return {
        "name": TOP_ARCH.name,
        "dsl_object_name": TOP_ARCH.dsl_object_name,
        "verilog_module_name": TOP_ARCH.verilog_module_name,
        "verilog_file_name": TOP_ARCH.verilog_file_name,
        "layer": "L3_architecture",
        "status": "implemented",
        "clock_domain": TOP_ARCH.clock_domain,
        "reset": TOP_ARCH.reset,
        "apb_decode_field": TOP_ARCH.apb_decode_field,
        "apb_slot_size_bytes": TOP_ARCH.apb_slot_size_bytes,
        "modules": [module.module for module in TOP_ARCH.modules],
        "module_instances": [module.instance for module in TOP_ARCH.modules],
        "apb_slots": [slot.region for slot in TOP_ARCH.apb_slots],
        "integrated_apb_regions": [slot.region for slot in TOP_ARCH.apb_slots if slot.integrated],
        "external_interfaces": list(TOP_ARCH.external_interfaces),
        "invariants": list(TOP_ARCH.invariants),
    }


__all__ = ["TopModule", "APBSlot", "TopLevelArchitecture", "TOP_ARCH", "describe"]
