# 仓库整理记录：2026-10-25

整理基点为 `c39d32372266678f9a4bcdbd93728b6c88b83868`。本批调整仓库展示、构建组织及产物跟踪，不修改仿真器语义。

## 调整

- 首页精简为构建、功能边界和目录入口；旧首页保留在 [README-m90.md](README-m90.md)，新增[主题导航](../README.md)和[开发指南](../../CONTRIBUTING.md)。
- 原始 parser 压缩包、早期补丁归入 [parser-origin](../parser-origin/README.md)，压缩包和补丁内容逐字节不变，来源与版权保留。
- CTest 注册移入 `cmake/Tests.cmake`，产品构建保留在根 CMake。源码包和发布输入哈希包含新模块；VCS 复核工具改为记录当前 `parsers/` 源码。
- 四个常规回归依赖的历史探针复制到 `tests/`，内容不变，测试不再读取 `validation/` 输入。
- 停止跟踪 15,332 个生成文件，共 151,886,071 字节；本机原文件保留，历史检索方法见[验证归档说明](../../validation/README.md)。不重写 Git 历史。
- 更新忽略规则和 GitHub Linguist 属性，避免生成代码主导语言统计。

## 验证

源码包在没有 `validation/` 的独立目录解压，完成 Release 构建：`dsim`、`dsim_sdf_models`、parser smoke 与相关基础测试目标。逐文件核对包内 SHA256 清单。

拆分前后 256 项 CTest 的名称、命令、属性完全相同；仅源位置回溯改变。`BUILD_TESTING=OFF` 可正常配置，注册零项测试。

以下七项在解压源码上全部通过，总耗时约 192 秒：

```text
gate_source
sdf_parser
runtime
rtl_frontend_compat
rtl_system_functions
rtl_semantic_memory
parser_bundle_smoke
```

四个迁移探针分别用整理前的开发构建和解压源码的新构建编译，逐项核对退出码、stdout、stderr 一致。此处验证行为不变，不把既有失败算作功能通过：`enum-member-update` 仍报 `raw bit writes`，与已知 packed 聚合写入缺陷一致；另外三个探针正常运行。

未重跑完整回归或 VCS 性能测量；本批不形成新的功能对齐或速度结论，稳定二进制沿用 M90 已发布版本。
