"""
交叉验证

不同数值方法的交叉验证：
- 有限差分 vs 有限元
- 显式 vs 隐式时间积分
- 不同线性求解器
"""

import numpy as np
from typing import Callable, Optional
from .base import BaseValidationTest, ValidationResult


class CrossValidationTest(BaseValidationTest):
    """交叉验证测试"""
    
    def __init__(self, validation_type: str = 'linear_solvers',
                 tolerance: float = 0.01):
        """
        Parameters
        ----------
        validation_type : str
            验证类型：
            - 'linear_solvers': 不同线性求解器
            - 'time_integration': 不同时间积分方法
            - 'spatial_discretization': 不同空间离散方法
        tolerance : float
            允许的相对误差
        """
        super().__init__(f"Cross Validation ({validation_type})")
        self.validation_type = validation_type
        self.tolerance = tolerance
    
    def run(self, device_builder: Callable) -> ValidationResult:
        """运行交叉验证测试"""
        try:
            if self.validation_type == 'linear_solvers':
                return self._test_linear_solvers(device_builder)
            elif self.validation_type == 'time_integration':
                return self._test_time_integration(device_builder)
            elif self.validation_type == 'spatial_discretization':
                return self._test_spatial_discretization(device_builder)
            else:
                return ValidationResult(
                    self.name,
                    False,
                    f"未知的验证类型: {self.validation_type}"
                )
        except Exception as e:
            return ValidationResult(
                self.name,
                False,
                f"交叉验证失败: {str(e)}"
            )
    
    def _test_linear_solvers(self, device_builder: Callable) -> ValidationResult:
        """不同线性求解器应该给出相同结果"""
        # 直接求解器
        sim_direct = device_builder()
        if hasattr(sim_direct, 'set_linear_solver'):
            sim_direct.set_linear_solver('direct')
        result_direct = sim_direct.run()
        
        # 迭代求解器
        sim_iterative = device_builder()
        if hasattr(sim_iterative, 'set_linear_solver'):
            sim_iterative.set_linear_solver('iterative')
        result_iterative = sim_iterative.run()
        
        # 比较结果
        error = self._compute_relative_error(result_direct, result_iterative, 'phi')
        passed = error < self.tolerance
        
        message = f"相对误差: {error:.2e}"
        if not passed:
            message += f" (阈值: {self.tolerance:.2e})"
        
        return ValidationResult(
            self.name,
            passed,
            message,
            {'error': error}
        )
    
    def _test_time_integration(self, device_builder: Callable) -> ValidationResult:
        """显式 vs 隐式时间积分"""
        dt = 1e-9
        
        # 显式方法
        sim_explicit = device_builder()
        if hasattr(sim_explicit, 'run_transient'):
            result_explicit = sim_explicit.run_transient(
                method='explicit', dt=dt, t_final=1e-7
            )
        else:
            result_explicit = sim_explicit.run()
        
        # 隐式方法
        sim_implicit = device_builder()
        if hasattr(sim_implicit, 'run_transient'):
            result_implicit = sim_implicit.run_transient(
                method='implicit', dt=dt, t_final=1e-7
            )
        else:
            result_implicit = sim_implicit.run()
        
        # 小时间步长下两者应该一致
        error = self._compute_relative_error(result_explicit, result_implicit, 'phi')
        passed = error < self.tolerance
        
        message = f"相对误差: {error:.2e}"
        if not passed:
            message += f" (阈值: {self.tolerance:.2e})"
        
        return ValidationResult(
            self.name,
            passed,
            message,
            {'error': error}
        )
    
    def _test_spatial_discretization(self, device_builder: Callable) -> ValidationResult:
        """有限差分 vs 有限元"""
        # 有限差分
        sim_fdm = device_builder()
        if hasattr(sim_fdm, 'set_discretization'):
            sim_fdm.set_discretization('FDM')
        result_fdm = sim_fdm.run()
        
        # 有限元
        sim_fem = device_builder()
        if hasattr(sim_fem, 'set_discretization'):
            sim_fem.set_discretization('FEM')
        result_fem = sim_fem.run()
        
        # 两种方法应该给出接近的结果
        error = self._compute_relative_error(result_fdm, result_fem, 'phi')
        passed = error < self.tolerance
        
        message = f"相对误差: {error:.2e}"
        if not passed:
            message += f" (阈值: {self.tolerance:.2e})"
        
        return ValidationResult(
            self.name,
            passed,
            message,
            {'error': error}
        )


class ModelComparisonTest(BaseValidationTest):
    """模型对比验证"""
    
    def __init__(self, model1: str, model2: str,
                 tolerance: float = 0.05):
        """
        Parameters
        ----------
        model1 : str
            第一个模型名称
        model2 : str
            第二个模型名称
        tolerance : float
            允许的相对误差
        """
        super().__init__(f"Model Comparison ({model1} vs {model2})")
        self.model1 = model1
        self.model2 = model2
        self.tolerance = tolerance
    
    def run(self, device_builder: Callable) -> ValidationResult:
        """运行模型对比验证"""
        try:
            # 模型1
            sim1 = device_builder()
            if hasattr(sim1, 'set_model'):
                sim1.set_model(self.model1)
            result1 = sim1.run()
            
            # 模型2
            sim2 = device_builder()
            if hasattr(sim2, 'set_model'):
                sim2.set_model(self.model2)
            result2 = sim2.run()
            
        except Exception as e:
            return ValidationResult(
                self.name,
                False,
                f"模型对比失败: {str(e)}"
            )
        
        # 比较结果
        error = self._compute_relative_error(result1, result2, 'phi')
        passed = error < self.tolerance
        
        message = f"{self.model1} vs {self.model2}: 相对误差 {error:.2e}"
        if not passed:
            message += f" (阈值: {self.tolerance:.2e})"
        
        return ValidationResult(
            self.name,
            passed,
            message,
            {'error': error}
        )
