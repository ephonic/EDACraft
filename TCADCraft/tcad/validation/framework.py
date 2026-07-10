"""
验证框架

主验证框架类，用于组织和管理所有验证测试。
"""

from typing import Callable, List, Optional, Dict, Any
from .base import BaseValidationTest, ValidationResult
from .convergence import GridConvergenceTest, TimeConvergenceTest, ParameterConvergenceTest
from .conservation import ConservationTest, TransientConservationTest
from .symmetry import SymmetryTest
from .limiting_cases import LimitingCaseTest
from .boundedness import BoundednessTest, MonotoneConvergenceTest, PhysicalBoundsTest
from .cross_validation import CrossValidationTest, ModelComparisonTest
from .sensitivity import SensitivityTest, ParameterImportanceTest
from .report import ValidationReport, create_validation_report


class ValidationFramework:
    """验证框架主类"""
    
    def __init__(self, device_builder: Callable, name: str = "物理效应验证"):
        """
        Parameters
        ----------
        device_builder : Callable
            构建设备的函数，返回 Simulator 对象
        name : str
            验证名称
        """
        self.device_builder = device_builder
        self.name = name
        self.tests: List[BaseValidationTest] = []
        self.results: List[ValidationResult] = []
    
    def add_test(self, test: BaseValidationTest):
        """添加单个测试"""
        self.tests.append(test)
    
    def add_tests(self, tests: List[BaseValidationTest]):
        """批量添加测试"""
        self.tests.extend(tests)
    
    def add_grid_convergence_test(self, mesh_sizes: List[int] = None,
                                 expected_order: float = 2.0,
                                 tolerance: float = 0.3):
        """添加网格收敛性测试"""
        self.tests.append(GridConvergenceTest(mesh_sizes, expected_order, tolerance))
    
    def add_time_convergence_test(self, dt_values: List[float] = None,
                                 t_final: float = 1e-6,
                                 tolerance: float = 0.1):
        """添加时间步长收敛性测试"""
        self.tests.append(TimeConvergenceTest(dt_values, t_final, tolerance))
    
    def add_parameter_convergence_test(self, param_name: str,
                                      param_values: List[float],
                                      tolerance: float = 0.05):
        """添加参数收敛性测试"""
        self.tests.append(ParameterConvergenceTest(param_name, param_values, tolerance))
    
    def add_conservation_test(self, check_charge: bool = True,
                             check_energy: bool = True,
                             check_entropy: bool = False,
                             tolerance: float = 1e-6):
        """添加守恒律测试"""
        self.tests.append(ConservationTest(check_charge, check_energy, 
                                          check_entropy, tolerance))
    
    def add_transient_conservation_test(self, dt: float = 1e-9,
                                       t_final: float = 1e-7,
                                       tolerance: float = 1e-3):
        """添加瞬态守恒律测试"""
        self.tests.append(TransientConservationTest(dt, t_final, tolerance))
    
    def add_symmetry_test(self, symmetry_type: str = 'voltage_reversal',
                         tolerance: float = 1e-3):
        """添加对称性测试"""
        self.tests.append(SymmetryTest(symmetry_type, tolerance))
    
    def add_limiting_case_test(self, limit_type: str,
                              tolerance: float = 0.05,
                              limit_params: Optional[Dict[str, Any]] = None):
        """添加极限情况测试"""
        self.tests.append(LimitingCaseTest(limit_type, tolerance, limit_params))
    
    def add_boundedness_test(self, check_positive_carriers: bool = True,
                            check_potential_bounds: bool = True,
                            check_monotone_convergence: bool = True,
                            check_ferroelectric_bounds: bool = True,
                            tolerance: float = 1e-10):
        """添加有界性测试"""
        self.tests.append(BoundednessTest(check_positive_carriers,
                                         check_potential_bounds,
                                         check_monotone_convergence,
                                         check_ferroelectric_bounds,
                                         tolerance))
    
    def add_monotone_convergence_test(self, tolerance: float = 1e-6):
        """添加单调收敛测试"""
        self.tests.append(MonotoneConvergenceTest(tolerance))
    
    def add_physical_bounds_test(self, max_carrier_density: float = 1e26,
                                min_carrier_density: float = 1e0,
                                max_electric_field: float = 1e9):
        """添加物理边界测试"""
        self.tests.append(PhysicalBoundsTest(max_carrier_density,
                                            min_carrier_density,
                                            max_electric_field))
    
    def add_cross_validation_test(self, validation_type: str = 'linear_solvers',
                                 tolerance: float = 0.01):
        """添加交叉验证测试"""
        self.tests.append(CrossValidationTest(validation_type, tolerance))
    
    def add_model_comparison_test(self, model1: str, model2: str,
                                 tolerance: float = 0.05):
        """添加模型对比测试"""
        self.tests.append(ModelComparisonTest(model1, model2, tolerance))
    
    def add_sensitivity_test(self, param_name: str,
                            param_range: tuple,
                            num_points: int = 10,
                            check_smoothness: bool = True,
                            check_no_jumps: bool = True,
                            tolerance: float = 0.1):
        """添加敏感性测试"""
        self.tests.append(SensitivityTest(param_name, param_range, num_points,
                                         check_smoothness, check_no_jumps,
                                         tolerance))
    
    def add_parameter_importance_test(self, param_names: List[str],
                                     param_ranges: dict,
                                     num_samples: int = 20):
        """添加参数重要性测试"""
        self.tests.append(ParameterImportanceTest(param_names, param_ranges,
                                                 num_samples))
    
    def run_all(self) -> List[ValidationResult]:
        """运行所有测试"""
        self.results = []
        
        for test in self.tests:
            try:
                result = test.run(self.device_builder)
                self.results.append(result)
            except Exception as e:
                # 如果测试本身出错，记录错误
                from .base import ValidationResult
                error_result = ValidationResult(
                    test.name,
                    False,
                    f"测试执行出错: {str(e)}"
                )
                self.results.append(error_result)
        
        return self.results
    
    def generate_report(self, title: Optional[str] = None) -> ValidationReport:
        """生成验证报告"""
        if not self.results:
            self.run_all()
        
        report_title = title or f"{self.name} - 验证报告"
        return create_validation_report(self.results, report_title)
    
    def print_report(self, title: Optional[str] = None):
        """打印验证报告"""
        report = self.generate_report(title)
        report.print_report()
    
    def save_report(self, filename: str, title: Optional[str] = None):
        """保存验证报告到文件"""
        report = self.generate_report(title)
        report.save_to_file(filename)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取验证摘要"""
        if not self.results:
            self.run_all()
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        return {
            'name': self.name,
            'total_tests': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': 100 * passed / total if total > 0 else 0,
            'all_passed': failed == 0,
            'failed_tests': [r.test_name for r in self.results if not r.passed]
        }
    
    def is_valid(self) -> bool:
        """检查是否所有测试都通过"""
        if not self.results:
            self.run_all()
        
        return all(r.passed for r in self.results)


def create_validation_framework(device_builder: Callable,
                               name: str = "物理效应验证",
                               test_suite: str = "basic") -> ValidationFramework:
    """
    创建验证框架的便捷函数
    
    Parameters
    ----------
    device_builder : Callable
        构建设备的函数
    name : str
        验证名称
    test_suite : str
        测试套件类型：
        - 'basic': 基本验证（收敛性、守恒律、有界性）
        - 'standard': 标准验证（basic + 对称性、极限情况）
        - 'comprehensive': 全面验证（standard + 交叉验证、敏感性）
    
    Returns
    -------
    ValidationFramework
        验证框架对象
    """
    framework = ValidationFramework(device_builder, name)
    
    if test_suite in ['basic', 'standard', 'comprehensive']:
        # 基本测试
        framework.add_grid_convergence_test()
        framework.add_conservation_test()
        framework.add_boundedness_test()
    
    if test_suite in ['standard', 'comprehensive']:
        # 标准测试
        framework.add_symmetry_test()
        framework.add_limiting_case_test('no_ferroelectric')
        framework.add_monotone_convergence_test()
    
    if test_suite == 'comprehensive':
        # 全面测试
        framework.add_time_convergence_test()
        framework.add_cross_validation_test()
        framework.add_sensitivity_test('Ps', (1.0, 1.8))
    
    return framework
