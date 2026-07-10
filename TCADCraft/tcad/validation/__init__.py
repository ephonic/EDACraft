"""
TCAD 验证策略集

为物理效应开发提供系统化的验证框架，确保代码正确性和可靠性。

验证策略包括：
- 收敛性验证（网格、时间步长）
- 守恒律验证（电荷、能量、熵）
- 对称性验证
- 极限情况验证
- 有界性和单调性验证
- 交叉验证
- 敏感性分析

使用方法：
    from tcad.validation import ValidationFramework
    
    framework = ValidationFramework(device_builder)
    framework.add_grid_convergence_test()
    framework.add_conservation_test()
    results = framework.run_all()
"""

from .framework import ValidationFramework
from .convergence import GridConvergenceTest, TimeConvergenceTest
from .conservation import ConservationTest
from .symmetry import SymmetryTest
from .limiting_cases import LimitingCaseTest
from .boundedness import BoundednessTest
from .cross_validation import CrossValidationTest
from .sensitivity import SensitivityTest
from .report import ValidationReport

__all__ = [
    'ValidationFramework',
    'GridConvergenceTest',
    'TimeConvergenceTest',
    'ConservationTest',
    'SymmetryTest',
    'LimitingCaseTest',
    'BoundednessTest',
    'CrossValidationTest',
    'SensitivityTest',
    'ValidationReport',
]
