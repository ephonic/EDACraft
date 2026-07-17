# Phase D 完成状态 — 波形输出多格式 + 增强 waveview（需求 4）

日期：2026-07-17。承接 Phase A+B+C（需求 6、7、1、3、2、5）。

## TL;DR

| 维度 | 状态 |
| --- | --- |
| 默认全量回归 | **170 tests, 145 PASSED / 0 FAILED / 51 SKIPPED**（C 后 139 + D 新增 6 个 WaveformExport 测试） |
| C++ 多格式导出 | CSV（原有）+ ngspice rawfile（ASCII）+ JSON，`.options format=` 选择 |
| 增强 waveview.py | 多格式 reader（CSV/raw/JSON 自动识别）+ FFT + XY(Lissajous) + 多面板 + 对数坐标 + PNG 导出 |

## 落地清单

### 新增文件

| 文件 | 作用 |
| --- | --- |
| `src/output/waveform_export.{hpp,cpp}` | `WaveFormat` 枚举 + `writeWaveformCsv/Rawfile/Json` + `writeWaveformFile`（按格式写文件）+ `parseWaveFormat` + `waveformSignalNames` |
| `tests/test_waveform_export.cpp` | 6 测试（格式解析往返/信号名含不含 Circuit/CSV/raw/JSON 内容校验） |

### 修改文件

| 文件 | 改动 |
| --- | --- |
| `src/cli/main.cpp` | `resolveWaveFormat()` 解析 `.options format=<csv\|raw\|json\|all>` 与 `.options post=2`；PSS 波形导出从内联 CSV 改为 `writeWaveformFile`（按格式） |
| `src/CMakeLists.txt` + `tests/CMakeLists.txt` | 注册 waveform_export 源/测试 |
| `tools/waveview.py` | 全面增强：多格式 reader（CSV/rawfile/JSON 自动识别）+ FFT 频谱 + XY/Lissajous + 多面板 + 对数坐标 + PNG 导出 + 信号筛选 + `--list` |

## 关键设计决策

### C++ 多格式导出（需求 4）

**原状**：PSS 波形硬编码导出 CSV（`time,v1,v2,...`），无其他格式。

**增强**：`waveform_export` 模块支持三种格式：
- **CSV**：rfsim 原生（向后兼容原 waveview.py）。
- **Rawfile**：ngspice/ltx ASCII "raw" 格式（Title/Plotname/Flags/Variables/Values），兼容 ngspice/GTKWave 等工具。
- **JSON**：结构化（`{title, signals, points:[{t, v}]}`），便于 web 端/脚本消费。

CLI `.options format=raw|json|csv|all` 或 `.options post=2`（HSPICE 风格→raw）选择；默认 csv。信号名优先用 Circuit 节点名（`v(in)`），否则 `vN`。

### 增强 waveview.py

**原状**：仅读 CSV，单图叠加，无 FFT/XY/对数/导出。

**增强**：
- **多格式 reader**：`detect_and_read` 按扩展名 + 内容嗅探自动识别 CSV/raw/JSON。
- **FFT 频谱**：`--fft SIG` 对单信号做 Hanning 窗 FFT，显示频域幅度（PSS/AC 分析常用）。
- **XY/Lissajous**：`--xy SIG_X SIG_Y` 显示两信号的 XY 图（环路分析、传输特性）。
- **多面板**：`--panel` 每信号一个子图（信号多时更清晰）。
- **对数坐标**：`--logx`/`--logy`（AC 频率响应）。
- **PNG 导出**：`--export out.png`（无显示器环境/CI）。
- **信号筛选**：位置参数选择信号；`--list` 列出全部信号。
- 依赖：matplotlib + numpy（文档化 `pip install`）。

## 交付标准核对

- [x] 默认 ctest **145/0/51** PASS（无退步）
- [x] C++ CSV/rawfile/JSON 三格式导出 + `.options format=` 接线
- [x] waveview.py 多格式 reader + FFT + XY + 多面板 + 对数 + PNG 导出
- [x] WaveformExport 单元测试 6/6 PASS（格式解析/信号名/三格式内容校验）
- [x] waveview.py 语法校验通过（py_compile）；CSV reader 逻辑实测通过

## 未做（控制范围）

- **二进制 rawfile / .tr0/.ac0（HSPICE 私有）**：需逆向格式，本轮只做 ASCII raw + JSON（更通用）。
- **MT0/MT1（HSPICE measure）**：measure 输出格式待 measure 功能扩展时一并。
- **Touchstone .sNp 导出**：S 参数模块（`sparam/`）已有 Touchstone **读取**；波形导出主要是时域，S 参数导出属另一通路。

## Phase A+B+C+D 总结（全部 7 需求）

| Phase | 需求 | 状态 |
| --- | --- | --- |
| A1 求解器抽象+自动选择 | 6 | ✅ |
| A2 HB/Shooting 收敛加固 | 7 | ✅ |
| B1 器件 bypass 强化 | 1 | ✅ |
| B2 multi-rate 增强 | 3 | ✅ |
| C2 表达式/参数化增强 | 5 | ✅ |
| C1 `.lib` corner 选择 | 2 | ✅（基础）；`level=54` 映射推迟 |
| D 波形输出多格式 + waveview | 4 | ✅ |

回归 **145/0/51**，新增 34 个单元测试，全程无退步。

## 后续（推迟项）

- **C1 `level=54` → OSDI 参数映射表**：需独立 sprint（~300 参数映射 + PDK 端到端与 HSPICE 对比验证）。
- **真正异步 multi-rate 时间网格**（B2 完全版）：每 cluster 独立 dt + 边界插值耦合，需重构积分循环。
- **二进制 rawfile / HSPICE .tr0**：逆向格式后补。
