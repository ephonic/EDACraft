# Ordered MIPD updates and physical source multiplicity

Sixteen fresh VCS cases, compiled separately, three runs each. Full raw TRACE
and every declared settled bit stream agree across all three runs. All first
annotation logs report zero errors/warnings, MAXIMUM approximation and default
pulse thresholds; subsequent runs reuse the annotation cache. No native support
or performance claim. The original thirteen oracles remain frozen.

Receiver readback is not a per-SDF-source maximum table. Starting from effective
9ps, decrementing either source by7ps gives2ps; incrementing to29ps then
decrementing the other by7 gives22ps. Smaller subsequent ABS cannot reduce the
effective double-driver receiver delay. Four controls annotate only one source:
ABS9→3 gives3/9ps for single/double physical drivers; ABS3, INC20, ABS4 gives
4/23ps. The second physical driver remainsZ throughout. Structural multiplicity,
not the number of annotated source records, changes ABS behavior.

Sparse ABS on9/10/12 with(5)()(8) gives9/0/12; sparse INC(20)()(-2) gives
29/10/10. Selected missing corners, six-value lists and ordinary corner choice
have complete four-state references. These observations do not establish all
unmeasured sparse/zero/corner/precision/alias combinations.

`verify.py` regenerates all input bytes, checks raw artifacts/archive manifests,
compiler/source/binary identity, full traces and all settled bits, and verifies
all twelve directed four-state transitions against observed effective tables.
`expected-updates.json` is saved separately from the original reference file.
The current native compiler reaches explicit unsupported INTERCONNECT errors
for all16 exact inputs and preserves protected outputs.

Full binaries, daidir dependencies, VCDs and logs are in`vcs-verified/` and
`fanin-vcs-verified/`; their archive SHA256 values are recorded alongside them.
The experiment changed the planned state representation; it did not implement
private input pins, cancellation, checkpoints or compiled wire delays.
