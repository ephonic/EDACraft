# LUT-era direct combinational model handlers — not adopted

The earlier pre-LUT full sample/commit/eval experiment remains untouched at
`validation/m5-model-handlers`. This new trial specializes only combinational
handlers against the accepted compact/fused/LUT backend. Each handler directly
calls its model's existing `gate_eval_N`; sequential and SDF path handlers,
runtime, process IDs/order, outputs, drivers and waits stay unchanged. No rejected
watch/queue/scalar-read patch is included.

Complete real design/128 golden and 100k flip-flop feedback; GCC11.5/C++17/O2,
fixed CPU0, warmup each, five alternating serial pairs, shared host unlocked
frequency. Median paired CPU saving: real **−0.33%**, feedback **−0.51%**.
The last real pair differs strongly as host conditions change; it is retained
and cannot replace the median. Real saving fails the preregistered ≥3% / at least
4-of-5 faster threshold. No independent repeat, adoption, or new VCS timing run.

The actual isolated emitter passed local 37/37. Eleven complete generated SDF
programs equal exactly the intended handler rewrite of the accepted sealed Linux
baseline, with all other emitted bytes identical. Each program's three traces
and settled output-bit waveforms independently match the accepted VCS reference.
The initial comparison accidentally used an earlier local build artifact predating
the accepted time-zero path fix; the complete difference is retained in
`initial-identity-difference.patch`. Final comparison uses the authoritative
accepted snapshot. There is no new sanitizer/two-platform acceptance claim for
this rejected candidate.

`verify.py` independently reconstructs candidates, checks source/binary identities,
recomputes all raw CPU/RSS/pairs/golden, and checks the actual emitter and eleven
complete generated programs plus their raw three-run reference traces/waves.
It verifies that production implementation, all parser files and original
waveform dependencies remain unchanged. Source snapshot
`6498bcb46b0bb936943bd6ae91546246af1eb684716dcaa0dd288abd89e50d8e`
has exactly one changed file, `src/gate_compiler.cpp`, versus the accepted SDF
archive. It was never installed in the default source tree.

`source-snapshot.json`, `screen-archive.json`, `local-archive.json` identify the
immutable `/tmp` archives. `screen-verified/` retains original performance inputs,
sources, binaries and raw runs; `local-verified/` retains the actual compiler,
complete SDF/gate/wave/checkpoint outputs and baseline generated programs.
`decision.json` records rejection. Use a copy if re-running the mutating verifier.
