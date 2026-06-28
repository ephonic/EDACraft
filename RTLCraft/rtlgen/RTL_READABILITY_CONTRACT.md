# rtlgen RTL Readability Contract

This document defines the review-oriented RTL contract used by `rtlgen`.
It is a gate for human review quality, not a proof of functional correctness.

## Review RTL

Review RTL is Verilog/SystemVerilog emitted for inspection, debug, triage, and
lightweight downstream smoke checks. It should preserve the authored structure
well enough that a reader can answer:

1. what module this is
2. what ports it exposes
3. where storage, initialization, combinational logic, and sequential logic live
4. which clock/reset semantics are attached to sequential blocks
5. which generated helpers are stable enough to discuss in a report

The review contract applies most strongly to `EmitProfile.review()`. It is also
useful for `default` output, but `compact` output may intentionally omit richer
comments and tables.

## Emit Profiles

| Profile | Intent | Readability expectation |
| --- | --- | --- |
| `review` | Human review, diagnostics, regression reports | Header, port table, section markers, block labels, stable helper names |
| `default` | General emitted RTL with moderate comments | Should remain readable, but can be less verbose than review output |
| `compact` | Small emitted text for size-sensitive flows | May omit header, port table, and long comments |

`EmitProfile.review()` should default to readable markers, preserve module and
port context, and avoid leaking anonymous CSE/helper names into review output.

## Required Structure

Review RTL should provide:

1. a clear module header before the module declaration
2. a readable port table with direction, width, and name
3. stable section markers for storage, internal declarations, structural logic,
   initialization, combinational logic, and sequential logic when those sections
   are present
4. labels before non-trivial `always` blocks, such as `Comb:` or `Seq:`
5. visible sequential timing comments that name clock/reset semantics
6. grouped memory declarations and initialization blocks
7. source-map comments that support debug without drowning the RTL body

## Anti-Patterns

The readability analyzer reports these patterns:

1. very long single-line expressions
2. anonymous helper names such as `_tmp17`, `_tmp_17`, `_cse42`, or `_cse_42`
3. duplicated block prefixes such as `// Comb: Comb: ...`
4. deep ternary chains in a single assignment
5. missing module headers or port tables in review/default output
6. unlabeled `always` blocks
7. dense source-map comments that should be moved to a sidecar map
8. ungrouped memory declarations or hidden clock/reset timing
9. missing or out-of-order review markers when a caller supplies an expected
   marker sequence

## Gate Boundary

The readability gate does not:

1. prove functional correctness
2. replace Python/C++ simulation
3. replace Verilator, VCS, or another RTL simulator
4. prove CDC safety or storage-policy closure
5. rewrite the DSL

It is intentionally a report-oriented preflight. Findings should include a rule,
location when available, an object or marker when useful, suggested fix text, and
evidence that helps the author move directly to the failing contract.

