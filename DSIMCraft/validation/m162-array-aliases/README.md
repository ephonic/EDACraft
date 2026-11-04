# M162：未打包类型别名与数组值调用

依据 REPORT-GAP2 和未修改公开 UVM 的 `typedef TYPE types_t[$]` 编译阻塞，实现类型形状、存储、实参和返回值的完整增量路径。功能范围及继续存在的边界见 [说明](../../docs/array-aliases.md)。原始报告/探针绑定见 [来源](report-binding.json)，旧稳定入口的两个失败复现见 [基线](baseline.json)。完整 UVM 与 REPORT-GAP/GAP2 目标仍未完成。

11 个正例，每个检查 serial/time-wheel/threads=2 后端的运行结果和 ordered/settled 的 VCD、DWF、异步 DWF；额外验证一次真实预测拒绝回滚、一次提交及指定信号/时间窗口。新组共34份生成程序和200捕获，14个编译拒绝边界。`parallel` 检查实际两分区，`report_r02` 是原始输入。元素类型、ref 上界、覆盖签名和回滚使用独立期望值，不以新实现的输出生成 oracle。开发正例200捕获与最终14负例分别通过，正式新组已全部通过。首个未发布候选因相关回归的四条旧容器诊断预期中止；输入仍保持类型拒绝测试，更新为现有更具体诊断后重新冻结，不能把该候选计为通过。

开发过程保留失败日志：测试曾使用保留强度词作为名字，改名；若干模型没有可导出的 integral 信号，增加结果信号供波形验证；负例诊断期望/有符号原子类型和空返回分别提前触发既有检查，调整输入以独立检查目标边界。这些测试输入修正不计作产品缺陷修复。随后补充 typed-container 回归发现非法类句柄选择被泛化形状探测提前诊断，已收紧为声明维度探测；第二候选虽六组通过仍撤回，重新冻结验收。运行时多维拒绝提前到类型装配阶段，保留同一维度限制并更新对应诊断预期。语法生成仍78个SR冲突、无RR。最终结果如下。

公开 UVM 固定版本未修改，预处理仍1888084字节/166依赖/原SHA；native 首错已推进至 `uvm_coreservice.svh:165` 的 `local`，不将首错推进记为 UVM 执行通过。103 只读 SSH 返回服务器无响应，M161 原 Intel 超时原因仍未定位，远端入口未替换；本批没有新 VCS 或跨平台一致性主张。独立压缩波形线程和用户指定范围继续纳入回归，DWF 不兼容 FSDB 二进制。本批不作速度结论。

最终冻结 `2ff24ad7432d2c189d585250bf0f0f26ecabe957`；Mac 七组1005捕获及 mandatory parser/格式 parser/原生 DB 全部通过，1016发布输入与冻结源码逐哈希绑定。稳定入口 `~/vibe-coding/dsim-test/bin/dsim` 已切到 `20261029T045933162646Z-520696d9881e`，实际入口重编译、完整和指定信号/时间范围异步波形与正式结果相同。原始 r02 从实际入口编译运行通过，省略 --top 自动选择 tb，生成代码和完整异步波形相同。见 [状态](status.json)、[发布绑定](mac-source-binding.json)、[实际入口](mac-activation.json) 和 [原始探针](report-stable.json)。

完整 parser、新11正例/14拒绝的前端及11实际生成程序、真实预测回放通过ASan/UBSan；额外16个typed-container负例也通过。真实双分区与独立异步writer的TSan执行保留，最终生成代码逐字节绑定相同。无LSan/速度结论。补充16组最初13通过、三组在旧诊断预期处失败，失败记录保留；修正后三组已在正式七组重跑通过。探测修正后重新生成的328份相关正常程序逐字节相同，此项是代码身份核验，**不是重新运行全16组**。详见 [初始结果](related-initial.json)、[代码身份](related-identity.json)、[sanitizer](sanitizers.json)。前两候选均未激活。

固定公开UVM326文件逐字节匹配原公开归档，实际稳定入口预处理仍1888084字节/166依赖/原SHA，native仍在 `uvm_coreservice.svh:165` 的 `local` 正常拒绝；完整UVM未完成。最终源码、Mac原始捕获/日志、sanitizer和补充回归分别归档并逐成员校验，收据见 source-freeze.json、mac-archive.json、sanitizers-final-archive.json、related-archive.json。展开的公开UVM源码不进入运行证据归档。103当前只读查询无响应，未上传新候选/未替换入口，未得到本批VCS或Intel结果；不宣称双平台一致。
