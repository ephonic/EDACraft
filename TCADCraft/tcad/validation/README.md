# TCAD 验证策略集

为物理效应开发提供系统化的验证框架，确保代码正确性和可靠性。

## 验证策略概览

```
        ┌─────────────────┐
        │  物理一致性验证  │  ← 对称性、守恒律、极限行为
        ├─────────────────┤
        │  数值方法验证    │  ← 收敛性、稳定性、精度
        ├─────────────────┤
        │  数学正确性验证  │  ← 单元测试、类型检查
        └─────────────────┘
```

## 目录结构

```
tcad/validation/
├── __init__.py              # 模块初始化
├── base.py                  # 基础类和工具函数
├── convergence.py           # 收敛性验证
├── conservation.py          # 守恒律验证
├── symmetry.py              # 对称性验证
├── limiting_cases.py        # 极限情况验证
├── boundedness.py           # 有界性和单调性验证
├── cross_validation.py      # 交叉验证
├── sensitivity.py           # 敏感性分析
├── report.py                # 验证报告生成
├── framework.py             # 验证框架主类
└── examples/
    └── example_usage.py     # 使用示例
```

## 验证策略详解

### 1. 收敛性验证 (`convergence.py`)

**网格收敛性测试** - 最重要的验证方法，不需要任何实验数据
- 验证数值解随网格加密收敛
- 计算收敛阶（二阶方法应为2.0）
- 检查误差单调递减

**时间步长收敛性测试**
- 验证瞬态模拟的时间步长收敛性
- 检查相邻时间步长结果的差异

**参数收敛性测试**
- 验证结果随参数变化的平滑性

### 2. 守恒律验证 (`conservation.py`)

**电荷守恒**
- 稳态：∇·J = 0（电流连续性）
- 瞬态：∂ρ/∂t + ∇·J = 0

**能量守恒**
- 输入能量 = 存储能量 + 耗散能量

**熵产生**
- 热力学第二定律：熵产生 ≥ 0

### 3. 对称性验证 (`symmetry.py`)

**电压反转对称性**
- V和-V应该给出镜像结果

**几何对称性**
- 对称结构应该给出对称结果

**铁电极化对称性**
- 无内建场时P-V曲线应该对称

### 4. 极限情况验证 (`limiting_cases.py`)

验证在极限情况下模型是否退化为已知模型：
- `no_ferroelectric`: 无铁电层退化为MOSFET
- `high_temperature`: 高温极限退化为经典模型
- `thin_oxide`: 超薄氧化层极限
- `nls_to_lk`: NLS模型退化为LK模型
- `preisach_to_lk`: Preisach模型退化为LK模型
- `no_traps`: 无陷阱退化为理想器件

### 5. 有界性和单调性验证 (`boundedness.py`)

**物理边界条件**
- 载流子浓度为正
- 电势在合理范围内
- 铁电极化不超过Ps

**单调收敛**
- Newton迭代残差单调递减

### 6. 交叉验证 (`cross_validation.py`)

不同数值方法的交叉验证：
- 有限差分 vs 有限元
- 显式 vs 隐式时间积分
- 不同线性求解器

### 7. 敏感性分析 (`sensitivity.py`)

**参数敏感性**
- 结果应该随参数平滑变化
- 不应该出现突然的跳变（除相变外）

**参数重要性**
- 识别关键参数

## 使用方法

### 基本使用

```python
from tcad.validation import ValidationFramework

# 定义设备构建函数
def device_builder(nx=40, ny=40, **kwargs):
    from tcad.simulator import Simulator
    from tcad.geometry import Device
    
    device = Device.mosfet(Lg=50e-9, tox=2e-9, tsi=10e-9, W=100e-9)
    sim = Simulator(device, nx=nx, ny=ny)
    
    # 设置物理参数
    if 'Ps' in kwargs:
        sim.set_ferroelectric(model='NLS', Ps=kwargs['Ps'])
    
    return sim

# 创建验证框架
framework = ValidationFramework(device_builder, name="NLS铁电模型验证")

# 添加测试
framework.add_grid_convergence_test(mesh_sizes=[20, 40, 80])
framework.add_conservation_test()
framework.add_boundedness_test()

# 运行测试
results = framework.run_all()

# 打印报告
framework.print_report()

# 保存报告
framework.save_report('validation_report.txt')
```

### 使用预定义测试套件

```python
from tcad.validation import create_validation_framework

# 创建标准验证框架
framework = create_validation_framework(
    device_builder,
    name="标准验证",
    test_suite='standard'  # 'basic', 'standard', 'comprehensive'
)

# 运行测试
framework.run_all()
framework.print_report()
```

### 自定义验证测试

```python
from tcad.validation.base import BaseValidationTest, ValidationResult

class CustomPhysicsTest(BaseValidationTest):
    def __init__(self):
        super().__init__("Custom Physics Test")
    
    def run(self, device_builder):
        try:
            sim = device_builder()
            result = sim.run()
            
            # 自定义验证逻辑
            phi = getattr(result, 'phi', np.zeros(1))
            condition_satisfied = True  # 你的验证条件
            
            return ValidationResult(
                self.name,
                condition_satisfied,
                "验证通过" if condition_satisfied else "验证失败"
            )
        except Exception as e:
            return ValidationResult(self.name, False, f"测试失败: {str(e)}")

# 使用自定义测试
framework = ValidationFramework(device_builder)
framework.add_test(CustomPhysicsTest())
framework.run_all()
```

## 验证流程建议

### 新物理效应开发流程

1. **数学正确性验证**
   - 单元测试
   - 类型检查
   - 矩阵对称性

2. **数值方法验证**
   - 网格收敛性测试（最重要！）
   - 时间步长收敛性测试
   - 参数收敛性测试

3. **物理一致性验证**
   - 守恒律验证
   - 对称性验证
   - 极限情况验证

4. **有界性和单调性验证**
   - 物理边界条件
   - 单调收敛

5. **交叉验证**
   - 不同数值方法对比
   - 不同模型对比

6. **敏感性分析**
   - 参数敏感性
   - 参数重要性

### 验证检查清单

- [ ] 网格收敛性测试通过
- [ ] 时间步长收敛性测试通过（瞬态问题）
- [ ] 电荷守恒满足
- [ ] 能量守恒满足（如适用）
- [ ] 对称性验证通过
- [ ] 极限情况退化为已知模型
- [ ] 载流子浓度为正
- [ ] 电势在合理范围内
- [ ] 收敛过程单调
- [ ] 交叉验证通过

## 示例

查看 `examples/example_usage.py` 获取完整示例：

```bash
python -m tcad.validation.examples.example_usage
```

## 报告格式

验证报告包含：
- 测试结果汇总（通过/失败数量）
- 详细测试结果（每个测试的状态、消息、详细信息）
- 失败测试列表
- 建议

## 最佳实践

1. **优先使用网格收敛性测试** - 这是最可靠的验证方法
2. **始终验证守恒律** - 这是物理定律的基石
3. **检查极限情况** - 新模型应该退化为已知模型
4. **验证对称性** - 物理系统通常具有对称性
5. **检查有界性** - 物理解应该在合理范围内
6. **使用交叉验证** - 不同方法应该给出一致结果

## 故障排除

### 测试失败

1. 检查失败测试的详细信息
2. 修复代码中的问题
3. 重新运行验证测试

### 收敛性问题

1. 检查网格质量
2. 调整时间步长
3. 检查物理参数是否合理

### 守恒律违反

1. 检查边界条件
2. 检查数值格式
3. 增加网格密度

## 参考资料

- 收敛性分析：Numerical Recipes in C
- 守恒律验证：Finite Volume Methods for Hyperbolic Problems
- 对称性验证：Group Theory and Physics

## 许可证

MIT License
