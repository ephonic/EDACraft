# 原生 Synopsys DB 读取

`parsers/liberty/db_api.h/cc` 已从用户提供的 103 服务器源码导入，只保留原生解码实现，依赖 C++17 和 zlib。不会启动 `lc_shell`、其他供应商工具或 shell，也不需要许可证。

```sh
dsim --liberty-db-info cells.db > cells.coverage.json
```

此命令读取 DB 内容，恢复 gzip 成员/片段及可识别对象，输出库名、物理记录数量、cell 名称/面积/footprint、片段恢复情况和明确的完整性标志。扩展名不决定格式。损坏头、没有可恢复 ROOT 的文件明确报错。

C++ 数据入口：

```cpp
#include "liberty/db_api.h"
edacraft::core::native::DbDocument document;
std::string error;
if (!edacraft::core::native::read_synopsys_db(path, document, &error)) {
    // 读取失败，document 保持不变。
}
// document.cells / tables / ccs / ports / timing
// tables 保留 axes 和 float32 values；ccs 保留坐标、时间和电流样本。
// document.simulation_model_complete 当前为 false。
```

`DbDocument` 保留尚未归属的物理对象，不把它们装成虚假的 `LibertyDB` timing arcs。`dbio::read_library_file` 是门级库的严格入口：文本 `.lib` 继续使用原 parser；识别到原生 DB 时，完整模型装配尚未实现就明确拒绝，不执行工具回退。文本读取先在独立数据库中解析，成功后才提交。SDF 条件准备入口同样拒绝将二进制 DB 当作文本解析。

当前边界：

- 已有 cell 解码规则针对远端样本的 `BWP6T16P96CPD` schema；不能声称通用 Synopsys DB 版本兼容。
- pins、条件 arcs、NLDM/receiver/power tables、CCS 向量可以提取，但准确 cell/pin/arc/table 归属、共享引用和完整逻辑/时序函数未恢复。
- 库单位、阈值尚未原生恢复，不能采用样本常量代替文件内容。
- 片段容错会保留解压出的数据；CRC 失败/未结束片段单列，恢复的物理数量不等于逻辑覆盖率。
- 不能把此版本用于直接从 DB 建立完整门级仿真模型；原生对象图装配仍需继续实现。当前 `--liberty cells.db` 会报出具体原因。

本轮不是完整 DB 仿真支持。验证包括合成容器的精确表值/CCS 样本、截断与随机字节、失败不修改输出、CLI 行为、既有文本库门级执行，以及远端真实 DB/Liberty 数据核对。实际结果见 `validation/m96-native-db/`。

真实样本核对：213 MB DB 原生恢复 1,139/1,143 个 cell，所有恢复 cell 的面积与文本库按 float32 完全相同；恢复 6,870 张表、996,594 个 CCS 向量。两个选定 cell 的严格全数组/全样本存在性核对为 NLDM 8/20、CCS 636/640；这些只是原始数据存在性核对，不能证明归属正确。缺失数据已记录，未用容差、统计坐标相似或工具回退掩盖。本机一次读取约 9.16 秒，未作 VCS 性能对比。
