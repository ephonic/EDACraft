"""L1 behavior model tests for EarphoneSRAM256K."""

import pytest

from earphone.modules.sram256k import SRAM256KFunctional


class TestSRAM256KFunctional:
    def test_initial_memory_zero(self):
        sram = SRAM256KFunctional()
        assert sram.read(0x0000) == 0
        assert sram.read(0x1000) == 0

    def test_word_write_read(self):
        sram = SRAM256KFunctional()
        sram.write(0x40, 0xDEADBEEF)
        assert sram.read(0x40) == 0xDEADBEEF

    def test_byte_masked_write(self):
        sram = SRAM256KFunctional()
        sram.write(0x44, 0xFFFFFFFF)
        sram.write(0x44, 0xAABBCCDD, mask=0b0101)
        val = sram.read(0x44)
        # Byte 0 replaced with 0xDD, byte 2 replaced with 0xBB; bytes 1,3 kept 0xFF
        expected = (0xFF << 24) | (0xBB << 16) | (0xFF << 8) | 0xDD
        assert val == expected

    def test_address_wrap(self):
        sram = SRAM256KFunctional()
        size = 256 * 1024
        sram.write(size, 0x12345678)
        assert sram.read(0) == 0x12345678

    def test_multiple_addresses(self):
        sram = SRAM256KFunctional()
        for i in range(8):
            sram.write(i * 4, 0x11111111 * i)
        for i in range(8):
            assert sram.read(i * 4) == (0x11111111 * i) & 0xFFFFFFFF


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
