# SPI — Serial Peripheral Interface

## Overview

SPI master/slave interface with full CPOL/CPHA mode support, configurable word length, and MSB/LSB data order selection.

## Architecture

```
SPI_TOP (top)
├── SPIClockDivider — free-running counter clock divider (2^DIV_N)
│   - Output = counter[DIV_N-1]
│   - Master mode only
│
└── SPIModule — core SPI engine
    - 2-state FSM: IDLE → CYCLE_BITS
    - Edge detectors (pos_edge_det / neg_edge_det) on SCLK
    - CPOL/CPHA combinational edge selection
    - bit_counter shift: MSB first (default) or LSB first (INVERT_DATA_ORDER)
    - Master mode: drives SCLK_OUT, SS_OUT
    - Slave mode: receives SCLK_IN, SS_IN
```

## PE Types

| PE Type | Reference File | Description |
|---------|---------------|-------------|
| spi_clock_divider | spi/rtl/clock_divider.v | Free-running counter clock divider |
| spi_module | spi/rtl/spi_module.v | Core SPI master/slave engine |
| spi_top | spi/rtl/spi2.v | Top-level wrapper (divider + core) |

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| CPOL | int | 0 | Clock polarity (0=idle low, 1=idle high) |
| CPHA | int | 0 | Clock phase (0=sample first edge, 1=sample second edge) |
| INVERT_DATA_ORDER | int | 0 | 0=MSB first, 1=LSB first |
| SPI_MASTER | int | 1 | 1=master mode, 0=slave mode |
| SPI_WORD_LEN | int | 8 | Word length in bits |
| CLK_DIV_N | int | 4 | Clock divider exponent (SCLK = clk / 2^DIV_N) |

## Key Design Patterns

- **Edge selection via CPOL/CPHA**: `delay_pol`, `get_number_edge`, `switch_number_edge` are combinational MUXes driven by CPOL and CPHA
- **2-state FSM**: `IDLE(0)` waits for `process_next_word & delay_pol`; `CYCLE_BITS(7)` shifts bits on clock edges
- **Bit counter**: counts from `SPI_WORD_LEN-1` down to `0` (MSB first) or `0` up to `SPI_WORD_LEN-1` (LSB first)
- **CPHA=1 first-edge ignore**: `status_ignore_first_edge` flag skips the first sample edge in CPHA=1 mode
- **Master/Slave multiplexing**: Master drives `sclk_out` and `ss_out`; Slave receives `sclk_in` and `ss_in`

## Import Path

```python
from skills.interfaces.spi import (
    SPIModuleModel, SPIClockDividerModel, SPITopModel,
    build_spi_arch,
    spi_module_template, spi_clock_divider_template, spi_top_template,
)
```
