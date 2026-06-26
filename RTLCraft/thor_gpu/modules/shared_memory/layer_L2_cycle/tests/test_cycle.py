"""L2 cycle model tests for ThorSharedMemory."""

import pytest

from rtlgen import CycleContext
from thor_gpu.modules.shared_memory.layer_L2_cycle.src.cycle import shmem_cycle_model, describe


class TestSharedMemoryCycle:
    def test_describe(self):
        info = describe()
        assert info["name"] == "ThorSharedMemory"

    def test_reset_clears(self):
        model = shmem_cycle_model()
        ctx = CycleContext()
        ctx.inputs = {"rst_n": 0}
        model(ctx)
        assert ctx.outputs["rdata"] == 0

    def test_write_then_registered_read(self):
        model = shmem_cycle_model()
        ctx = CycleContext()
        # Write addr=3, data=0xDEAD.
        ctx.inputs = {"rst_n": 1, "we": 1, "re": 0, "addr": 3, "wdata": 0xDEAD}
        model(ctx)
        # Now read addr=3.
        ctx.inputs = {"rst_n": 1, "we": 0, "re": 1, "addr": 3, "wdata": 0}
        model(ctx)
        assert ctx.outputs["rdata"] == 0xDEAD


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
