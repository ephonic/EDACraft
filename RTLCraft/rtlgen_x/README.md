# rtlgen_x

`rtlgen_x` is the clean-core reboot area for RTLCraft.

It intentionally keeps only capability-oriented code:

1. lightweight generic architecture simulation
2. a reusable DSL kernel for structural/behavioral hardware modeling
3. local executable design model for the compiled simulator
4. simulator backend scaffolding for a compiled C++ execution path

It intentionally does **not** carry over:

1. document-generation flow
2. multi-layer authored IR workflow
3. approval-gate orchestration
4. review bundle logic
5. shared contracts between tools

The first baseline here is small but executable:

- `archsim/` provides behavior-level and cycle-level architecture simulation
- `archsim/` models bandwidth-aware service timing for memory/interconnect/datapath stages, so `bytes_per_token` can affect both behavior-level and cycle-level throughput
- `archsim/` now also provides reusable reference scenarios for CPU, GPU, NPU, controller, and streaming datapath exploration
- `dsl/` provides the imported legacy RTL DSL kernel under the `rtlgen_x` namespace, including Verilog emission, Python simulation, linting, protocols, RAM wrappers, and DSL simulation validation
- `sim/` provides a self-contained compiled-simulator model, Python reference runtime, C++ emitter, compile/load runtime, and benchmark helpers
- `sim/` also provides compiled-vs-RTL differential cosim hooks for legacy DSL modules via `iverilog`
- `ppa/` provides a first-pass structural/runtime PPA advisor for executable modules and architecture simulations
- `verify/` provides directed/streaming verification, SystemVerilog UVM collateral export, and a Python UVM-style execution framework on top of the local simulators
- `tests/` regression-locks the new clean baseline

Minimal benchmark entry points are available directly from `rtlgen_x.sim`:

- `build_stress_module()`
- `generate_stress_input_buffer(...)`
- `generate_stress_inputs(...)`
- `benchmark_compiled_speedup(...)`
- `benchmark_streaming_capacity(...)`

Architecture exploration entry points:

- `build_all_reference_scenarios()`
- `build_all_advanced_scenarios()`
- `build_cpu_in_order_scenario(...)`
- `build_gpu_throughput_scenario(...)`
- `build_npu_systolic_scenario(...)`
- `build_controller_scenario(...)`
- `build_streaming_datapath_scenario(...)`
- `build_cache_hierarchy_scenario(...)`
- `build_dma_copy_scenario(...)`
- `build_gpu_warp_cluster_scenario(...)`
- `build_npu_dataflow_scenario(...)`
- `queue_stage(...)`, `controller_stage(...)`, `memory_stage(...)`, `interconnect_stage(...)`, `compute_stage(...)`, `datapath_stage(...)`
- composite stage-group helpers: `cache_hierarchy(...)`, `dma_engine(...)`, `warp_cluster(...)`, `dataflow_array(...)`
- `run_stage_capacity_sweep(...)`, `run_stage_initiation_interval_sweep(...)`, `run_stage_latency_sweep(...)`, `run_stage_queue_depth_sweep(...)`, and `run_stage_bandwidth_sweep(...)` for what-if exploration
- `rank_capacity_upgrades(...)`, `rank_initiation_interval_upgrades(...)`, `rank_latency_upgrades(...)`, `rank_queue_depth_upgrades(...)`, and `rank_bandwidth_upgrades(...)` for quick bottleneck triage

High-throughput simulator entry points:

- `pack_u64_numpy(...)` for contiguous `numpy.uint64` packed inputs
- `pack_u64_numpy_rows(...)` for 2D `(cycles, inputs)` matrices
- `pack_u64_words(...)` to pre-pack row-major inputs once
- `CompiledSimulator.run_batch_buffered(...)` for zero-copy packed batches
- `CompiledSimulator.run_batch_matrix(...)` for 2D `numpy.uint64` batches
- `CompiledSimulator.iter_batch_buffered(...)` for chunked streaming with bounded memory

High-capacity verification entry points:

- `run_streaming_test(...)` for chunked vector-driven scoreboard checking
- `run_streaming_check(...)` for online expected-value checking without materializing all vectors
- `run_streaming_check_adaptive(...)` for chunked checking that replays only the suffix needed to stop at the failure budget
- `max_failures`, `failure_block_cycles`, and `trace_stride` to trade off precision vs throughput
- `trace_sink` to stream sampled trace points into custom logging/reporting sinks

Verification bridge entry points:

- `generate_uvm_collateral(...)` to export SystemVerilog UVM skeletons and a Python reference model from `SimModule`
- `write_uvm_collateral(...)` to materialize generated SV/Python verification collateral
- generated collateral now also includes a minimal Python DPI helper and C DPI shim alongside the SV scoreboard hook
- generated SV scoreboards include a DPI-style predictor hook that points at the emitted Python reference model path
- `run_python_uvm_test(...)` to execute a lightweight UVM-style environment directly on `PythonSimulator` or `CompiledSimulator`
- `run_legacy_rtl_cosim(...)` to compare compiled execution against emitted RTL with a race-free `iverilog` testbench
- `PythonUvmSequenceLibrary` to compose reusable local sequence sets
- `PythonUvmCoverage` to collect transaction/input/output bins during local regressions
- `dump_python_uvm_triage(...)` to write JSON failure/trace/coverage bundles from Python-side UVM runs
- `batch_cycles` on `run_python_uvm_test(...)` to enable chunked batch execution on simulators/reference models that expose batch paths

DSL capability entry points:

- `rtlgen_x.dsl` re-exports the imported legacy DSL kernel so existing module-building patterns can be reused under the new namespace
- `VerilogEmitter` / `Simulator` / `DSLSimValidator` cover emit, execute, and validate loops for DSL-authored modules
- `Bundle`, `AXI4*`, `APB`, `Wishbone`, `SinglePortRAM`, `SimpleDualPortRAM`, `FSM`, `SyncFIFO`, and related helpers are available directly from `rtlgen_x.dsl`

PPA entry points:

- `analyze_module_ppa(...)`
- `analyze_architecture_ppa(...)`
- `advise_ppa(...)`
- architecture-side PPA recommendations now attach local sweep evidence so the report can point at whether a bottleneck is more sensitive to capacity, II, latency, queue depth, or bandwidth
