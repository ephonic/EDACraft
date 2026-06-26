"""L1 behavior model tests for EarphoneAPBBridge."""

import pytest

from earphone.modules.apb_bridge.layer_L1_behavior.src.behavior import (
    APB_SLAVE_SLOTS,
    SLOT_SIZE,
    apb_decode,
    describe,
)


class TestAPBBridgeBehavior:
    def test_describe(self):
        info = describe()
        assert info["name"] == "EarphoneAPBBridge"
        assert info["layer"] == "L1_behavior"
        assert info["num_slave_slots"] == 8
        assert "QSPI" in info["slave_slots"]

    def test_decode_each_slot_base(self):
        for idx, (name, base, _) in enumerate(APB_SLAVE_SLOTS):
            decoded_idx, decoded_name = apb_decode(base)
            assert decoded_idx == idx
            assert decoded_name == name

    def test_decode_slot_internal_offset(self):
        # Offset inside SRAM region (slot 1)
        idx, name = apb_decode(SLOT_SIZE + 0x12345)
        assert idx == 1
        assert name == "SRAM"

    def test_decode_out_of_range_fallback(self):
        idx, name = apb_decode(8 * SLOT_SIZE)
        assert idx == 0
        assert name == "QSPI"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
