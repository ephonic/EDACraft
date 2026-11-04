# 通用文件 I/O 回归

九个同源模型覆盖 FD/MCD、动态路径、宽 packed/string 读行、EOF/回推/定位、二进制/NUL字节、追加与更新、automatic/ref、final、内存文件互通及实际双分区。expected.json 固定 VCS W-2024.09 的完整 TRACE 和 12 份输出文件字节。

regression.py 对 serial/wheel/threads=2 的 ordered/settled 全部数值流逐项比较，再验证普通无波形程序、拒绝预测和接受预测；预测运行期间直接读取真实文件，确认没有提前写入或截断。runtime.cpp 进一步验证已打开句柄的游标恢复、读己写、事务提交失败不重放及内存文件互通。非法实参和未实现行为有独立编译/运行拒绝用例。

VCS 不 dump 未打包数组，故数组值由完整 TRACE 核对；其余数值位全部核对，不排除 FD。export.txt 来自既有 $writememh，各工具允许注释不同，不列入通用文本 I/O 的逐字节对比。

运行：`python3 tests/file_io/regression.py <dsim> <output-dir> [CMakeCache.txt]`。
