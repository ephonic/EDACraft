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
from .conservation import ConservationTest, TransientConservationTest
from .symmetry import SymmetryTest
from .limiting_cases import LimitingCaseTest
from .boundedness import BoundednessTest
from .cross_validation import CrossValidationTest
from .sensitivity import SensitivityTest
from .report import ValidationReport
from .sentaurus import native_lk_to_sentaurus, sentaurus_lk_to_native, sentaurus_fn_to_native
from .reference import ReferenceComparisonTest
from .ferroelectric_protocol import ferroelectric_program_read_protocol
from .ferroelectric_reference import audit_uniform_ferroelectric_reference
from .electrode_charge import audit_electrode_charge_balance, integrate_electrode_surface_charge
from .sentaurus_log import audit_sentaurus_nonlinear_convergence
from .sentaurus_newton import audit_sentaurus_newton_diagnostics
from .tetrahedral_charge import tetrahedral_surface_quadrature, integrate_tetrahedral_electrode_charge
from .ferroelectric_energy import audit_ferroelectric_device_energy

__all__ = [
    'ValidationFramework',
    'GridConvergenceTest',
    'TimeConvergenceTest',
    'ConservationTest',
    'TransientConservationTest',
    'SymmetryTest',
    'LimitingCaseTest',
    'BoundednessTest',
    'CrossValidationTest',
    'SensitivityTest',
    'ValidationReport',
    'native_lk_to_sentaurus',
    'sentaurus_lk_to_native',
    'sentaurus_fn_to_native',
    'ReferenceComparisonTest',
    'ferroelectric_program_read_protocol',
    'audit_uniform_ferroelectric_reference',
    'audit_electrode_charge_balance',
    'integrate_electrode_surface_charge',
    'audit_sentaurus_nonlinear_convergence',
    'audit_sentaurus_newton_diagnostics',
    'tetrahedral_surface_quadrature',
    'integrate_tetrahedral_electrode_charge',
    'audit_ferroelectric_device_energy',
]
