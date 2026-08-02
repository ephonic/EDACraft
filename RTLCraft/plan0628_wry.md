# plan0628_wry: 2026-06-28 RTLCraft 收口总计划

日期：2026-06-28

工作目录：`C:\Users\F先生\fudan-work\RTLCraft`

## 1. 总目标

0628 的工作目标，是把 0627 已形成的 foundation contract gate 从可执行基础设施推进到真实设计、真实 seed 和完整回归收口。工作从 `gpu_sm/gpgpu_stack` seed gate 接入开始，先解决 legacy import、package-level API 和真实模块 authoring hygiene；随后推进到 `rv32` hygiene、GPGPU seed artifact 落盘；最后进入 contract cleanup 和 full regression 收口。

演进路径可以概括为：

```text
seed gate / real-module cleanup
  -> rv32 hygiene / seed artifact delivery
  -> Simulator / blackbox / fft256 contract cleanup
  -> full regression no failure, explicit external dependency skip only
```

本计划的最终边界不是重跑或重做已经完成的实现任务，而是沉淀已经形成的最终交付口径、验收矩阵、风险和后续建议。

## 2. 工作脉络

### 前期：seed gate 与真实模块入口

目标：

- 将 `plan0627_wry` 形成的 foundation gate 接到真实 `gpu_sm/gpgpu_stack` seed flow。
- 恢复必要 legacy compatibility surface，包括 `rtlgen_x` 路径、top-level `rtlgen.Simulator` 和 constraint framework package-level exports。
- 修复 `earphone_sram256k`、`earphone_simd16` 等真实模块最直接的 authoring hygiene blocker。
- 收掉 initial block 和 packed struct 的小语义残留。

关键动作：

- 增加窄口径 `rtlgen_x` compatibility shim。
- 恢复 `rtlgen.Simulator` 与 constraint framework public API。
- 让 `gpgpu_stack` seed flow 能跑，并生成 `GpuSm()` foundation report。
- 将 SRAM/SIMD helper wire 注册到 `self.*`，避免 `UntrackedSignal`。
- 修复 initial block state / array init 与 packed struct field runtime 输出问题。
- 同步 seed gate 贡献记录。

完成状态：

- foundation baseline、contract framework、seed flow、GPU SM functional/arch、SRAM/SIMD/RV32 focused UVM、docs/catalog 等 targeted gates 进入通过状态。
- 当时剩余 `dsl_import` focused failure 已归类为 `earphone_rv32` local helper wire 的 authoring-intent blocker。

后续承接项：

- `rv32` helper wire hygiene。
- GPGPU seed artifact 从内存结果推进到可落盘交付物。
- full regression 剩余 failure 重新归类。

### 中段：`rv32` hygiene 与 seed artifact 落盘

目标：

- 收掉 `earphone_rv32` 的 `UntrackedSignal` authoring hygiene blocker。
- 把 GPGPU seed flow 的 architecture / PPA / foundation report 固化成可落盘 artifact bundle。
- 对 full regression 剩余失败重新归类，并选择一个低风险语义残留收口。

关键动作：

- 将 `earphone_rv32` 中 diagnostics 指名的 execute、branch、divider、multiplier helper wires 注册到 `self.*`。
- 增加并导出 `write_gpu_sm_seed_artifacts(result, output_dir)`。
- 写出 `architecture.md`、`ppa.md`、`foundation.md`、`foundation.json`，并用 focused regression 校验 header 和 foundation JSON diagnostics schema。
- 修复 bundle bulk-connect 中可选 `clk/rst` extra ports 与无对应 child port 的边界；其它未知端口仍走 `UnknownSubmodulePort` hard gate。

完成状态：

- `rv32` targeted import/lowering 通过。
- SRAM/SIMD/RV32 UVM focused gate、SRAM/SIMD/RV32/initial/packed DSL focused gate、foundation baseline、seed artifact gates、docs/catalog gate 均通过。
- full regression 剩余失败缩小为三个已归类 contract / dependency policy 问题。

后续承接项：

- top-level `rtlgen.Simulator` 的 public API contract 与旧 removed-surface 测试冲突。
- external parameterized blackbox output direct mapping vs helper-wire contract 冲突。
- `fft256` 缺失 `design_scripts.design_fft` 时仍表现为裸 `ModuleNotFoundError`。

### 收口：contract cleanup 与 full regression

目标：

- 把前序留下的三个已归类 failure 转成明确 contract / dependency policy。
- 让 full `test_dsl_import.py` 无 failure。
- 让 full `test_verify_uvm.py` 无 failure，或仅保留明确的 external dependency skip。
- 保护已修 focused gates，并同步文档与 contribution。

关键动作：

- 将 `rtlgen.Simulator` 明确为 top-level narrow compatibility wrapper，旧 AST/JIT simulator surface 仍保持 removed。
- 为 external parameterized blackbox output 实现窄口径 direct passthrough：仅 external_verilog child output 直连 same-width parent `Output` 时允许 `.dout(dout)`；普通 DSL submodule output 仍保持 helper-wire plus assign。
- 将 `earphone_fft256` 的 `design_scripts.design_fft` 定义为外部 FFT generator dependency：缺失时显式 skip，存在时必须真实运行。
- 重跑 full `dsl_import`、full `verify_uvm` 和 protected gates。
- 更新 `rtlgen/README.md`、`earphone/README.md` 与 contribution 记录。

完成状态：

- full `rtlgen\tests\test_dsl_import.py`：`205 passed, 1 skipped`。
- full `rtlgen\tests\test_verify_uvm.py`：`58 passed, 1 skipped`。
- 保留的 skip 是 `design_scripts.design_fft` 未安装导致的显式外部依赖 skip。
- 本地 required work 已收口。

## 3. 最终 contract 决策

### `rtlgen.Simulator`

`rtlgen.Simulator` 是 top-level narrow compatibility wrapper，用于迁移和旧 seed-gate 兼容。它不代表恢复完整历史 AST/JIT simulator。

最终口径：

- `rtlgen.Simulator` 存在，并指向 `rtlgen.dsl.sim.Simulator`。
- wrapper 可通过 `reset/poke/peek/step` 驱动 lowered DSL module 的 `PythonSimulator` 路径。
- `rtlgen.dsl.Simulator`、`rtlgen.dsl.DSLSimValidator` 等旧 DSL AST/JIT surface 仍不重新导出。
- `rtlgen.dsl.sim_jit`、`rtlgen.dsl.dsl_sim.DSLSimValidator(...)`、`rtlgen.dsl.sim.SimValue(...)` 等历史 helper 仍保持 removed/error surface。
- 新代码推荐使用 `lower_dsl_module_to_sim(...)` + `PythonSimulator` 或 compiled simulator path。

### external parameterized blackbox output

最终口径是窄口径 direct passthrough：

- 仅当 child 是 `external_verilog`，child output 被直接赋给 same-width parent `Output`，且没有 slice/concat/额外转换时，emitter 允许直接端口映射，例如 `.dout(dout)`。
- 普通 DSL submodule output、复杂表达式、slice/concat、多 consumer、非 parent output direct mapping 仍保持 helper-wire plus assign 语义。
- `UnknownSubmodulePort`、bundle authoring-intent 和其它 hard gate 不放宽。

### `fft256`

`earphone_fft256` 依赖外部 FFT generator：

- 依赖名：`design_scripts.design_fft`。
- 依赖缺失时，对应 FFT256 UVM runtime case 显式 skip，skip reason 必须包含 `design_scripts.design_fft`。
- 依赖存在时必须真实运行 wrapper path，不允许无条件 skip，也不伪造 FFT 设计通过。
- 这不是本地 RTL/UVM 生成失败，而是外部生成器可用性策略。

### authoring-intent

本日工作不放宽以下 contract：

- `UntrackedSignal` 仍要求跨 lowering 捕获的 helper wire 注册到 `self.*`。
- `UnknownSubmodulePort` 仍是 hard gate。
- bundle extra ports 仅对 child 不暴露的常见 optional `clk/rst` 做窄处理；其它未知端口仍失败。
- storage/reset/CDC/readability foundation gate 的 report schema 与 diagnostics 字段仍保留。

### seed artifact

GPGPU seed artifact bundle 的交付边界：

- seed flow 仍可返回内存 artifact。
- `write_gpu_sm_seed_artifacts(result, output_dir)` 可将结果落盘。
- 最小文件集合为 `architecture.md`、`ppa.md`、`foundation.md`、`foundation.json`。
- `foundation.json` 必须保留 diagnostics schema，包含 rule/source/object/suggested_fix 等用于后续汇总的字段。

## 4. 最终验收矩阵

以下矩阵汇总最终有意义的验收命令和记录结果。本次文档整理未重新执行测试。

| 命令 | 最终结果 | 说明 |
| --- | --- | --- |
| `python -m pytest -q rtlgen\tests\test_dsl_import.py` | `205 passed, 1 skipped` | full DSL import regression 无 failure。 |
| `python -m pytest -q rtlgen\tests\test_verify_uvm.py` | `58 passed, 1 skipped` | full UVM regression 无 failure；唯一 skip 为 `design_scripts.design_fft` 外部依赖缺失。 |
| `python -m pytest -q rtlgen\tests\test_dsl_import.py -k "Simulator or simulation_surfaces"` | `19 passed, 187 deselected` | `rtlgen.Simulator` compatibility wrapper contract 收口。 |
| `python -m pytest -q rtlgen\tests\test_dsl_import.py -k "blackbox or external_parameterized"` | `2 passed, 204 deselected` | external parameterized blackbox direct-output contract 收口。 |
| `python -m pytest -q rtlgen\tests\test_verify_uvm.py -k "fft256"` | `1 skipped, 58 deselected` | 本地缺失 `design_scripts.design_fft` 时显式 skip。 |
| `python -m pytest -q rtlgen\tests\test_dsl_import.py -k "UnknownSubmodulePort or bundle"` | `15 passed, 191 deselected` | protected authoring-intent gate 维持通过。 |
| `python -m pytest -q rtlgen\tests\test_dsl_import.py -k "rv32"` | `2 passed` | `rv32` 不再停在 `UntrackedSignal`。 |
| `python -m pytest -q rtlgen\tests\test_dsl_import.py -k "sram256k or simd16 or rv32 or initial_block or packed_struct"` | `12 passed` / 后续记录为 `12 passed, 194 deselected` | real-module DSL focused gate。 |
| `python -m pytest -q rtlgen\tests\test_verify_uvm.py -k "sram256k or simd16 or rv32"` | `3 passed` / 后续记录为 `3 passed, 56 deselected` | real-module UVM focused gate。 |
| `python -m pytest -q gpgpu_stack\tests\test_seed_flow.py gpgpu_stack\tests\test_seed_foundation_gate.py` | `5 passed` | seed artifact gates。 |
| `python -m pytest -q rtlgen\tests\test_readability_contract.py rtlgen\tests\test_foundation_contract.py rtlgen\tests\test_cdc.py` | `52 passed` | readability/foundation/CDC protected gates。 |
| `python -m pytest -q rtlgen\tests\test_dsl_docs.py rtlgen\tests\test_stdlib_catalog.py` | `10 passed` | docs/catalog gate。 |
| `python -m pytest -q tests\test_contract_framework.py gpgpu_stack\tests\test_seed_flow.py gpu_sm\tests\test_arch.py gpgpu_stack\tests\test_seed_foundation_gate.py` | `24 passed` | seed-gate and compatibility focused suite。 |
| `python -m pytest -q gpu_sm\tests\test_functional.py` | `9 passed, 2 skipped` | GPU SM functional focused gate。 |

## 5. 风险与后续

- `design_scripts.design_fft` 未安装时，`fft256` 仍是显式 skip。若后续安装或提供该 generator，需要重跑 `python -m pytest -q rtlgen\tests\test_verify_uvm.py -k "fft256"` 和 full `python -m pytest -q rtlgen\tests\test_verify_uvm.py`，把 skip 转成真实运行结果。
- blackbox direct-output path 是窄实现。未来 slice、concat、multi-consumer、非 parent output 或普通 submodule direct mapping 不应隐式扩大，需要单独 contract 决策和 focused regression。
- `rtlgen.Simulator` 只是 migration wrapper。不要把它解读为恢复旧 AST/JIT simulator，也不要在新代码里继续扩大旧 API 依赖。
- authoring-intent gate 仍然是边界：`UntrackedSignal`、`UnknownSubmodulePort`、bundle hard gate、storage/reset/CDC/readability diagnostics 不应为了让旧设计通过而放宽。
- 当前环境曾记录到 `C:\Users\F先生\fudan-work` 下可见 `.git` 目录，但 `git status` 不识别为 repository。记录方式以手动列出 touched files 和测试命令为准，避免任何 rollback-style 操作。
- 若后续接入 CI 或提供外部 FFT generator，需要把 explicit skip 和真实依赖可用状态分开报告。

## 6. 一句话结论

0628 最低可交付目标已经收口：真实 seed、real-module hygiene、seed artifact、contract cleanup 和 protected gates 均已完成；本地 full regression 记录为无失败，`verify_uvm` 仅保留 `design_scripts.design_fft` 缺失导致的显式外部依赖 skip。
