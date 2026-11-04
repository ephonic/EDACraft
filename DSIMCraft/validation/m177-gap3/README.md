# M177：REPORT-GAP3 本地复查与容器补齐

用户要求先在本地工作。本批未访问103、未推送GitHub、未替换稳定入口。
开发编译器位于 `build-m176/dsim`；目录名沿用上一批，内容为当前源码构建。

## 报告复查

输入是 `../dsim-test/rtl-tests/complex/REPORT-GAP3.md` 和其 `probes3/*.sv`。
报告文字写27探针/21通过，实际目录有29份源码。修改前冻结的前端复测为18生成/11拒绝，
不是17/12（最初口头统计有误），也不以生成成功替代运行通过。

`probes.py` 保留原始源码并逐份记录SHA、前端返回码、编译/运行输出。当前18份均编译、执行返回0，
其中14份有有效检查或核验输出（包括真正加载C动态库的 `add_one(5)=6`）；
`q08_sequence`仅打印完成标记、`q11_std`仅打印版本烟测，单独列为两份完成性探针。
`q08_sequence`还输出8条断言失败信息，本批不据完成标记宣称其断言时序已对齐。另两份不适合作为随机取值测试：

- `q13_scope_rand.sv`：`a=std::randomize(a) ...` 在随机化完成后把状态1写回a，输出 `rc=1 a=1`。
- `r09_rand_inline.sv`：同样用返回状态覆盖x，故输出 `BAD rc x=1`，不能据此判定约束求解失败；
  原目录的 `r09b.sv` 分离rc/x，实际运行输出通过。

`r13_impl.sv`只有蕴含约束，输出虽然标注solve-before，不能据此计为solve-before支持。
复测保持原探针不变；不能把两份无效探针归为有效功能通过，也不能宣称29份全部通过。
详见 `reported-probes.json`、`baseline.json`，可重跑：

```sh
python3 validation/m177-gap3/probes.py build-m176/dsim \
  ../dsim-test/rtl-tests/complex/probes3 validation/m177-gap3/reported-probes
```

## 本地实现

1. 队列末下标：支持 `q[$]`、`q[$-n]`、括号与嵌套下标、末元素赋值/复合赋值、`q[$+1]`追加，
   以及packed元素成员/片选。每个下标的`$`绑定到最近的队列，随当前size求值；固定/动态数组和packed轴不能冒用。
   空队列及非法下标沿用容器的默认读/忽略写规则。队列切片仍明确拒绝。
2. 关联键：新增 `int unsigned` 和显式 `int signed` 形式，保留32位键截断、分别按无符号/有符号排序，
   接通first/last/next/prev、foreach下标签名、定位方法返回下标、复制、类属性、automatic存储及多实例克隆。
   有符号与无符号键数组的整体复制明确拒绝；其他宽度/自定义关联键类型仍不算支持。
3. Bison维持86个shift/reduce、无reduce/reduce；显式优先级保留队列声明的`[$]`/`[$:bound]`解释。

新增 `tests/gap3_containers`，CTest入口 `rtl_gap3_containers`。
本地新增六模型、110次捕获、11个编译拒绝、一次预测回滚/提交通过，实际验证双分区的两条时间线。
完整parser和六个前端/生成程序/回放通过ASan/UBSan；生成CPP及异步波形与普通构建逐字节相同。
不包含LSan、新TSan或新VCS对照，不作性能提升结论。
最终验收结果见 `containers.json`、`sanitizer.json`、`guards.json` 和 `mandatory.json`。

旧字符串关联组首次失败于陈旧的`unsupported_formal`负例：未调用的关联形参声明在M175稳定版也接受，
证据见 `stale-guard.json`。负例已改为实际传入关联数组，确认在真实不支持的调用处拒绝；
保留首次失败日志，重新验收该整组通过。旧四组共28模型、494次捕获通过，
84份已执行生成CPP与最终源码重发射结果逐字节绑定。

## 真实公开 UVM 与下一步

对未修改 Accellera UVM 2020.3.1（`+define+UVM_NO_DPI`）执行预处理及原生编译，
预处理保持1888084字节、166依赖和原SHA；语法首错由 `uvm_sequencer_base.svh:426` 的
`int unsigned` 推进到 `uvm_sequence_library.svh:191` 的`randc`。
这是完整库首个语法错误的定位结果，不能证明前面所有语义或运行已通过；完整UVM仍不能原生编译运行。

报告中的mailbox/semaphore、randc/dist/solve-before、clocking、covergroup、program、let、
RTL specify时序检查及assert控制仍有缺口。下一轮先实现IPC的阻塞/唤醒与取消、FIFO及checkpoint状态，
同时沿公开UVM的randc及后续真实阻塞继续推进。IPC需要原生状态/调度实现，不能仅接受语法或用零延时轮询代替。
