# 命名有限 SVA 序列（M138）

支持模块及 generate 作用域中的无形参、无显式时钟 sequence 声明，以名称或空括号调用，继承 property 的单一时钟。例如：

```systemverilog
sequence response();
  ready ##2 done;
endsequence : response
sequence burst;
  response()[*3] ##0 accepted;
endsequence
assert property (@(posedge clk) disable iff (reset) request |-> burst)
  passed++; else failed++;
```

名称在所在作用域预注册，支持前向引用和嵌套调用。声明按词法作用域绑定：内层同名声明不会改变外层序列内部引用的含义；参数化实例和 generate 克隆各自绑定。引用只持有非拥有声明指针，不复制或接管声明 AST，递归图在编译时检查，包括未使用声明。

调用在参数绑定后展开到既有有限阶段列表，可以与括号组、固定周期延迟和固定正数连续重复组合。采样表达式在一次展开中只降低一次，随后由重复阶段共享，保持既有 Preponed 采样、Reactive 动作、异步 disable iff、独立尝试及预测提交/回滚语义。没有修改 runtime 头文件或门级 parser。

计数为已知整数常量 1..256；展开总计最多 256 阶段、65536 拍；命名引用链和组/引用展开深度最多 128。支持 endsequence 可选同名标签、无括号或空括号声明/引用。Verilog 语言模式仍允许 sequence/endsequence 作为标识符。

M140 已支持有限 sequence 作为蕴含前件，见[范围](sequence-antecedents.md)。尚不支持 sequence 形参/实参、局部变量、显式时钟、package 内声明或层次调用、布尔表达式中使用 sequence、空/范围/无界重复、多时钟和完整 SVA。这些能力不由本批成功用例推断为已具备。验收与双端稳定发布记录见 [M138](../validation/m138-named-sequences/README.md)，本批没有性能测量。
