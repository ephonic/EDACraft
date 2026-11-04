# 零延迟输入通道是否可消除：VCS判别

完整scalar工作负载的129,634,749次延迟交付中，78,922,808次（60.88%）为零，见`../m5-sdf-event-profile/results.json`。这不等于可直接删掉这些事件。本批同一VCS程序实例化已注解d及未注解e，通过驱动语句后的立即XMR读取、输入变化观察以及完整波形，判断零IC/PORT的实际可见行为。八例覆盖同Active和#0脉冲、四态、有效值经更新归零、多驱动、正IOPATH、边沿路径和width检查；另有9ps IC正对照，以证明注解和观察点能够检测实际输入延迟。

首任务`probe`在编译第一例后被严格注解警告检查中止：输入通过`assign n=a`连接，VCS报`SDFCOM_IWSBA`（仍会回标）。没有运行仿真，不能作为零通道证据。13文件原始归档`9b6cfb0421c5c3e8aa87aaeffa763f128378b48fd1dcb8587886612766a8fa08`已保存。`followup`改用直接输入连接；多驱动PORT仍使用真实解析网。原首任务输入和日志不覆盖。

`followup`八例、`control`一例各三次VCS均已正常退出0，27份原始VCD/TRACE及输入哈希独立核对通过。七组零通道的立即读取及全部d/e内部物理位一致；9ps正对照与ABSOLUTE9后ABSOLUTE0均保留非零输入延迟，观察方法能够区分。后者揭示旧实现的错误：ABS写零不能清除已有MIPD，INCREMENT可以减至零。已修正该规则，原始证据不覆盖，见[vendor-verification.json](vendor-verification.json)。这些TB的XMR仅用于vendor判别；native版本移除被动XMR监视与e对照实例，只比较明确导出的物理信号。

实际编译器已加入默认关闭的`--gate-fold-zero-inputs`：仅消除最终量化三值全零的IC/PORT接收槽、通道与处理作业，接收引脚继续作为源网的波形别名；非零输入、全部IOPATH/条件/边沿、检查与每实例输出状态保留。过滤后的描述符重新连续编号，IR以`zero_input_pins_folded`报告数量。未合并RTL/gate parser，也未更改runtime/parallel/wave头。

454文件源码SHA256为`597019eb611b936ecbc7c6b5665b92819d1de8ff34d8b968fe53105646082d04`，见[source.json](source.json)。本地实际九例×三后端通过：162份完整ordered/settled VCD/raw/Zstd流，192次VCS物理位对照；除有意修复的ABS归零反例外，24次关闭选项整个CPP与450逐字相同。三例×两后端的预测提交/错误预测回滚通过24份完整捕获，另24份macOS ASan/UBSan捕获通过。两个既有PORT单/多驱动优先级流程48份捕获及四个非法CLI边界通过。独立解码与源身份见[local-validation.json](local-validation.json)。不是完整本地104项或Linux sanitizer。

额外八例×三次VCS的181份原始文件已归档并审计，见[readback-verification.json](readback-verification.json)。直接顶层输入的非零ABS重复9→3仍为9，与既有内部单驱动末次更新策略存在差异；作用域/驱动解析尚待调查。这八例不声称native等价，七组零延迟的结论不能推广为完整MIPD兼容。

同一454冻结包的原Linux任务`/tmp/dsim-zero-input-full-1018-VirMp81E`现已正常退出0，1,563份证据归档SHA256 `2735f90b6081c4b84b834b1a449f2ce8a1eaad9ca0c51e974d28acba0147f21a`，独立[全量审计](full-verification.json)PASS：五项定向CTest，162常规+24回滚跨平台捕获，192次VCS物理位比较；原设计790,222个输入通道全部满足折叠条件，生成完整CPP仅有预期消除；folded/jobs与folded/dictionary-wheel两版实际重新发射、编译并执行，各128笔匹配。保留867,982 IOPATH、86,496检查、零禁用检查及23,051负limit夹零。不是Linux完整104项或Linux sanitizer。

独立性能初筛原任务`/tmp/dsim-zero-input-timing-1018-9WPJVpYL`已正常退出0且原PID消失，99份归档SHA256 `5df1ca1287c9686825d99841c700519b453bad1842bed75fb9b3a84059aea956`下载并[独立复算PASS](measurement-verification.json)：固定CPU0，基线/仅折叠/VCS各一次预热、六轮循环换序，全部21次各128笔匹配，输入/二进制/SDF缓存身份未变。只隔离折叠收益，基线为已验证整个CPP相同的432 scalar/jobs二进制，无时间轮或路径字典；关闭波形、默认非负检查，VCS重载已接受缓存。

| 指标 | scalar/jobs基线 | 增加零通道折叠 | 同轮VCS |
| --- | --- | --- | --- |
| CPU中位数（秒） | 81.00 | 51.935 | 7.01 |
| RSS中位数（KiB） | 524,364 | 309,824 | 213,096 |
| CPU/VCS | 11.55 | 7.41 | 1 |

六对CPU耗时分别下降34.78%/36.88%/34.24%/38.62%/36.01%/32.46%，配对中位数35.39%；RSS中位数下降40.91%。全部样本保留，共享主机未锁频率；默认关闭、独立复测待做，不能将候选成绩称为默认后端或RTL性能。后继异步波形源不混入此测量。零输入之外的传播融合、自动并行和波形扩展继续推进。
