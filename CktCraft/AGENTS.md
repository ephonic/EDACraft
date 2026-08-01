# CktCraft / rfsim — Agent 指南

RF/模拟电路仿真器（C++17，MSVC + CMake + Ninja）。当前版本 v0.2.0。

## 结构

- `src/` — 仿真器核心（parser / circuit / model / assembly / solver / output / cli）
- `src/model/generated/` — Verilog-A 生成模型（`*_gen.cpp/.h` + `generated_registry.cpp`），
  **由 vaParser 产出，改动需同步 codegen 或接受被重新生成覆盖**
- `tools/vaparser/` — Verilog-A → C++ 代码生成器（随主构建产出 `bin/vaParser.exe`，
  lex/yacc 产出物已入库，无需 flex/bison）
- `tools/regen_registry.sh` — 汇总 `*_reg.inc` 重写注册表 AUTO 段
- `models/` — 紧凑模型 `.va` 源
- `tests/` — gtest（26 源，155 case + HEAVY/诊断门控）

## 构建与测试

```cmd
build.bat configure && build.bat build && build.bat test
```

- Release 构建产出：`build/bin/rfsim.exe`、`rfsim_tests.exe`、`vaParser.exe`、`vaDeriv.exe`
- HEAVY 测试默认 skip：`RFSIM_FORCE_HEAVY=1` 启用；诊断 case 用 `RFSIM_FORCE_*`
- 中文用户名路径会破坏 cl.exe 临时文件：构建脚本已把 TMP/TEMP 重定向到 `build/tmp`

## 关键约定（踩过坑）

- **器件模型唯一路径 = 生成模型**（OSDI/OpenVAF DLL 已于 v0.2 移除；
  `.model ... file="*.dll"` 属性兼容解析但忽略）。
- **生成模型使用必须先 `allocateInternalNodes()`**：否则 `nodes_[4..]` 全为 0（地），
  模型退化（漏极看不到栅压）。生产路径 device_factory 自动调用；测试需手动。
- **mod 参数有效值**：bsim4va 的 rdsmod/rgatemod/rbodymod 未设置时是 sentinel
  `-9999999`，内部节点分配判断必须用与 eval 一致的有效值解析
  （`rfsim_bsim4_eff_*`，见 bsim4va_gen.cpp 头部）。
- **残差符号约定**：生成模型 `eval()` 的 `out.f` 是「电流从节点流入器件」（流出为正），
  所有装配路径（DC/瞬态/HB）统一 `F += f`。HB 频域为 `F += +(I + jωQ)`。
- **HB-NL**：非线性装配在 `src/assembly/hb_jacobian.cpp`（IFFT→`DeviceModel::evalHb`
  →FFT + 2NH 精确卷积雅可比）；LM 阻尼失败时**升** λ 且复用装配（skipAssemble）；
  小残差窄谷按 `HbNlOptions.stallAcceptRel` 放宽接受（结果标 `relaxedConvergence`）。
- 生成模型 HB 目前纯阻性（无电荷卷积项），高频强动态请用 `.pss` 交叉验证。

## 新增 Verilog-A 模型

```cmd
build\bin\vaParser.exe models\<m>.va src\model\generated\<name> --format=rfsim
tools\regen_registry.sh
:: 然后全量重新构建
```

## Git

- 主仓 `ephonic/EDACraft`（main）。根目录 `_*.bat`、`conv_grid_*.csv`、`ref/`、`build/`
  均为本地文件（gitignored/untracked），不要提交。
