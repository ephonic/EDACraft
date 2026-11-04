# SV 函数的原生编译边界

大语句中重复调用非平凡 SV 函数时，将每次调用的完整 PC 解释器内联到同一个 C++ 函数，会放大 Clang/GCC 优化开销。生成器对展开函数体达到1024字节的调用 lambda 标记 `noinline`，保留编译边界；小函数继续由原生编译器正常优化。Intel LLVM 对已隔离的大函数体另加 minsize，约束内部 helper 的展开，其他代码继续采用配置的优化级别；Clang/GCC 保留 noinline 边界。阈值基于生成体大小，不依赖 HDL 名称、case 或刺激。仍使用原有实参求值顺序、ref guard、返回/副作用和 runtime 计步规则。

原始 retained_memory_codec 在 M157 的 -O2 编译复现180秒超时。试验隔离调用后52秒，正式生成器开发运行约49秒，随后约4秒完成15418个观测并与合格VCS四态周期参考逐位一致。这些为本机该输入的编译时间测量，不是普遍加速倍数、runtime与VCS速度对比或完整签核。编译后另发现默认1000万指令上限误终止合法长运行，默认限额改为uint64最大值，显式 --max-events 与 API 预算继续生效；见[预算语义](budget-resume.md)。发布与最终跨平台结果以validation/m158-function-boundaries为准。
