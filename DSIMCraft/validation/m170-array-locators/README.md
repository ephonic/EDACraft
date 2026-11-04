# M170：数组定位、unique with 和类迭代器

实现范围及边界见 [数组定位方法](../../docs/array-locators.md)。
最终开发验收四模型、74 次捕获、九拒绝例、预测一次回滚/一次提交通过；
串行、时间轮及双线程请求，VCD、同步/异步 DWF、ordered/settled、
用户指定信号和时间范围均检查。请求不代表全部模型实际双分区。
旧 reduction-with 七模型87捕获/三回滚重跑通过；
完整 parser、格式 parser、原生 Liberty DB 检查通过。

最终 ASan/UBSan 覆盖完整 parser、四前端、九拒绝、四生成程序和预测回放；
生成 CPP 和异步波形逐字节匹配正常验收。不作 LSan/TSan 或性能声明。
最终执行收据为 native.json、sanitizer.json 和 vcs.json；早期 dev/final、asan
使用的是修订前 fixture，不用来证明最终代码。

VCS 四个相同正例编译运行输出一致，fixture SHA 记录在 vcs.json。
九个拒绝边界中七个与 VCS 相同，多维定位和修改迭代器两项 VCS 接受而原生拒绝。
首次对照发现类句柄 unique 无 with 不合法，修正键类型限制并加入反例；
VCS 不支持本轮尝试的定位结果直接 .size()，正例改为队列赋值后的查询，
原生已有的链式能力不删除。定位遍历顺序/重复代表没有假定为跨工具保证。

独立 parser 直接输入 rollback.sv 的 timescale 指令会失败，CLI 预处理也保留该指令。
重复 parser corpus 验证移除了该唯一指令（驱动单独处理），三轮解析清理通过；
两次失败记录保留，不算原始文本独立 parser 通过。
旧 reduction-with 首次仅陈旧诊断断言失败，确认 M169 同样诊断后精确修订并重跑全组。

未修改的公开 Accellera UVM 2020.3.1 native 首错从 callback:1141
推进到 report_object:542，无括号且无局部声明的函数体仍不支持。
完整 UVM、受约束随机、IPC、virtual interface/clocking、coverage 等目标继续。
本批尚未更新稳定入口，稳定仍 M169；Linux M169 Intel 回归独立运行中。
