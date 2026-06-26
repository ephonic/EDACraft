"""L1 behavior model tests for EarphoneQSPI."""

import pytest

from earphone.modules.qspi import QSPIFlashFunctional


class TestQSPIFlashFunctional:
    def test_load_and_read(self):
        flash = QSPIFlashFunctional()
        flash.load_data(0x1000, b"\x01\x02\x03\x04")
        assert flash.xip_read(0x1000) == 0x04030201

    def test_read_uninitialized_zero(self):
        flash = QSPIFlashFunctional()
        assert flash.xip_read(0) == 0

    def test_read_cross_boundary(self):
        flash = QSPIFlashFunctional()
        flash.load_data(0x10, b"\xFF" * 8)
        assert flash.xip_read(0x10, nbytes=4) == 0xFFFFFFFF


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
