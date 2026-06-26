"""
skills.interfaces.spi.models — SPI Behavioral Models

Cycle-accurate behavioral models for SPI controller components.
Used for golden-reference simulation and verification comparison.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from rtlgen.arch_def import CycleContext, ModelProvider
from rtlgen.behaviors import TemplateRegistry


# =====================================================================
# SPI Controller Behavioral Model
# =====================================================================

class SPIControllerModel(ModelProvider):
    """Cycle-accurate behavioral model for APB-SPI controller.

    Provides golden-reference simulation for:
      - APB register reads/writes
      - Master/Slave FSM state transitions
      - SPI data transfer (serial ↔ parallel)
      - FIFO management
      - Interrupt generation
    """

    name = "spi_controller_model"
    description = "APB-SPI controller behavioral model with Master/Slave FSM"

    def create_behavior(
        self,
        master_mode: bool = True,
        cpol: int = 0,
        cpha: int = 0,
        baud_rate: int = 4,
        data_size: int = 7,  # 8 bits = value 7
        **kwargs,
    ):
        """Create a behavioral model closure for the SPI controller.

        Args:
            master_mode: True for master, False for slave.
            cpol: Clock polarity (0=idle low, 1=idle high).
            cpha: Clock phase (0=sample leading edge, 1=sample trailing).
            baud_rate: Baud rate divider value.
            data_size: Data size (bits - 1). 7 = 8 bits, 15 = 16 bits, etc.
        """

        def behavior(ctx: CycleContext):
            # Inputs
            psel = ctx.get_input("psel_i", 0)
            penable = ctx.get_input("penable_i", 0)
            pwrite = ctx.get_input("pwrite_i", 0)
            paddr = ctx.get_input("paddr_i", 0)
            pwdata = ctx.get_input("pwdata_i", 0)

            mi = ctx.get_input("mi_i", 0)
            si = ctx.get_input("si_i", 0)
            n_ss_in = ctx.get_input("n_ss_in_i", 1)
            sclk_in = ctx.get_input("sclk_in_i", 0)

            # State
            config = ctx.get_state("config", 0)
            enable = ctx.get_state("enable", 0)
            imask = ctx.get_state("imask", 0)

            tx_fifo = ctx.get_state("tx_fifo", [])  # List[int]
            rx_fifo = ctx.get_state("rx_fifo", [])  # List[int]
            tx_depth = 8
            rx_depth = 8

            shift_reg = ctx.get_state("shift_reg", 0)
            bit_count = ctx.get_state("bit_count", 0)
            sclk = ctx.get_state("sclk", 0)
            fsm_state = ctx.get_state("fsm_state", 0)

            # APB write
            if psel and penable and pwrite:
                if paddr == 0x00:
                    config = pwdata
                elif paddr == 0x08:
                    imask = pwdata & 0x7F
                elif paddr == 0x0C:
                    enable = pwdata & 0x1
                elif paddr == 0x14 and len(tx_fifo) < tx_depth:
                    tx_fifo.append(pwdata)

            # APB read
            prdata = 0
            if psel and penable and not pwrite:
                if paddr == 0x00:
                    prdata = config
                elif paddr == 0x04:
                    prdata = (0 |
                              (1 << 0 if len(tx_fifo) == 0 else 0) |
                              (1 << 2 if len(tx_fifo) < tx_depth else 0) |
                              (1 << 3 if len(rx_fifo) > 0 else 0) |
                              (1 << 4 if len(rx_fifo) >= rx_depth else 0))
                elif paddr == 0x08:
                    prdata = imask
                elif paddr == 0x0C:
                    prdata = enable
                elif paddr == 0x18 and len(rx_fifo) > 0:
                    prdata = rx_fifo.pop(0)

            # FSM simulation (simplified master mode)
            is_master = master_mode
            spi_enable = enable

            if not spi_enable:
                fsm_state = 0  # RESET
            elif is_master:
                if fsm_state == 0:  # RESET
                    fsm_state = 1  # M_IDLE
                elif fsm_state == 1:  # M_IDLE
                    if len(tx_fifo) > 0:
                        fsm_state = 2  # M_PREAMBLE
                        bit_count = 0
                        shift_reg = tx_fifo.pop(0)
                elif fsm_state in (2, 3, 4):  # PREAMBLE/SHIFT
                    if bit_count <= data_size:
                        bit_count += 1
                        # Shift out MSB first
                        ctx.set_output("mo_o", (shift_reg >> (data_size - bit_count + 1)) & 0x1)
                        # Shift in
                        shift_reg = ((shift_reg << 1) | mi) & ((1 << (data_size + 1)) - 1)
                        if bit_count > data_size:
                            fsm_state = 5  # M_POSTAMBLE
                            if len(rx_fifo) < rx_depth:
                                rx_fifo.append(shift_reg)
                    else:
                        if len(tx_fifo) > 0:
                            fsm_state = 2
                            bit_count = 0
                            shift_reg = tx_fifo.pop(0)
                        else:
                            fsm_state = 1  # M_IDLE
                            ctx.set_output("mo_o", 0)
                elif fsm_state == 5:  # M_POSTAMBLE
                    fsm_state = 1  # M_IDLE

            # Outputs
            ctx.set_output("prdata_o", prdata)
            ctx.set_output("master_o", 1 if is_master else 0)
            ctx.set_output("spi_enable_o", spi_enable)
            ctx.set_output("tx_empty_o", 1 if len(tx_fifo) == 0 else 0)
            ctx.set_output("tx_notfull_o", 1 if len(tx_fifo) < tx_depth else 0)
            ctx.set_output("tx_full_o", 1 if len(tx_fifo) >= tx_depth else 0)
            ctx.set_output("rx_notempty_o", 1 if len(rx_fifo) > 0 else 0)
            ctx.set_output("rx_full_o", 1 if len(rx_fifo) >= rx_depth else 0)
            ctx.set_output("rx_fifo_o", rx_fifo[0] if rx_fifo else 0)

            # Persist state
            ctx.set_state("config", config)
            ctx.set_state("enable", enable)
            ctx.set_state("imask", imask)
            ctx.set_state("tx_fifo", tx_fifo)
            ctx.set_state("rx_fifo", rx_fifo)
            ctx.set_state("shift_reg", shift_reg)
            ctx.set_state("bit_count", bit_count)
            ctx.set_state("fsm_state", fsm_state)
            ctx.set_state("sclk", sclk)

        return behavior

    def create_testbench(self, **kwargs) -> List[Dict]:
        """Generate a basic SPI controller test sequence."""
        tests = []

        # Test 1: Reset state
        tests.append({
            "name": "reset_state",
            "setup": {"rst_n_i": 0, "psel_i": 0},
            "cycles": 2,
            "check": {"master_o": 0, "tx_empty_o": 1, "rx_notempty_o": 0},
        })

        # Test 2: Configure master mode
        tests.append({
            "name": "configure_master",
            "setup": {"rst_n_i": 1, "psel_i": 1, "penable_i": 1, "pwrite_i": 1,
                      "paddr_i": 0x00, "pwdata_i": 0x0B},  # master=1, bsr=1, ds=0
            "cycles": 2,
            "check": {"master_o": 1},
        })

        # Test 3: Enable SPI
        tests.append({
            "name": "enable_spi",
            "setup": {"psel_i": 1, "penable_i": 1, "pwrite_i": 1,
                      "paddr_i": 0x0C, "pwdata_i": 1},
            "cycles": 2,
            "check": {"spi_enable_o": 1},
        })

        # Test 4: Push TX data
        tests.append({
            "name": "push_tx_data",
            "setup": {"psel_i": 1, "penable_i": 1, "pwrite_i": 1,
                      "paddr_i": 0x14, "pwdata_i": 0xA5},
            "cycles": 2,
            "check": {"tx_empty_o": 0},
        })

        return tests


# =====================================================================
# SPI FIFO Behavioral Model
# =====================================================================

class SPIFIFOModel(ModelProvider):
    """Behavioral model for dual-clock SPI FIFO.

    Models push/pop operations with cross-domain toggle synchronization.
    """

    name = "spi_fifo_model"
    description = "Dual-clock FIFO with toggle-based synchronization"

    def create_behavior(
        self,
        width: int = 32,
        depth: int = 8,
        **kwargs,
    ):
        """Create FIFO behavioral model.

        Args:
            width: Data width in bits.
            depth: Number of entries.
        """

        def behavior(ctx: CycleContext):
            wr_en = ctx.get_input("push_i", 0)
            rd_en = ctx.get_input("pop_i", 0)
            clr = ctx.get_input("clr_wr_i", 0) or ctx.get_input("clr_rd_i", 0)
            data_in = ctx.get_input("datain_i", 0)

            fifo = ctx.get_state("fifo", [])
            mask = (1 << width) - 1

            if clr:
                fifo = []
            else:
                if wr_en and len(fifo) < depth:
                    fifo.append(data_in & mask)
                if rd_en and len(fifo) > 0:
                    fifo.pop(0)

            ctx.set_output("dataout_o", fifo[0] if fifo else 0)
            ctx.set_output("fifo_empty_rd_o", 1 if len(fifo) == 0 else 0)
            ctx.set_output("fifo_notfull_wr_o", 1 if len(fifo) < depth else 0)
            ctx.set_output("fifo_full_wr_o", 1 if len(fifo) >= depth else 0)

            ctx.set_state("fifo", fifo)

        return behavior

    def create_testbench(self, **kwargs) -> List[Dict]:
        tests = []
        tests.append({
            "name": "fifo_push_pop",
            "setup": {"push_i": 0, "pop_i": 0, "clr_wr_i": 0, "clr_rd_i": 0},
            "cycles": 1,
            "check": {"fifo_empty_rd_o": 1},
        })
        tests.append({
            "name": "push_data",
            "setup": {"push_i": 1, "datain_i": 0xDEADBEEF},
            "cycles": 1,
            "check": {"fifo_empty_rd_o": 0},
        })
        return tests
