"""
skills.interfaces — Interface Protocol Skills

Domain-specific skills for interface protocols:
  - spi: APB-SPI controller (Master/Slave dual-mode)
  - uart: AXI-Stream UART (transmitter + receiver)
  - wishbone: Wishbone bus register slice + 2-to-1 MUX
  - axis: AXI-Stream skid register, width adapter, broadcaster
  - axi_lite: AXI-Lite RAM
  - axi: AXI dual-port RAM
  - i2c: I2C single-register slave with input filter
  - pcie: PCIe pulse merge + P-Tile flow control counter
  - ethernet: PTP timestamp extraction
"""

# UART
from skills.interfaces.uart import (
    UART_TX_Model, UART_RX_Model, UART_ControllerModel, build_uart_arch,
    uart_tx_template, uart_rx_template, uart_top_template,
)

# Wishbone
from skills.interfaces.wishbone import (
    WB_Reg_Model, WB_MUX_2_Model, Wishbone_BusModel, build_wishbone_arch,
    wb_reg_template, wb_mux_2_template,
)

# AXI-Stream
from skills.interfaces.axis import (
    AXIS_Register_Model, AXIS_Adapter_Model, AXIS_StreamModel, build_axis_arch,
    axis_register_template, axis_adapter_template, axis_broadcast_template,
)

# AXI-Lite
from skills.interfaces.axi_lite import (
    AXIL_RAM_Model, AXIL_RAM_ArchModel, build_axil_ram_arch,
    axil_ram_template,
)

# AXI
from skills.interfaces.axi import (
    AXI_DP_RAM_Simple_Model, AXI_DP_RAM_Model, build_axi_arch,
    axi_dp_ram_simple_template,
)

# I2C
from skills.interfaces.i2c import (
    I2C_Single_Reg_Model, I2C_SlaveModel, build_i2c_arch,
    i2c_single_reg_template,
)

# PCIe
from skills.interfaces.pcie import (
    Pulse_Merge_Model, PCIe_PTile_FC_Model, PCIe_Model, build_pcie_arch,
    pulse_merge_template, pcie_ptile_fc_template,
)

# Ethernet
from skills.interfaces.ethernet import (
    PTP_TS_Extract_Model, Ethernet_TSModel, build_ethernet_arch,
    ptp_ts_extract_template,
)

__all__ = [
    # UART
    "UART_TX_Model", "UART_RX_Model", "UART_ControllerModel", "build_uart_arch",
    "uart_tx_template", "uart_rx_template", "uart_top_template",
    # Wishbone
    "WB_Reg_Model", "WB_MUX_2_Model", "Wishbone_BusModel", "build_wishbone_arch",
    "wb_reg_template", "wb_mux_2_template",
    # AXI-Stream
    "AXIS_Register_Model", "AXIS_Adapter_Model", "AXIS_StreamModel", "build_axis_arch",
    "axis_register_template", "axis_adapter_template", "axis_broadcast_template",
    # AXI-Lite
    "AXIL_RAM_Model", "AXIL_RAM_ArchModel", "build_axil_ram_arch",
    "axil_ram_template",
    # AXI
    "AXI_DP_RAM_Simple_Model", "AXI_DP_RAM_Model", "build_axi_arch",
    "axi_dp_ram_simple_template",
    # I2C
    "I2C_Single_Reg_Model", "I2C_SlaveModel", "build_i2c_arch",
    "i2c_single_reg_template",
    # PCIe
    "Pulse_Merge_Model", "PCIe_PTile_FC_Model", "PCIe_Model", "build_pcie_arch",
    "pulse_merge_template", "pcie_ptile_fc_template",
    # Ethernet
    "PTP_TS_Extract_Model", "Ethernet_TSModel", "build_ethernet_arch",
    "ptp_ts_extract_template",
]
