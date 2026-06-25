# rtlgen_x DSL Semantic Contract

This document describes the canonical semantic contract for `rtlgen_x.dsl`.

The goal is not to describe every implementation detail. The goal is to define
which authored objects are primary, how they flow into the executable stack,
and where the current boundaries are.

## 1. The one public authoring surface

`rtlgen_x.dsl` is the only supported high-level authoring surface in
`rtlgen_x`.

Three related objects appear in the implementation:

1. DSL `Module`: the authored design object
2. `LoweredDslModule`: a debug/inspection wrapper around lowering output
3. `SimModule`: the internal executable model

Their roles are different:

- author and edit designs as DSL `Module`
- inspect lowering results through `LoweredDslModule`
- treat raw `SimModule` as an internal or expert-only low-level executable IR

Public verify, PPA, and UVM APIs are DSL-facing. They are expected to receive:

1. the original DSL `Module`, or
2. a `LoweredDslModule`

They intentionally reject raw `SimModule` so callers do not accidentally bypass
the authoring-level semantic boundary.

## 2. Canonical execution path

The intended detailed-design path is:

```text
DSL Module
  -> elaboration / flattening
  -> lower_dsl_module_to_sim(...)
  -> LoweredDslModule(module=SimModule, report=...)
  -> PythonSimulator / CompiledSimulator
  -> verify / PPA / cosim / collateral generation
```

This means the executable semantics of the DSL are defined by the lowered
`SimModule` plus the runtimes that consume it.

## 3. Elaboration and flattening

Lowering assumes a flattened design view.

Current contract:

1. lowering may flatten the module before building the executable model
2. unsupported top-level statement forms fail fast during lowering
3. behavioral callbacks and black-box callback modules are outside the
   supported lowering subset

If a construct cannot be flattened and lowered into the canonical executable
model, it is not part of the stable round-trip contract.

## 4. Process semantics

The DSL currently defines four main process styles.

### 4.1 Combinational

`@comb` and top-level combinational statements become `phase="comb"`
assignments in the executable model.

Contract:

1. combinational dependencies are topologically ordered during lowering
2. outputs recompute from the combinational graph in the runtimes
3. combinational logic must not rely on hidden scheduling beyond the explicit
   dependency graph

### 4.2 Sequential

`@seq(clk, rst)` blocks become `phase="seq"` assignments in the executable
model and are tied to one clock domain.

Contract:

1. each lowered sequential assignment belongs to one explicit clock domain
2. sequential assignment targets must be legal stateful objects
3. conflicting reset semantics on the same clock domain fail fast

### 4.3 Latch

`with self.latch:` becomes `phase="latch"` in the executable model.

Contract:

1. latch intent is preserved through lowering
2. Python and compiled runtimes both model latch update/hold behavior
3. emitted RTL preserves latch intent with `always_latch` on the supported
   export path

### 4.4 Initialization

`with self.init:` contributes initial values for state and storage.

Contract:

1. register initialization can propagate into lowered state init values
2. memory initialization can propagate into lowered memory contents
3. emitted RTL preserves supported initialization forms used by the current
   DSL storage path

## 5. Expression and assignment semantics

The stable executable subset includes:

1. constants and references
2. unary and binary operations in the supported lowering set
3. muxes
4. concatenation
5. supported bit/slice/part-select reads and writes
6. memory reads and writes in the supported storage subset

Important current rules:

1. nested slice chains are normalized during lowering/emission
2. multiply lowering preserves full product width rather than truncating to the
   widest operand width
3. unsupported expression forms fail fast through `DslLoweringError`
4. DSL values are not valid Python booleans: authored hardware conditions must
   stay inside the DSL surface rather than falling back to Python truthiness

### 5.1 Python syntax boundary

The DSL is embedded in Python, but not every Python expression form is a valid
hardware-authoring construct.

Authoring contract:

1. do not use `if sig:` or `while sig:` on DSL `Signal` / `Expr` objects
2. do not use Python `and` / `or` / `not` on DSL values
3. do not use Python ternary expressions such as `a if cond else b` when
   `cond` is a DSL value
4. do not rely on Python container truthiness for DSL objects such as
   `Array`, `ArrayProxy`, `MemProxy`, `Vector`, or `Parameter`

Use these DSL forms instead:

1. `with If(cond):` / `with Else():` for hardware control flow
2. `a & b`, `a | b`, `~a` for bitwise logic
3. `Mux(cond, a, b)` for value selection
4. explicit index/read/compare expressions for array and memory elements

This boundary is enforced intentionally so Python cannot silently consume a DSL
condition before lowering or emitted-RTL checks ever see it.

## 6. Clock and reset semantics

Clock and reset semantics now have a DSL-facing authoring layer through
`ClockDomainSpec`, `ResetDomainSpec`, `clock_domain(...)`, and
`seq_domain(...)`, but the full storage/reset-policy story is still not fully
normalized.

Current contract:

1. clock-domain membership is carried into the lowered executable model
2. author-declared domain specs must agree with observed sequential-block reset
   semantics during lowering
3. reusing one reset signal with conflicting declared semantics is rejected at
   the DSL declaration layer rather than deferred to later phases
4. domain-name lookup failures report the currently known declared domains to
   keep multi-clock authoring errors local and actionable
5. explicitly declared single-clock domain intent is preserved through lowering
   rather than being discarded as unnamed default timing
6. sync and explicit async-low reset styles are preserved on the supported RTL
   export path
7. multi-clock execution is explicit: callers must use domain-aware stepping
   rather than assuming an implicit schedule
8. CDC and reset-release analysis are report-oriented: the tools describe the
   issue and point at likely fixes, including recognized primitive and
   hand-written sync patterns, but they do not rewrite the DSL

Multi-clock implications:

1. `step(...)` is the normal single-clock execution path
2. `step_clocks(...)` is the explicit multi-clock execution path
3. public multi-clock verification flows require explicit event/domain
   annotation such as `active_domains`

## 7. Storage semantics

Storage semantics are available, but still not fully normalized into a rich
first-class storage contract.

What is already part of the current contract:

1. arrays and memories can lower into executable storage objects
2. memory writes carry explicit write intent into the runtimes
3. supported initialization data can stay aligned between lowering and emitted
   RTL
4. `Memory(..., read_during_write="write_first" | "read_first")` is preserved
   through lowering, Python simulation, compiled simulation, and generated
   Python reference models
5. `Memory(..., read_ports=..., write_ports=..., read_style=..., read_latency=...)`
   is now explicit authoring/runtime metadata, and unsupported executable
   storage shapes fail fast instead of silently collapsing into the default
   comb-read / seq-write model; the executable lowering path now also
   normalizes single-read/single-write `read_style="sync"/read_latency=1`
   memories into explicit sampled state
6. `Memory(..., byte_enable_granularity=...)` and
   `mem.write(..., byte_enable=...)` now make partial-write intent explicit and
   close across authoring, lowering, Python execution, compiled execution,
   emitted RTL, generated reference-model rendering, and RTL cosim for the
   executable storage subset

What is still incomplete:

1. full executable closure for richer port-count, style, latency, and macro
   mapping policy
2. richer storage-port shape behavior beyond the current comb-read / seq-write
   executable subset
3. emitted RTL closure for sync-read memories without requiring authors to
   write the sampled-output structure explicitly themselves

These remaining gaps are why generic storage policy is still marked `partial`
in the support matrix even though `read_during_write` and byte-enable writes
are now closed in the main executable subset, and `sync-read/read_latency=1`
is executable through lowering.

## 8. Verification and analysis contract

The DSL is meant to feed the rest of `rtlgen_x` without forcing users to manage
another public IR.

Current contract:

1. directed/streaming verification helpers are DSL-facing
2. Python-UVM helpers are DSL-facing
3. generated SV/UVM collateral helpers are DSL-facing
4. module-side PPA helpers are DSL-facing
5. CDC analysis is DSL-facing

Low-level exceptions remain by design:

1. `PythonSimulator` and `CompiledSimulator` operate on executable models
2. architecture inference helpers operate on executable models
3. rewrite helpers operate on executable models

This separation is intentional. It keeps the public design loop centered on the
authored DSL while still exposing low-level runtime hooks for expert workflows.

## 9. Source mapping contract

`rtlgen_x` is expected to preserve enough source identity that findings can be
fed back into the authored design.

Current contract:

1. lowering records assignment source file and source line when available
2. CDC findings try to report source/destination sites
3. PPA findings try to report assignment targets, storage hotspots, and source
   locations
4. verification traces and generated collateral are expected to stay close
   enough to the authored structure that failures remain actionable

This source mapping is part of why DSL authoring is valuable relative to plain
RTL text editing.

## 10. Stability rule

A feature should only be treated as stable when the same authored construct can
survive the main closure path without ad hoc escape hatches:

1. author in DSL
2. lower into the canonical executable model
3. execute in Python
4. execute in compiled C++
5. emit RTL when applicable
6. be consumed by the relevant verify/PPA/CDC/UVM helper

If any of those steps currently require special handling, the feature should be
documented as `partial`, `experimental`, or `unsupported` rather than being
presented as fully closed.

## 11. Authoring intent gate

Some patterns are not merely "discouraged style"; they violate the intended
DSL authoring model strongly enough that the public lowering / emission
surfaces reject them.

Current hard-reject set:

1. assigning a `Reg` in `@comb`
2. assigning an `Output` directly in `@seq`
3. illegal hierarchical writes into non-port child state
4. illegal hierarchical reads from non-port child state

This is intentional. The goal is to keep both humans and agents inside the DSL
contract instead of letting structurally ambiguous or semantically misleading
authoring patterns drift deeper into lowering, simulation, or emitted RTL.
