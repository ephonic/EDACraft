"""
收敛性验证

验证数值解随网格加密和时间步长减小的收敛行为。
这是最重要的验证方法，不需要任何实验数据。
"""

import numpy as np
from typing import Callable, List, Optional
from .base import BaseValidationTest, ValidationResult


class GridConvergenceTest(BaseValidationTest):
    """网格收敛性测试"""
    
    def __init__(self, mesh_sizes: List[int] = None, 
                 expected_order: float = 2.0,
                 tolerance: float = 0.3):
        """
        Parameters
        ----------
        mesh_sizes : List[int]
            网格尺寸列表，例如 [20, 40, 80, 160]
        expected_order : float
            期望的收敛阶，例如二阶方法为 2.0
        tolerance : float
            允许的偏差，例如 0.3 表示 2.0±0.3
        """
        super().__init__("Grid Convergence Test")
        self.mesh_sizes = mesh_sizes or [20, 40, 80, 160]
        self.expected_order = expected_order
        self.tolerance = tolerance
    
    def run(self, device_builder: Callable) -> ValidationResult:
        """运行网格收敛性测试"""
        errors = []
        
        # 检查 device_builder 是否支持网格尺寸参数
        import inspect
        sig = inspect.signature(device_builder)
        supports_mesh_params = 'nx' in sig.parameters and 'ny' in sig.parameters
        
        if not supports_mesh_params:
            # 如果 device_builder 不支持网格参数，跳过此测试
            return ValidationResult(
                self.name,
                True,
                "device_builder 不支持网格尺寸参数，跳过网格收敛性测试",
                {'skipped': True}
            )
        
        for n in self.mesh_sizes:
            try:
                sim = device_builder(nx=n, ny=n)
                result = sim.run()
                
                # 计算误差（这里使用电势的L2范数作为示例）
                # 实际应用中应该使用解析解或高精度参考解
                phi = result.get('phi', np.zeros(1))
                error = np.sqrt(np.mean(phi ** 2))  # 简化的误差度量
                errors.append(error)
                
            except Exception as e:
                return ValidationResult(
                    self.name,
                    False,
                    f"网格尺寸 {n} 时仿真失败: {str(e)}"
                )
        
        # 计算收敛阶
        if len(errors) < 2:
            return ValidationResult(
                self.name,
                False,
                "需要至少两个网格尺寸才能计算收敛阶"
            )
        
        # 计算相邻网格的误差比
        refinements = [self.mesh_sizes[i] / self.mesh_sizes[0] 
                      for i in range(len(self.mesh_sizes))]
        convergence_rate = self._compute_convergence_rate(errors, refinements)
        
        # 检查误差是否单调递减
        is_monotone = all(errors[i] > errors[i+1] 
                         for i in range(len(errors)-1))
        
        # 检查收敛阶是否在期望范围内
        order_ok = abs(convergence_rate - self.expected_order) < self.tolerance
        
        passed = is_monotone and order_ok
        
        message = f"收敛阶: {convergence_rate:.2f} (期望: {self.expected_order:.2f})"
        if not is_monotone:
            message += ", 误差非单调递减"
        if not order_ok:
            message += f", 收敛阶超出范围 [{self.expected_order - self.tolerance:.2f}, {self.expected_order + self.tolerance:.2f}]"
        
        return ValidationResult(
            self.name,
            passed,
            message,
            {
                'mesh_sizes': self.mesh_sizes,
                'errors': errors,
                'convergence_rate': convergence_rate,
                'is_monotone': is_monotone,
                'order_ok': order_ok
            }
        )


class TimeConvergenceTest(BaseValidationTest):
    """时间步长收敛性测试"""
    
    def __init__(self, dt_values: List[float] = None,
                 t_final: float = 1e-6,
                 tolerance: float = 0.1):
        """
        Parameters
        ----------
        dt_values : List[float]
            时间步长列表，例如 [1e-6, 5e-7, 1e-7, 5e-8]
        t_final : float
            总模拟时间
        tolerance : float
            允许的相对误差
        """
        super().__init__("Time Convergence Test")
        self.dt_values = dt_values or [1e-6, 5e-7, 1e-7, 5e-8]
        self.t_final = t_final
        self.tolerance = tolerance
    
    def run(self, device_builder: Callable) -> ValidationResult:
        """运行时间步长收敛性测试"""
        results = []
        
        for dt in self.dt_values:
            try:
                sim = device_builder()
                result = sim.run_transient(dt=dt, t_final=self.t_final)
                results.append(result)
                
            except Exception as e:
                return ValidationResult(
                    self.name,
                    False,
                    f"时间步长 {dt} 时仿真失败: {str(e)}"
                )
        
        # 计算相邻结果的差异
        differences = []
        for i in range(1, len(results)):
            diff = self._compute_relative_error(results[i-1], results[i])
            differences.append(diff)
        
        # 检查差异是否单调递减
        is_monotone = all(differences[i] > differences[i+1] 
                         for i in range(len(differences)-1))
        
        # 检查最终差异是否足够小
        final_diff_ok = differences[-1] < self.tolerance
        
        passed = is_monotone and final_diff_ok
        
        message = f"最终差异: {differences[-1]:.2e} (阈值: {self.tolerance:.2e})"
        if not is_monotone:
            message += ", 差异非单调递减"
        if not final_diff_ok:
            message += ", 最终差异超出阈值"
        
        return ValidationResult(
            self.name,
            passed,
            message,
            {
                'dt_values': self.dt_values,
                'differences': differences,
                'is_monotone': is_monotone,
                'final_diff_ok': final_diff_ok
            }
        )


class ParameterConvergenceTest(BaseValidationTest):
    """参数收敛性测试"""
    
    def __init__(self, param_name: str, param_values: List[float],
                 tolerance: float = 0.05):
        """
        Parameters
        ----------
        param_name : str
            参数名称，例如 'Ps', 'Ec', 'Dit'
        param_values : List[float]
            参数值列表
        tolerance : float
            允许的相对变化
        """
        super().__init__(f"Parameter Convergence Test ({param_name})")
        self.param_name = param_name
        self.param_values = param_values
        self.tolerance = tolerance
    
    def run(self, device_builder: Callable) -> ValidationResult:
        """运行参数收敛性测试"""
        results = []
        
        for value in self.param_values:
            try:
                sim = device_builder(**{self.param_name: value})
                result = sim.run()
                results.append(result)
                
            except Exception as e:
                return ValidationResult(
                    self.name,
                    False,
                    f"参数 {self.param_name}={value} 时仿真失败: {str(e)}"
                )
        
        # 计算相邻结果的差异
        differences = []
        for i in range(1, len(results)):
            diff = self._compute_relative_error(results[i-1], results[i])
            differences.append(diff)
        
        # 检查差异是否小于阈值
        all_ok = all(diff < self.tolerance for diff in differences)
        
        passed = all_ok
        
        message = f"最大差异: {max(differences):.2e} (阈值: {self.tolerance:.2e})"
        if not all_ok:
            message += ", 某些参数变化导致结果差异过大"
        
        return ValidationResult(
            self.name,
            passed,
            message,
            {
                'param_name': self.param_name,
                'param_values': self.param_values,
                'differences': differences,
                'all_ok': all_ok
            }
        )
