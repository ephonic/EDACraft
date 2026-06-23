# rtlgen_x DSL Support Matrix

This document defines the current support level for the single public
authoring surface in `rtlgen_x`: `rtlgen_x.dsl`.

It is intentionally conservative. A construct is marked `stable` only when the
current codebase and tests exercise a real round trip through the intended
consumers. If a feature can be authored but is not yet uniformly closed across
lowering, simulation, emitted RTL, and analysis, it is marked `partial`.

## Status levels

- `stable`: recommended for normal design authoring and expected to close the
  main loop
- `partial`: usable with clear boundaries or reduced downstream coverage
- `experimental`: exposed for exploration, but not yet a dependable design
  surface
- `unsupported`: not part of the supported round-trip path

## Public surface roles

| Surface | Status | Intended use | Notes |
| --- | --- | --- | --- |
| DSL `Module` | `stable` | Main user-facing authoring surface | Preferred input to public verify, PPA, and UVM APIs |
| `LoweredDslModule` | `stable` | Debug/inspection wrapper around lowering output | Accepted by many public DSL-facing helpers, but not the preferred authored object |
| raw `SimModule` | `stable` for low-level internals only | Internal executable model and expert-only low-level helper input | Public verify/PPA/UVM APIs intentionally reject raw `SimModule` |

## Main round-trip coverage

| Construct / capability | Authoring | Lowering | Python sim | C++ sim | Emitted RTL | Verify / PPA / UVM | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Module`, `Input`, `Output`, `Reg`, `Wire`, `Array` | Yes | Yes | Yes | Yes | Yes | Yes | `stable` | Baseline authoring path |
| `If` / `Else` / `Elif` / `Switch` / `When` | Yes | Yes | Yes | Yes | Yes | Yes | `stable` | Control trees are part of the tested lowering subset |
| Single-clock `@comb` + `@seq` | Yes | Yes | Yes | Yes | Yes | Yes | `stable` | Main closure path |
| `with self.latch:` | Yes | Yes | Yes | Yes | Yes | Yes | `stable` | Lowered as latch-phase state and emitted as `always_latch` |
| `with self.init:` register and memory initialization | Yes | Yes | Yes | Yes | Yes | Yes | `stable` | Includes `Memory(..., init_data=...)` propagation |
| Bit/slice/part-select updates | Yes | Yes | Yes | Yes | Yes | Yes | `stable` | Includes nested slice flattening and fallback emit paths |
| Arithmetic and signed operations in the tested lowering subset | Yes | Yes | Yes | Yes | Yes | Yes | `stable` | Includes full-width multiply preservation and arithmetic right shift |
| Source-mapped assignment metadata | Yes | Yes | Yes | Yes | N/A | Yes | `stable` | Findings can point back to assignment targets and source locations |
| Multi-clock authoring | Yes | Partial | Partial | Partial | Yes | Partial | `partial` | `clock_domain(...)` / `seq_domain(...)` exist at authoring level; closure still requires explicit domain stepping or directed active-domain flows |
| Authored reset semantics preservation | Yes | Partial | Partial | Partial | Yes | Partial | `partial` | Sync and explicit async-low reset styles are preserved, and DSL reset-domain specs now exist, but broader reset policy closure is still incomplete |
| `ClockDomainSpec` / `ResetDomainSpec` / `seq_domain(...)` | Yes | Yes | Indirect | Indirect | Indirect | Indirect | `stable` | Authoring-level domain declarations close through lowering and fail fast on conflicting sequential reset semantics |
| Reset-release safety diagnostics | Yes | Partial | N/A | N/A | N/A | Partial | `partial` | CDC catches common unsafe patterns plus primitive and hand-written multi-stage sync-release structures, but rule coverage is still not complete |
| `Memory(..., read_during_write="write_first" | "read_first")` | Yes | Yes | Yes | Yes | Indirect | Yes | `stable` | Same-address read/write policy now closes through lowering, both simulators, and generated Python reference models |
| `Memory(..., read_ports=..., write_ports=..., read_style=..., read_latency=...)` metadata | Yes | Yes | Yes | Yes | Indirect | Partial | `partial` | Storage intent is now explicit and preserved, but the executable subset still only closes single-read/single-write async-read zero-latency memories |
| `Memory(..., byte_enable_granularity=...)` and `mem.write(..., byte_enable=...)` metadata | Yes | Yes | Yes | Partial | Indirect | Partial | `partial` | Partial-write intent is now explicit and preserved, generated Python reference models render it, and non-closed backends fail fast instead of silently degrading it |
| Generic storage policy semantics beyond `read_during_write` (byte-enable, port policy, latency) | Partial | Partial | Partial | Partial | Partial | Partial | `partial` | Richer storage contracts are still not fully modeled as first-class semantics |
| `Bundle` / `Interface` / bulk connect helpers | Yes | Partial | Partial | Partial | Partial | Partial | `partial` | Useful authoring helpers, but not every interface pattern has full structured downstream coverage |
| Protocol bundles (`AXI4*`, `APB`, `Wishbone`, `AHBLite`) | Yes | Partial | Partial | Partial | Partial | Partial | `partial` | Public verification helpers support several protocol flows, but protocol abstraction is not yet a fully uniform semantic layer |
| Library structures (`FSM`, `Pipeline`, `SyncFIFO`, `AsyncFIFO`) | Yes | Partial | Partial | Partial | Partial | Partial | `partial` | Common patterns exist and some are regression-covered, but support is not yet expressed as a formal contract for every downstream consumer |
| `SinglePortRAM`, `SimpleDualPortRAM` helper modules | Yes | Partial | Partial | Partial | Yes | Partial | `partial` | Available as library authoring helpers; they currently inherit the executable storage subset rather than a full macro policy contract |
| `BehavioralModule` / behavioral callbacks through executable lowering | Yes | No | No | No | Partial | No | `unsupported` | Lowering rejects behavioral callback modules |
| `BlackBoxModule` callbacks through executable lowering | Yes | No | No | No | Partial | No | `unsupported` | Lowering rejects black-box callback modules |

## Multi-clock closure snapshot

| Surface | Single-clock | Multi-clock | Notes |
| --- | --- | --- | --- |
| DSL authoring | Yes | Yes | Multiple domains can be authored today |
| `lower_dsl_module_to_sim(...)` | Yes | Partial | Fails fast on conflicting reset semantics for the same domain |
| `PythonSimulator` | Yes | Partial | Multi-clock uses explicit `step_clocks(...)` |
| `CompiledSimulator` | Yes | Partial | Multi-clock uses explicit `step_clocks(...)` |
| `run_python_uvm_test(...)` | Yes | Partial | Multi-clock requires explicit `active_domains` in each sequence item |
| Generated Python reference model | Yes | Partial | Multi-clock uses explicit `predict_clocks(...)` |
| Generated SV/UVM collateral | Yes | Partial | Supported only for directed event-style sequences with explicit `active_domains` |
| Emitted RTL for external simulators | Yes | Yes | Preferred closure path for broader multi-clock verification |

## Guidance for users and agents

Use these rules when deciding what to pass into a tool:

1. pass the original DSL `Module` to public verify, PPA, and UVM helpers
2. pass `LoweredDslModule` only when you already have it from a prior lowering
   step and want to keep the lowering report attached
3. pass raw `SimModule` only to low-level executable helpers such as
   `PythonSimulator`, `CompiledSimulator`, architecture inference helpers, or
   rewrite helpers that are explicitly documented as executable-model APIs

## What counts as stable

A DSL feature should be treated as `stable` only when it closes the same main
path that `rtlgen_x` expects users to rely on:

1. it can be authored in `rtlgen_x.dsl`
2. it lowers without special-case escape hatches
3. it executes consistently in the Python simulator
4. it executes consistently in the compiled C++ simulator
5. it emits RTL consistently when RTL export is part of the feature story
6. the relevant analysis and verification helpers can consume it without
   requiring users to drop down to ad hoc internal IR handling
