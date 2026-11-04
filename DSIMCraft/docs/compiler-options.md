# C++ 编译器与选项

DSIM 先将 RTL/门级模型降低成 C++，再调用 C++ 编译器。`--cxx PATH` 选择编译器，重复的 `--cxx-flag ARG` 按顺序传递单个参数；使用 argv 调用，不执行 shell。选项放在构建配置指定的默认参数之后、生成源码及输出路径之前，因此 `-O3` 可覆盖默认优化级别；实际默认参数可通过 `--help` 查看。

```sh
source /opt/intel/oneapi/setvars.sh --force
dsim --top tb rtl.sv tb.sv -o simv --cxx icpx \
  --cxx-flag -O3 --cxx-flag -xHost --cxx-flag -ipo \
  --cxx-flag -fp-model=strict
./simv
```

也可使用 GCC：`--cxx c++ --cxx-flag -O3 --cxx-flag -march=native`。这些本机指令集选项生成的程序可能不能移到其他 CPU；早期发布默认使用系统 `c++ -O2`（下文说明新的构建配置）。选项由用户选择，应避免破坏仿真语义的浮点优化。编译失败时原有目标可执行文件保持完整。`--emit-only` 只生成 C++，不会运行所选编译器。

只用 Intel 编译器重编 DSIM 前端，并不会改变已有仿真可执行程序。运行时性能比较需要重编实际生成的 C++；M106 保留同一份 M105 C++、完整原始工作量及校验和，再比较编译选项，见 [测量记录](../validation/m106-intel-parallel/README.md)。

oneMKL 提供 BLAS、稀疏矩阵、FFT、向量数学等计算接口（[Intel 官方范围](https://www.intel.com/content/www/us/en/docs/onemkl/developer-reference-c/2026-0/onemkl-library-overview.html)）。当前 perf-kit 热点是标量整数位运算、四态传播、信号存储与事件调度，未发现可直接替换的数学内核。因此本轮不引入 MKL 链接依赖，也不把链接未调用的库计作加速。未来若实现浮点矩阵/DPI 等适用接口，需另验数值、四态、顺序和线程语义。

构建时可以固定模型编译器及其参数。`DSIM_MODEL_CXX` 默认跟随构建 DSIM 的 C++ 编译器（AppleClang 使用 `/usr/bin/clang++` SDK 入口）；`DSIM_MODEL_OPTIMIZATION` 默认 `-O2`。`DSIM_MODEL_CXX_FLAGS` 是 CMake 分号列表，按独立 argv 传给默认模型编译器。例如：

```sh
cmake -S . -B build-intel \
  -DCMAKE_CXX_COMPILER=/opt/intel/oneapi/compiler/2026.1/bin/icpx \
  -DDSIM_MODEL_OPTIMIZATION=-O3 \
  '-DDSIM_MODEL_CXX_FLAGS=-xHost;-ipo'
cmake --build build-intel --target dsim -j4
```

这同时用 Intel 编译 DSIM 和生成的仿真程序。Intel 前端构建及名为 `icpx`/`icpc` 的模型编译调用显式加 `-fp-model=strict`。`--help` 显示默认编译器及参数；`--cxx` 选择其他编译器时不携带默认编译器的额外参数，重复的 `--cxx-flag` 仍放在最后。是否启用 O3、IPO 和本机指令集由完整工作量对照确定，不能从编译器名称推断收益。

纯连续过程的 FIFO 执行批次目前只在 Clang 系列编译器上默认候选启用，GCC 保持原有 M125 调度路径；`DSIM_REFERENCE_LEAF_BATCH` 关闭新批次，`DSIM_EXPERIMENTAL_LEAF_BATCH` 可在 GCC 上显式试验。两条调度路径需要分别测试编译选项，结果见 [M126](../validation/m126-leaf-batch/README.md)。
