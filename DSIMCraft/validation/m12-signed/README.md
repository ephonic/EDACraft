# M12：signed packed 类型与运算

生产改动在 `src/rtl_compiler.cpp`、`include/dsim/runtime.hpp` 和独立 RTL parser 的 `veri_num.cpp`。门级 parser 未改。支持范围及边界见 [signed.md](../../docs/signed.md)，计划见 [plan1017.md](../../plan1017.md)。

本批接通 packed signed 声明、端口/存储器元素、负常量、上下文共同类型和扩展、signed 比较/除余、算术移位、`$signed/$unsigned`、三目/case/拼接、负 repeat 与十进制打印。修复声明位宽高于有效数字时常量高位未分配的问题，以及未知常量取负。V/信号/事件布局未扩大，无符号算术仍走原模板调用；没有新的整体速度测量。

本地验证：

- 六组模型共 75 次捕获，覆盖 VCD/DWF、ordered/settled、serial/time-wheel/双线程，以及三组真实失败预测回放。独立 Python 整数模型穷举 256 组四位输入的算术与混合上下文。见 `local-signed.log`、`local-results.json`。
- 九项受影响 CTest 和独立 preprocessing 通过。见 `local-affected.log`、`local-preprocess.log`；未运行完整 CTest 集。
- 四个实际生成程序通过 macOS ASan/UBSan：design/wide/context 串行，parallel 真双线程，捕获与普通程序相同。独立 RTL parser 语义单测及六组源码各三次解析/清理也通过 ASan/UBSan。关闭 leak 检测，未运行 Linux sanitizer。原始日志为 `*-runtime-san.log`、`parser-unit-san.log`、`*-parser-san.log`。
- `--emit-ir` 的 signed 声明元数据有实际回归断言。

实际 VCS 六组源/编译日志/运行日志/波形保留在 `vcs/`。macOS、Linux 两个平台的 TRACE 及 **3378 条可观察物理位时间线**分别与同六组 VCS 一致。`verify.py` 对比较范围双向核对全部名字、位索引及完整时间线。VCS 不导出 unpacked 存储器元素，因此明确排除 native 独有数组字，逐项名单在 `vcs-results.json`；不宣称这些数组本体由 VCS 独立导出对齐。signed 默认十进制字段至少 32 位的规则由 VCS 差分发现并修正。

Linux 原任务 **2159045 退出 0**，远程目录 `/tmp/dsim-m12-signed-RcjbUU`。507 文件的同源包 manifest 校验通过，从源码构建后，`rtl_signed`、`rtl_semantic_memory`、`compiled_regression`、`gate_source_cli` 四项 CTest 全部通过，共 117.18 秒。六个完整 serial CPP 与 macOS 逐字节相同。下载的真实 Linux 波形和输出重新执行 `verify.py` 通过，日志与生成物保留在 `linux/`。

源码包 SHA256 为 `69136375a088625a36be93121405e6b38ccc60926e831cac8752d5a9897a1856`；工作区全部 507 个打包文件与 `source-manifest.json` 一致。当前编译器已重建，摘要见 `results.json`。

复查：

```sh
python3 tests/signed/regression.py build/dsim build/rtl-signed
python3 validation/m12-signed/verify.py
python3 validation/m12-signed/verify.py validation/m12-signed/linux/source/build/rtl-signed
```

仍缺 `int/integer`、过程局部声明、类型/尺寸 cast、完整常量求值、负下界 packed 索引、函数/任务、多维/端口数组、完整层次表达式、UDP/完整 specify/SDF/timing checks、自动预测与内部自动分区。这是常见 signed 路径补全，尚未达到完整 IEEE 或 VCS 功能覆盖；本批不提供新的 VCS 速度比例。
