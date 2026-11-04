# M144：modport 原型 import

实现提交 `1b12e4064b2ae819251f14b5aa29a09bfce156ef`。冻结归档 SHA256 `e16e53230f8968ebbaf93efccfcbeffbede074c479b8659e131ea57aa20655e5`，1805 个源码成员逐项匹配 Git blob 与 manifest。RTL 与门级 parser 保持分离，runtime 未改动。本轮补功能，没有性能测量。

支持 interface 的 `import task/function` 原型、前向声明、参数化克隆、按视图默认参数和签名核验。命名实参按实际实现的形参名绑定，默认参数来自所选视图。packed 向量/整数/结构体按位宽、符号和状态类型匹配；固定 unpacked 数组按维数和各维长度匹配，下标标签可以不同；枚举保留身份。正例覆盖不同 typedef/packed rank、固定数组方向、80 位 signed、string/ref/output/inout、真实双分区、共享 automatic 激活、延时与 NBA。

八模型新组每端 40 份完整逐信号有序捕获（串行、time-wheel、两线程、预测接受和拒绝），8 次提交、8 次回滚、2 次 checkpoint 恢复及 44 个拒绝例。还回归原有 interface 子程序、interface 信号、实参绑定和头部 import，包含 mandatory RTL parser、格式 parser 和原生 Liberty DB 检查。Mac 完整 parser 与 16 份生成程序通过 ASan/UBSan（关闭 leak detection）。六个旧模型生成 C++、八个 runtime 头文件与 M143 逐字节相同；这不构成新的运行速度结论。

VCS W-2024.09 同源对照以实际结果为准：五模型输出和层次归一化后 1713 个共同声明 bit 的完整 settled 时间线相同。四模型声明完全覆盖；arguments 中 64 个固定数组 bit 未被 VCS 导出，精确列举并不计为比较成功。basic/defaults 的前向原型默认参数被 VCS 报 `USVSIETD`；timing 在同一 clause 混合名称和原型导入被报 `CMIETF`，这三模型只计 DSIM 自检与后端/事务一致性，不计 VCS 成功。另 7 个可运行默认参数/命名绑定独立探针、6 个拒绝探针与 VCS 一致，18 个新增非法签名也均被 VCS 拒绝。不能将这些结果表述为完整语言覆盖。

首次候选在等价签名审计时发现数组边界和 packed 类型检查过严，两端在切换稳定入口之前终止。修正后重新冻结、构建与回归；`first-mac-stage.json` 和原始 signature-audit 记录保留。早期 types 开发例中的直接 return assignment pattern 仍受既有上下文限制；正式 fixture 使用具名结构体局部变量，不据此宣称修复所有 assignment pattern 返回上下文。

modport export、外部方法实现、virtual interface、interface 数组、完整 clocking、parameter type、class/约束随机/UVM、完整 SVA 和其他已有后端限制仍有缺口。

稳定入口、二进制 SHA、实际入口运行及对照记录分别见 `mac-release.json`、`linux-release.json`、`mac-activation.json`、`linux-activation.json`、`mac-vcs.json`、`linux-vcs.json`；跨平台完整 40 捕获/C++/stdout 对比见 `cross-platform.json`。原始资料只归档 DSIM 自有源码/生成程序、输入 SV、VCD 和工具诊断，不导出厂商生成代码或二进制。`evidence-index.json` 绑定归档大小和 SHA256，`mirror-proof.json` 验证本地与 103 的每个归档成员。源码归档以 `source-proof.json` 为准。

当前稳定版：Mac `20261028T122922366599Z-6cac74f24b16`（`~/vibe-coding/dsim-test/bin/dsim`），Linux Intel `20261028T123002Z-1b12e40`（`/apps/EDAs/own/dsim/bin/dsim` 与 `/apps/EDAs/own/dsim/dsim`）。两端五组回归与实际入口验收完成，最终审计见 `audit.json`。镜像首次检查发现额外的辅助 model 导出不在 raw 索引内，移至 `exports/` 后，两端两个 raw 归档及所有成员校验均通过；未丢弃导出或放宽 raw 索引检查。
