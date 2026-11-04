# 类成员访问权限

M163 在独立 RTL parser 中补入 `local` / `protected` 属性和 function/task（含构造器）。未限定的成员保持 public，`local static` / `static local`、`protected virtual` / `virtual protected` 及 pure virtual 原型保留限定符；重复和互斥限定符会拒绝。

权限按声明所在类和调用处的词法类检查，不按接收者的动态类型判断。同一类可以访问另一实例的 local 成员；派生类可以访问 protected 成员，不能访问基类 local 成员。继承的基类方法仍在基类词法作用域执行，基类私有字段与派生同名字段保持独立。查找派生类未限定名称时跳过基类 local 成员，允许继续查找外层同名符号。对象成员、类作用域、参数化特化、静态方法和生成的调用副本共享这套检查。

local 构造器可以由本类工厂调用，类外 new 会拒绝；它也使该类不可继承，因为隐式和显式 super.new 都需要访问权限。protected 构造器允许派生类调用。虚方法覆盖须保持相同访问权限；没有远端 VCS 实测时不据此声称与某个 VCS 版本全部一致。

声明元数据随语法克隆复制，符号作用域记录非拥有的类身份；重复解析清理会重置继承和类身份关联。检查发生在编译阶段，不给仿真运行时增加逐次权限判断。

本批仍有边界：未调用的方法体按原有机制延迟绑定，未调用体内的非法访问可能暂不诊断；private/protected typedef及嵌套类权限组合未完成（extern/类外方法定义见 [M165](extern-methods.md)）；类实例 queue/动态/固定数组属性仍不支持，当前实例数组属性限一维 int/string 键关联数组。限定符不会扩大底层存储能力，也不意味着完整 OOP/UVM 已实现。VCD/DWF 仍通过用户的观察变量导出动态字段。

标准依据为 IEEE 1800-2017 §8.17–8.20 和 Annex A.1.9，见[标准文本](https://fpga.mit.edu/6205/_static/F25/documentation/1800-2017.pdf)。新增用例及现存边界见 [class_access](../tests/class_access)，验收和原始 REPORT-GAP2 的复查见 [M163](../validation/m163-class-access/README.md)。
