# M90: parser 整理与升序 packed RTL

实现提交 `2f1a93f761c86c1f3d12c84d6aacb92cc89582fb`。功能、稳定发布和实际安装入口验收均已完成。

用户要求将第三方 parser 整理到 dsim 自身管理：已将原日期快照目录拆为 `parsers/rtl`、`gate`、`liberty`、`spef` 和 `common`。四个独立编译库，格式汇总目标不包含 RTL；可无需 Tcl 独立构建格式 parser。原始命名空间、版权和生成器声明保留，原始清单/旧构建文件转入 `docs/parser-origin`。迁移109文件，其中101份字节不变，8份为 include/fixture 路径、生成器路径和 typedef/字段范围检查变更。全部迁移前 hash 对照上一稳定版发布输入一致；逐文件前后 hash 见 `REORGANIZATION.json`。无外部 EDACraft/ftimer 源码路径依赖；原始包和早期 patch 仅作历史记录。

升序 RTL 覆盖 `[0:7]`、非零/负标号、静态与动态选择、四态、部分越界、一次求值、延迟 NBA、参数、typedef、packed 字段、固定数组、层次读取、端口、function/task/ref、组合敏感性和双分区。静态选择在编译期转换成物理区间；动态选择先验证原始全宽下标再做镜像。标准 VCD 字典保留原始方向；只修复公共声明的宽度计算，不改变波形编码。

- 原生：5模型、19份完整 ordered 捕获、4次失败预测回滚、6类拒绝，实际2分区。
- Sanitizer：10个实际 ASan/UBSan 程序（四回滚和真实双分区），6份 sanitized compiler 完整 C++ 身份一致，6类拒绝；leak 检测关闭。
- Parser：原生/sanitizer RTL 语义与格式往返通过；formats-only 独立构建和CTest通过。重新生成70个shift/reduce、0个reduce/reduce，与此前一致。
- 实际 VCS W-2024.09：5模型全部523个共同信号位完整 settled 时间线一致，没有删去时间区间。aggregate 的16个数组存储位VCS未dump，逐项列在 `vcs-check.json`。
- 输出：4模型完全一致。selects 仅两条极端64位下标输出有已知差异：VCS返回0101x，dsim全宽检查返回xxxxx；其余完整输出同独立Python oracle。差异完整保留在 `vcs-check.json`，没有宣称这两条对齐。

`tests/ascending_packed/oracle.py` 按声明标号逐位生成独立期望；`regression.py` 对比完整输出和每信号完整ordered流。`verify-vcs.py` 核对同源字节、输出和全部共同位。`run-sanitizer.py` 编译实际instrumented程序；`verify-artifacts.py` 比较完整C++、输出和ordered波形；`check-installed.py` 由实际安装入口重编译并逐字节比较整份VCD。

已知旧回归失败：`rtl_packed_aggregates` 的 values.sv:18。上一稳定版也失败，非本次迁移新增。观测混合packed结构/union的bit字段写入：dsim为 `0100xxxx / 0100 / 00001100`，VCS为 `x1z0xxxx / 0100 / xz0011zx`。本批不修改该语义，保留原断言、基线/当前失败日志、同源观测及VCS日志，不冒称旧组全通过。旧named-types拒绝列表包含现已支持的ascending/负标号与unpacked struct；移除过时期望后该组通过，相关正例分别由新组和complex报告回归覆盖。

不宣称完整SystemVerilog/VCS功能，不新增性能比值。用户 `experiments/matvec16` 未触碰。

稳定发布完成：macOS 72项检查PASS，release=`20261025T050718424054Z-c94a713d2b34`，binary SHA256=`872155ae894d2a4926810623c31b8c9ccd7d3319bb24880ae5dcdcb77ddb4168`，source SHA256=`c94a713d2b34093c36545d399965b9b0884e86c5034bae134d65f88d6e38fefd`。496项发布输入和全部runtime快照均核对实现提交2f1a93f。启动时git_dirty包含验收文件及用户未跟踪目录，不代表编译源偏离提交。

Linux从全新源码包实际编译并通过9组：RTL parser、格式parser、ascending_packed、indexed_selects、comb_sensitivity、frontend_compat、complex_report2、gate_source、named_types。release=`/apps/EDAs/own/dsim/releases/20261025T050753Z-2f1a93f`，binary SHA256=`b04c5e12f0c10ba1da835051d76d1ecc081e994101c1279468c60fb29cbfdb04`。全部1319源码包文件hash与Git提交一致；19份完整C++、输出与ordered流同macOS。两个远端别名均指向该二进制。本地实际入口和加载syn.bash后的远端实际入口各重编译四个模型，整份VCD与原生逐字节相同，完整C++身份相同。

上一稳定版的451份输出和483份波形文件逐字节相同。初版比较脚本按扩展名读取显式`--wave-format dwf`生成的`.vcd`文件而停止；改用实际magic后完成核验，文件本身没有变化，原停止日志保留。完整SystemVerilog/VCS和上述已知边界仍未补齐。
