"""
skills.interfaces.i2c.arch_templates — I2C Architecture Templates
"""
from __future__ import annotations

from rtlgen import ProcessingElement, PortDesc, StateDesc
from rtlgen import ArchDefinition
from rtlgen.arch_def import Protocol_Model
from rtlgen.behaviors import TemplateRegistry


def build_i2c_arch(
    filter_len: int = 4,
    dev_addr: int = 0x70,
) -> ArchDefinition:
    """Build I2C architecture with 1 PE: i2c_single_reg."""
    behavior = TemplateRegistry.get("i2c_single_reg")

    pe = ProcessingElement(
        name="I2C_SINGLE_REG", pe_type="i2c_single_reg",
        inputs=[
            PortDesc("clk", "input", 1), PortDesc("rst", "input", 1),
            PortDesc("scl_i", "input", 1),
            PortDesc("sda_i", "input", 1),
            PortDesc("data_in", "input", 8),
            PortDesc("data_latch", "input", 1),
        ],
        outputs=[
            PortDesc("scl_o", "output", 1),
            PortDesc("scl_t", "output", 1),
            PortDesc("sda_o", "output", 1),
            PortDesc("sda_t", "output", 1),
            PortDesc("data_out", "output", 8),
        ],
        state=[
            StateDesc("state_reg", "int", "FSM state", rtl_type="reg", rtl_width=3),
            StateDesc("data_reg", "int", "Data register", rtl_type="reg", rtl_width=8),
            StateDesc("shift_reg", "int", "Shift register", rtl_type="reg", rtl_width=8),
            StateDesc("bit_count_reg", "int", "Bit counter", rtl_type="reg", rtl_width=4),
        ],
        behavior=behavior(filter_len=filter_len, dev_addr=dev_addr) if behavior else None,
        can_stall=False, latency=1,
    )

    return ArchDefinition(
        name="I2C",
        description=f"I2C slave register: addr=0x{dev_addr:02x}, filter_len={filter_len}",
        isa="protocol",
        processing_elements=[pe],
        interconnects=[],
        model=Protocol_Model(),
    )


I2C_SlaveModel = Protocol_Model

__all__ = ["build_i2c_arch", "I2C_SlaveModel"]
