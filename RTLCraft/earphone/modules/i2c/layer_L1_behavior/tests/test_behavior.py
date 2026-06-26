"""L1 behavior model tests for EarphoneI2C."""

import pytest

from earphone.modules.i2c import I2CBusFunctional


class TestI2CBusFunctional:
    def test_write_transaction_logged(self):
        bus = I2CBusFunctional()
        bus.write(0x50, [0xAB, 0xCD])
        assert len(bus.transactions) == 1
        addr, data, is_read = bus.transactions[0]
        assert addr == 0x50
        assert data == [0xAB, 0xCD]
        assert is_read is False

    def test_read_transaction_logged(self):
        bus = I2CBusFunctional()
        data = bus.read(0x50, 3)
        assert data == [0, 0, 0]
        assert len(bus.transactions) == 1
        addr, _, is_read = bus.transactions[0]
        assert addr == 0x50
        assert is_read is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
