# M163：报告复查与类成员权限

原始报告：`/Users/yangfan/vibe-coding/dsim-test/rtl-tests/complex/REPORT-GAP2.md`，SHA256 `0a316c371261b0ab962f0a46a7e4818d6df74d70f4c051dc044720b798eba366`。该报告基于 M156；static 成员、string 键关联数组、原始 r02 ADT 的旧失败已在后续增量修复。本批重新检查实际现存19个 SV 文件，其中7个原始探针编译运行且没有 BAD；q11_std 只验接受性，不计执行通过。报告列出的 r04–r07 不在当前 probes3 目录，不自行合成“原始”输入。

访问权限按词法类检查，同类跨实例、基类方法克隆、继承的 protected、static、参数化特化和工厂构造贯通；重复限定符和越权引用拒绝。完整实现边界见 [class-access.md](../../docs/class-access.md)。新增十模型检查三调度后端、文本 VCD/同步和独立接收线程 DWF、ordered/settled 波形、用户选择范围、预测回滚/提交与真实双分区。反例包括当前实例 queue 属性存储边界，不将其计为已支持。

开发首轮因缺符号定义头文件构建失败；修正为 veri_tfmg.hpp 后通过。首轮新容器模型包含实例 queue 属性，被现有存储边界拒绝，原文件保存在 dev/class-queue-unsupported.sv；当前正例检查实际支持的一维关联数组，另将 queue 边界纳入明确拒绝用例。旧 parser recovery 测试曾把类内 local 方法当作非法，现改为真正未支持的 rand 声明，并保留类外权限限定符拒绝/随后再次解析的检查。开发失败不计为通过。

固定未修改 Accellera UVM2020.3.1（78c06547a2a0a29b3dc9dcafae62b75b2ff61544）仍不能原生编译运行。本批诊断从 coreservice:165 local 推进到 globals:124 export "DPI-C"；该导出不受 UVM_NO_DPI 条件屏蔽。没有删库、跳关键字或将 VCS 执行替代 native UVM。还需要完整类/容器、约束随机、mailbox/semaphore、virtual interface/clocking、功能覆盖与 DPI 等依赖。

103 的唯一新只读查询以255返回（11.67秒，服务器无响应），既有 M161 Intel 超时原因仍待读取。没有新远端发布、VCS对照或速度/压缩率结论。用户的 experiments/matvec16 未改。

开发/最终验收状态在本目录结构化结果中记录；原始日志、生成程序与波形留在本地证据目录，排除公开 UVM 展开源码和 VCS 生成代码。

## 最终本地验收

冻结实现 b7d58d5643dc9397802caed4da45236433ea03be，1863归档源码成员与Git一致，1021发布输入逐项绑定；新31生成程序与开发验收逐字节相同，10前端生成结果及8普通程序/回放ASan/UBSan、真双分区程序TSan均绑定到同一最终CPP。最后增加的两条虚覆盖权限合同在普通和ASan前端24反例全集补验，早期sanitizer记录22反例保留；没有LSan或性能声明。

Mac最终五组778捕获与mandatory parser/格式/原生DB通过，新十模型182捕获、24拒绝、1回滚1提交；真实2分区与独立writer/用户范围通过。另十组开发回归分批执行全通过，不能混称十组全部在冻结源之后重跑。Mac稳定入口已激活20261029T052753094098Z-63eaada79c82；实际入口重新编译的完整/所选异步DWF及生成CPP和候选相同。原始r02不改字节、从实际入口省略--top编译运行通过。

实际稳定入口对未修改公开UVM预处理仍1888084字节/166依赖/原SHA；326参考文件与原固定归档逐哈希相同。native仍以1正常拒绝于globals:124，不产生部分CPP。全量UVM、REPORT-GAP/GAP2目标继续。原始证据在~/vibe-coding/dsim-test/evidence/m163-class-access，含Git源包、开发与候选验收归档及逐成员哈希清单；不包含公开库展开文本或VCS生成代码。归档首次快照先于原始报告用例日志落盘，补齐四个日志后重新归档并验证；没有修改仿真源码或重跑既已通过的模拟验收。
