# FTimer 0.1.1

FTimer is a standalone C++17 static timing and power analysis engine, with a
command-line executable, a C++ library, a C API and a Python driver. The shared
design, library and constraint data model is included in this directory;
building FTimer does not require fsyn or another EDACraft checkout.

## Features

- Liberty text and compiled `.ftlib` libraries, gate-level Verilog, SDC and SPEF inputs.
- Setup/hold timing, pin arrival and slew queries, timing exceptions, timing checks,
  design-rule reports, path reporting and incremental updates.
- NLDM and CCS delay models, RC waveform calculation, coupled-RC waveform solving
  and explicit CCSN analysis interfaces.
- Leakage, internal and switching power, per-cell/net detail, explicit activity,
  SAIF/VCD input through Python, and activity annotation coverage.
- An installable CMake SDK and Python-defined timing constraints.

Supported mechanisms and measured accuracy depend on the library, constraints,
activity model and analysis configuration. See [validation scope](docs/VALIDATION.md)
for the tested release and the remaining SI qualification limits.

## Build

The validated platform is Linux x86_64. Requirements are CMake 3.20 or newer, a
C++17 compiler, threads and zlib development headers. TBB is optional. The Python
driver requires Python 3.9 or newer and uses the executable boundary.

From the EDACraft repository root:

```sh
cmake -S FTimer -B build/ftimer -DCMAKE_BUILD_TYPE=Release -DTIME_ENGINE_ENABLE_TBB=OFF
cmake --build build/ftimer -j 4
./build/ftimer/bin/ftimer -help
```

The build produces `bin/ftimer`, `bin/lib2ftlib` and the timing/model libraries.
Copying `FTimer/` on its own is also supported; use `cmake -S . -B build` inside
that directory. The native `.db` inspection target is experimental and disabled
by default; normal use starts with Liberty text or `.ftlib` libraries.

## Run the examples

The included Liberty files are small synthetic models, so these examples do not
require a foundry library or a commercial tool.

```sh
./build/ftimer/bin/ftimer -lib FTimer/examples/simple/cells.lib \
  -verilog FTimer/examples/simple/design.v -sdc FTimer/examples/simple/design.sdc \
  -report 5 -report_min 5

export FTIMER_BIN="$PWD/build/ftimer/bin/ftimer"
export PYTHONPATH="$PWD/FTimer/python${PYTHONPATH:+:$PYTHONPATH}"
python3 FTimer/examples/simple/run.py
python3 FTimer/examples/power/run.py
```

For your own design, supply matching libraries, a mapped gate netlist, constraints
and, when available, an extracted SPEF:

```sh
./build/ftimer/bin/ftimer -lib cells.lib -verilog design.v -sdc design.sdc \
  -spef design.spef -report 10 -report_min 10 -power 1e9 -activity 0.1 -power_detail
```

`-power` takes frequency in Hz; `-activity` is both-edge transitions per cycle.
Per-net annotations take transitions per second and probability of logic one.
Use the same activity assumptions when comparing power across tools.

## Install and use the SDK

```sh
cmake --install build/ftimer --prefix "$PWD/install/ftimer"
source install/ftimer/env.sh
ftimer -help

cmake -S FTimer/examples/cpp -B build/ftimer-consumer \
  -DCMAKE_PREFIX_PATH="$PWD/install/ftimer"
cmake --build build/ftimer-consumer -j 4
./build/ftimer-consumer/ftimer_consumer FTimer/examples/simple/cells.lib \
  FTimer/examples/simple/design.v FTimer/examples/simple/design.sdc
```

CMake consumers use `find_package(TimeEngine CONFIG REQUIRED)` and link
`TimeEngine::time_engine`. The C++ facade is
[`include/time_engine/engine.hh`](include/time_engine/engine.hh); the C entry
points are in [`include/time_engine/api_c.h`](include/time_engine/api_c.h).
See the [Python guide](python/README.md) for constraints, queries and power.

## Directory layout

| Directory | Contents |
| --- | --- |
| `src/` | Engine, parsers, delay/RC solvers, search, power, CLI/tools and embedded shared model |
| `include/` | Public C/C++ interfaces and shared data model headers |
| `docs/` | Architecture, usage, release notes and validation scope |
| `python/` | CLI driver, SDC builder and Python constraint example |
| `examples/` | Synthetic timing/power examples and an SDK consumer |
| `cmake/` | Source lists, embedded model target, SDK export and source manifest |

This public snapshot contains the principal source directories. Regression
archives, build caches, installed binaries, private process libraries and
commercial EDA tools are maintained outside this snapshot.

## Version and validation

Version: **0.1.1**, published source snapshot dated **2026-11-08**. The timing and
power implementation is taken from the validated standalone release and remains
shared with the development `ftimer_craft` used by fsyn. See
[release notes](docs/RELEASE_NOTES.md), [architecture](docs/ARCHITECTURE.md) and
[validation](docs/VALIDATION.md). Licensing follows the repository
[LICENSE](../LICENSE).
