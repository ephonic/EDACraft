"""L1 behavior model tests for ThorSharedMemory."""

import pytest

from thor_gpu.modules.shared_memory import shmem_read, shmem_write, shmem_functional
from thor_gpu.modules.shared_memory.layer_L1_behavior.src.behavior import describe


class TestSharedMemoryBehavior:
    def test_describe(self):
        info = describe()
        assert info["depth"] == 4096
        assert info["word_width"] == 256

    def test_write_then_read(self):
        mem = {}
        shmem_write(mem, 5, 0xABCD)
        assert shmem_read(mem, 5) == 0xABCD

    def test_uninitialized_read_zero(self):
        mem = {}
        assert shmem_read(mem, 100) == 0

    def test_write_priority_functional(self):
        mem = {7: 0x1111}
        res = shmem_functional(mem, we=1, re=1, addr=7, wdata=0x2222)
        assert res["rdata"] == 0x2222  # write committed first

    def test_address_mask(self):
        mem = {}
        shmem_write(mem, 0x1FFF, 0x99)  # masked to 0xFFF
        assert shmem_read(mem, 0xFFF) == 0x99


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
