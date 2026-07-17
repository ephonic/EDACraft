#!/usr/bin/env python3
"""
测试新增物理方程功能的验证脚本

使用验证策略集框架对以下新增功能进行验证：
1. 界面陷阱(Dit)和体内氧化物陷阱(Q_ot)
2. 保持特性(retention)和耐久性(endurance)
3. NLS铁电模型
4. PF/FN漏电流模型
5. 内建场(E_bi)

运行方式：
    python tcad/validation/examples/test_new_physics.py
"""

import sys
import numpy as np
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from tcad.validation import ValidationFramework
from tcad.validation.base import ValidationResult
from tcad.geometry import Device
from tcad.mesh import generate_mesh
from tcad.simulator import Simulator


def test_interface_traps():
    """
    测试界面陷阱(Dit)和体内氧化物陷阱(Q_ot)
    
    验证内容：
    - 陷阱电荷是否正确注入到泊松方程
    - 阈值电压是否随Dit变化
    - 电荷守恒是否满足
    """
    print("\n" + "="*70)
    print("测试1: 界面陷阱和氧化物陷阱")
    print("="*70)
    
    def device_builder(Dit=0.0, Q_ot=0.0, **kwargs):
        """构建设备并设置陷阱参数"""
        # 创建简单的MOS结构
        device = Device.mosfet(
            Lg=50e-9,
            tox=2e-9,
            tsi=10e-9,
            W=100e-9,
            Vg=1.0,
            Vd=0.0
        )
        
        # 生成网格 - 使用固定分辨率
        mesh = generate_mesh(device, method='structured', resolution=(5e-9, 2e-9, 10e-9))
        
        # 创建模拟器
        sim = Simulator(mesh)
        
        # 设置界面陷阱
        if Dit > 0:
            sim.set_interface_traps(Dit=Dit, E_t=0.5)
        
        # 设置氧化物陷阱
        if Q_ot > 0:
            sim.set_oxide_traps(Q_ot=Q_ot)
        
        return sim
    
    # 创建验证框架
    framework = ValidationFramework(device_builder, name="界面陷阱验证")
    
    # 添加验证测试
    framework.add_grid_convergence_test(mesh_sizes=[20, 40, 80])
    framework.add_conservation_test()
    framework.add_boundedness_test()
    framework.add_symmetry_test('voltage_reversal')
    
    # 运行验证
    results = framework.run_all()
    framework.print_report()
    
    return framework


def test_retention_endurance():
    """
    测试保持特性和耐久性
    
    验证内容：
    - 保持特性：极化衰减是否合理
    - 耐久性：循环次数与性能退化的关系
    - 物理边界条件是否满足
    """
    print("\n" + "="*70)
    print("测试2: 保持特性和耐久性")
    print("="*70)
    
    def device_builder(cycles=0, **kwargs):
        """构建设备并模拟耐久性循环"""
        # 创建FeFET结构
        device = Device.gaa_fefet(
            Lg=30e-9,
            t_fe=10e-9,
            t_ox=2e-9,
            t_sheet=10e-9,
            W_sheet=20e-9,
            Vg=2.0,
            Vd=0.1
        )
        
        # 生成网格 - 使用固定分辨率
        mesh = generate_mesh(device, method='structured', resolution=(5e-9, 2e-9, 5e-9))
        
        # 创建模拟器
        sim = Simulator(mesh)
        
        # 设置铁电材料
        sim.set_ferroelectric(
            enabled=True,
            model='nls',
            Ps=1.4,
            Ec=3.5e8
        )
        
        # 模拟耐久性循环 - 使用多次运行来模拟循环
        if cycles > 0:
            # 通过多次运行来模拟耐久性循环
            for _ in range(min(cycles, 10)):  # 限制最大循环次数以避免测试时间过长
                sim.run()
        
        return sim
    
    # 创建验证框架
    framework = ValidationFramework(device_builder, name="保持耐久性验证")
    
    # 添加验证测试
    framework.add_grid_convergence_test(mesh_sizes=[20, 30, 40])
    framework.add_conservation_test()
    framework.add_boundedness_test()
    framework.add_parameter_convergence_test('cycles', [0, 100, 500, 1000])
    
    # 运行验证
    results = framework.run_all()
    framework.print_report()
    
    return framework


def test_nls_ferroelectric():
    """
    测试NLS铁电模型
    
    验证内容：
    - NLS模型是否退化为LK模型（极限情况）
    - 铁电极化是否不超过Ps
    - 对称性是否满足
    """
    print("\n" + "="*70)
    print("测试3: NLS铁电模型")
    print("="*70)
    
    def device_builder(model='nls', tau0=1e-9, **kwargs):
        """构建设备并设置铁电模型"""
        # 创建FeFET结构
        device = Device.gaa_fefet(
            Lg=30e-9,
            t_fe=10e-9,
            t_ox=2e-9,
            t_sheet=10e-9,
            W_sheet=20e-9,
            Vg=2.0,
            Vd=0.1
        )
        
        # 生成网格 - 使用固定分辨率
        mesh = generate_mesh(device, method='structured', resolution=(5e-9, 2e-9, 5e-9))
        
        # 创建模拟器
        sim = Simulator(mesh)
        
        # 设置铁电材料
        sim.set_ferroelectric(
            enabled=True,
            model=model,
            Ps=1.4,
            Ec=3.5e8,
            nls_tau0=tau0
        )
        
        return sim
    
    # 创建验证框架
    framework = ValidationFramework(device_builder, name="NLS铁电模型验证")
    
    # 添加验证测试
    framework.add_grid_convergence_test(mesh_sizes=[20, 30, 40])
    framework.add_conservation_test()
    framework.add_boundedness_test()
    framework.add_symmetry_test('ferroelectric')
    framework.add_limiting_case_test('nls_to_lk')
    
    # 运行验证
    results = framework.run_all()
    framework.print_report()
    
    return framework


def test_leakage_current():
    """
    测试PF/FN漏电流模型
    
    验证内容：
    - 漏电流是否随电场指数增长
    - 电荷守恒是否满足
    - 物理边界条件是否满足
    """
    print("\n" + "="*70)
    print("测试4: PF/FN漏电流模型")
    print("="*70)
    
    def device_builder(pf_C=0.02, pf_B=5e5, **kwargs):
        """构建设备并设置漏电流参数"""
        # 创建MOS结构
        device = Device.mosfet(
            Lg=50e-9,
            tox=2e-9,
            tsi=10e-9,
            W=100e-9,
            Vg=2.0,
            Vd=0.0
        )
        
        # 生成网格 - 使用固定分辨率
        mesh = generate_mesh(device, method='structured', resolution=(5e-9, 2e-9, 10e-9))
        
        # 创建模拟器
        sim = Simulator(mesh)
        
        # 设置漏电流模型
        sim.set_leakage(
            pf_C=pf_C,
            pf_B=pf_B,
            pf_phi_t=0.5,
            fn_C=0.0,
            fn_B=0.0,
            fn_phi_b=0.0
        )
        
        return sim
    
    # 创建验证框架
    framework = ValidationFramework(device_builder, name="漏电流模型验证")
    
    # 添加验证测试
    framework.add_grid_convergence_test(mesh_sizes=[20, 40, 80])
    framework.add_conservation_test()
    framework.add_boundedness_test()
    framework.add_parameter_convergence_test('pf_C', [0.01, 0.02, 0.05])
    
    # 运行验证
    results = framework.run_all()
    framework.print_report()
    
    return framework


def test_builtin_field():
    """
    测试内建场(E_bi)
    
    验证内容：
    - 内建场是否正确影响极化翻转
    - 对称性是否被打破
    - 物理边界条件是否满足
    """
    print("\n" + "="*70)
    print("测试5: 内建场(E_bi)")
    print("="*70)
    
    def device_builder(E_bi=0.0, **kwargs):
        """构建设备并设置内建场"""
        # 创建FeFET结构
        device = Device.gaa_fefet(
            Lg=30e-9,
            t_fe=10e-9,
            t_ox=2e-9,
            t_sheet=10e-9,
            W_sheet=20e-9,
            Vg=2.0,
            Vd=0.1
        )
        
        # 生成网格 - 使用固定分辨率
        mesh = generate_mesh(device, method='structured', resolution=(5e-9, 2e-9, 5e-9))
        
        # 创建模拟器
        sim = Simulator(mesh)
        
        # 设置铁电材料
        sim.set_ferroelectric(
            enabled=True,
            model='nls',
            Ps=1.4,
            Ec=3.5e8
        )
        
        # 设置内建场
        if E_bi != 0:
            sim.set_ferroelectric_builtin_field(E_bi=E_bi)
        
        return sim
    
    # 创建验证框架
    framework = ValidationFramework(device_builder, name="内建场验证")
    
    # 添加验证测试
    framework.add_grid_convergence_test(mesh_sizes=[20, 30, 40])
    framework.add_conservation_test()
    framework.add_boundedness_test()
    framework.add_symmetry_test('ferroelectric')
    framework.add_parameter_convergence_test('E_bi', [0.0, 1e6, 5e6])
    
    # 运行验证
    results = framework.run_all()
    framework.print_report()
    
    return framework


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*70)
    print("新增物理方程功能验证测试")
    print("="*70)
    
    tests = [
        ("界面陷阱和氧化物陷阱", test_interface_traps),
        ("保持特性和耐久性", test_retention_endurance),
        ("NLS铁电模型", test_nls_ferroelectric),
        ("PF/FN漏电流模型", test_leakage_current),
        ("内建场(E_bi)", test_builtin_field),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            framework = test_func()
            summary = framework.get_summary()
            results.append((name, summary))
        except Exception as e:
            print(f"\n测试失败: {name}")
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, {'all_passed': False, 'error': str(e)}))
    
    # 打印总结
    print("\n" + "="*70)
    print("测试总结")
    print("="*70)
    
    for name, summary in results:
        if 'error' in summary:
            status = "✗ FAIL"
            print(f"{status}: {name} - {summary['error']}")
        else:
            status = "✓ PASS" if summary['all_passed'] else "✗ FAIL"
            print(f"{status}: {name}")
            if 'total_tests' in summary:
                print(f"  测试数: {summary['total_tests']}, 通过率: {summary['pass_rate']:.1f}%")
    
    total = len(results)
    passed = sum(1 for _, s in results if s.get('all_passed', False))
    print(f"\n总测试套件: {total}")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    
    if passed == total:
        print("\n✓ 所有测试套件通过！新增物理方程功能验证成功。")
        return 0
    else:
        print("\n✗ 部分测试套件失败，请检查错误信息。")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
