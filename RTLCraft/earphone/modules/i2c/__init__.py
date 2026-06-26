"""EarphoneI2C module package.

Public API:
    - I2CBusFunctional: L1 functional I2C transaction model.
"""

from __future__ import annotations

from earphone.modules.i2c.layer_L1_behavior.src.behavior import I2CBusFunctional

__all__ = ["I2CBusFunctional"]
