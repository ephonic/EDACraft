"""
skills.interfaces.axi_lite.models — AXI-Lite RAM Behavioral Model

Golden-reference simulator for AXI-Lite RAM.
Used for cycle-accurate comparison against generated RTL.
"""
from __future__ import annotations


class AXIL_RAM_Model:
    """AXI-Lite RAM behavioral model.

    Simplified AXI-Lite slave with word-level read/write:
      - Write: AW handshake + W handshake -> B response (1-cycle)
      - Read: AR handshake -> R response with data (1-cycle)
      - Zero-initialized memory (dict-backed)
      - bresp/rresp always OK (0)
    """

    def __init__(self, data_width: int = 32, addr_width: int = 16):
        self.data_width = data_width
        self.addr_width = addr_width
        self.reset()

    def reset(self):
        """Reset all internal state."""
        # Write channel
        self.s_axil_awready = 0
        self.s_axil_wready = 0
        self.s_axil_bvalid = 0
        self.s_axil_bresp = 0
        # Read channel
        self.s_axil_arready = 0
        self.s_axil_rvalid = 0
        self.s_axil_rdata = 0
        self.s_axil_rresp = 0
        # Internal registers
        self._awready_reg = 0
        self._wready_reg = 0
        self._bvalid_reg = 0
        self._arready_reg = 0
        self._rvalid_reg = 0
        self._rdata_reg = 0
        self._awaddr_reg = 0
        self._araddr_reg = 0
        # Memory (word-addressable, zero-initialized)
        self._mem: dict[int, int] = {}

    def cycle(
        self,
        rst: int = 0,
        s_axil_awaddr: int = 0,
        s_axil_awvalid: int = 0,
        s_axil_wdata: int = 0,
        s_axil_wvalid: int = 0,
        s_axil_bready: int = 0,
        s_axil_araddr: int = 0,
        s_axil_arvalid: int = 0,
        s_axil_rready: int = 0,
    ):
        """Execute one clock cycle of the AXI-Lite RAM model.

        Args:
            rst: Async reset (active high)
            s_axil_awaddr: Write address
            s_axil_awvalid: Write address valid
            s_axil_wdata: Write data
            s_axil_wvalid: Write data valid
            s_axil_bready: Response ready
            s_axil_araddr: Read address
            s_axil_arvalid: Read address valid
            s_axil_rready: Read data ready
        """
        if rst:
            self.reset()
            return

        # Write response clear
        if s_axil_bready and self._bvalid_reg:
            self._bvalid_reg = 0

        # Read response clear
        if s_axil_rready and self._rvalid_reg:
            self._rvalid_reg = 0

        # Write transaction: awvalid & wvalid & !bvalid
        if s_axil_awvalid and s_axil_wvalid and (not self._bvalid_reg):
            self._awready_reg = 1
            self._wready_reg = 1
            self._bvalid_reg = 1
            self._awaddr_reg = s_axil_awaddr
            self._mem[s_axil_awaddr] = s_axil_wdata & ((1 << self.data_width) - 1)
        else:
            self._awready_reg = 0
            self._wready_reg = 0

        # Read transaction: arvalid & (!rvalid | rready)
        if s_axil_arvalid and (not self._rvalid_reg or s_axil_rready):
            self._arready_reg = 1
            self._rvalid_reg = 1
            self._araddr_reg = s_axil_araddr
            self._rdata_reg = self._mem.get(s_axil_araddr, 0)
        else:
            self._arready_reg = 0

        # Drive outputs
        self.s_axil_awready = self._awready_reg
        self.s_axil_wready = self._wready_reg
        self.s_axil_bvalid = self._bvalid_reg
        self.s_axil_bresp = 0
        self.s_axil_arready = self._arready_reg
        self.s_axil_rvalid = self._rvalid_reg
        self.s_axil_rdata = self._rdata_reg
        self.s_axil_rresp = 0

    def read_mem(self, addr: int) -> int:
        """Direct memory read (for testbench inspection)."""
        return self._mem.get(addr, 0)

    def write_mem(self, addr: int, data: int):
        """Direct memory write (for testbench setup)."""
        self._mem[addr] = data & ((1 << self.data_width) - 1)


def create_testbench():
    """Simple AXI-Lite RAM testbench: write then read back."""
    ram = AXIL_RAM_Model(data_width=32, addr_width=8)

    # Reset
    ram.cycle(rst=1)

    # Write address 0x05 with data 0xDEADBEEF
    ram.cycle(
        s_axil_awaddr=0x05, s_axil_awvalid=1,
        s_axil_wdata=0xDEADBEEF, s_axil_wvalid=1,
        s_axil_bready=0,
    )
    assert ram.s_axil_awready == 1, "AW should be ready"
    assert ram.s_axil_wready == 1, "W should be ready"
    assert ram.s_axil_bvalid == 1, "B should be valid"

    # Accept B response
    ram.cycle(s_axil_bready=1)
    assert ram.s_axil_bvalid == 0, "B should be cleared after ready"

    # Read address 0x05
    ram.cycle(s_axil_araddr=0x05, s_axil_arvalid=1, s_axil_rready=0)
    assert ram.s_axil_arready == 1, "AR should be ready"
    assert ram.s_axil_rvalid == 1, "R should be valid"
    assert ram.s_axil_rdata == 0xDEADBEEF, \
        f"Expected 0xDEADBEEF, got 0x{ram.s_axil_rdata:08X}"

    # Accept R response
    ram.cycle(s_axil_rready=1)
    assert ram.s_axil_rvalid == 0, "R should be cleared after ready"

    print("AXI-Lite RAM testbench: PASSED")


if __name__ == "__main__":
    create_testbench()
