# Linux x86_64 二进制发行

**DSIMCraft 0.13.0 / M238**，约 24.2 MiB。解压后使用 `bin/dsim`，无需编译 dsim 本身。

- [直接下载压缩包](https://github.com/ephonic/EDACraft/raw/refs/heads/main/DSIMCraft/binaries/linux-x86_64/dsimcraft-0.13.0-m238-linux-x86_64.tar.gz)
- [SHA256SUMS](linux-x86_64/SHA256SUMS)、[构建来源](linux-x86_64/release.json)、[验收结果](linux-x86_64/verification.json)、[动态依赖审计](linux-x86_64/compatibility.json)

## 使用

```sh
cd DSIMCraft/binaries/linux-x86_64
sha256sum -c SHA256SUMS
tar -xzf dsimcraft-0.13.0-m238-linux-x86_64.tar.gz
cd dsimcraft-0.13.0-m238-linux-x86_64
./bin/dsim --version
./bin/dsim examples/counter.sv -o /tmp/dsim-counter
/tmp/dsim-counter
```

预期 `dsim 0.13.0` 和 `DSIMCRAFT COUNTER PASS 4`。可将解压目录的 `bin` 加入 PATH，或为 `bin/dsim` 建立符号链接。安装路径可以包含空格，调用者的工作目录及 filelist 路径规则保持不变。

验收平台是 **CentOS Stream 9 x86_64**。需要 glibc **2.34+**、提供 `GLIBCXX_3.4.29` 的兼容 libstdc++（GCC 11 级别），以及本机 **C++17 编译器**。其他 Linux 发行版、macOS 和 Windows 未在本次二进制发行中验收。

```sh
./bin/dsim tb.sv --cxx clang++ -o simv
./simv
```

生成模型默认使用 PATH 中的 `c++`；可设 `DSIM_CXX=/path/to/compiler`，显式 `--cxx` 优先。包内没有 C++ 工具链；用户无需安装 Intel 编译器来运行 dsim。

## 包内内容与来源

| 内容 | 用途 |
| --- | --- |
| `bin/dsim` | 可重定位启动器，支持符号链接，保留参数和工作目录 |
| `libexec/dsim` | 由 Intel icpx 2026.1.1、`-no-intel-lib` 构建的 x86_64 ELF |
| `share/dsim/` | 对应源码的 runtime、宽位串、DPI、波形及分区等头文件 |
| `include/`、`lib/` | Z3 4.15.4 / Zstd 1.5.5 头文件及静态库、Tcl 8.6 / zlib 运行库 |
| `examples/` | 计数器、约束随机化、参数化虚接口及门级 SDF 示例 |
| `licenses/` | 各组件原始许可，第三方组件未重新授权 |

固定源码为 [`ephonic/dsim@6958112e`](https://github.com/ephonic/dsim/commit/6958112ed747a4165b74d61ae25a95070c0de250)，包含 M237 参数化 virtual interface 及 M238 资源路径配置。功能开发、修复及源码推送继续使用 [ephonic/dsim](https://github.com/ephonic/dsim)。二进制与目录内源码快照的提交身份分别记录；二进制以包内 `release.json` 为准。

包内压缩及求解库使用静态链接，因此生成的示例程序在清空开发环境变量后仍可独立运行。启动器为 dsim 本身配置包内 Tcl/zlib 及资源路径；请使用 `bin/dsim`。包内没有商业 EDA 库、Intel 编译器运行库或 UVM 源码。

## 本次验收

解压到带空格的新目录，使用符号链接，从另一个工作目录启动，并清空开发环境变量。构建时将默认资源路径故意设为不存在，避免验收误用原构建目录。

- 相对 filelist 编译并运行计数器；请求分区及波形支持时相关头文件正确装载。
- 文本 VCD 和独立线程 Zstd 压缩波形完整解码结果一致。
- 用包内 Z3 静态库完成约束随机化；用包内 runtime 完成 8/65 位参数化虚接口方法调用。
- 门级 Liberty / SDF 注解、路径字典执行通过，26 项有序输出与固定参考一致。
- ELF 依赖审计通过，生成的四个程序在干净环境中运行，未依赖开发目录或商业 EDA/Intel 运行库。

这些属于列明的发布子集，不能据此宣称完整 VCS/UVM/VIP/RAL 兼容。virtual clocking、interface 实例数组、完整对象图约束随机化、DPI/VPI/SVA/覆盖率仍有缺口。构建和验收脚本在源码仓库的 [`scripts/package_binary.py`](https://github.com/ephonic/dsim/blob/6958112ed747a4165b74d61ae25a95070c0de250/scripts/package_binary.py) 与 [`scripts/check_binary_package.py`](https://github.com/ephonic/dsim/blob/6958112ed747a4165b74d61ae25a95070c0de250/scripts/check_binary_package.py)。

发行包本身也通过未修改的完整 Accellera UVM 2020.3.1 库的参数化接口集成测试（181 个库文件；`UVM_NO_DPI`、`--shared-functions`、Clang 22.1.3、原生 `-O0`）。最终发行编译器重新生成的完整 C++ 与已原生编译验收的输入逐字一致后复用执行，原版库的指纹与全部 TRACE 再次核对。驱动、DUT、monitor 与 scoreboard 观察到三笔 100/101/102、总和303，零 UVM_ERROR/FATAL；库与测试指纹同此前 VCS 对照一致。见 [UVM 验收](linux-x86_64/uvm-verification.json)。这是一项真实库集成测试，不是全部 UVM 功能认证。
