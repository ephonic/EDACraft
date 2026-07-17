"""
验证框架使用示例

展示如何使用验证框架对新开发的物理效应进行验证。
"""

import numpy as np
import sys
sys.path.insert(0, '/Users/yangfan/tcad')

from tcad.validation import ValidationFramework, create_validation_framework


def example_basic_validation():
    """
    示例1: 基本验证
    
    对新开发的铁电模型进行基本验证。
    """
    print("=" * 70)
    print("示例1: 基本验证")
    print("=" * 70)
    
    # 定义设备构建函数
    def device_builder(nx=40, ny=40, **kwargs):
        """构建测试设备"""
        from tcad.simulator import Simulator
        from tcad.geometry import Device
        
        # 创建简单的MOSFET结构
        device = Device.mosfet(
            Lg=50e-9,
            tox=2e-9,
            tsi=10e-9,
            W=100e-9,
            Vg=kwargs.get('Vg', 1.0),
            Vd=kwargs.get('Vd', 0.1)
        )
        
        # 创建模拟器
        sim = Simulator(device, nx=nx, ny=ny)
        
        # 设置铁电参数（如果提供）
        if 'Ps' in kwargs:
            sim.set_ferroelectric(
                model='NLS',
                Ps=kwargs['Ps'],
                Ec=kwargs.get('Ec', 3.5e8)
            )
        
        return sim
    
    # 创建验证框架
    framework = ValidationFramework(device_builder, name="NLS铁电模型验证")
    
    # 添加基本测试
    framework.add_grid_convergence_test(mesh_sizes=[20, 40, 80])
    framework.add_conservation_test()
    framework.add_boundedness_test()
    
    # 运行测试
    results = framework.run_all()
    
    # 打印报告
    framework.print_report()
    
    # 获取摘要
    summary = framework.get_summary()
    print(f"\n验证结果: {'通过' if summary['all_passed'] else '失败'}")
    print(f"通过率: {summary['pass_rate']:.1f}%")
    
    return framework


def example_ferroelectric_validation():
    """
    示例2: 铁电模型全面验证
    
    对新开发的NLS铁电模型进行全面验证。
    """
    print("\n" + "=" * 70)
    print("示例2: 铁电模型全面验证")
    print("=" * 70)
    
    def device_builder(nx=40, ny=40, **kwargs):
        """构建FeFET设备"""
        from tcad.simulator import Simulator
        from tcad.geometry import Device
        
        device = Device.gaa_fefet(
            Lg=30e-9,
            t_fe=10e-9,
            t_ox=2e-9,
            t_body=10e-9,
            W=20e-9,
            Vg=kwargs.get('Vg', 1.0),
            Vd=kwargs.get('Vd', 0.1)
        )
        
        sim = Simulator(device, nx=nx, ny=ny)
        
        # 设置NLS铁电模型
        model = kwargs.get('model', 'NLS')
        if model == 'NLS':
            sim.set_ferroelectric(
                model='NLS',
                Ps=kwargs.get('Ps', 1.4),
                Ec=kwargs.get('Ec', 3.5e8),
                tau0=kwargs.get('tau0', 1e-9),
                E0=kwargs.get('E0', 1e8)
            )
        elif model == 'LK':
            sim.set_ferroelectric(
                model='LK',
                alpha=-5e8,
                beta=1.5e10
            )
        
        return sim
    
    # 创建全面验证框架
    framework = create_validation_framework(
        device_builder,
        name="NLS铁电模型全面验证",
        test_suite='comprehensive'
    )
    
    # 添加铁电特定的测试
    framework.add_limiting_case_test('nls_to_lk', tolerance=0.1)
    framework.add_symmetry_test('ferroelectric', tolerance=0.05)
    
    # 运行测试
    results = framework.run_all()
    
    # 打印报告
    framework.print_report()
    
    # 保存报告
    framework.save_report('ferroelectric_validation_report.txt')
    
    return framework


def example_interface_traps_validation():
    """
    示例3: 界面陷阱模型验证
    
    对新开发的界面陷阱模型进行验证。
    """
    print("\n" + "=" * 70)
    print("示例3: 界面陷阱模型验证")
    print("=" * 70)
    
    def device_builder(nx=40, ny=40, **kwargs):
        """构建带界面陷阱的MOSFET"""
        from tcad.simulator import Simulator
        from tcad.geometry import Device
        
        device = Device.mosfet(
            Lg=50e-9,
            tox=2e-9,
            tsi=10e-9,
            W=100e-9,
            Vg=kwargs.get('Vg', 1.0),
            Vd=kwargs.get('Vd', 0.1)
        )
        
        sim = Simulator(device, nx=nx, ny=ny)
        
        # 设置界面陷阱
        if 'D_it' in kwargs and kwargs['D_it'] > 0:
            sim.set_interface_traps(
                D_it=kwargs['D_it'],
                E_t=kwargs.get('E_t', 0.0)
            )
        
        return sim
    
    # 创建验证框架
    framework = ValidationFramework(device_builder, name="界面陷阱模型验证")
    
    # 添加测试
    framework.add_grid_convergence_test(mesh_sizes=[20, 40, 80])
    framework.add_conservation_test()
    framework.add_limiting_case_test('no_traps', tolerance=0.01)
    framework.add_sensitivity_test('D_it', (0, 1e13), num_points=5)
    
    # 运行测试
    results = framework.run_all()
    
    # 打印报告
    framework.print_report()
    
    return framework


def example_retention_endurance_validation():
    """
    示例4: 保持特性和耐久性验证
    
    对新开发的保持特性和耐久性模型进行验证。
    """
    print("\n" + "=" * 70)
    print("示例4: 保持特性和耐久性验证")
    print("=" * 70)
    
    def device_builder(nx=40, ny=40, **kwargs):
        """构建FeFET设备"""
        from tcad.simulator import Simulator
        from tcad.geometry import Device
        
        device = Device.gaa_fefet(
            Lg=30e-9,
            t_fe=10e-9,
            t_ox=2e-9,
            t_body=10e-9,
            W=20e-9,
            Vg=kwargs.get('Vg', 1.0),
            Vd=kwargs.get('Vd', 0.1)
        )
        
        sim = Simulator(device, nx=nx, ny=ny)
        sim.set_ferroelectric(model='NLS', Ps=1.4, Ec=3.5e8)
        
        # 设置氧化物陷阱（用于保持/耐久性）
        if 'Q_ot' in kwargs:
            sim.set_oxide_traps(Q_ot=kwargs['Q_ot'])
        
        return sim
    
    # 创建验证框架
    framework = ValidationFramework(device_builder, name="保持/耐久性模型验证")
    
    # 添加测试
    framework.add_grid_convergence_test()
    framework.add_transient_conservation_test(dt=1e-9, t_final=1e-7)
    framework.add_boundedness_test()
    framework.add_parameter_convergence_test('Q_ot', [0, 1e4, 1e5, 1e6])
    
    # 运行测试
    results = framework.run_all()
    
    # 打印报告
    framework.print_report()
    
    return framework


def example_custom_validation():
    """
    示例5: 自定义验证
    
    展示如何自定义验证测试。
    """
    print("\n" + "=" * 70)
    print("示例5: 自定义验证")
    print("=" * 70)
    
    from tcad.validation.base import BaseValidationTest, ValidationResult
    
    # 自定义测试类
    class CustomPhysicsTest(BaseValidationTest):
        """自定义物理测试"""
        
        def __init__(self):
            super().__init__("Custom Physics Test")
        
        def run(self, device_builder):
            """运行自定义测试"""
            try:
                sim = device_builder()
                result = sim.run()
                
                # 自定义验证逻辑
                # 例如：检查某个物理量是否满足特定条件
                phi = getattr(result, 'phi', np.zeros(1))
                
                # 检查电势是否满足拉普拉斯方程（简化版本）
                # 实际应用中需要根据具体物理模型定义
                condition_satisfied = True  # 简化版本
                
                return ValidationResult(
                    self.name,
                    condition_satisfied,
                    "自定义物理条件满足" if condition_satisfied else "自定义物理条件不满足",
                    {'condition': condition_satisfied}
                )
                
            except Exception as e:
                return ValidationResult(
                    self.name,
                    False,
                    f"测试失败: {str(e)}"
                )
    
    def device_builder(nx=40, ny=40):
        from tcad.simulator import Simulator
        from tcad.geometry import Device
        
        device = Device.mosfet(Lg=50e-9, tox=2e-9, tsi=10e-9, W=100e-9)
        return Simulator(device, nx=nx, ny=ny)
    
    # 创建验证框架
    framework = ValidationFramework(device_builder, name="自定义验证")
    
    # 添加自定义测试
    framework.add_test(CustomPhysicsTest())
    
    # 添加标准测试
    framework.add_grid_convergence_test()
    framework.add_conservation_test()
    
    # 运行测试
    results = framework.run_all()
    
    # 打印报告
    framework.print_report()
    
    return framework


if __name__ == '__main__':
    # 运行所有示例
    print("\n" + "=" * 70)
    print("TCAD 验证框架使用示例")
    print("=" * 70 + "\n")
    
    # 示例1: 基本验证
    try:
        framework1 = example_basic_validation()
    except Exception as e:
        print(f"示例1失败: {e}")
    
    # 示例2: 铁电模型全面验证
    try:
        framework2 = example_ferroelectric_validation()
    except Exception as e:
        print(f"示例2失败: {e}")
    
    # 示例3: 界面陷阱模型验证
    try:
        framework3 = example_interface_traps_validation()
    except Exception as e:
        print(f"示例3失败: {e}")
    
    # 示例4: 保持/耐久性验证
    try:
        framework4 = example_retention_endurance_validation()
    except Exception as e:
        print(f"示例4失败: {e}")
    
    # 示例5: 自定义验证
    try:
        framework5 = example_custom_validation()
    except Exception as e:
        print(f"示例5失败: {e}")
    
    print("\n" + "=" * 70)
    print("所有示例运行完成")
    print("=" * 70)
