M235 subsequently fixes the enum cast identity loss and passes the original 8192-bit UVM packing fixture; see [M235](../m235-stream-enums/README.md).

# M233 — streaming assignment targets and UVM field utilities

Implement dynamic-array/queue, fixed-array and mixed streaming assignment targets. Snapshot the RHS once, capture all target addresses before stores, allocate only the first dynamic target greedily after reserving all fixed fields, and right-pad the last partial element. Fixed destinations truncate before chunk reversal; left streams use the VCS-observed forward chunk reversal even for non-divisible widths. Bounded queues clip stored elements without consuming the following field's bits. Four-state and wide values retain their existing representation. Packed scalar fast paths remain available.

Eighteen same-byte models match VCS. Three modes pass 54 complete ordered waveform captures, five protected compile diagnostics and two runtime rejections. Six frontend/native ASan/UBSan models pass; the later M234 frontend reproduces all 54 original native inputs exactly. Compile boundaries are explicitly classified: VCS accepts handle-array targets and NBA dynamic targets that dsim still rejects, and rejects the other three boundaries. Both runtime size/null errors are rejected.

The unchanged full Accellera UVM 2020.3.1 utilities fixture now runs `uvm_field_int/string`, randomize with a simple integer constraint, independent clone, compare/copy and uvm_event trigger/wait with zero UVM_ERROR/UVM_FATAL. This uses UVM_NO_DPI and native -O0, matching the original VCS test source. No UVM library is patched or replaced.

At this checkpoint an additional 8192-bit pack/unpack fixture remains blocked by enum typing in `uvm_tlm2_generic_payload.svh:622`; it is not counted as a pass. Earlier M230 bare-byte-queue stream and side-effect differences also remain explicitly outside this claim. Validation files retain old capability probes; virtual-interface rejection in those M232 stable results is superseded by M234.

Raw artifacts: `dsim-test/evidence/m233-stream-targets/` and M234 `legacy-stream/`. Release progress is recorded with M234. No performance comparison.
