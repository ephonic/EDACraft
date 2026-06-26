"""L2 cycle model tests for EarphoneAPBBridge."""

import pytest

from earphone.modules.apb_bridge.layer_L2_cycle.src.cycle import describe


class TestAPBBridgeCycle:
    def test_describe(self):
        info = describe()
        assert info["name"] == "EarphoneAPBBridge"
        assert info["layer"] == "L2_cycle"
        assert info["decode_latency_cycles"] == 0
        assert info["num_slave_slots"] == 8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
