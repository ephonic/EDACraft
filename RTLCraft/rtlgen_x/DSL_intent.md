# rtlgen_x DSL Intent

This document explains the intended role of the Python DSL in `rtlgen_x`.

It is not an API reference and not a complete semantic contract. Those belong
in [DSL_SEMANTICS.md](./DSL_SEMANTICS.md) and
[DSL_SUPPORT_MATRIX.md](./DSL_SUPPORT_MATRIX.md).

The goal here is simpler: explain why the DSL exists, where it is genuinely
useful, and where it is the wrong tool.

## 1. Core position

The Python DSL is not meant to replace all Verilog.

It is meant to be a programmable design-intent layer that works well with:

1. generated structure
2. executable simulation
3. reference models and verification
4. agent-driven modification
5. analysis and reporting

If the DSL cannot help with those things, it does not justify its own
existence.

## 2. What the DSL is good at

### 2.1 Design families, not just one-off modules

The DSL is strongest when one piece of source code describes a family of
related structures rather than one frozen concrete implementation.

Typical examples:

1. queues, FIFOs, register slices, skid buffers
2. parameterized pipelines
3. protocol wrappers and adapters
4. reusable control-plane blocks
5. generated datapaths with width / depth / stage-count variation

In those cases, the DSL is more valuable than plain Verilog because the source
code is acting as a generator, not only as one final RTL snapshot.

### 2.2 Tight connection to executable behavior

The DSL is designed to connect quickly to the executable model stack:

```text
DSL Module
  -> lowering
  -> Python / C++ simulation
  -> verification / cosim / collateral generation
  -> analysis
```

That matters because the useful artifact is not only emitted RTL. The useful
artifact is also:

1. runnable behavior
2. replayable tests
3. reference-model alignment
4. analysis hooks such as CDC / PPA / readability

This is one of the main advantages over writing only Verilog text first and
trying to bolt everything else on later.

### 2.3 Agent-friendly structural editing

For an agent, a DSL object model is easier to reason about and transform than
raw RTL text.

The DSL is therefore a better surface for:

1. inserting pipeline stages
2. swapping buffering strategies
3. generating wrappers and harnesses
4. building protocol-aware collateral
5. applying structural rewrites across a design family

This does not mean the DSL automatically creates better hardware. It means the
design surface is easier for automation to inspect and modify safely.

### 2.4 Explicit authoring contract

The DSL can reject patterns that are semantically misleading or contrary to the
intended hardware-authoring model.

Examples include:

1. falling back to Python truthiness on DSL values
2. writing a `Reg` in `@comb`
3. writing an `Output` directly in `@seq`
4. illegal hierarchical access into child internal state

This is valuable because the DSL can act as a constrained authoring surface
instead of a loose scripting layer.

### 2.5 Standard-library leverage

A DSL standard library can package more than just emitted RTL shape. It can
package:

1. executable semantics
2. expected protocol behavior
3. verification helpers
4. analysis hooks
5. readable parameterization patterns

That makes the DSL a good foundation for reusable protocol bundles, buffering
blocks, CDC helpers, and other structured hardware building blocks.

## 3. What the DSL is not good at

### 3.1 It is not a universal replacement for hand-written RTL

The DSL should not be forced onto every design.

It is usually a poor fit for:

1. mature legacy Verilog / SystemVerilog IP
2. heavily hand-optimized timing-critical RTL
3. vendor-specific primitive wrappers and macro-heavy designs
4. large existing SoC subsystems that already live naturally in RTL

In those cases, trying to rewrite everything into the DSL usually increases
friction more than it creates value.

### 3.2 It does not automatically produce better PPA

The DSL is not better than Verilog simply because it emits Verilog.

It does not guarantee:

1. better timing
2. better area
3. better power
4. more readable final RTL

Those outcomes still depend on the actual structure authored in the DSL and on
the quality of the emitted RTL patterns.

### 3.3 It is not the right place to absorb arbitrary external RTL

Existing Verilog assets should generally be reused at the RTL simulator /
UVM / cosim boundary, not forcibly translated into the executable DSL model.

That means the DSL should coexist with external RTL rather than pretending it
must subsume it all.

## 4. Where the DSL should be preferred

The DSL should usually be the first choice for:

1. new reusable components
2. generated wrappers and adapters
3. protocol-centric control blocks
4. family-style datapath generators
5. verification-oriented harnessable modules
6. places where agent-driven structural rewriting is expected

## 5. Where existing Verilog should be preferred

Existing RTL should usually remain first-class for:

1. already-validated IP blocks
2. macro-bound RAM / DSP / PHY / vendor primitive wrappers
3. timing-tuned or floorplan-sensitive hand-authored modules
4. designs whose main value is already captured in stable RTL source

In those cases, the DSL should provide glue, wrappers, reference models,
stimulus generation, or verification collateral around the RTL rather than
replacing it.

## 6. Practical value statement

The DSL is worth keeping only if it helps reduce real engineering cost in at
least one of these ways:

1. fewer handwritten repetitive structures
2. faster design-verify-analyze iteration
3. better automation leverage for agents
4. more reusable standard-library components
5. clearer authoring constraints than raw Python or ad hoc code generation

If a block is simply easier to express and maintain as plain Verilog, that is a
valid outcome. The DSL should not be used out of ideology.

## 7. Bottom line

The Python DSL is best understood as:

1. a programmable hardware-intent layer
2. a generator surface for design families
3. a bridge to simulation, verification, and analysis
4. an agent-friendly structural editing surface

It is not best understood as:

1. a universal Verilog replacement
2. a guarantee of better emitted RTL
3. a reason to discard existing RTL assets

The project should therefore judge the DSL by whether it improves closure,
reuse, and automation around hardware design, not by whether it can express
every possible RTL style.
