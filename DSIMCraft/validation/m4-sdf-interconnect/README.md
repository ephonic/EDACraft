# Fresh INTERCONNECT executable reference study

This batch collects semantics for the next runtime implementation; it does not
implement native INTERCONNECT. Thirteen independent VCS W-2024.09 compilations,
three runs each, preserve raw traces, all 39 VCDs and first-run annotation logs.
All first annotation logs report zero errors and warnings, MIPD `MAXIMUM` and
pulse_r/e100. Later VCS runs reuse annotation cache; only the first annotation
log is required. Binary and daidir dependencies are included; csrc intermediates
are excluded. No VCS performance timing is claimed.

`verify.py` regenerates exact input files, checks archives and all hashes, decodes
every declared settled bit and trace in all three runs, and independently checks
the proposed value-selected delay rules against all separated directed four-state
transitions. It checks per-receiver separation, destination rounding, default
positive pulse rejection in the tested widths, source-order-independent MAXIMUM
before X derivation, and ordered duplicate/increment updates. The first recording
is retained in `verify-record.log`; the default replay of the saved reference is
in `verify-accepted.log`. `tests/sdf_interconnect/expected.json` records complete
settled bit streams and traces for actual future native comparisons.

Important observations, detailed in `docs/sdf-interconnect.md`:

- MIPD selects by destination value; it cannot reuse IOPATH transition tables.
  The twelve-value test acts as the first three values in this VCS mode.
- Crossed multi-source3/10/6 and9/4/12 yield9/10/12, with X9, independent of source
  annotation order.
- Duplicate same-source ABS updates replace: forward order gives9/11/13, reversed
  gives3/4/6. They cannot all be merged by MAXIMUM.
- Multi-source current9 plus INCREMENT20 on the previously3 source gives29, not23;
  sparse/mixed update rules need further evidence before generalizing a merge
  algorithm.
- Receiver10ps quantizes4/6 to0/10; changing only the source precision preserves
  the fine receiver delay.

The unchanged default CLI was also attempted on the identical original fixture.
It fails on the valid opening timescale directive in the independent structural
parser, before SDF annotation. Raw failure/protected outputs are retained under
`native-strict/fanout` and `initial-native-header-failure.json`. This is a newly
identified front-end gap, **not** a native reference match or a claim that all13
reached the INTERCONNECT rejection. Inputs were not stripped to hide the failure.
The next step is gate preprocessing/scope-time metadata followed by receiving-pin
annotation/runtime, with RTL and gate parsers kept separate.

Evidence is split without replacing earlier artifacts:

- `vcs-verified/`: eight base cases; archive SHA
  `c2541c0981754040e916aa039793725dba7a49dab694e5f07423631d83b2c73a`.
- `extra-vcs-verified/`: five update-disambiguation cases; archive SHA
  `69e5aa89e7aa7657f91a3ddc142b72db17e6e2af22ecf12d202b7786920edf4d`.
- `vcs-archive.json`, `extra-vcs-archive.json` identify immutable local/remote
  `/tmp` archives and original job roots. Extra `_basis/` contains fixture
  generation dependencies, not eight additional VCS runs.
- `verified-results.json`, `source-snapshot/` and `verification-manifest.json`
  preserve the final observations, generator/decoder/reference sources and hashes.
  Re-run the mutating verifier in a copy with these frozen inputs if needed.
