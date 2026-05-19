# I2C — Single Register Slave

## Overview

I2C slave with 7-bit address matching, single-byte read/write, and input glitch filtering.

## Architecture

```
I2C_SINGLE_REG
  SCL/SDA → [input filter] → [edge detect] → [FSM]
  FSM: IDLE → ADDRESS → ACK → WRITE_1/2 or READ_1/2/3
```

## PE Types

| PE Type | Reference File | Description |
|---------|---------------|-------------|
| i2c_single_reg | i2c/rtl/i2c_single_reg.v | I2C slave with FILTER_LEN input filter |

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| FILTER_LEN | int | 4 | Input filter sample count |
| DEV_ADDR | int | 0x70 | 7-bit device address |

## Key Design Patterns

- **Input filtering**: `filter_reg = (filter_reg << 1) | input; filter_out = (all_ones or all_zeros)`
- **Start detection**: `sda_negedge & scl_i` (SDA falling while SCL high)
- **Stop detection**: `sda_posedge & scl_i` (SDA rising while SCL high)
- **ACK/NACK**: Master drives SDA low during READ to continue, high to stop
