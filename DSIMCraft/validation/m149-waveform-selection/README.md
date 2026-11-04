M149落实持久目标中的“波形输出由用户指定范围”，完整VCS/UVM目标继续进行。范围语义和命令见[文档](../../docs/waveform-format.md#用户指定输出范围m149)，其余缺口见remaining-gaps.json；本批没有新增class/UVM执行能力。

实现冻结 `d7eeef3d784a95a0fc3c4aae9f300d39c4c2d0d1`，1845个源码成员逐个匹配Git blob和归档清单。新增重复层次根（并集）、相对深度、完整声明名包含/排除（`*`/`?`，数组方括号为字面量）、闭区间tick窗口及进入窗口前状态。保留同刻顺序、四态值、别名可见性和dump控制；晚启动采集不构造过去历史，不相交区间产生有效空事件文件。过滤不改变仿真执行。范围接入VCD、同步/异步DWF、SDF、时间轮、实际双分区合并及JSON流程；异步时间窗口适配器归单独writer线程，默认无时间过滤不构造该适配器。

Mac/103 Intel各三组共399捕获及mandatory parser/格式/原生DB检查通过：新范围组232捕获/62对同步异步逐字节身份/11非法CLI及9非法JSON拒绝/一次预测回滚及一次提交；原波形线程组72捕获、基础容器组95捕获。跨平台全部8份生成C++和234份完整捕获一致（包含JSON流程额外两份）。真实run_flow --vcs对照TRACE和全部274个所选声明位的物理时间线，既不取声明交集也不忽略缺失键。四个sanitizer程序包括所选窗口程序和writer内核，均分别通过ASan/UBSan与TSan；最终发布C++与sanitizer输入身份已核验，macOS禁用LeakSanitizer，不作泄漏检查或性能收益声明。

Mac稳定入口 `~/vibe-coding/dsim-test/bin/dsim` 对应 `20261028T164601652786Z-b2107660a645`；103的 `/apps/EDAs/own/dsim/bin/dsim` 和 `/apps/EDAs/own/dsim/dsim` 对应 `20261028T164616Z-d7eeef3`。三个实际入口重编译并使用多个层次、包含/排除、深度、时间窗口和独立writer运行，生成C++、stdout及DWF字节均与正式JSON流程一致。激活脚本发生异常时恢复原链接，实际记录见mac/linux-stable-entry.json。

额外旧波形三个模型通过；**完整旧waveform_dump组没有通过**：75捕获之后，SDF root-buffer monitor比旧oracle多出 `TRACE t=0 z=x`。原M148二进制复现完全相同输出；103对相同SV字节再次运行VCS确认旧oracle正确，初始化调度差异确实仍需修复。原始失败、基线身份及VCS复测记录分别在legacy-dump-failure.log、legacy-dump-baseline.json、legacy-vcs.json。没有删除这条断言或改写旧oracle，也不把该组计入通过数。优先跟进此缺陷，同时继续class/对象与UVM主线。

开发阶段首个控制记录oracle误把reader的token列表当作字符串；随后预测测试选择没有设计事件的tick5引入合法额外时间标记，改在已有tick6提交后比较完整流。跨平台首次导出比较未归一化随机run-*目录，修正证据路径映射后比较全部源文件及事件；这些都是测试/验收辅助问题，没有更改仿真值来迎合oracle。

四份原始归档（冻结源码、Mac/Intel自有模型和日志/捕获、VCS源SV/文本/VCD）及逐成员SHA清单位于本地 `../dsim-test/evidence/m149-waveform-selection/archives` 和103的 `/apps/EDAs/own/dsim/evidence/m149-waveform-selection/archives`，不包含VCS生成代码或二进制。索引见evidence-index.json，verify-evidence.py可对任一归档目录独立核验；两端实测结果见mirror-local/remote.json。运行audit.py复核本批范围验收；waveform-audit.json明确保持full goal未完成。
