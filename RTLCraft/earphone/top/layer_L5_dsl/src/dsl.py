"""L5 DSL compatibility wrapper for the Earphone top-level SoC."""

from __future__ import annotations

from typing import Any, Dict

from earphone.design_earphone import EarphoneTop


def build_top() -> EarphoneTop:
    """Instantiate the current top-level DSL contract."""
    return EarphoneTop()


def describe() -> Dict[str, Any]:
    """Return L5 DSL metadata for top-level document generation and tests."""
    return {
        "name": "EarphoneTop",
        "layer": "L5_dsl",
        "status": "compatibility_wrapper",
        "dsl_object_name": "earphone_top",
        "verilog_module_name": "EarphoneTop",
        "verilog_file_name": "earphone_top.v",
        "source": "earphone.design_earphone.EarphoneTop",
        "external_ports": [
            "clk",
            "rst_n",
            "imem_addr",
            "dmem_addr",
            "apb_paddr",
            "qspi_cs_n",
            "scl_o",
            "sda_o",
        ],
    }


__all__ = ["EarphoneTop", "build_top", "describe"]
