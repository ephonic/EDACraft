# Mixed DSL + External Verilog Cosim Guide

This guide turns the current mixed-design closure path into one small worked
example you can rerun locally.

It is meant to answer three practical questions:

1. how to package a DSL parent with an external Verilog leaf
2. how ROM `init_file` payloads travel with emitted RTL
3. which RTL backend to use for smoke, local closure, or stronger signoff

## Worked Example Shape

The regression-backed minimal example already lives in
[tests/test_cosim.py](./tests/test_cosim.py).

The shape is intentionally small:

1. `DslCosimExternalLeaf`: a `BlackBoxModule` with `external_verilog=True`
2. `DslCosimMixedExternalRomTop`: a DSL parent that instantiates that leaf
3. `Memory(..., init_file=...)`: a ROM whose emitted RTL uses `$readmemh(...)`
4. `run_dsl_rtl_cosim(...)`: the emitted-RTL parity entry point

Representative structure:

```python
class DslCosimExternalLeaf(BlackBoxModule):
    def __init__(self, *, verilog_source, include_dir):
        super().__init__(
            name="DslCosimExternalLeaf",
            verilog_module_name="cosim_ext_leaf",
            inputs=[("din", 8)],
            outputs=[("dout", 8)],
            external_verilog=True,
            verilog_sources=[verilog_source],
            include_dirs=[include_dir],
            defines={"COSIM_EXT": "1"},
        )


class DslCosimMixedExternalRomTop(Module):
    def __init__(self, *, verilog_source, include_dir, init_file):
        super().__init__("DslCosimMixedExternalRomTop")
        self.addr = Input(2, "addr")
        self.din = Input(8, "din")
        self.out = Output(8, "out")
        self.ext = DslCosimExternalLeaf(
            verilog_source=verilog_source,
            include_dir=include_dir,
        )
        self.mem = self.add_memory(Memory(8, 4, "mem", init_file=init_file))

        @self.comb
        def _comb():
            self.ext.din <<= self.din
            self.out <<= self.ext.dout + self.mem[self.addr]
```

This example is useful because it exercises all three artifact classes at
once:

1. external Verilog source files
2. include trees and `+define+...` flags
3. ROM init-file payloads used by emitted `$readmemh(...)`

## Packaging Contract

Use `collect_external_verilog_artifacts(module)` when emitted RTL is not
self-contained.

Today that bundle includes:

1. `sources`
2. `include_dirs`
3. `defines`
4. `init_files`

The regression that locks this behavior is
`test_collect_external_artifact_bundle_stages_external_and_init_files(...)` in
[tests/test_cosim.py](./tests/test_cosim.py).

That test checks all of the important staging details:

1. the emitted DUT source is always present as `dut.sv`
2. the external Verilog leaf is staged under `external_sources/...`
3. include directories are rewritten into staged `include_dirs/...`
4. ROM `init_file` payloads are staged under `init_files/...`
5. emitted `$readmemh(...)` calls are rewritten to point at the staged path

Recommended rule:

1. if the emitted RTL depends on a file at compile time or runtime, that file
   must be considered part of the artifact bundle

## Backend Recommendation

`run_dsl_rtl_cosim(...)` accepts `rtl_backend="auto" | "iverilog" | "verilator" | "vcs"`.

The release resolution policy in
[sim/cosim.py](./sim/cosim.py)
is:

1. `auto -> verilator` when a local `verilator` is available
2. otherwise `auto -> vcs` when local VCS is available
3. otherwise `auto -> iverilog`

Use that policy like this:

1. `cpp_backend` first when you are still fixing DSL semantics or datapath bugs
2. `verilator` as the preferred local emitted-RTL closure path
3. `vcs` when you need stronger project-style simulator behavior and have a local VCS install
4. `iverilog` as a lightweight compile-smoke / compatibility backend

The key point is that `iverilog` is still useful, but it is not the only or
strongest correctness gate for emitted SystemVerilog.

The backend selection regressions are also in
[tests/test_cosim.py](./tests/test_cosim.py):

1. `test_dsl_rtl_cosim_auto_backend_reports_iverilog_when_verilator_missing`
2. `test_dsl_rtl_cosim_auto_backend_prefers_vcs_over_iverilog_when_verilator_missing`

## Local Rerun Loop

When a mixed DSL/external design fails, use this order:

```bash
PYTHONPATH=. pytest -q rtlgen/tests/test_cosim.py -k 'collect_external_artifact_bundle'
PYTHONPATH=. pytest -q rtlgen/tests/test_cosim.py -k 'compile_and_run_with_iverilog_stages_compile_flags'
PYTHONPATH=. pytest -q rtlgen/tests/test_cosim.py -k 'auto_backend'
```

Then rerun the DUT-shaped entry point with the backend you actually care about.

Practical triage:

1. if the emitted RTL cannot find a ROM file, inspect `init_file` staging first
2. if the external leaf does not compile, inspect `verilog_sources`, `include_dirs`, and `defines`
3. if Python/compiled sim passes but emitted RTL fails only on one backend, inspect backend contract assumptions before changing the DSL

## Local VCS Note

The release documentation assumes users run VCS locally when VCS is part of
their verification environment.

Recommended policy:

1. use `rtl_backend="verilator"` for the default local emitted-RTL closure loop
2. use `rtl_backend="vcs"` only when a local VCS installation is available
3. keep artifact staging identical across `iverilog`, `verilator`, and local
   `vcs`: external sources, include trees, defines, and ROM init files must all
   travel with the emitted DUT
4. use the local simulator setup for release-level VCS runs

## Current Boundary

This guide closes the packaging and backend-selection story for mixed designs.

It does not expand the storage support subset by itself.

Still treat these as explicit boundaries unless the support matrix says
otherwise:

1. generic sync-read RAM semantics
2. non-zero read latency storage
3. broad multi-port storage contracts
