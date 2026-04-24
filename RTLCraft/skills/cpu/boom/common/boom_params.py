"""
BOOM Processor Parameters

Reference: Berkeley Out-of-Order Machine (BOOM) v3 microarchitecture.
This is a simplified parameter set for the rtlgen reference implementation.
"""

from rtlgen import Parameter


class BOOMParams:
    """Parameter bundle for a configurable BOOM core."""

    def __init__(
        self,
        xlen: int = 32,
        num_rob_entries: int = 16,
        num_int_prf: int = 64,
        issue_width: int = 2,
        num_alu: int = 2,
        num_mul: int = 1,
        num_lsu: int = 1,
        fetch_width: int = 2,
        bht_entries: int = 64,
        btb_entries: int = 16,
    ):
        self.XLEN = xlen
        self.NUM_ROB_ENTRIES = num_rob_entries
        self.NUM_INT_PRF = num_int_prf
        self.ISSUE_WIDTH = issue_width
        self.NUM_ALU = num_alu
        self.NUM_MUL = num_mul
        self.NUM_LSU = num_lsu
        self.FETCH_WIDTH = fetch_width
        self.BHT_ENTRIES = bht_entries
        self.BTB_ENTRIES = btb_entries

        # Derived
        self.ARCH_REG_COUNT = 32
        self.ROB_ADDR_W = max(num_rob_entries.bit_length(), 1)
        self.PRF_ADDR_W = max(num_int_prf.bit_length(), 1)
        self.BHT_ADDR_W = max(bht_entries.bit_length(), 1)
        self.BTB_ADDR_W = max(btb_entries.bit_length(), 1)
