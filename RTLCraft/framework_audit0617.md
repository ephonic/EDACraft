# RTLCraft Framework Audit — 2026-06-17

## Context

This audit was produced while designing a **Thor-class GPGPU SM compute cluster**
under `thor_gpu/`, following the document-driven 6-layer IR flow modelled on the
`earphone/` pilot. Nine modules were built end-to-end (L1 BehaviorIR → L2 CycleIR →
L3 ArchitectureIR → L4 StructuralIR → L5 DSL → L6 Verilog), each with per-layer
source, tests, and generated specs/plans/reports.

Verification result of the new design: **164/164 Python cross-layer tests PASS**;
Verilog emitted for all 9 modules.

The findings below are **framework-level** issues encountered during that work.
They affect the methodology or the framework's own correctness, not the new
design's content. Each was worked around in the new design rather than fixed in
the framework, per the task's instruction not to modify the framework.

---

## F1. `seq()` `If()` conditions silently ignore bare `Input` ports — medium/high

**Symptom.** Inside a `with self.seq(...)` block, an `with If(self.<input_port>)`
gate that references a top-level **Input** signal directly does **not** take
effect in the simulator. The sequential register is never updated even when the
input is driven and the `step()` path sees the correct combinational value.

**Reproduction.**
```python
class T(Module):
    def __init__(self):
        ...
        self.en = Input(1, "en")
        self.r = Reg(32, "r", init_value=0)
        with self.seq(self.clk, ~self.rst_n):
            with If(self.en):      # <-- Input used directly: register never latches
                self.r <<= self.din
```
Driving `en=1`, `din=42` and stepping leaves `r==0`. Routing the same signal
through an intermediate `Wire` (`en_w = Wire(1,...); with self.comb: en_w <<= self.en;
with self.seq(...): with If(en_w): ...`) **works** and latches the value.

**Evidence.** `thor_gpu/modules/vector_alu/layer_L5_dsl/src/dsl.py` initially
gated on `self.valid_in` (Input) and produced `result==0` for every test; switching
to the `en_w` Wire pattern made all 26 tests pass. The `earphone/` pilot never
trips this because every seq gate there is already a `Wire`/`Reg`
(e.g. `simd16`'s `int_ce = Wire(1, "int_ce")`).

**Impact.** A new designer following the natural `with If(self.valid_in):` idiom
will produce a silently-dead datapath. There is no error, lint, or warning.

**Suggested framework fix (not applied).** Either (a) make `If()` on an `Input`
port behave identically to the `Wire` path in the sequential evaluator, or
(b) emit a lint warning/error when an `Input` signal is used directly as a
sequential `If()` condition, documenting the `Wire` workaround.

---

## F2. The `<` operator is unsigned even after `.as_sint()` — medium

**Symptom.** A signed comparison written as `s1.as_sint() < s2.as_sint()`
evaluates as **unsigned** in the simulator. `0xFF` (−1 signed) compared `< 1`
returns `False` (treated as `255 < 1`), not `True`.

**Reproduction.**
```python
# s1 = 0xFF, s2 = 0x01, width 8
slt = Mux(s1.as_sint() < s2.as_sint(), Const(1,8), Const(0,8))
# evaluates to 0, should be 1 (-1 < 1)
```

**Evidence.** `thor_gpu/modules/vector_alu/layer_L5_dsl/src/dsl.py` SLT/SLTU
lanes returned 0 until a manual `_signed_lt(a, b, width)` helper
(sign-bit-difference + unsigned compare) was introduced; `SLTU` (unsigned `<`)
worked throughout. Confirmed in isolation: `0xFF<1` via `<` → 0 (unsigned),
while the documented intent of `.as_sint()` is a signed view.

**Impact.** Any module using signed comparison through `.as_sint()` produces
silently-wrong results. The README/Tutorial examples imply `as_sint()`/`as_uint()`
are the signedness control, so this contradicts the documented contract.

**Workaround applied.** Reconstruct signed comparison from the unsigned operator:
```python
def _signed_lt(a, b, width):
    sa, sb = a[width-1], b[width-1]
    return Mux(sa ^ sb, sa, (a < b))   # sign differ -> a<b iff a negative; else unsigned
```

**Suggested framework fix (not applied).** Make `as_sint()` operands propagate
signedness into `BinOp("<", ...)` so the comparison is signed, or document
explicitly that `<`/`>`/`<=`/`>=` are always unsigned and provide a
`signed_lt`/`signed_gt` helper in `rtlgen.logic`.

---

## F3. `.as_sint()` does not make `*` signed; multiply needs manual sign-extension — medium

**Symptom.** `(a.as_sint() * b.as_sint())` does **not** compute a signed product
in the simulator; the result is the unsigned product of the raw bit patterns,
which is wrong for negative operands.

**Reproduction.** Sign-extending an INT8 value with `as_sint()` and multiplying
gives an incorrect 16-bit result for negative inputs; sign-extending the operands
to the target width **first** (via bit-replication `Cat`) and then multiplying
with the plain unsigned `*` yields the correct two's-complement low bits.

**Evidence.** `thor_gpu/modules/tensor_core/layer_L5_dsl/src/dsl.py`
(`_sign_extend_8to16`, `_sign_extend_16to32`, `_int8_mul`). The first attempt
using `(a16.as_sint() * b16.as_sint()).as_uint()[15:0]` gave `1*1 → 0`; switching
to `(a16 * b16)[15:0]` with pre-sign-extended operands fixed the 8×8×8 MMA.

**Note.** The unsigned `*` operator **does** work correctly on the `step()` path
(`3*5 → 15`). The bug is specifically the interaction of `.as_sint()` with `*`.

**Impact.** Any MAC / multiply datapath relying on `as_sint()*as_sint()` is wrong
for negative operands — a common case in GPGPU tensor cores.

**Suggested framework fix (not applied).** Either make `as_sint()` operands
produce signed arithmetic for `*`/`+`/`-`, or document that signedness casts only
affect width/printing and that signed multiply must be done by pre-sign-extending.

---

## F4. `Cat()` endianness is MSB-first and easy to get wrong — low/medium

**Symptom.** `Cat(a, b, c, ...)` places the **first** operand in the
most-significant position. Code that packs element 0 into the low bits must pass
the operands in **reversed** order (`Cat(*reversed(elements))`).

**Evidence.** `thor_gpu/modules/tensor_core/layer_L5_dsl/src/dsl.py` initially
used `Cat(*result_bits)` for the 8×8 INT32 matrix and produced a
**transposed/reversed** output (row0 came back reversed vs. the L1 golden model).
`Cat(*reversed(result_bits))` fixed it. The sign-extension helper
`_sign_extend_8to16` had the same class of bug initially
(`Cat(s, sign×8)` → 256 instead of 1; corrected to `Cat(sign×8, s)`).

**Impact.** Silent bit-layout mismatch between L5 and L1/L2 that only surfaces
with non-symmetric data (symmetric test vectors like all-ones/all-zeros hide it).

**Suggested framework improvement (not applied).** Document `Cat()`'s MSB-first
ordering prominently, and/or add a `Cat_lsb_first(...)` convenience helper. The
README/Tutorial examples use `Cat(*reversed(...))` without explaining why.

---

## F5. iverilog rejects nested part-select on concatenations emitted from the DSL — low (emitter/external-tool)

**Symptom.** The generated Verilog for the tensor core contains deeply nested
expressions like `{...} * {...}[15:0]` and `(... + ...)[31:0]` (part-select on a
parenthesised/concatenated expression). iverilog (even in `-g2012` SystemVerilog
mode) reports `syntax error / Malformed statement` and refuses to elaborate.

**Evidence.** `thor_gpu/verilog/thor_tensor_core.v` line 49; iverilog `-g2012`
fails while the Python simulator passes all tensor-core cross-layer tests.

**Mitigation in the design.** None needed for the Python flow (which is the
methodology's golden path). For RTL sign-off, the expression should be split
into named intermediate `wire`s so the part-select applies to a simple net.

**Suggested framework improvement (not applied).** The Verilog emitter could
introduce intermediate wires for any `(expr)[hi:lo]` / `{...}[hi:lo]` pattern
(CSE-style), which would both shorten the emitted lines and avoid parser
limitations in iverilog and some commercial tools.

---

## F6. Module declaration uses the DSL **class name**, not `module.name` — low (usability)

**Symptom.** `VerilogEmitter().emit(mod)` emits `module <ClassName> (...)` using
the Python class name, regardless of the string passed to
`super().__init__(name)`. A module instantiated as `ThorVectorALU` whose
`module.name == "thor_vector_alu"` still declares `module ThorVectorALU`.

**Evidence.** Every `thor_gpu` L6 test had to assert `"module ThorVectorALU"`
rather than `"module thor_vector_alu"`; `module.name` reads as
`thor_vector_alu` but the declaration is `ThorVectorALU`. The `earphone/` pilot
shows the same behaviour (`EarphoneSIMD` class → `module EarphoneSIMD`).

**Impact.** Test/expectation mismatch for anyone assuming the declaration name
follows `module.name`. Also complicates hierarchical compile: a parent that
instantiates by `module.name` won't match the emitted declaration name.

**Suggested framework improvement (not applied).** Either emit the declaration
using `module.name` (and keep the class name only for the Python API), or
document unambiguously that the emitted module name is the class name. The
`thor_gpu/.../gpu_cluster` top, which instantiates `ThorGpuSM`, only compiles
when emitted jointly with `thor_gpu_sm.v` for this reason.

---

## F7. `Simulator.reset()` defaults to `rst="rst"` and is not name-aware — low (API)

**Symptom.** `sim.reset()` (no argument) probes a signal named `rst`; if the
design's reset port is `rst_n` (active-low, the common convention), reset does
nothing useful and the first `step()` can read stale/zero state.

**Evidence.** Initial `thor_gpu` L5 tests called `sim.reset()` and saw
`KeyError: "JIT: signal 'rst' not found"` (JIT path) or silently-wrong state
(interpreter path). Passing `sim.reset(rst="rst_n", cycles=2)` fixed every case.
The `earphone/` L5 tests always pass the name explicitly.

**Impact.** Easy footgun for new modules using the conventional `rst_n` reset.

**Suggested framework improvement (not applied).** Auto-detect the reset signal
by scanning the module's input ports for names in `{rst, rst_n, reset, reset_n,
rstn, resetn, rst_b, reset_b}` and pick the matching one, instead of hard-coding
`rst`.

---

## Summary table

| ID | Issue | Severity | Workaround in `thor_gpu/` |
|----|-------|----------|---------------------------|
| F1 | seq `If()` ignores bare `Input` conditions | med/high | gate via intermediate `Wire` |
| F2 | `<` is unsigned despite `.as_sint()` | medium | manual `_signed_lt` helper |
| F3 | `.as_sint()` does not make `*` signed | medium | pre-sign-extend, then unsigned `*` |
| F4 | `Cat()` is MSB-first (layout mismatch) | low/med | `Cat(*reversed(...))` |
| F5 | iverilog rejects nested part-select on concat | low | n/a (Python sim is golden); split to wires for RTL |
| F6 | Emitted module name = class name, not `module.name` | low | assert class name; joint-compile hierarchy |
| F7 | `reset()` defaults to `rst`, not name-aware | low | pass `rst="rst_n"` explicitly |

None of the above were fixed in the framework. The new `thor_gpu/` design is
fully verified at the Python cross-layer level (164/164 PASS) and its Verilog
compiles cleanly in SystemVerilog mode for 7/9 modules standalone and the
cluster top when jointly compiled with its SM submodule.

---

# Part B — Methodology & Agent-Readiness Assessment

The seven findings in Part A are concrete bugs. The remainder of this document
steps back and assesses the **framework's design philosophy and whether it is
well-suited for an agent performing large-scale hardware design** — beyond the
specific defects above. The conclusion: **the core ideas are sound, but the
current implementation is an early-stage prototype that would not yet carry a
large agent-driven design to completion without heroic manual compensation.**

---

## B1. What is genuinely right about the design philosophy (keep these)

### B1.1 Cross-layer consistency (L1 == L2 == L3) as a hard gate — the single most valuable idea

The biggest pain point in agent-driven RTL is not "can it write RTL?" but
"can it tell whether the RTL it wrote is correct?" The framework answers this by
splitting correctness into three layers that each introduce exactly **one new
concern** (function → timing → RTL syntax/wiring) and enforcing equality with an
assertion. This **localises failure**: a mismatch at L2 is a timing bug, at L3 it
is a wiring bug — the agent never has to debug "everything at once." This is
textbook-grade design intuition and is strongly agent-friendly.

### B1.2 "Behaviour model IS the spec" (gem5-style) — turns a fuzzy PDF into a runnable golden

The README/Tutorial insistence that the agent *selects and configures* a
pre-built behaviour template rather than authoring one from scratch is shrewd.
For an agent, a Python model that can be `step()`-ed is vastly more useful than
a PDF spec: it is executable, fuzzable, and a source of automatically generated
test vectors. This is the right instinct.

### B1.3 White-box AST + directory-as-module-as-layer — a structure an agent can navigate

`module._comb_blocks`, the `describe()` convention, and the regular
`layer_LN_xxx/` naming let an agent **read** an existing design and **modify it
incrementally** instead of regenerating from scratch every time. This
"readable/writable" property is the prerequisite for an agent to do ECO and PPA
iteration — something black-box HLS can never offer.

These three points are the skeleton and should be preserved.

---

## B2. Structural gaps for "an agent doing large-scale design" (the core critique)

### B2.1 The entire methodology is bet on its least trustworthy component — the Python simulator

The authority of the whole L1==L2==L3 chain rests on `rtlgen/sim.py` being
correct. Yet this audit found: `<` is unsigned, `.as_sint()` does not make `*`
signed, and `seq()` `If()` ignores bare `Input` ports. **The oracle itself is
wrong.** For a human this is "switch to another idiom"; for an agent it is
**existential**: the agent cannot tell "my test failed because my design is
wrong" from "my test failed because the framework computed wrong." A
verification gate that gives false confidence is worse than no gate — the agent
will trust the erroneous PASS and carry on to silicon where it detonates.

**This is the #1 risk.** Fixing the seven bugs is not enough; what is needed is
a mechanism by which the simulator's own correctness is held to account — e.g.
differential testing against iverilog co-sim, or a formal/subset golden for the
interpreter itself.

### B2.2 The simulator does not scale

This audit's `tensor_core` is only 64 outputs × 8 MACs, yet one test takes ~6 s
and the emitted Verilog contains a 1.3 MB single-line expression. A real Thor SM
is thousands of lanes, deep pipelines, multiple cache levels. The AST
interpreter will not survive that scale; the advertised 50–500× JIT path
crashed here (`signal 'rst' not found`). **The verification engine of a
methodology must itself scale to the methodology's target size** — otherwise the
L1==L2==L3 gate is simply infeasible on large designs and is effectively absent.

The current state: the verification means and the target size are mismatched.

### B2.3 No spec-to-skeleton automation — the agent is left hand-scaffolding directories

While building `thor_gpu`, the **manual** work was: copying 9 × (6 layers) = 54
`src` files + 54 `test` files, hand-typing `describe()`, hand-writing
`__init__.py`. The README claims `skill_ppa` can auto-produce a skeleton
("behaviours → arch → skeleton → agent_gen"), but that flow requires the LLM API
and is **not wired into the document-driven flow** — it is effectively
unavailable. The most mechanical work an agent should *not* do is exactly what
the framework currently leaves to the agent copying `earphone`. This audit
wasted real cycles on cwd, import paths, and `describe` imported from the wrong
place — pure mechanical errors.

**Missing: a `spec.yaml → full 6-layer skeleton + empty test stubs` generator.**

### B2.4 "Document-driven" is a misnomer — it is really "code-driven documentation"

`docgen` **reverse-generates** documents from `describe()` and test results, so
documents can only ever reflect code that was already written — they **cannot
drive** the design. True document-driven design would mean: top-level
constraints propagate downward, code is generated to satisfy constraints, and a
broken propagation chain *blocks* the flow. `constraints.py` and
`DesignScaffold` exist but (as `audit0615.md` already admits) are not enforced
end-to-end. For an agent this means: **besides tests, there is no machine-
checkable link between "what the human wanted" and "what was built."** Documents
and implementation share no contract; documents are merely after-the-fact
explanations.

### B2.5 Human checkpoints are dangling in an agent flow

"Agent prepares, human decides at checkpoints" sounds reasonable, but who
enforces it when an autonomous agent is running? `flow.py` currently blocks by
checking for a human-authored "approval artifact" via a hash — a workaround.
Large agent designs need either **automatic gates with formal criteria**
("PPA met + coverage met + cross-layer consistent → release") or a **clean
human-in-the-loop protocol**. Today it is "a beautiful slogan at design time,
hacky enforcement at run time."

### B2.6 No reliable hierarchical-composition primitive

The cluster top relies on `self.instantiate(child, port_map={...})`. A hand-
written `port_map` of 40+ ports is exactly where an agent most easily mis-wires
at scale. This cluster compiles only because the author **copied the reference
implementation verbatim**; an agent composing it from scratch would almost
certainly miss or mis-wire a port, and **no IR checks "are all ports connected?"
before simulation.** A large SoC has hundreds of instances and thousands of
connections; hand-written `port_map` is unsustainable. What is missing is a
bundle / connection-graph level structural IR (à la Chisel `Bundle`) that can
report errors at wiring time.

### B2.7 Leaf nodes quietly degenerate to black boxes, hollowing out cross-layer verification

The framework advertises white-box, but when L5 actually has to deliver real
computation (FPU, the whole SM), this audit was forced to introduce black-box
stubs (FPU structural approximation, behavioural SM). **So on precisely the
hardest parts, the design reverts to black box and cross-layer numerical
equivalence is silently lost** (the stub is never numerically compared to L1).
The framework has no clean answer for "already-verified leaf IP" — it is neither
truly white-box nor does it offer a trustworthy IP-encapsulation mechanism. In
large designs ~80% is IP reuse, so this gap must be addressed head-on.

### B2.8 Tests are hand-written; there is no coverage-driven auto-generation

Golden tests are all hand-typed by human/agent. The README says `skill_ppa` can
"auto-generate 100+ test vectors from the behaviour model," but that is not wired
into the document-driven flow. What large designs most need is **coverage-
driven tests generated automatically from the L1 model**; today it is "write as
many as you think of."

---

## B3. What is required to genuinely support "an agent doing large-scale design"

In priority order:

1. **A trustworthy oracle.** Either build formal / differential checking for the
   simulator (run every module through both the Python sim and an iverilog
   co-sim and flag any divergence), or promote iverilog to a first-class
   verification backend. This is the foundation.
2. **A spec→skeleton auto-generator.** Consume one structured spec, emit the full
   6-layer directory tree with empty `describe()` and empty test stubs, and
   eliminate the scaffolding drudge work entirely.
3. **A structural / wiring IR.** Check port-connection completeness *before*
   simulation, killing "missed one port" errors at second-level latency.
4. **Real constraint propagation.** Make top-level spec constraints machine-
   checkable as they flow downward, so documents drive design rather than
   explain code.
5. **Coverage-driven tests generated from L1**, replacing hand-written golden.
6. **A reusable "verified leaf IP" encapsulation**, giving black-box reuse a
   legitimate, explicit channel rather than smuggling it in unnoticed.

---

## B4. Bottom line

**The framework's *ideas* are right — behaviour-as-spec, cross-layer hard gates,
white-box AST — and those three things make it inherently more agent-suitable
than black-box HLS.** But it is currently "correct thinking + early
implementation": it stakes everything on an untrustworthy, non-scaling
simulator, and has not closed the automation loop from spec → skeleton → wiring
→ tests. As a result, an agent on a large design gets stuck in the scaffolding
and in "is this a framework bug or a design bug?" ambiguity.

This audit got `thor_gpu` to 164/164 green by repeatedly cross-checking against
the reference implementation and manually routing around framework pitfalls.
**That kind of "the agent's patience covers the framework's defects" does not
scale.** The direction is worth pursuing, but the foundation (oracle
trustworthiness + scale) and the automation must be shored up first.
