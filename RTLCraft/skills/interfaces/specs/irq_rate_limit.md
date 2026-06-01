# irq_rate_limit

## Parameters
- `IRQ_INDEX_WIDTH = 11`

## Ports (10)
- `input [1] clk`
- `input [1] rst`
- `input [IRQ_INDEX_WIDTH-1:0] in_irq_index`
- `input [1] in_irq_valid`
- `output [1] in_irq_ready`
- `output [IRQ_INDEX_WIDTH-1:0] out_irq_index`
- `output [1] out_irq_valid`
- `input [1] out_irq_ready`
- `input [15:0] prescale`
- `input [15:0] min_interval`

## Logic Block Types
- seq
