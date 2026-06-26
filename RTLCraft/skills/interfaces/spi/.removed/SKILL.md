# SPI Controller Skill

APB-based SPI controller with Master/Slave dual-mode operation,
12-state FSM, CPOL/CPHA support, and programmable baud-rate divider.

## Architecture

```
SPIController (top wrapper: APB ↔ SPI pins)
├── SPIRegisters    (APB register interface, 9 registers, interrupt generation)
├── SPIControl      (12-state Master/Slave FSM, timing generator)
├── SPITransmit     (TX FIFO + parallel-to-serial mux + output enables)
├── SPIReceive      (serial-to-parallel + RX FIFO)
├── SPISlaveSync    (slave data/clock sync, metastability protection)
├── SPISlaveTX      (slave bit-select counter, slave_in_clk domain)
└── SPIExtSync      (external clock edge detector)
```

## Module PE Mapping

| PE Type | Submodule | Behavior Template | Key States |
|---------|-----------|-------------------|------------|
| `spi_registers` | SPIRegisters | spi_registers_template | config_reg, status_reg, enable_reg |
| `spi_control` | SPIControl | spi_control_template | 12-state FSM (RESET/M_IDLE/PREAMBLE/SHIFT/POSTAMBLE/PAUSE/S_IDLE/...) |
| `spi_transmit` | SPITransmit | spi_transmit_template | master_out, so_reg, tx_fifo state |
| `spi_receive` | SPIReceive | spi_receive_template | rx_data shift register |
| `spi_slave_sync` | SPISlaveSync | spi_slave_sync_template | si_sync chain, s_inprogress, slave clock gen |
| `spi_slave_tx` | SPISlaveTX | spi_slave_tx_template | s_txsel down-counter |
| `spi_ext_sync` | SPIExtSync | spi_ext_sync_template | ext_clk_sync chain |

## Registers (APB Address Map)

| Addr | Name | R/W | Description |
|------|------|-----|-------------|
| 0x00 | CONFIG | R/W | master/cpol/cpha/cks/pdec/ss/datasize |
| 0x04 | STATUS | R | tx_empty/tx_notfull/tx_full/rx_notempty/rx_full/ovrf/tx_uf/modf |
| 0x08 | IMASK | R/W | Interrupt mask (7 sources) |
| 0x0C | ENABLE | R/W | SPI enable |
| 0x10 | DELAY | R/W | d_init/d_after/d_btwn/d_nss (4×8-bit delays) |
| 0x14 | TXD | W | TX FIFO push data |
| 0x18 | RXD | R | RX FIFO pop data |
| 0x1C | SIC | R/W | Slave idle count |
| 0x20 | TX_THRESH | R/W | TX FIFO threshold |
| 0x24 | RX_THRESH | R/W | RX FIFO threshold |

## FSM States (SPIControl)

| State | Value | Description |
|-------|-------|-------------|
| STATE_RESET | 0 | Reset, all counters cleared |
| STATE_M_IDLE | 1 | Master idle, waiting for TX data |
| STATE_M_PREAMBLE | 2 | Master preamble delay (d_init/d_after/d_btwn) |
| STATE_M_SHIFT1 | 3 | Master shift phase 1 (first bit) |
| STATE_M_SHIFT2 | 4 | Master shift phase 2 (subsequent bits) |
| STATE_M_POSTAMBLE | 5 | Master postamble delay (d_after/d_nss) |
| STATE_M_PAUSE | 6 | Inter-transfer pause |
| STATE_S_IDLE | 7 | Slave idle, waiting for n_ss_in |
| STATE_S_PREAMBLE | 8 | Slave preamble sync |
| STATE_S_SHIFT | 9 | Slave shift phase |
| STATE_S_POSTAMBLE | 10 | Slave postamble |
| STATE_S_DONE | 11 | Slave transfer complete |

## CPOL/CPHA Modes

| Mode | CPOL | CPHA | Clock Idle | Sample Edge |
|------|------|------|------------|-------------|
| 0 | 0 | 0 | Low | Rising |
| 1 | 0 | 1 | Low | Falling |
| 2 | 1 | 0 | High | Falling |
| 3 | 1 | 1 | High | Rising |

## Key Design Patterns

1. **Dual-clock FIFO**: TX/RX FIFOs use separate wr_clk/rd_clk domains with
   cross-domain toggle synchronization (pop_i toggled → SPIDataSync → XOR edge detect).
2. **Metastability protection**: SI input passes through 3-flop synchronizer chain.
3. **Glitch-free master output**: master_out register updates only on m_out_change signal.
4. **Slave sub-domain**: SPISlaveTX runs on slave_in_clk (derived from sclk_in),
   with n_ss_in as async reset domain boundary.
5. **Programmable baud-rate**: baud_rate register /2 to /256 via bsel[2:0] selector.
6. **Mode-fail detection**: If master sees n_ss_in asserted during transfer → m_modf.
   If slave sees n_ss_in deassert mid-transfer → s_modf.

## Usage

```python
from skills.interfaces.spi.behaviors import (
    spi_registers_template,
    spi_control_template,
    spi_transmit_template,
    spi_receive_template,
    spi_slave_sync_template,
    spi_slave_tx_template,
    spi_ext_sync_template,
)
from skills.interfaces.spi.models import SPIControllerModel
from skills.interfaces.spi.arch_templates import build_spi_arch
```

## Reference RTL

Based on Cadence CDNSSPI IP (cdnsspi.v and submodules).
See `ref_rtl/spi/spi/hdl/hdl_src/` for original Verilog.
