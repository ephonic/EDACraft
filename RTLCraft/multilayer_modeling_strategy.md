# Multi-Layer Modeling Strategy For Professional CPU Generation

## Why this matters

Yes: making the models and modules more fine-grained, with stepwise lowering and verification at each layer, is one of the clearest ways to make the system more professional.

The current flow already has the right ingredients:

- skills
- architecture templates
- behavioral models
- skeleton generation
- DSL modules
- PPA / lint / RTL emission

But to become genuinely professional, these pieces need to be organized as an explicit multi-layer contract system rather than only a code generation pipeline.

The key shift is:

- not "let the agent directly generate RTL from a prompt"
- but "let the agent operate inside a constrained layered model, where every lowering step has an interface, invariants, and verification targets"


## What "more professional" means here

For this project, a more professional CPU generation framework should have these properties:

1. Stable abstraction boundaries
2. Progressive lowering from intent to implementation
3. Machine-checkable contracts between layers
4. Reusable domain knowledge captured in skills
5. Agent freedom only inside bounded local decisions
6. Verification attached to each layer, not only final RTL

This matters because high-end CPU design is not merely "more modules". It is:

- decomposition discipline
- traceable refinement
- constrained synthesis
- local correctness before global integration


## Recommended layer stack

We should model the system as at least 6 layers.

### L0. Product / design intent

This is the user-visible goal layer.

Examples:

- "4-core 64-bit RISC-V OoO processor"
- "high-performance cluster with private L1 and shared L2"
- "area-optimized edge CPU"

This layer should define:

- target workload
- target performance envelope
- target power / area direction
- required ISA / privilege / memory features
- required verification confidence

This layer should not contain implementation details.


### L1. Architectural contract

This should be the current `arch_templates` / `arch_def` style layer, but stricter.

It should define:

- block graph
- module roles
- visible interfaces
- latency budget
- throughput budget
- memory hierarchy topology
- coherence topology
- core count / cluster count / cache sharing

Examples:

- `Frontend`
- `DecodeRename`
- `Dispatch`
- `Issue`
- `Backend`
- `Commit`
- `L1I`
- `L1D`
- `Directory`
- `L2Slice`
- `MeshTop`

At this layer, each module should expose:

- inputs / outputs
- protocol type
- timing assumptions
- architectural invariants


### L2. Executable behavioral model

This layer should answer:

- what the module does
- what state it owns
- what ordering rules it must preserve

This is where cycle-level and functional models belong.

Examples:

- branch predictor update rules
- rename map / freelist semantics
- ROB ordering semantics
- LSU ordering and replay semantics
- coherence request / probe / grant semantics

Every L1 module should have an L2 reference model, even if simplified.


### L3. Structured microarchitecture DSL

This is the main generation layer.

It should describe:

- submodule composition
- pipeline registers
- queues / arrays / metadata
- arbitration and hazard logic
- stage-to-stage handoff

Important point:

L3 should not be free-form natural language. It should be structured and typed enough that the agent cannot casually violate module boundaries.

For CPU blocks, L3 should include:

- stage-local state
- pipeline handshakes
- valid / ready / replay semantics
- exceptions / flush / redirect hooks
- width / depth / queue sizing


### L4. Lowered implementation skeleton

This layer should be closer to synthesizable RTL structure, but still partially schematic.

It should resolve:

- exact pipeline cut placement
- local wires / regs / arrays
- concrete submodule instantiation
- mux / select / wakeup topology
- reset and init behavior

This is where we should expect agent assistance, but with strong constraints from L3.


### L5. Final RTL

This is the emitted Verilog / SystemVerilog layer.

It should be judged on:

- lint
- synthesis sanity
- interface correctness
- structural completeness
- consistency with upstream models


## Why stepwise lowering improves professionalism

Stepwise lowering helps in five concrete ways.

### 1. It localizes errors

If the final RTL is wrong, we can ask:

- was the architecture wrong?
- was the behavior wrong?
- was the DSL composition wrong?
- was the lowering wrong?

Without layers, every failure becomes "the generated RTL looks weird".


### 2. It constrains the agent

Agents are useful, but unconstrained generation drifts.

If an agent is only allowed to refine:

- one module at a time
- from one typed layer to the next
- under existing contracts

then the agent becomes much more reliable.


### 3. It makes verification compositional

Each layer can have its own checks:

- L1: topology and interface checks
- L2: behavior simulation and invariants
- L3: DSL shape / handshake / width checks
- L4: structural checks
- L5: lint / synthesis / equivalence-style checks


### 4. It allows better reuse

The same `Frontend` architecture can target:

- an in-order core
- a 2-wide OoO core
- a 6-wide OoO core

if the contracts are explicit.


### 5. It separates knowledge from search

This is the biggest answer to your question about skills vs agent.

- skills should hold knowledge
- the agent should perform bounded search and refinement


## Per-layer and per-module objective driving

This is not optional. It is one of the main mechanisms that makes local optimization meaningful.

If a module has no explicit local objectives, then:

- the agent does not know what tradeoff to optimize
- verification can only say pass/fail, not better/worse
- local edits cannot be ranked
- the design drifts toward arbitrary structure

So every layer and every submodule should carry both:

- functional objectives
- performance objectives

This is what lets optimization stay local without becoming blind.


### Functional objectives

Functional objectives answer:

- what must this module do correctly
- what architectural semantics must it preserve
- what corner cases must it handle

Examples:

- `FrontendUnit`: fetch correct instruction bytes under redirect
- `DecodeRenameUnit`: preserve destination register semantics and never double-allocate a phys reg
- `BackendUnit`: preserve enqueue/issue/retire ordering rules
- `CommitUnit`: retire only completed instructions and update visible architectural state in order
- `CoherenceDir`: never grant conflicting ownership states


### Performance objectives

Performance objectives answer:

- what should this module optimize for locally
- what timing or throughput pressure it sits under
- what structural cost it is allowed to spend

Examples:

- `FrontendUnit`: 1 fetch request per cycle, bounded redirect penalty
- `DecodeRenameUnit`: sustain rename throughput target under no-stall conditions
- `IssueQueue`: bounded wakeup-select depth, bounded entry count, issue rate target
- `BackendUnit`: keep ROB full rate below threshold, avoid LSU becoming dominant bottleneck
- `L2CacheSlice`: hit latency target, refill overlap target


### Why local objectives are essential

The project goal is global, but optimization must usually happen locally.

That only works if each module exposes a local scorecard.

Otherwise "optimize the design" becomes under-specified.

With local objectives, the agent can do something much more disciplined:

- change one module
- measure local effect
- check contract compliance
- accept or reject the change

That is a much more professional loop than:

- change RTL
- hope top-level PPA improves


## Recommended local scorecard per module

Each module should carry a scorecard with at least these fields:

1. functional invariants
2. latency target
3. throughput target
4. structural budget
5. observability hooks
6. allowed optimization knobs


### 1. Functional invariants

Examples:

- no duplicate allocation
- in-order retirement
- no dropped valid handshake
- no illegal coherence transition


### 2. Latency target

Examples:

- max 1 cycle decode stage
- max 2 cycles branch redirect visible at fetch
- max N cycles L2 hit response


### 3. Throughput target

Examples:

- 1 fetch bundle / cycle
- 2 rename ops / cycle
- 4 issue ops / cycle
- 1 directory grant / cycle


### 4. Structural budget

Examples:

- max logic depth
- max queue depth
- max array ports
- max state bits

This prevents a local optimization from becoming structurally unreasonable.


### 5. Observability hooks

A module should expose counters or trace points for what matters locally.

Examples:

- stall cycles
- replay count
- queue occupancy histogram
- rename freelist low-watermark
- branch redirect count

Without observability, performance objectives are hard to verify.


### 6. Allowed optimization knobs

This is the constraint side.

Examples:

- queue depth may vary between 16 and 48
- pipeline split allowed between wakeup and select
- branch predictor table size may scale
- resource sharing allowed or forbidden

This is important because it tells the agent not only what to improve, but what moves are legal.


## How this helps the agent

If every module has a local objective bundle, the agent can work like a constrained optimizer.

For one module, the workflow becomes:

1. read contract
2. read local scorecard
3. refine implementation
4. run local verification
5. compare scorecard metrics
6. keep or reject the change

That is much closer to real engineering than unconstrained code generation.


## What should live in skills versus generated artifacts

This objective system should be split carefully.

### Skills should define the canonical objectives

Skills should provide:

- default invariants
- typical latency/throughput targets
- legal optimization knobs
- recommended observability points

This makes the agent start from domain truth, not from a blank slate.


### Generated artifacts should hold instance-specific objectives

Artifacts produced for one design instance should record:

- chosen width / depth / topology
- active performance targets
- overridden local budgets
- current measured metrics

So:

- skills provide priors
- artifacts provide instantiated intent


## The practical rule

For every layer and every submodule, require:

- one correctness story
- one performance story
- one verification story

If one of these is missing, the module is under-specified.


## Strong recommendation

The framework should evolve so that no module is considered "ready for lowering" unless it has:

- contract
- local functional invariants
- local performance targets
- local verification hooks

That is the point where optimization becomes principled and remains local.


## Skills vs agent: who should provide what?

This should be made very explicit.

### Skills should provide stable domain knowledge

Skills are the right place for:

- architecture templates
- protocol definitions
- interface standards
- verified behavioral models
- canonical module decompositions
- known-good lowering recipes
- verification templates
- PPA heuristics

In other words:

skills should contain the "design grammar" of the domain.

For CPU generation, skills should know things like:

- what a rename stage must preserve
- what a ROB must guarantee
- how LSU interacts with memory ordering
- how branch redirect flows upstream
- what a legal cache-coherence interaction looks like


### The agent should provide controlled synthesis of details

The agent is best used for:

- filling in one module implementation under a contract
- selecting between a few legal architectural variants
- refining queue depths / widths / partitioning
- repairing violations discovered by lint / simulation / invariants
- generating missing glue logic between already-specified blocks

The agent should not be the only source of architectural truth.

If the agent invents architecture and implementation at the same time, quality will be unstable.


## The practical rule

Use this rule:

- skills define what is legal
- agent chooses among legal possibilities

That gives us both flexibility and discipline.


## How to build a stronger multi-layer model

Here is the most important recommendation:

### Make every module carry a contract bundle

For each module, we should store:

1. role
2. interface
3. state model
4. timing contract
5. refinement obligations
6. verification checklist

For example, for `DecodeRenameUnit`:

- role: decode fetched instructions and allocate physical destinations
- interface: fetched valid/instr in, renamed uops out
- state: rename map, freelist snapshot or rename side effects
- timing: one-cycle decode+rename, backpressure if rename resources exhausted
- refinement obligations:
  - preserve decoded rd semantics
  - no duplicate phys register allocation
  - legal flush rollback hook
- verification checklist:
  - unique phys rd on consecutive allocations
  - reset state correctness
  - no rename_done when fetch_valid is low


## Recommended project direction

To make this framework significantly more professional, we should evolve toward the following flow.

### A. Promote modules to first-class refinement units

Instead of one big core generator, every module should be lowered independently:

- `Frontend`
- `DecodeRename`
- `Dispatch`
- `Issue`
- `Execute`
- `ROB`
- `LSU`
- `Commit`
- `ClusterTop`
- `MeshTop`

Each module should have:

- architecture spec
- behavior model
- DSL implementation
- local tests


### B. Add formal layer transitions

Every lowering step should produce artifacts:

- L1 -> L2: behavior obligations
- L2 -> L3: state / interface mapping
- L3 -> L4: concrete pipeline structure
- L4 -> L5: RTL + lint + trace map

These transitions should be explicit files or objects, not hidden in prompt context.


### C. Use the agent as a refinement worker, not an unconstrained designer

Example workflow:

1. skill defines `DecodeRenameUnit` contract
2. agent generates or edits only that module
3. verifier checks local invariants
4. only then allow integration into `OoOCore`


### D. Attach verification to every module

For each module we should generate:

- reset tests
- protocol tests
- width / structural checks
- behavior cross-checks
- local lint gate

For some modules:

- queue conservation checks
- no-double-allocation checks
- monotonic ordering checks
- flush / rollback checks


### E. Maintain a canonical decomposition library

This is where skills become extremely valuable.

We should have a library of canonical decompositions such as:

- in-order RV64 core
- 2-wide OoO core
- 4-wide OoO core
- directory-based 4-core cluster
- tiled mesh interconnect

Each decomposition should include:

- architecture
- contracts
- behavior reference
- DSL template
- verification recipes


## What we should avoid

There are three traps to avoid.

### Trap 1. Letting the agent infer all hidden assumptions

If assumptions only live in prompt text, generation quality will vary too much.


### Trap 2. Jumping directly from high-level intent to RTL

That usually produces plausible-looking but weakly grounded designs.


### Trap 3. Using skills only as examples

Skills should not just be "reference text". They should act like constrained domain packages.

They should define:

- legal interface patterns
- legal state transitions
- legal decomposition paths
- legal verification obligations


## A clean split of responsibility

A strong long-term architecture would look like this:

- `skills/`:
  domain knowledge, templates, invariants, verification recipes, canonical decompositions

- `rtlgen/arch_*`:
  typed architecture and refinement IR

- `rtlgen/behavior_*`:
  executable behavioral contracts

- `rtlgen/dsl_*`:
  structured lowering into module DSL

- `rtlgen/skill_ppa.py`:
  pipeline orchestration, checks, reporting

- `agent`:
  local refinement, repair, bounded synthesis under explicit contracts


## Concrete next steps

To operationalize this, the next practical steps should be:

1. Add a per-module contract schema
2. Add per-layer artifact emission
3. Add local verification hooks per module
4. Lower `OoOCore` module-by-module instead of as one generator blob
5. Promote existing `skills/cpu` modules into canonical reusable lowering targets
6. Restrict agent edits to one module + one layer transition at a time


## Immediate implementation order

To keep momentum and avoid over-design, the implementation order should be:

1. Introduce a small contract IR
2. Attach one contract to one real module
3. Make the pipeline emit one artifact per lowering edge
4. Gate agent generation on contract presence
5. Expand module coverage incrementally

More concretely:

### Step A. Add a tiny contract schema first

Start with a minimal typed object, not a huge framework.

For each module contract, include only:

- module name
- role
- ports
- state elements
- timing assumptions
- invariants
- verification hooks
- allowed submodules

This can live in `rtlgen/` first and later be imported by skills.


### Step B. Pilot on four CPU modules only

Do not try to convert the whole SoC at once.

The first pilot set should be:

- `FrontendUnit`
- `DecodeRenameUnit`
- `BackendUnit`
- `CommitUnit`

Why these four:

- they already exist
- they form a clean path through the core
- they represent real front/back-end boundaries
- they are enough to prove the layered method works


### Step C. Emit artifacts at each transition

For one module, the pipeline should emit:

- `contract.json`
- `behavior_summary.md`
- `dsl_structure.json`
- `lowering_report.md`
- `rtl_manifest.json`

The artifact names matter less than the rule:

every lowering edge must leave a machine-readable trace.


### Step D. Let the agent modify only one layer step at a time

A good generation task should look like:

- "refine `DecodeRenameUnit` from contract to DSL"
- not "make the 4-core processor better"

The second phrasing is too unconstrained.


### Step E. Reuse `skills/cpu` as canonical providers

The existing `skills/cpu` modules should become the preferred source for:

- decode logic
- rename semantics
- issue queue behavior
- commit behavior

That does not mean copy-paste them blindly into the new core.

It means:

- use them as canonical lower-level building blocks
- use their tests as verification anchors
- use their interface shape as the legal design space


## Recommended code changes

If we continue implementation, the most useful code changes would be:

1. Add `rtlgen/contracts.py` support for per-module contract objects
2. Extend `rtlgen/skill_ppa.py` with a `contract_emit` stage
3. Add contract-bearing metadata to skill DSL modules
4. Create local module verifiers for `FrontendUnit`, `DecodeRenameUnit`, `BackendUnit`, `CommitUnit`
5. Convert `DecodeRenameUnit` from placeholder rename wrapper into a true decode + rename lowering path


## The key design discipline

The right long-term habit is:

- skills define the space
- contracts define the boundary
- artifacts define the trace
- verifiers define acceptance
- the agent performs bounded refinement

If we keep that discipline, the model stack becomes much more reliable without losing generation flexibility.


## Recommended principle

The framework should be designed so that:

- knowledge is stored in skills
- structure is stored in typed layer models
- generation is done by the agent
- acceptance is controlled by verifiers

That combination is what gives both flexibility and professionalism.


## Short answer

So the answer to your two questions is:

1. Yes, finer-grained stepwise lowering with verification at every layer will absolutely increase professionalism.
2. The low-level decomposition should not come only from the agent. It should primarily come from skills plus typed intermediate models, with the agent used as a constrained refinement engine.

The real design problem is not only "how to generate RTL", but "how to build a layered contract system that makes good RTL the easiest outcome".
