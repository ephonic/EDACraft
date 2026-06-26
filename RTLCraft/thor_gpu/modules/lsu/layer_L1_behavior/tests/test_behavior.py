"""L1 behavior model tests for ThorLSU."""

import pytest

from thor_gpu.modules.lsu import lsu_functional
from thor_gpu.modules.lsu.layer_L1_behavior.src.behavior import describe


class TestLSUBehavior:
    def test_describe(self):
        info = describe()
        assert info["data_width"] == 256

    def test_store_then_load(self):
        mem = {}
        lsu_functional(mem, op=1, addr=0x10, wdata=0xCAFE)
        res = lsu_functional(mem, op=0, addr=0x10, wdata=0)
        assert res["rdata"] == 0xCAFE
        assert res["done"] == 1

    def test_load_uninit_zero(self):
        mem = {}
        res = lsu_functional(mem, op=0, addr=0x20, wdata=0)
        assert res["rdata"] == 0

    def test_store_request_signals(self):
        mem = {}
        res = lsu_functional(mem, op=1, addr=0x30, wdata=0x99)
        assert res["mem_req"] == 1
        assert res["mem_wen"] == 1
        assert res["mem_addr"] == 0x30
        assert res["mem_wdata"] == 0x99


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
