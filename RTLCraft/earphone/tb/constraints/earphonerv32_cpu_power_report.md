# CPU Active Power Report

**Constraint**: CPU active power < 0.5 mW/MHz  
**Target module**: `EarphoneRV32`

## Applied Optimizations

1. **Iterative restoring divider** — replaces combinational divider to reduce area and dynamic power.
2. **Pipeline clock gating** — `core_clk_en = ~core_stall & ~muldiv_busy` freezes registers during stalls/divides.
3. **Multiplier operand isolation** — multiplier output forced to zero when no M-extension instruction is in execute.
4. **ICG insertion** — clock gating cells placed before pipeline register groups.

## RTL Coding Style

```systemverilog
if (core_clk_en) begin
    pc_reg     <= next_pc;
    fetch_valid<= next_fetch_valid;
    // ...
end
```

## Status

Power target remains a design-time assumption until synthesis results are back-annoted.
