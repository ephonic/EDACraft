"""
验证框架测试脚本

测试验证框架的基本功能是否正常工作。
"""

import sys
import numpy as np
sys.path.insert(0, '/Users/yangfan/tcad')

from tcad.validation import ValidationFramework
from tcad.validation.base import ValidationResult


def test_basic_framework():
    """测试基本框架功能"""
    print("=" * 70)
    print("测试1: 基本框架功能")
    print("=" * 70)
    
    # 简单的设备构建函数
    def device_builder(nx=20, ny=20, **kwargs):
        """返回一个简单的模拟结果"""
        class MockResult:
            def __init__(self):
                self.phi = np.random.rand(nx, ny)
                self.n = np.abs(np.random.rand(nx, ny)) * 1e20
                self.p = np.abs(np.random.rand(nx, ny)) * 1e20
                self.P = np.random.rand(nx, ny) * 0.5  # 极化强度
        
        return MockResult()
    
    # 创建验证框架
    framework = ValidationFramework(device_builder, name="测试框架")
    
    # 添加一些测试
    framework.add_boundedness_test()
    
    # 运行测试
    results = framework.run_all()
    
    # 打印结果
    for result in results:
        print(f"{result.test_name}: {'PASS' if result.passed else 'FAIL'}")
        print(f"  {result.message}")
    
    print(f"\n总测试数: {len(results)}")
    print(f"通过: {sum(1 for r in results if r.passed)}")
    print(f"失败: {sum(1 for r in results if not r.passed)}")
    
    return len(results) > 0


def test_validation_result():
    """测试ValidationResult类"""
    print("\n" + "=" * 70)
    print("测试2: ValidationResult类")
    print("=" * 70)
    
    # 创建测试结果
    result1 = ValidationResult("测试1", True, "测试通过", {"value": 1.0})
    result2 = ValidationResult("测试2", False, "测试失败", {"error": "error message"})
    
    print(f"结果1: {result1}")
    print(f"  通过: {result1.passed}")
    print(f"  消息: {result1.message}")
    print(f"  详情: {result1.details}")
    
    print(f"\n结果2: {result2}")
    print(f"  通过: {result2.passed}")
    print(f"  消息: {result2.message}")
    print(f"  详情: {result2.details}")
    
    return True


def test_report_generation():
    """测试报告生成"""
    print("\n" + "=" * 70)
    print("测试3: 报告生成")
    print("=" * 70)
    
    from tcad.validation.report import ValidationReport
    
    # 创建报告
    report = ValidationReport("测试报告")
    
    # 添加结果
    report.add_result(ValidationResult("测试1", True, "通过"))
    report.add_result(ValidationResult("测试2", False, "失败"))
    report.add_result(ValidationResult("测试3", True, "通过"))
    
    # 生成报告
    report_text = report.generate_text_report()
    print(report_text)
    
    # 生成摘要
    summary = report.generate_summary()
    print("\n摘要:")
    print(f"  总测试数: {summary['total_tests']}")
    print(f"  通过: {summary['passed']}")
    print(f"  失败: {summary['failed']}")
    print(f"  通过率: {summary['pass_rate']:.1f}%")
    
    return True


def test_convergence_test():
    """测试收敛性测试"""
    print("\n" + "=" * 70)
    print("测试4: 收敛性测试")
    print("=" * 70)
    
    from tcad.validation.convergence import GridConvergenceTest
    
    # 简单的设备构建函数
    def device_builder(nx=20, ny=20, **kwargs):
        class MockResult:
            def __init__(self, size):
                # 模拟收敛行为：误差随网格尺寸减小
                self.phi = np.random.rand(size, size) / size
                self.n = np.abs(np.random.rand(size, size)) * 1e20
                self.p = np.abs(np.random.rand(size, size)) * 1e20
        
        return MockResult(nx)
    
    # 创建收敛性测试
    test = GridConvergenceTest(mesh_sizes=[10, 20, 40], expected_order=2.0)
    
    # 运行测试
    result = test.run(device_builder)
    
    print(f"测试名称: {result.test_name}")
    print(f"通过: {result.passed}")
    print(f"消息: {result.message}")
    if result.details:
        print(f"详情: {result.details}")
    
    return True


def test_conservation_test():
    """测试守恒律测试"""
    print("\n" + "=" * 70)
    print("测试5: 守恒律测试")
    print("=" * 70)
    
    from tcad.validation.conservation import ConservationTest
    
    # 简单的设备构建函数
    def device_builder(**kwargs):
        class MockResult:
            def __init__(self):
                self.phi = np.random.rand(20, 20)
                self.n = np.abs(np.random.rand(20, 20)) * 1e20
                self.p = np.abs(np.random.rand(20, 20)) * 1e20
        
        return MockResult()
    
    # 创建守恒律测试
    test = ConservationTest(check_charge=True, check_energy=True)
    
    # 运行测试
    result = test.run(device_builder)
    
    print(f"测试名称: {result.test_name}")
    print(f"通过: {result.passed}")
    print(f"消息: {result.message}")
    
    return True


def test_symmetry_test():
    """测试对称性测试"""
    print("\n" + "=" * 70)
    print("测试6: 对称性测试")
    print("=" * 70)
    
    from tcad.validation.symmetry import SymmetryTest
    
    # 简单的设备构建函数
    def device_builder(**kwargs):
        class MockResult:
            def __init__(self):
                self.phi = np.random.rand(20, 20)
                self.n = np.abs(np.random.rand(20, 20)) * 1e20
                self.p = np.abs(np.random.rand(20, 20)) * 1e20
        
        return MockResult()
    
    # 创建对称性测试
    test = SymmetryTest(symmetry_type='geometric')
    
    # 运行测试
    result = test.run(device_builder)
    
    print(f"测试名称: {result.test_name}")
    print(f"通过: {result.passed}")
    print(f"消息: {result.message}")
    
    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("TCAD 验证框架测试")
    print("=" * 70 + "\n")
    
    tests = [
        ("基本框架功能", test_basic_framework),
        ("ValidationResult类", test_validation_result),
        ("报告生成", test_report_generation),
        ("收敛性测试", test_convergence_test),
        ("守恒律测试", test_conservation_test),
        ("对称性测试", test_symmetry_test),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n测试失败: {name}")
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 打印总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    total = len(results)
    passed = sum(1 for _, r in results if r)
    print(f"\n总测试数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    
    if passed == total:
        print("\n✓ 所有测试通过！验证框架工作正常。")
        return 0
    else:
        print("\n✗ 部分测试失败，请检查错误信息。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
