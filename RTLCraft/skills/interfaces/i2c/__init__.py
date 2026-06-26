"""
skills.interfaces.i2c — I2C Skill

I2C single-register slave with input filtering and 7-bit address matching.

Architecture:
  I2C_SINGLE_REG — 8-state FSM: IDLE→ADDRESS→ACK→WRITE/READ
  - Input glitch filter (FILTER_LEN samples)
  - Start/stop detection on SDA edges while SCL high

Modules:
  - behaviors.py: i2c_single_reg_template
  - models.py: I2C_Single_Reg_Model
  - arch_templates.py: build_i2c_arch()
  - skeleton_templates.py: DSL skeleton generation steps
"""

import skills.interfaces.i2c.behaviors  # noqa: F401
import skills.interfaces.i2c.skeleton_templates  # noqa: F401

from skills.interfaces.i2c.models import I2C_Single_Reg_Model
from skills.interfaces.i2c.arch_templates import I2C_SlaveModel, build_i2c_arch
from skills.interfaces.i2c.behaviors import i2c_single_reg_template

from skills.interfaces.i2c.dsl_modules import (
    I2C_SINGLE_REG,
)

__all__ = [
    "I2C_SINGLE_REG",
    "I2C_Single_Reg_Model", "I2C_SlaveModel", "build_i2c_arch",
    "i2c_single_reg_template",
]
