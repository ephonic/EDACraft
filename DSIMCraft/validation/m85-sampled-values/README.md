# M85 并发断言采样值函数

实现单时钟 property 的 $sampled/$past/$rose/$fell/$stable/$changed；支持 $past 常量深度、可选门控、嵌套及动作/disable iff 的 $sampled。RTL parser 与 gate parser 分离，历史和结果在 Sim 中，参与 checkpoint 与实际并行分区。范围见 ../../docs/concurrent-assertions.md。

7 个同源模型在实际 VCS W-2024.09_Full64 运行通过，全部 1,350 个共同物理位完整 settled 时间线相同，无尾部排除；所有非共同位逐项列在 vcs-alignment.json。verify.py 从源 hash、stdout 和完整 VCD 重算，不只比较 PASS 字样。

原生 27 份完整 ordered VCD 捕获（三后端加六次实际失败预测回滚）、14 类错误拒绝通过，parallel.sv 实际分为两个独立 worker。冻结源码和完整生成 C++/二进制 hash 见 input-provenance.json 和 accepted-artifacts.json，大型 C++/程序留在 /tmp/dsim-m85-native-accepted，完整输出和波形保留在 native。

sanitized/results.json 记录 14 个实际 ASan/UBSan 程序（七 serial、六失败预测、一个真正双分区程序），全部输出及完整 ordered 波形与验收一致，14 类负例正确拒绝。parser 反复解析/实例克隆/清理原生和 sanitizer 通过，包含嵌套函数/门控/多实例与 $time。关闭 leak 检测。

实现提交 dc8a08f，$time 修复提交 1a0c90f。64组本地稳定发布通过，已切换本机入口；Linux 四组检查通过并部署，68次实际执行输出和完整 ordered 波形与验收一致。Linux 的7同源模型与VCS的1350个物理位完整settled时间线相同。安装入口在加载 syn.bash 后实际编译运行 history 通过。身份和 hash 见 stable-release.json、linux/release.json、stable-identity.json、linux-identity.json。

开发记录：首轮双实例测试因自身 $fatal 导致串行回退，改用独立 done 信号并检查真实两分区；新下降沿首拍测试初始预期漏算静态 clock X->0 的时间零边沿，修正检查次数为五，不修改调度器。其参考 always 在时间零还与 initial 赋值产生 Active 顺序竞态，VCS 在下一沿失败而 dsim 通过；修正参考过程为只在非零时刻更新，避免将合法的 Active 顺序差异当成历史函数语义。原始失败输出和源保留在 development。VCS 首拍初值探针区分静态声明初始化和时间零过程赋值。

修正参考测试使用 $time>0 时，发现原有 parser 的数值操作数检查漏接 vtSYS_VAR；新增合法类型分支，复用原有 $time 运行时 lowering，并增加 parser 反复克隆清理测试。第一次发布构建和 Linux 构建因该新增缺陷修复主动中断，稳定入口保持旧版；保留中断记录，再从修复提交重新构建。

早期 sanitizer 验证指向旧版 initial 生成代码，随后又在 native 的 replay.cpp 尚未生成时访问，均按失败保存；最终等待冻结 native 全部完成，再以 --resume 校验实际生成 C++ 身份、运行所有程序并比较完整输出/波形，最终全部通过。development 保留这些日志，不将早期失败隐藏为成功。

第二次 Linux 构建启动时曾因本地脚本准备失败而沿用旧提交标签；在发布前中止并以 1a0c90f 重新执行，保留 linux-metadata-interrupted 日志。最终构建逐项核对源码、runtime 和二进制 hash 通过。
