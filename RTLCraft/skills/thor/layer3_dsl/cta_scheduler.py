"""Thor GPU — CTA Scheduler L3 DSL. Workgroup dispatch round-robin to SMs."""
from rtlgen.core import Module, Input, Output, Wire, Reg
from rtlgen.logic import If, Else


class CTAScheduler(Module):
    def __init__(self, n_sm=4):
        super().__init__("cta_scheduler")
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.kernel_start = Input(1, "kernel_start")
        self.num_ctas = Input(16, "num_ctas")
        self.sm_ready_mask = Input(n_sm, "sm_ready_mask")
        self.dispatched_sm = Output(4, "dispatched_sm")
        self.dispatch_valid = Output(1, "dispatch_valid")
        self.remaining_ctas = Output(16, "remaining_ctas")
        self._total = Reg(16, "total_remain"); self._ptr = Reg(4, "dispatch_ptr")
        self._active = Reg(1, "kernel_active")

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._total <<= 0; self._ptr <<= 0; self._active <<= 0
            with Else():
                with If(self.kernel_start):
                    self._total <<= self.num_ctas; self._ptr <<= 0; self._active <<= 1
                with Else():
                    with If(self._active & (self._total > 0)):
                        self._ptr <<= self._ptr + 1
                        self._total <<= self._total - 1
                    with If(self._active & (self._total == 1)):
                        self._active <<= 0

        with self.comb:
            self.remaining_ctas <<= self._total
            self.dispatch_valid <<= self._active & (self._total > 0)
            self.dispatched_sm <<= self._ptr % 4
