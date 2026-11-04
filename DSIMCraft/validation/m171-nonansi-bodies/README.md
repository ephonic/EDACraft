# M171：零端口非 ANSI 函数体

支持范围见 [无括号函数声明](../../docs/nonansi-bodies.md)。
最终四模型74捕获、四拒绝、一次预测回滚/一次提交，完整parser/格式parser/原生DB通过。
旧 extern 十一模型200捕获、一次回滚一次提交通过。
ASan/UBSan 完整parser、四前端/四拒绝、四生成程序及回放通过，
CPP和异步波形与正常执行逐字节相同；不作LSan/TSan声明。
VCS四个原样源码执行输出一致，四个拒绝例同样拒绝；源码SHA记录在vcs.json。
初次开发脚本匹配规则计数失败，没有写入文件；修订后十个无声明分支及
两个参数化返回值生命周期分支生成成功，冲突数保持86。

普通和ASan的未修改公开Accellera UVM 2020.3.1预处理仍为1888084字节、
166依赖、SHA a0e1425aeebafd981a99a5f563b3327d800b968f448f790d95293d4c83d1611d。
使用原有UVM_NO_DPI选项，native首错从report_object:542推进到transaction:443的const属性。
公开库仍未完成编译或运行，约束随机、IPC、virtual interface/clocking、coverage等目标继续。
当前准备冻结发布，稳定仍M169，M169的103 Intel回归仍独立进行，不以本地结果替代远端结果。

M171本地候选已冻结69893493并激活：2200源码成员、1121发布输入、九组1064捕获及mandatory通过。13CPP/74新捕获精确绑定开发证据，实际入口四模型和所选异步波形、原始r02省略--top、公开UVM首错复核通过。稳定入口为20261029T113541915558Z-2cf55140a1f4，二进制SHA e091cf0f5c319d155912c2a9fdf55a1266288f780b902da61334e6e5c6c860f3。源归档保存于dsim-test/evidence/m171-nonansi-bodies。103此时已更新M169，M171尚未向远端发布。
