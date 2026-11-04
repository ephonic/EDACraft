# 原生 DB reader 来源

按用户指定，从 `yangfan@10.131.254.103:/home/yangfan/c906/t12/db_api.h` 和 `db_api.cc` 导入原生接口、容器/gzip 解码及对象提取代码，维护于 `parsers/liberty/db_api.h/cc`。导入前文件大小和 SHA256 见 [IMPORT.json](IMPORT.json)。没有新增许可证授权；不导入 PDK DB、Liberty 库或其数据表。

dsim 适配：

- 删除 `lc_shell` / SDBD / shell 启动、环境修复及许可依赖，只编译原生代码。
- 改用仓库内 LibertyDB、StringPool 头文件，不依赖远端目录结构。
- 新增 `DbDocument` 一次遍历提取入口、覆盖 JSON，以及按内容识别的严格 Liberty 模型入口。
- 纠正原 `read_synopsys_db_native` 返回成功但仅创建 cell 骨架的问题。完整图未恢复前返回明确失败，不硬编码单位或阈值，不静默导出成可仿真库。
- 修复 varint 越界移位、截断浮点数组检查、偏移零处 cell 名遗漏；限制单 gzip 输出大小；避免在没有 NLDM values 标记的 CCS 载体上反复搜索表。

原始代码已经明确声明 native 归属恢复为 best effort。原生接口中的提取结果不代表完整逻辑库，限制见 [使用说明](../../liberty-db.md)。
