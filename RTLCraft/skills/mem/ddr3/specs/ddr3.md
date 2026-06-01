# ddr3

## Parameters
- `check_strict_mrbits = 1`
- `check_strict_timing = 0`
- `feature_pasr = 1`
- `feature_truebl4 = 0`
- `feature_odt_hi = 0`
- `PERTCKAVG = TDLLK`
- `LOAD_MODE = 4'b0000`
- `RFF_BITS = DQ_BITS*BL_MAX`
- `RFF_CHUNK = 8 * (RFF_BITS/32 + (RFF_BITS%32 ? 1 : 0))`
- `SAME_BANK = 2'd0`
- `DIFF_BANK = 2'd1`
- `DIFF_GROUP = 2'd2`
- `SIMUL_500US = 500`
- `SIMUL_200US = 200`

## Logic Block Types
- seq
- seq_async_reset
