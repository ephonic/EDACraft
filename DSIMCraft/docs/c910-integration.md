# C910 / smart_run 集成

以 `dsim-test/c910.md` 的 524 个源文件为输入，恢复原始 smart_run TB，不使用现场的 RTL/TB 覆盖层。M213 修复了无关模块导致的假循环、模块 static 数据、合法嵌套复制拼接、根层次及晚声明实例引用、模块隐式标量线网、前向常量函数、模块名与变量名同名，以及嵌套 generate 展开时的失效父节点引用。重复模块诊断现在包含名字、两处原始文件及行列。

报告中的 `{N{1{1'bx}}}` 缺少内层拼接的大括号，VCS 同样拒绝；合法形式为 `{N{{1{1'bx}}}}`。模块级 automatic 数据也被 VCS 拒绝，不能作为支持要求。synthesis 注释本来就由预处理器移除；6308 的真实原因是所选可达模块图的入度错误，不是属性注释。`-y` 库自动搜索仍未实现；本轮使用显式去重文件清单。

## 程序镜像

原始手写 `gen_prog.py` 将指令数值直接输出为八位十六进制文本。smart_run TB 把文本的最高字节写入 ram0，而 ram0 返回 AXI 数据的最低字节，因此每条 RV64 指令的四个字节需要逆序。`validation/m213-c910/run-little-endian.py` 在独立目录生成镜像，保留原输入，不修改 RTL/TB、不强制 PASS 或覆盖 CPU 内部信号。

103 的 VCS W-2024.09 用原始 RTL/TB 编译后，原镜像运行 180 秒未完成；字节序修正的同一手写程序得到 `TEST PASS`，仿真时间 21395000 ps，VCS CPU 时间 0.760 秒。该程序只证明最小指令执行与 TB 成功判据，不能代表 hello_world、CoreMark 或 ISA 全面验证。原脚本的 printf 地址注释与指令不一致，且先产生 PASS token，因此本轮不宣称打印了 DSIM 文本。

## 大数组表示

无波形、串行编译的静态整型变量数组可使用运行时固定存储，数组仅注册一个变化通知信号。原来超过 1048576 个元素的数组在满足条件时自动使用该表示。`--compact-memories` 显式把选择阈值降至 1024，供大设计使用；默认保持已有较小数组的表示及功能。

支持一维/多维元素读写、非零下标、反向声明、四态/二态及宽数据、部分写、延迟 NBA、事件 NBA、越界/未知选择和一维 `$readmemh/$readmemb/$writememh/$writememb`。数据仍使用常规四态运行时容器，尚未使用稀疏分页存储。固定数组不能调用动态数组的分配/大小修改方法。

显式紧凑模式暂不支持波形、并行、整数组复制/传参、ref 元素及解包数组端口；这些路径给出错误，不能静默改变行为。net、自动局部、real、class/aggregate/string 等数组保留原表示与上限。

示例（在包含 inst.pat/data.pat 的独立工作目录中）：

```sh
dsim --compact-memories --top tb \
  +define+no_warning+TSMC_NO_WARNING+NO_DUMP \
  --timescale 1ns/100ps -f original-files.f \
  --emit-cpp c910.cpp -o simv
./simv
```

前端成功、原生编译成功和完整运行 PASS 分别记录在 `validation/m213-c910`，不得互相替代。

## M214：完整设计已得到 TEST PASS

原始 524 文件和未修改 smart_run TB 已完成通用 C++ 分片、Intel 原生链接，并用上述 VCS 验证镜像实际得到 `run_case.report = TEST PASS`。这是最小手写 RV64 程序，不是完整 ISA/CoreMark/系统软件验收。

生成模型有 323879 个过程。首次仅拆过程体的 80 个单元通过，但剩余 114 MB 初始化入口使 Intel 编译器崩溃；追加信号、连接及等待注册分片后，共 308 个单元成功链接。`scripts/compile_split_model.py` 的 `--split-setup` 同时将巨大的启动排除表达式改成有序 ID 扫描，保持过程注册及入队顺序。它适用于生成的串行 RTL 模型，不包含 C910 名称或行为特判；目前显式拒绝波形、DPI、门级和并行模型。

从本页的前端命令生成 `c910.cpp` 后，可以显式构建：

```sh
python3 scripts/compile_split_model.py c910.cpp /tmp/c910-native \
  --cxx /opt/intel/oneapi/compiler/2026.1/bin/icpx \
  --split-setup --batch 4096 --jobs 4 --timeout 1200
```

然后在包含修正后的 inst.pat/data.pat 的独立目录运行 `/tmp/c910-native/native`。
本轮实际复用了旧构建中源码和公共头逐字相同、编译已成功的 80 个过程对象，另编译主入口及 227 个初始化单元。当前稳定版生成的完整模型与该保存模型仅相差一个未启用的 `DSIM_SHARED_FUNCTIONS_ENABLED` 运行时块；严格限定这一归一化后的代码逐字相同，见 [代码身份](../validation/m214-uvm-functions/c910-code-identity.json)。

实际通过的程序保留在 103 `/tmp/dsim-m214-c910-setup/native`，运行目录 `/tmp/dsim-m214-c910-run900`。首次 300 秒预算超时；900 秒预算内以 669.25 秒 wall 得到 PASS。模型分片使用 `-O0 -fp-model=strict`，运行期间与编译任务共享服务器，并做过调用栈观察；不能将这一 wall 时间除以 VCS 的历史时间作为公平 runtime 比值。速度差距仍很大，采样热点包含宽向量多驱动解析。

单独以 -O2 编译共享运行时、保留模型分片的后续实验通过了小模型，包括延迟与递归引用；完整 C910 在 300 秒预算内仍未完成，未计性能改进，也未加入默认工具路径。详细通过、失败与发布收据见 [M214](../validation/m214-uvm-functions/README.md)。
