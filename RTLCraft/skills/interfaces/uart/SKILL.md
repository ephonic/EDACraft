# UART — AXI-Stream Serial Interface

## Overview

UART (Universal Asynchronous Receiver/Transmitter) with AXI-Stream interfaces for byte-level data transfer. Supports configurable data width and baud rate via prescale parameter.

## Architecture

```
UART (top)
├── UART_TX — AXI-Stream input → serial TxD output
│   - FSM-less counter-based design
│   - Frame: start(0) + data[N:0] + stop(1)
│   - Baud rate = clk / (prescale × 8)
└── UART_RX — serial RxD input → AXI-Stream output
    - Start bit detection with half-bit sampling
    - Frame error detection (stop bit ≠ 1)
    - Overrun error detection
```

## PE Types

| PE Type | Reference File | Description |
|---------|---------------|-------------|
| uart_tx | uart/rtl/uart_tx.v | Transmitter with prescale-based bit timing |
| uart_rx | uart/rtl/uart_rx.v | Receiver with error detection |
| uart_top | uart/rtl/uart.v | Top-level wrapper |

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| DATA_WIDTH | int | 8 | Data bus width |
| prescale | input[15:0] | — | Baud rate divider |

## Key Design Patterns

- **Counter-based timing**: No explicit FSM states; uses `bit_cnt` and `prescale_reg` for bit timing
- **Frame encoding**: `data_reg` initialized as `{1'b1, s_axis_tdata}` (stop bit + data), then shifted out LSB first
- **Start bit sampling**: RX prescale set to `(prescale << 2) - 2` for half-bit offset sampling
- **Error flags**: `overrun_error` when valid not consumed, `frame_error` when stop bit is 0

## Import Path

```python
from skills.interfaces.uart import (
    UART_TX_Model, UART_RX_Model,
    build_uart_arch,
    uart_tx_template, uart_rx_template, uart_top_template,
)
```
