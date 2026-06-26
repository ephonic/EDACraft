"""EarphoneAPBBridge module package.

Public API:
    - APB_SLAVE_SLOTS, apb_decode, describe: L1 behavior decoder.
"""

from __future__ import annotations

from earphone.modules.apb_bridge.layer_L1_behavior.src.behavior import (
    APB_SLAVE_SLOTS,
    apb_decode,
    describe,
)

__all__ = ["APB_SLAVE_SLOTS", "apb_decode", "describe"]
