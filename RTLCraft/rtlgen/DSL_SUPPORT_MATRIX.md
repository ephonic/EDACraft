# rtlgen DSL Support Matrix

This document defines the current support level for the single public
authoring surface in `rtlgen`: `rtlgen.dsl`.

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
| Readable RTL analysis | Yes | N/A | N/A | N/A | Yes | Partial | `partial` | Review-profile RTL can be checked for headers, port tables, block labels, generated-name leakage, source-map noise, memory grouping, and clock/reset visibility; this is a readability preflight, not a functional proof |
| Review-profile readability gate | Yes | N/A | N/A | N/A | Yes | Partial | `partial` | `assert_emitted_rtl_contract(...)` and `analyze_emitted_readability(...)` gate representative modules, while compact output may intentionally omit richer review markers |
| Unified diagnostics report | Yes | N/A | N/A | N/A | N/A | Partial | `partial` | Readability, CDC, storage, lowering, and authoring-intent findings can be projected into `DiagnosticFinding` / `DiagnosticReport` with Markdown and JSON rendering |
| Foundation contract preflight | Yes | Partial | N/A | N/A | Partial | Partial | `partial` | `analyze_foundation_contract(...)` combines readability, CDC/reset-release, storage/lowering, emitted-RTL fail-fast checks, and unified reporting for promotion preflight |
| Multi-clock authoring | Yes | Partial | Partial | Partial | Yes | Partial | `partial` | `clock_domain(...)` / `seq_domain(...)` exist at authoring level, including direct `seq_domain("name")` binding, declared reset-domain reuse by name, raw-reset auto-reuse when semantics match a prior declaration, and clearer known-domain diagnostics; closure still requires explicit domain stepping or directed active-domain flows |
| Authored reset semantics preservation | Yes | Partial | Partial | Partial | Yes | Partial | `partial` | Sync and explicit async-low reset styles are preserved, DSL reset-domain specs now exist, and explicitly declared single-clock domain/reset intent now survives lowering; broader reset policy closure is still incomplete |
| `ClockDomainSpec` / `ResetDomainSpec` / `seq_domain(...)` | Yes | Yes | Indirect | Indirect | Indirect | Indirect | `stable` | Authoring-level domain declarations close through lowering, reject conflicting reset-domain semantics earlier, and fail fast on conflicting sequential reset semantics |
| Reset-release safety diagnostics | Yes | Partial | N/A | N/A | N/A | Partial | `partial` | CDC catches common unsafe patterns plus primitive and hand-written multi-stage sync-release structures, but rule coverage is still not complete |
| Reset-release CDC preflight | Yes | Partial | N/A | N/A | N/A | Partial | `partial` | The foundation gate reports raw async reset release as a CDC diagnostic and treats unsafe data crossings as errors; it remains report-oriented rather than formal proof |
| `Memory(..., read_during_write="write_first" | "read_first")` | Yes | Yes | Yes | Yes | Indirect | Yes | `stable` | Same-address read/write policy now closes through lowering, both simulators, and generated Python reference models |
| `Memory(..., read_ports=..., write_ports=..., read_style=..., read_latency=...)` metadata | Yes | Yes | Yes | Yes | Indirect | Partial | `partial` | Storage intent is explicit and preserved; executable lowering closes single-read/single-write async-read zero-latency memories and normalizes sync-read latency-1 memories, while emitted RTL now fails fast outside the single-read/single-write async-read zero-latency subset |
| Storage emitted RTL fail-fast boundary | Yes | Partial | Partial | Partial | Partial | Partial | `partial` | The foundation gate reports unsupported emitted-RTL storage contracts such as multi-port, arbitrary latency, and macro-mapping requests as deliberate fail-fast diagnostics instead of unknown crashes |
| `Memory(..., byte_enable_granularity=...)` and `mem.write(..., byte_enable=...)` metadata | Yes | Yes | Yes | Yes | Indirect | Yes | `stable` | Partial-write intent now closes through lowering, Python sim, compiled sim, emitted RTL, generated Python reference models, and RTL cosim for the executable storage subset |
| Generic storage policy semantics beyond `read_during_write` (byte-enable, port policy, latency) | Partial | Partial | Partial | Partial | Partial | Partial | `partial` | Richer storage contracts are still not fully modeled as first-class semantics |
| `Bundle` / `Interface` / bulk connect helpers | Yes | Partial | Partial | Partial | Partial | Partial | `partial` | Useful authoring helpers, but not every interface pattern has full structured downstream coverage |
| Protocol bundles (`ReadyValid`, `ReqRsp`, `AXI4*`, `APB`, `Wishbone`, `AHBLite`) | Yes | Partial | Partial | Partial | Partial | Partial | `partial` | `ReadyValid`, `ReqRsp`, `APB`, `AXI4Lite`, and `Wishbone` now expose clearer protocol-aware port-map/sequence/reference-model helpers; APB, AXI-Lite, and Wishbone reference models now honor byte-lane writes (`pstrb` / `wstrb` / `sel_i`), and Wishbone now has an explicit registered-ack helper path for stdlib slaves, but full protocol semantics are still not yet a uniform downstream contract across every downstream consumer |
| Library structures (`FSM`, `Pipeline`, `SkidBuffer`, `ReadyValidRegister`, `ReadyValidFIFO`, `ReqRspQueue`, `APBRegisterBank`, `AXI4LiteRegisterBank`, `WishboneRegisterBank`, `SyncFIFO`, `AsyncFIFO`) | Yes | Partial | Partial | Partial | Partial | Partial | `partial` | Common patterns exist and some are regression-covered; `SkidBuffer`, `ReadyValidRegister`, `ReadyValidFIFO`, `ReqRspQueue`, `APBRegisterBank`, `AXI4LiteRegisterBank`, and `WishboneRegisterBank` now have explicit lowering + Python-UVM coverage, but a broader component contract is still not yet uniform across every downstream consumer |
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
path that `rtlgen` expects users to rely on:

1. it can be authored in `rtlgen.dsl`
2. it lowers without special-case escape hatches
3. it executes consistently in the Python simulator
4. it executes consistently in the compiled C++ simulator
5. it emits RTL consistently when RTL export is part of the feature story
6. the relevant analysis and verification helpers can consume it without
   requiring users to drop down to ad hoc internal IR handling
