# operand_arbiter

## Parameters
- `DEPTH_4_COLLECTORUNIT = $clog2(4*`NUM_COLLECTORUNIT)`

## Ports (10)
- `input [1] clk`
- `input [1] rst_n`
- `input [4*`NUM_COLLECTORUNIT-1:0] arbiter_valid_i`
- `input [`DEPTH_BANK*4*`NUM_COLLECTORUNIT-1:0] arbiter_bankID_i`
- `input [2*4*`NUM_COLLECTORUNIT-1:0] arbiter_rsType_i`
- `input [`DEPTH_REGBANK*4*`NUM_COLLECTORUNIT-1:0] arbiter_rsAddr_i`
- `output [`NUM_BANK-1:0] scalar_valid_o`
- `output [`DEPTH_REGBANK*`NUM_BANK-1:0] scalar_rsAddr_o`
- `output [`NUM_BANK-1:0] vector_valid_o`
- `output [`DEPTH_REGBANK*`NUM_BANK-1:0] vector_rsAddr_o`

## Submodule Instances
- `U_round_robin_arb_scalar`
- `U_one2bin_scalar`
- `U_round_robin_arb_vector`
- `U_one2bin_vector`
