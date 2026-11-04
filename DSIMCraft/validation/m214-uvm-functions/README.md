# M214 — UVM call semantics and generated function sharing

Unmodified Accellera UVM 2020.3.1 remains incomplete. The smoke test now reaches
`uvm_resource.svh:80`, `$typename(T)`, and rejects it with `type name is not a
value: T`. No UVM run_phase PASS is claimed. No new dsim/VCS runtime ratio was
measured. The original C910 RTL/TB now passes the minimal RV64 smoke; details follow below.

Production changes:

- Decode unknown string escapes, octal and two-digit hex consistently in packed
  and string contexts; dynamic strings with embedded NUL remain rejected.
- Preserve `null` and other multi-expression actual arguments. Report the name
  of a missing required formal.
- Support recursive input/ref/const-ref scalar and array arguments, class/null
  conditional expressions, multi-level parameterized factory type aliases, and
  value-context calls with omitted empty parentheses.
- Add opt-in `--shared-functions` for serial RTL. Shared function bodies retain
  per-call automatic frames and references, copy-in/out, recursion guards, DPI
  environments and wave capture. Recursive output/inout, tasks and array results
  remain unsupported. The default generator is retained.
- Deduplicate write-range dependency metadata; repeated call edges previously
  copied the same records exponentially. No executed assignment is deleted.
- Add `scripts/compile_split_model.py` for bounded native translation units.
  It preserves process registration order and factors self-contained setup
  blocks when requested. Startup exclusion scanning preserves enqueue order.
  Serial RTL only; wave, DPI, gate and parallel model splits are rejected.
  This remains an explicit build path, not integrated into the default CLI.

Development validation (external logs under `/private/tmp/dsim-m214`):

- Seven `uvm_call_values` fixtures pass inline, shared and shared + time-wheel
  native execution; 22 complete ordered VCD captures match, including failed
  prediction replay. Five negative cases preserve existing output.
- Exact same seven source fixtures and complete TRACE pass VCS W-2024.09 on
  103 (`/tmp/dsim-m214-uvm-all/results`). Source SHA values are recorded.
- A 26-level repeated call graph produces 345395 bytes of C++ and runs to 92.
  The exponentially expanded inline form was deliberately not compiled.
- Seven shared-function DPI fixtures pass actual C ABI calls, exported callback
  scopes and late discovery of DPI requirements. Four new native models pass
  ASan/UBSan, as does parser repeated cleanup. Six affected CTest groups pass.
- Original UVM preprocessing remains 166 dependencies / 1,888,084 bytes, SHA256
  `a0e1425aeebafd981a99a5f563b3327d800b968f448f790d95293d4c83d1611d`.
  Package SHA/commit are pinned by `public-uvm.py`; the source is unmodified.
  Normal compiler and ASan compiler with `ulimit -s 65520` reach the same
  remaining language gap. Default ~8 MiB ASan stack overflows first; both logs
  are retained. This is an explicit sanitizer host-stack limitation.
- Split timing model including delayed continuous drivers passes native
  ASan/UBSan; expected TRACE is 35 then 63. C910 compilation is still being
  checked; compiling parts or generating C++ alone is not a runtime PASS.

Reproduce the new model regression:

```
python3 tests/uvm_call_values/regression.py build/dsim /tmp/uvm-values
python3 validation/m214-uvm-functions/shared-dpi.py . build/dsim /tmp/shared-dpi
```

Frozen publication is complete. Production commit `3ca118ba` has 1521 inputs,
source SHA256 `060aedf5c60673f3cde7fb98a3b0e7e0877b4c260a2082f32a8625879a7c3622`.
Mac stable is `20261101T145923006249Z-060aedf5c606`; Intel/103 stable is
`20261101T150100571422Z-060aedf5c606`. Both release receipts and actual entry
checks pass. Each platform recompiled all seven new value models, nine frontend
models, two compact storage models and seven shared-DPI models. 35 complete C++
models and 22 ordered captures match across platforms; the diamond model and
seven same-source DPI TRACE results also match. See the JSON receipts here.

C910 native acceptance:

- Original 524 source files and TB are unmodified. Images have exactly the
  SHA256 values from M213's independently VCS-passed corrected program.
- All 80 process units compiled, but the remaining 114 MB main entry crashed
  Intel's compiler after 950.30 seconds. This failed attempt is retained.
- Factoring setup yields 308 successful units: 80 exact source/header/flag
  matches reused from that build, plus main and 227 new initialization units.
  Link succeeds. The 103 executable is `/tmp/dsim-m214-c910-setup/native`.
- Current stable emits code byte-identical to that build input after removing
  only the newly added, disabled shared-function runtime block; full code SHA
  equality and that narrowly bounded normalization are recorded.
- First run times out at 300 seconds; a fresh 900-second-budget run returns 0
  after 669.25 wall seconds and the original TB writes `TEST PASS`.
  This is a minimal hand-written RV64 smoke, not ISA/CoreMark certification.
  Process code is -O0, and execution shared the machine with compilation and
  included a stack observation. No fair dsim/VCS performance ratio is claimed.
- Stack capture shows wide driver resolution during simulation. The additional
  `optimized-runtime.py` mixed-optimization experiment preserves definitions
  and all model objects, passes three small native checks (two ASan/UBSan),
  but its C910 run still exceeds 300 seconds. It is **not** accepted as a
  performance improvement or put in the default tool path.

Full original UVM remains incomplete. Next priority is `$typename(T)` and
subsequent actual original-library blockers; isolated microtests do not replace
complete UVM phase/factory/objection execution.

Both current stable entries emitted the full C910 model with exactly SHA256
`55064f544cd0b15648299187e21c369c55b76c04fb3f3df7d46d340bcbcbe213`.
The additional 103 frontend check first exceeded a 180-second budget during
other work; repeating the identical command completed in 23.65 seconds with
that exact hash. The original timeout is retained; its cause was not isolated.
