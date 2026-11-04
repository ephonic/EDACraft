# const 类属性

RTL parser 和编译执行链路保留 `const` 属性元数据，包括 local/protected、
static、参数化特化、继承及 extern 构造器。支持整数、宽 packed、实数、字符串和类句柄属性。

带声明初始化的属性只在初始化处赋值，其余写入拒绝。
不带初始化的实例常量可在声明该属性的类构造器中赋值；
运行时按对象和字段记录是否已经赋值，第二次赋值报错，包括写入相同的默认值。
该记录随对象堆进入 checkpoint，预测回滚保留句柄别名和常量状态。
构造器内的循环/嵌套块保留所属构造器身份，普通被调方法不继承初始化权限。
静态常量必须带声明初始化，其只读信号编号随 elaboration 的信号重排同步更新。

```systemverilog
class Child;
  int count;
endclass
class Token;
  const int id;
  const local Child child = new;
  static const int limit = 32;
  function new(int n); id=n; endfunction
  function void tick(); child.count++; endfunction
endclass
```

类句柄常量保护句柄本身；可以通过它调用方法和修改所指对象的普通属性。
不能重新给这个句柄赋值。此处的只读规则依据
[IEEE 1800-2017 §8.19、§6.20.6](https://fpga.mit.edu/6205/_static/F25/documentation/1800-2017.pdf)。

仍有边界：const 未打包类数组、类外 const 变量尚未接通；
派生构造器给继承常量赋值当前拒绝，本轮 VCS 接受，保留为待进一步对齐项。
VCS 也接受本轮测试中的已初始化常量位选写入和静态常量传给可写 ref，原生仍拒绝。
运行时循环对同一实例常量重复赋值时，本轮 VCS 未拦截，运行到了测试的兜底 `$fatal`；
原生按一次赋值规则报错，不能把这个负例称为两工具运行结果一致。
未调用方法体沿既有机制延迟绑定，不能据此声明所有未使用的非法定义已被诊断。

四个模型覆盖值链路、可变的所指对象、继承、泛型、static/extern 和预测恢复，
74 次捕获、11 个编译拒绝、一个重复赋值运行时拒绝通过。
完整/所选时间与信号范围的 VCD、同步/异步压缩 DWF 一致；
四个原样源码与 VCS 输出一致，拒绝边界八项一致、三项接受差异。
ASan/UBSan 前端、完整 parser、生成程序、回放和运行时拒绝通过；
旧 class static/access 两组各182捕获通过，不作性能、LSan/TSan或完整UVM声明。
