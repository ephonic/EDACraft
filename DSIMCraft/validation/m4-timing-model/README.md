# Specify 模型与 SDF IOPATH 数值表

本批增加 `src/timing_model.*` 与 `src/sdf_annotation.*`，将实际 Verilog 模型精度和 specify 基值接到既有 SDF 绑定/数值层。结构 gate parser 与 RTL parser 保持分开；运行时、波形/并行 header 和 RTL/门级代码生成器均保持前批版本。

最终源码快照为 `source-snapshot-current.json`：237 工程文件、108 parser 文件、3 波形原型依赖；归档 SHA `a58842948d3fad23cf7130dc458830e5dfdafdca9a4ef6004aabfae34da2579a`。初始和中间快照留作历史；最终验收使用 current 快照和 `remote-corners.json` 指向的独立构建。

验证内容：

- 模型 timescale、标量/位选/转义端口、specparam/corner、if/ifnone、边沿、极性及 data 表达式、完整路径的端点对隔离、timing-check/notifier/pulse 声明保留、失败不提交及输入文件保护。
- 54 组既有 VCS 数值参考经实际模型解析、精确端点与路径匹配后表值一致，4 组已知数值限制仍明确拒绝。原 SDF SHA 不变；检查派生文件仅将原空 INSTANCE 改为叶单元 u，保留全部数值，未称作新 VCS 原设计运行。
- 6 组新 VCS 单独编译，每组三次一致 trace：任一方省略输入边沿可匹配；明确不同的边沿不匹配；模型 typ/SDF min 得15ps，模型 min/SDF max 得34ps。正匹配注解日志无警告，明确不同边沿 VCS 警告、native 检查器严格拒绝。原始源码、编译、注解和运行日志在两个 `vcs-*-verified/` 目录。
- 本地与 Linux 各31+1=32项。两个实际 ASan/UBSan 程序（模型/绑定测试、完整CLI）运行新测试，检查实际符号与全部 stderr；没有新增 runtime 或 TSan 声明。
- 24份完整门级生成 C++ 与已采用 LUT 版逐字相同；默认 `build/dsim` 重建，RTL计数器及两个门级例生成代码逐字相同并通过实际 golden，默认CLI实际读取111模型。本批未进行新的仿真速度测量。

真实文件使用未修改的原网表、完整1.2GB Liberty、111模型和原始两份 SDF，运行前后校验 SHA。flattened 文件建立 867,982 张路径表；790,222 INTERCONNECT、40,394 SETUP、43,248 HOLD、2,854 RECOVERY 只做端点绑定，明确计入 deferred。原始条件文件因模型没有对应 COND 路径，在 AO22D1.A1→Z 处严格拒绝，stdout为空；没有剥离条件或输出部分表。

`verify_real_tables.py` 另以 Python Decimal 对固定 flattened 文件逐行构造模型/端点/边沿/12转换的全量多重集，独立检查数值结果。这个核对范围是全部路径表的聚合值；实例身份依赖严格绑定，不能当作逐实例运行时或全设计 VCS 时序仿真 oracle。

`verify.py` 校验冻结源码、全部证据 SHA、两平台回归、实际 sanitizer、默认构建与真实表。`verify_vcs.py` 重建新微例的 native 表并检查六组独立 VCS 日志。数据详细边界见 [接口说明](../../docs/timing-models.md)。一般路径因果/条件执行、脉冲、逐接收 pin 互连、timing checks/notifier、自动分区及波形扩展仍需继续实现，整体目标未完成。
