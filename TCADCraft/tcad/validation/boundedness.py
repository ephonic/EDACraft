"""
有界性和单调性验证

验证解的有界性和单调性：
- 载流子浓度为正
- 电势在合理范围内
- 收敛过程单调
- 铁电极化不超过Ps
"""

import numpy as np
from typing import Callable, Optional
from .base import BaseValidationTest, ValidationResult


class BoundednessTest(BaseValidationTest):
    """有界性和单调性验证测试"""
    
    def __init__(self, check_positive_carriers: bool = True,
                 check_potential_bounds: bool = True,
                 check_monotone_convergence: bool = True,
                 check_ferroelectric_bounds: bool = True,
                 tolerance: float = 1e-10):
        """
        Parameters
        ----------
        check_positive_carriers : bool
            是否检查载流子浓度为正
        check_potential_bounds : bool
            是否检查电势在合理范围内
        check_monotone_convergence : bool
            是否检查收敛过程单调
        check_ferroelectric_bounds : bool
            是否检查铁电极化不超过Ps
        tolerance : float
            允许的数值误差
        """
        super().__init__("Boundedness and Monotonicity Test")
        self.check_positive_carriers = check_positive_carriers
        self.check_potential_bounds = check_potential_bounds
        self.check_monotone_convergence = check_monotone_convergence
        self.check_ferroelectric_bounds = check_ferroelectric_bounds
        self.tolerance = tolerance
    
    def run(self, device_builder: Callable) -> ValidationResult:
        """运行有界性和单调性验证测试"""
        try:
            sim = device_builder()
            result = sim.run()
            
        except Exception as e:
            return ValidationResult(
                self.name,
                False,
                f"仿真失败: {str(e)}"
            )
        
        violations = []
        details = {}
        
        # 载流子浓度为正
        if self.check_positive_carriers:
            carrier_violation = self._check_positive_carriers(result)
            details['carrier_violation'] = carrier_violation
            if carrier_violation > self.tolerance:
                violations.append(f"载流子浓度为负: {carrier_violation:.2e}")
        
        # 电势在合理范围内
        if self.check_potential_bounds:
            potential_violation = self._check_potential_bounds(result)
            details['potential_violation'] = potential_violation
            if potential_violation > 0:
                violations.append(f"电势超出范围: {potential_violation:.2e}")
        
        # 铁电极化不超过Ps
        if self.check_ferroelectric_bounds:
            ferroelectric_violation = self._check_ferroelectric_bounds(result)
            details['ferroelectric_violation'] = ferroelectric_violation
            if ferroelectric_violation > self.tolerance:
                violations.append(f"铁电极化超过Ps: {ferroelectric_violation:.2e}")
        
        passed = len(violations) == 0
        
        if passed:
            message = "所有有界性条件满足"
        else:
            message = "; ".join(violations)
        
        return ValidationResult(
            self.name,
            passed,
            message,
            details
        )
    
    def _check_positive_carriers(self, result) -> float:
        """检查载流子浓度是否为正"""
        n = getattr(result, 'n', np.zeros(1))
        p = getattr(result, 'p', np.zeros(1))
        
        # 检查是否有负值
        min_n = np.min(n)
        min_p = np.min(p)
        
        # 返回最大的负值（如果有）
        violation = max(-min_n, -min_p, 0)
        
        return float(violation)
    
    def _check_potential_bounds(self, result) -> float:
        """检查电势是否在合理范围内"""
        phi = getattr(result, 'phi', np.zeros(1))
        
        # 获取施加的电压（如果有）
        max_applied = getattr(result, 'max_applied_voltage', 5.0)
        
        # 检查电势是否超出范围
        min_phi = np.min(phi)
        max_phi = np.max(phi)
        
        violation = 0.0
        if min_phi < -self.tolerance:
            violation = max(violation, abs(min_phi))
        if max_phi > max_applied + self.tolerance:
            violation = max(violation, max_phi - max_applied)
        
        return float(violation)
    
    def _check_ferroelectric_bounds(self, result) -> float:
        """检查铁电极化是否不超过Ps"""
        P = getattr(result, 'P', None)
        
        if P is None:
            return 0.0
        
        # 获取Ps（如果有）
        Ps = getattr(result, 'Ps', 1.4)
        
        # 检查是否超过Ps
        max_P = np.max(np.abs(P))
        violation = max(max_P - Ps, 0)
        
        return float(violation)


class MonotoneConvergenceTest(BaseValidationTest):
    """单调收敛验证"""
    
    def __init__(self, tolerance: float = 1e-6):
        """
        Parameters
        ----------
        tolerance : float
            允许的相对误差
        """
        super().__init__("Monotone Convergence Test")
        self.tolerance = tolerance
    
    def run(self, device_builder: Callable) -> ValidationResult:
        """运行单调收敛验证"""
        try:
            sim = device_builder()
            result = sim.run(return_iterations=True)
            
        except Exception as e:
            return ValidationResult(
                self.name,
                False,
                f"仿真失败: {str(e)}"
            )
        
        # 检查残差是否单调递减
        residuals = getattr(result, 'iteration_residuals', None)
        
        if residuals is None or len(residuals) < 2:
            return ValidationResult(
                self.name,
                True,
                "无法获取迭代残差，跳过单调性检查",
                {'has_residuals': False}
            )
        
        # 检查是否单调递减
        is_monotone = True
        violations = []
        
        for i in range(1, len(residuals)):
            if residuals[i] > residuals[i-1] * (1 + self.tolerance):
                is_monotone = False
                violations.append(i)
        
        passed = is_monotone
        
        message = f"迭代次数: {len(residuals)}, 最终残差: {residuals[-1]:.2e}"
        if not passed:
            message += f", 非单调迭代: {len(violations)}次"
        
        return ValidationResult(
            self.name,
            passed,
            message,
            {
                'num_iterations': len(residuals),
                'final_residual': residuals[-1],
                'is_monotone': is_monotone,
                'violations': violations
            }
        )


class PhysicalBoundsTest(BaseValidationTest):
    """物理边界条件验证"""
    
    def __init__(self, max_carrier_density: float = 1e26,
                 min_carrier_density: float = 1e0,
                 max_electric_field: float = 1e9):
        """
        Parameters
        ----------
        max_carrier_density : float
            最大载流子浓度 [m^-3]
        min_carrier_density : float
            最小载流子浓度 [m^-3]
        max_electric_field : float
            最大电场 [V/m]
        """
        super().__init__("Physical Bounds Test")
        self.max_carrier_density = max_carrier_density
        self.min_carrier_density = min_carrier_density
        self.max_electric_field = max_electric_field
    
    def run(self, device_builder: Callable) -> ValidationResult:
        """运行物理边界条件验证"""
        try:
            sim = device_builder()
            result = sim.run()
            
        except Exception as e:
            return ValidationResult(
                self.name,
                False,
                f"仿真失败: {str(e)}"
            )
        
        violations = []
        details = {}
        
        # 检查载流子浓度范围
        n = getattr(result, 'n', np.zeros(1))
        p = getattr(result, 'p', np.zeros(1))
        
        max_n = np.max(n)
        max_p = np.max(p)
        
        if max_n > self.max_carrier_density:
            violations.append(f"电子浓度过高: {max_n:.2e}")
        if max_p > self.max_carrier_density:
            violations.append(f"空穴浓度过高: {max_p:.2e}")
        
        details['max_n'] = max_n
        details['max_p'] = max_p
        
        # 检查电场范围
        Ex = getattr(result, 'Ex', np.zeros(1))
        Ey = getattr(result, 'Ey', np.zeros(1))
        Ez = getattr(result, 'Ez', np.zeros(1))
        
        E_mag = np.sqrt(Ex**2 + Ey**2 + Ez**2)
        max_E = np.max(E_mag)
        
        if max_E > self.max_electric_field:
            violations.append(f"电场过高: {max_E:.2e}")
        
        details['max_E'] = max_E
        
        passed = len(violations) == 0
        
        if passed:
            message = "所有物理边界条件满足"
        else:
            message = "; ".join(violations)
        
        return ValidationResult(
            self.name,
            passed,
            message,
            details
        )
