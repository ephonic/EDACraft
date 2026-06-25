# rtlgen_x Stdlib Support Matrix

This document snapshot is derived from the executable stdlib catalog in
`rtlgen_x.stdlib_catalog`.

Support levels are intentionally conservative:

- `yes`: the surface is explicitly part of the current public closure
- `partial`: the surface exists but still has important boundaries
- `no`: not part of the current public story for that stdlib entry

## Protocol entries

| Entry | Family | Status | DSL | Lowering | Python sim | C++ sim | Emitted RTL | Readable RTL | Python verify | SV/UVM | Analysis | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ReadyValid` | channel | `partial` | yes | partial | partial | partial | partial | no | yes | partial | partial | Bundle authoring is available today, but full downstream semantic closure is still not uniform across every consumer. |
| `ReqRsp` | channel | `partial` | yes | partial | partial | partial | partial | no | yes | partial | partial | Useful for control-plane and transaction datapaths that do not need a full bus protocol. |
| `APB` | control_bus | `partial` | yes | partial | partial | partial | partial | no | yes | partial | partial | Two-phase APB helper path is closed on the verify side; bundle-to-all-consumers closure is still conservative. |
| `AXI4Lite` | control_bus | `partial` | yes | partial | partial | partial | partial | no | yes | partial | partial | Registered response timing and byte-lane semantics are modeled in the verify path. |
| `AXI4Stream` | stream | `partial` | yes | partial | partial | partial | partial | no | yes | partial | partial | Generated-UVM bridge is available for lightweight directed streaming stimulus. |
| `Wishbone` | control_bus | `partial` | yes | partial | partial | partial | partial | no | yes | partial | partial | The verify path distinguishes same-step Wishbone from registered-ack WishboneClocked timing. |
| `AHBLite` | control_bus | `partial` | yes | partial | partial | partial | partial | no | yes | partial | partial | Protocol checking is available, but the full bundle story is still being standardized. |

## Component entries

| Entry | Family | Status | DSL | Lowering | Python sim | C++ sim | Emitted RTL | Readable RTL | Python verify | SV/UVM | Analysis | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `SkidBuffer` | buffer | `partial` | yes | yes | yes | yes | yes | yes | yes | partial | partial | Lowering, simulation, emitted RTL, Python-UVM, and generated directed UVM collateral/runtime bundle are regression-covered locally; broader external-simulator UVM closure remains intentionally partial. |
| `ReadyValidRegister` | buffer | `partial` | yes | yes | yes | yes | yes | yes | yes | partial | partial | Regression-covered through lowering, simulation, emitted RTL, Python-UVM, and generated directed UVM collateral/runtime bundle; broader external-simulator UVM closure remains intentionally partial. |
| `ReadyValidFIFO` | buffer | `partial` | yes | yes | yes | yes | yes | yes | yes | partial | partial | Useful as the current protocol-aware queue primitive for ready/valid datapaths, with lowering, simulation, Python-UVM, and generated directed UVM collateral/runtime bundle now regression-covered locally. |
| `ReadyValidAsyncBridge` | cdc | `partial` | yes | yes | yes | yes | yes | yes | yes | partial | yes | Lowering, Python/C++ multi-clock simulation, Python-UVM, and generated multi-clock UVM collateral are regression-covered; broader external simulator closure remains intentionally partial. |
| `ReqRspQueue` | queue | `partial` | yes | yes | yes | yes | yes | yes | yes | partial | partial | Useful for request-latency decoupling before a fuller protocol-aware queue family exists. |
| `APBRegisterBank` | csr | `partial` | yes | yes | yes | yes | yes | yes | yes | yes | partial | This is the strongest current control-plane stdlib closure for lowering, simulation, and generated-UVM smoke usage; raw async reset release still appears as a CDC warning until a per-domain reset-release wrapper is authored. |
| `AXI4LiteRegisterBank` | csr | `partial` | yes | yes | yes | yes | yes | yes | yes | yes | partial | Generated-UVM directed-sequence closure is available via protocol transfer bridging, and the current synchronous-reset implementation does not introduce a reset-release CDC warning. |
| `WishboneRegisterBank` | csr | `partial` | yes | yes | yes | yes | yes | yes | yes | yes | partial | Closes on the registered-ack Wishbone helper path rather than the simpler same-step mode, and the current synchronous-reset implementation does not introduce a reset-release CDC warning. |
| `SyncFIFO` | queue | `partial` | yes | yes | yes | yes | yes | yes | yes | partial | partial | Lowering, Python/C++ simulation, Python-UVM, and generated directed UVM collateral are regression-covered for the current single-clock FIFO behavior; broader protocol-aware queue family standardization remains lighter here. |
| `AsyncFIFO` | cdc | `partial` | yes | yes | yes | yes | yes | yes | yes | partial | yes | Lowering, Python/C++ multi-clock simulation, Python-UVM, and generated directed multi-clock UVM collateral are regression-covered; broader protocol-aware or randomized UVM closure remains intentionally conservative. |
| `MAC` | arithmetic | `partial` | yes | yes | yes | yes | yes | yes | partial | no | partial | Review-profile readability regression now covers this arithmetic helper; protocol-aware verify/UVM closure is still intentionally lightweight. |
| `SignedMultiplier` | arithmetic | `partial` | yes | yes | yes | yes | yes | yes | partial | no | partial | Readable RTL regression covers the staged payload/valid structure, and PPA analysis can already point at multiplier-heavy hotspots for this style of datapath. |
| `RegisterFile` | storage | `partial` | yes | yes | yes | yes | yes | yes | partial | no | partial | Review-profile readability regression covers explicit decoded reads and writes; memory semantic standardization beyond this helper remains future work. |
| `DualPortRAM` | storage | `partial` | yes | yes | yes | yes | yes | yes | partial | no | partial | Readable RTL regression covers storage declarations and simple dual-port access shape; broader macro-mapping policy is still analysis-first. |
| `LUT` | storage | `partial` | yes | yes | yes | yes | yes | yes | partial | no | partial | Readable RTL regression covers initialization and combinational read shape; larger coefficient-table policies still belong in higher-level design review and PPA analysis. |

## Vip entries

| Entry | Family | Status | DSL | Lowering | Python sim | C++ sim | Emitted RTL | Readable RTL | Python verify | SV/UVM | Analysis | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ReadyValidVIP` | channel | `partial` | no | no | no | no | no | no | yes | partial | yes | Generated-UVM reuse is available for directed stimulus, while the richer closure remains on the Python-VIP/checker side. |
| `ReqRspVIP` | channel | `partial` | no | no | no | no | no | no | yes | partial | yes | The transaction surface is useful today, but full generated-UVM standardization is still in progress. |
| `APBVIP` | control_bus | `partial` | no | no | no | no | no | no | yes | yes | yes | Local Python-VIP and generated-UVM directed smoke closure are both available for the current control-plane path. |
| `AXI4LiteVIP` | control_bus | `partial` | no | no | no | no | no | no | yes | yes | yes | Generated-UVM directed-sequence bridging is available for the current AXI4-Lite register-bank path. |
| `AXI4StreamVIP` | stream | `partial` | no | no | no | no | no | no | yes | partial | yes | Generated-UVM reuse currently targets lightweight directed streaming DUTs rather than a dedicated SV/UVM protocol environment. |
| `WishboneVIP` | control_bus | `partial` | no | no | no | no | no | no | yes | partial | yes | Same-step Wishbone is still distinct from the registered-ack WishboneClocked helper path. |
| `WishboneClockedVIP` | control_bus | `partial` | no | no | no | no | no | no | yes | yes | yes | This is the preferred VIP mode for the current Wishbone register-bank stdlib block. |
| `AHBLiteVIP` | control_bus | `partial` | no | no | no | no | no | no | yes | partial | yes | Python-VIP and checking are available; fuller generated-UVM specialization remains future work. |
