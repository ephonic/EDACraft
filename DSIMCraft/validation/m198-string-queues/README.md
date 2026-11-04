# M198：string 队列与元素方法

普通/局部变量、类属性和参数化类的 string 队列现在可使用 push/pop、insert/delete、元素读写、有界队列、整队列复制、函数返回、input/output/ref 传参。空队列弹出和越界读取返回空字符串；存储保留不可变字符串所有权，队列副本和预测快照互不污染。队列描述符仍为调度器使用的整数信号，与字符串元素类型分开标记。

解析器按剩余 unpacked 维度区分 string 队列和标量 string，元素可调用 len/toupper/putc 等已有字符串方法。locator 迭代项保留字符串类型，可 find/find_index/min/max/unique；sum 的 with 表达式可取 item.len()。直接把字符串用于数值 reduction、算术、packed 选择和不兼容传参会明确拒绝。

生产提交 `c2a75ac831b0ffb6fcc32c6d5db375601d905274`。七个未修改同源模型已在 VCS W-2024.09 与 dsim 生成程序执行，TRACE 全部一致，源文件 SHA 见 `vcs.json`。有界队列正例不包含 VCS 会以运行错误终止的负索引 insert/delete；该边界差异仍保留，未计作对齐。

前端与七个生成程序通过 ASan/UBSan，含一回滚/一提交、异步压缩波形执行、13 反例和解析器重复清理；未启用 leak 检查。七份前端 CPP 与参考逐字一致。收据见 `asan.json`，可用 `sanitize.py` 重现。

未改公开 UVM 已越过 string push_back 解析阻塞；固定库预处理仍为 166 依赖、1,888,084 字节、SHA a0e1425aeebafd981a99a5f563b3327d800b968f448f790d95293d4c83d1611d。下一处失败在 `uvm_cmdline_processor::get_inst`，静态单例中的 handle/null 比较进入整数常量函数求值器后查询 unsupported $bits。`next-blocker.sv` 为独立复现；调用栈见 `public-uvm-stack.txt`。完整 UVM 尚未编译运行，本批没有性能结论。

已阅读新出的 REPORT-GAP6：clocking 的 #1step/输出 skew/周期延迟抽测通过。后续重点为 covergroup 的真实采样、bins 计数和查询；同时推进公开 UVM 单例句柄求值阻塞。报告中的抽测范围与完整公开 UVM 的状态分别记录。固定 string 数组、string 动态数组/string 值关联数组、string 字节 packed 选择、部分容器排序等仍有缺口，不声称完整支持所有字符串容器。

冻结四组回归及双端发布状态见 `progress.json`；只有已完成的验收才更新稳定入口。

## 冻结验收与稳定入口

1356 输入，SHA `ea4f2f571d68d205f86e4abb435fcef45f1fd2f4d75a8ea5198697b4f8788f5d`。Mac 稳定入口已更新至 `20261031T100531984281Z-ea4f2f571d68`。实际入口七模型再次生成/执行，CPP、解码波形和本批异步编码字节与冻结候选相同；公开 UVM 前后复测保持上述后续阻塞。

| 组 | 模型 | 捕获 | 编译拒绝 | 回滚 | 提交 |
| --- | ---: | ---: | ---: | ---: | ---: |
| string_queues | 7 | 128 | 13 | 1 | 1 |
| strings | 9 | 31 | 25 | 4 | 0 |
| string_subroutines | 7 | 46 | 10 | 4 | 0 |
| typed_containers | 14 | 256 | 23 | 2 | 2 |
| 合计 | 37 | 461 | 71 | 11 | 3 |

RTL semantic memory、format parser bundle、原生 Liberty DB mandatory 检查通过。生成程序的 ASan/UBSan 七模型 CPP 与冻结候选相同。跨端参考为 123 CPP、461 解码捕获，编码摘要另存。

103 Intel 候选先完成同源四组回归，再比对跨端参考和源码/运行时摘要，并通过实际入口、公开 UVM 前后及根目录别名检查后激活；失败保留旧版或回滚。Z3 显式使用已验证的静态库路径。stage PID `2983372`、finalizer PID `3742751`；日志 `/tmp/dsim-m198-publish.log`、`/tmp/dsim-m198-finalize.log`，最终收据 `/tmp/dsim-m198-final`。Linux 尚在最后一组回归，本段不视作 Linux 发布已完成。

103 验收现已全部完成：`linux-final.json`、`linux-entry.json`、`linux-release.json` 与 `cross-platform.json` 记录稳定入口 `20261031T100513018878Z-ea4f2f571d68` 激活成功。双端各 37 模型/461 捕获/71 编译拒绝/11 回滚/3 提交及 mandatory 通过，123 CPP、461 解码捕获、编码字节全部相同；两端各七个实际入口模型及 Linux 根目录别名通过。上文的待完成状态为发布过程快照。
