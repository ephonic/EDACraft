# rtlgen Release Preparation

This document records the release-preparation data for replacing the current
`main/RTLCraft` content with the clean-core `rtlgen` release.

## Release Intent

The release should publish the current `rtlgen_x` capability set under the
public package name `rtlgen`.

The release is a clean engineering toolkit:

1. DSL authoring
2. lowering and executable simulation
3. compiled C++ simulation
4. SystemVerilog emission
5. local RTL simulator smoke / closure
6. verification collateral generation
7. CDC/report helpers
8. PPA and architecture exploration
9. JPEG datapath worked example and reusable cookbook

It is not a release of the historical prompt/workflow stack.

## Required Rename

Before final packaging:

1. rename directory `rtlgen_x/` to `rtlgen/`
2. rewrite Python imports from `rtlgen_x` to `rtlgen`
3. rewrite docs from `rtlgen_x` to `rtlgen`
4. rewrite environment variable prefixes from `RTLGEN_X_` to `RTLGEN_` where
   the feature remains in the release
5. remove release documentation for remote-login VCS flows

The current working tree still contains both historical `rtlgen/` and
`rtlgen_x/` directories. The release package should take the `rtlgen_x`
clean-core implementation as the new `rtlgen` package.

## Include In Release

Recommended release payload:

```text
README.md
README_CN.md
Tutorial.md
Tutorial_CN.md
RELEASE_PREP.md
release_manifest.json
pyproject.toml
LICENSE

rtlgen/                         # renamed from current rtlgen_x/
  archsim/
  dsl/
  ppa/
  sim/
  verify/
  tests/
  README.md
  DSL_SEMANTICS.md
  DSL_SUPPORT_MATRIX.md
  STDLIB_SUPPORT_MATRIX.md
  JPEG_DATAPATH_COOKBOOK.md
  MIXED_DESIGN_COSIM_GUIDE.md

jpeg_decoder/
  README.md
  dsl_modules.py
  tests/
```

Optional examples can be included only if they are clean, documented, and have
small rerun commands.

## Exclude From Release

Exclude these directories from the release payload:

1. `skills/`
2. `tools/`
3. historical `rtlgen/` implementation after it has been replaced by the
   clean-core package
4. `generated*/`
5. `generated_skill_ppa*/`
6. `build/`
7. `.venv/`
8. `.pytest_cache/`
9. temporary probe directories such as `tmp_*`
10. simulator binaries and scratch outputs
11. downloaded third-party source trees such as `verilator-master/`
12. old paper/slide build artifacts
13. historical audit notes such as `rtlgen/audit*.md`

## Remote VCS Policy

Release documentation should not require or advertise remote SSH/VCS flows.

Allowed release wording:

1. use local `vcs` when available
2. use `verilator` as the preferred open local emitted-RTL closure backend
3. use `iverilog -g2012` as compile smoke / compatibility backend
4. use Python and compiled C++ simulators as the primary semantic closure path

Do not include:

1. hard-coded hosts
2. SSH commands
3. remote cache instructions
4. remote farm setup instructions

## Documentation Set

Required release documents:

1. `README.md` - English overview and design philosophy
2. `README_CN.md` - Chinese overview and design philosophy
3. `Tutorial.md` - English best-practice tutorial
4. `Tutorial_CN.md` - Chinese best-practice tutorial
5. `rtlgen/README.md` - package-level capability reference after rename
6. `rtlgen/DSL_SEMANTICS.md` - DSL semantic contract
7. `rtlgen/DSL_SUPPORT_MATRIX.md` - support matrix
8. `rtlgen/STDLIB_SUPPORT_MATRIX.md` - stdlib support matrix
9. `rtlgen/JPEG_DATAPATH_COOKBOOK.md` - datapath pattern cookbook
10. `rtlgen/MIXED_DESIGN_COSIM_GUIDE.md` - local mixed-design packaging/cosim guide
11. `jpeg_decoder/README.md` - worked-example rerun guide

## pyproject Changes For Final Release

Current `pyproject.toml` still reflects historical packaging. Before publishing:

1. set `[project].name` to `rtlgen`
2. update the description to describe the clean-core DSL/sim/verify/PPA toolkit
3. make `README.md` the project readme
4. restrict package discovery to the new `rtlgen` package
5. remove `skills*` from package discovery
6. ensure tests discover the release test paths

Recommended package discovery:

```toml
[tool.setuptools.packages.find]
include = ["rtlgen*"]
exclude = [
    "tests*",
    "jpeg_decoder*",
    "skills*",
    "tools*",
    "design_scripts*",
    "generated*",
]
```

Whether `jpeg_decoder` is packaged as importable Python or shipped as an
example directory should be decided explicitly during final packaging.

## Validation Before Release

Minimum validation after rename:

```bash
PYTHONPATH=. pytest -q rtlgen/tests/test_dsl_import.py -k 'round_shift or signed_shift or signed_unsigned or storage_contract or authoring_intent'
PYTHONPATH=. pytest -q rtlgen/tests/test_cosim.py -k 'collect_external_artifact_bundle or compile_and_run_with_iverilog_stages_compile_flags or auto_backend'
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_idct_basic.py jpeg_decoder/tests/test_cpp_idct.py jpeg_decoder/tests/test_dequant_idct.py jpeg_decoder/tests/test_cpp_entropy_dequant.py jpeg_decoder/tests/test_verilog.py
python -m compileall -q rtlgen jpeg_decoder
```

Recommended broader validation:

```bash
PYTHONPATH=. pytest -q rtlgen/tests
PYTHONPATH=. pytest -q jpeg_decoder/tests
```

## Current Known Boundaries

These are release boundaries, not accidental omissions:

1. arbitrary multi-port memory contracts are not a stable emitted-RTL feature
2. arbitrary non-zero read latency storage is limited / fail-fast
3. broad macro mapping is out of scope
4. `iverilog` is smoke / compatibility, not universal SystemVerilog signoff
5. PPA reports are early engineering guidance, not final implementation signoff
6. CDC analysis is report-oriented and pattern-aware, not a full formal proof

## Final Publishing Steps

1. create a clean release branch
2. remove excluded directories and generated scratch files
3. replace historical `rtlgen/` with the selected clean-core content from
   current `rtlgen_x/`
4. rewrite imports/docs/env prefixes
5. update `pyproject.toml`
6. run validation
7. tag the release
8. replace the target `main/RTLCraft` content
