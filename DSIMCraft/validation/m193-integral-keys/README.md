# M193：整数与枚举关联索引

生产实现 fe82757a（首次实现 8071a844，后根据 VCS 放宽整数索引复制的状态类型限制）。支持命名 packed 整数与枚举索引，贯通完整位宽存储、符号排序、存取/游标、foreach、locator 队列、类属性、类型特化、复制及预测恢复。边界见 [说明](../../docs/integral-associative-keys.md)。

Mac 稳定入口已更新为 `20261031T035345667621Z-6036fa468a9c`，1315 个冻结输入，源码 SHA256 为 `6036fa468a9c2139be48e2ac8033f50b0fc93cd3dfb4859a8b5bef15e2df0053`。两组选定回归 21 个模型、384 份捕获、35 个编译拒绝、两条运行错误、三次回滚/提交及 mandatory parser/格式 parser/Liberty DB 检查通过。七个新增模型占 128 捕获；七个实际稳定入口模型复验通过。68 份 CPP 和 384 份解码波形摘要已记录。首次候选未激活，按 VCS 的复制兼容性修正后重新构建并验收。

ASan/UBSan 的 parser 重复清理、七模型、一次回放、12 个编译拒绝、两条运行错误及宽索引内核通过，未开启 leak 检查。本地完整构建通过。额外字符串关联数组、constraint foreach 和原有整数容器回归共 351 捕获通过；最终稳定编译器重现其全部 63 份已执行 CPP，证明复制检查修正未改变这些模型的生成代码。

VCS W-2024.09：六个相同 SV 正例的 TRACE、六个编译反例对齐。另单列三个边界/差异：129 位关联索引约束为供应商 NYI；129 位索引最高位含 X 的读写被 VCS 接受而 dsim 拒绝。它们不计入共同运行通过。窄索引 X/Z 写入和读取的 VCS 错误保留在独立探针归档中。详见 vcs.json 与完整原始日志。

未修改公开 UVM 的预处理仍为 1,888,084 字节、166 个依赖，SHA256 为 `a0e1425aeebafd981a99a5f563b3327d800b968f448f790d95293d4c83d1611d`。28 位枚举索引限制已越过，当前首错为 `uvm_copier.svh:70` 的三维关联数组 `m_recur_states`。完整 UVM 仍未原生编译运行，此批不作性能结论。

103 的 M192 仍在验收，本批已排队等待，未激活；原入口保留 M190。后续自动流程在旧 finalizer 退出后进行 Intel 构建、回归、跨端 CPP/解码波形比较及实际入口检查；所有条件通过才切换链接。进度见 linux-pending.json，不能计为 Linux 验收通过。

完整生成代码、日志、原始波形和解码摘要归档在 `~/vibe-coding/dsim-test/evidence/m193-integral-keys/mac`，内容清单见 archive-catalog.json。关键收据为 mac-release.json、mac-entry.json、asan.json、vcs.json 和 progress.json。
