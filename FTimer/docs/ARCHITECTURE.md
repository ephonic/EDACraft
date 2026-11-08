# Architecture

`time_engine` is the timing/power library. `edacraft_core` holds the shared design,
library, constraint and timing data model and is embedded in the same source
package. Neither target requires a sibling source checkout.

The input path is Liberty/Verilog/SDC/SPEF → parsers → network/timing graph →
delay calculation → arrival/required propagation → timing and power queries.

| Path | Responsibility |
| --- | --- |
| `src/cli`, `src/tools` | `ftimer`, `lib2ftlib` and optional native DB inspector |
| `src/core`, `include/edacraft` | Shared schemas, design database and SDC parser/writer |
| `src/parser`, `src/liberty` | Netlist, parasitic and library inputs and library serialization |
| `src/network`, `src/graph` | Connectivity, library binding and timing graph |
| `src/dcalc`, `src/parasitics` | NLDM/CCS, RC response and coupling solvers |
| `src/search`, `src/sdc` | Arrival/required propagation, paths and resolved constraints |
| `src/engine` | C++/C facade, scenarios, SI waveform queries and power |
| `src/incremental`, `src/storage` | Dirty tracking and backing storage |
| `python` | Process-based driver, result parsing and SDC construction |

The C++ entry point is `te::TimingEngine`. It can parse its own inputs or attach
to a shared design database for synthesis integration. The runtime network maps
its pin IDs to shared model handles and writes timing snapshots back through
that interface. The public standalone build vendors these shared schemas under
`src/core` and `include/edacraft`.

Power calculation distinguishes physical pins, logical state and electrical net
aliases. Alias names remain queryable after connectivity merging; their activity
follows the canonical network, while disconnected alias records contribute no
additional capacitance or switching power.

SI interfaces can operate on reciprocal coupled RC networks and explicit CCSN
source/stage descriptions. Solver verification and reconstruction of a complete
cell/noise analysis from characterized libraries have different validation scopes;
see [validation](VALIDATION.md).

The public layout folds the development CLI/tool entry points into `src` and
exports the same library targets through `cmake/TimeEngineConfig.cmake.in`.
`cmake/source_manifest.json` records the published files and the correspondence
of the calculation sources to release 0.1.1.
