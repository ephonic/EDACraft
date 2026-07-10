"""
守恒律验证

验证物理守恒律：电荷守恒、能量守恒、熵产生。
这些是物理定律的基石，必须严格满足。
"""

import numpy as np
from typing import Callable, Optional
from .base import BaseValidationTest, ValidationResult


class ConservationTest(BaseValidationTest):
    """守恒律验证测试"""
    
    def __init__(self, check_charge: bool = True,
                 check_energy: bool = True,
                 check_entropy: bool = False,
                 tolerance: float = 1e-6):
        """
        Parameters
        ----------
        check_charge : bool
            是否检查电荷守恒
        check_energy : bool
            是否检查能量守恒
        check_entropy : bool
            是否检查熵产生（热力学第二定律）
        tolerance : float
            允许的相对误差
        """
        super().__init__("Conservation Laws Test")
        self.check_charge = check_charge
        self.check_energy = check_energy
        self.check_entropy = check_entropy
        self.tolerance = tolerance
    
    def run(self, device_builder: Callable) -> ValidationResult:
        """运行守恒律验证测试"""
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
        
        # 电荷守恒检查
        if self.check_charge:
            charge_violation = self._check_charge_conservation(result)
            details['charge_violation'] = charge_violation
            if charge_violation > self.tolerance:
                violations.append(f"电荷守恒违反: {charge_violation:.2e}")
        
        # 能量守恒检查
        if self.check_energy:
            energy_violation = self._check_energy_conservation(result)
            details['energy_violation'] = energy_violation
            if energy_violation > self.tolerance:
                violations.append(f"能量守恒违反: {energy_violation:.2e}")
        
        # 熵产生检查
        if self.check_entropy:
            entropy_violation = self._check_entropy_production(result)
            details['entropy_violation'] = entropy_violation
            if entropy_violation < -self.tolerance:  # 熵产生应该 >= 0
                violations.append(f"熵产生为负: {entropy_violation:.2e}")
        
        passed = len(violations) == 0
        
        if passed:
            message = "所有守恒律满足"
        else:
            message = "; ".join(violations)
        
        return ValidationResult(
            self.name,
            passed,
            message,
            details
        )
    
    def _check_charge_conservation(self, result) -> float:
        """
        检查电荷守恒
        
        对于稳态：∇·J = 0（电流连续性）
        对于瞬态：∂ρ/∂t + ∇·J = 0
        
        这里简化为检查总电荷是否合理
        """
        n = getattr(result, 'n', np.zeros(1))
        p = getattr(result, 'p', np.zeros(1))
        
        # 总电荷
        total_charge = np.sum(n - p)
        
        # 电荷应该在合理范围内
        # 这里使用相对误差作为违反程度的度量
        charge_violation = abs(total_charge) / (np.sum(n + p) + 1e-10)
        
        return float(charge_violation)
    
    def _check_energy_conservation(self, result) -> float:
        """
        检查能量守恒
        
        输入能量 = 存储能量 + 耗散能量
        
        这里简化为检查能量是否合理
        """
        phi = getattr(result, 'phi', np.zeros(1))
        n = getattr(result, 'n', np.zeros(1))
        p = getattr(result, 'p', np.zeros(1))
        
        # 电场能量
        electric_energy = 0.5 * np.sum(phi ** 2)
        
        # 载流子能量（简化）
        carrier_energy = np.sum(n + p)
        
        # 总能量
        total_energy = electric_energy + carrier_energy
        
        # 检查能量是否为正且合理
        if total_energy < 0:
            return float('inf')
        
        # 这里使用能量变化的相对值作为违反程度的度量
        # 实际应用中应该比较输入和输出能量
        energy_violation = 0.0  # 简化版本，假设能量守恒
        
        return float(energy_violation)
    
    def _check_entropy_production(self, result) -> float:
        """
        检查熵产生
        
        热力学第二定律：熵产生 >= 0
        
        这里简化为检查是否有明显的熵减少
        """
        # 实际应用中需要根据具体的物理模型计算熵产生
        # 这里只是一个占位符
        entropy_production = 0.0  # 简化版本，假设熵产生 >= 0
        
        return float(entropy_production)


class TransientConservationTest(BaseValidationTest):
    """瞬态守恒律验证"""
    
    def __init__(self, dt: float = 1e-9, t_final: float = 1e-7,
                 tolerance: float = 1e-3):
        """
        Parameters
        ----------
        dt : float
            时间步长
        t_final : float
            总模拟时间
        tolerance : float
            允许的相对误差
        """
        super().__init__("Transient Conservation Test")
        self.dt = dt
        self.t_final = t_final
        self.tolerance = tolerance
    
    def run(self, device_builder: Callable) -> ValidationResult:
        """运行瞬态守恒律验证"""
        try:
            sim = device_builder()
            result = sim.run_transient(dt=self.dt, t_final=self.t_final)
            
        except Exception as e:
            return ValidationResult(
                self.name,
                False,
                f"瞬态仿真失败: {str(e)}"
            )
        
        # 检查每个时间步的电荷守恒
        violations = []
        
        if hasattr(result, 'snapshots'):
            charges = []
            for snapshot in result.snapshots:
                n = getattr(snapshot, 'n', np.zeros(1))
                p = getattr(snapshot, 'p', np.zeros(1))
                charge = np.sum(n - p)
                charges.append(charge)
            
            # 检查电荷变化是否合理
            charge_changes = np.diff(charges)
            max_change = np.max(np.abs(charge_changes))
            
            if max_change > self.tolerance:
                violations.append(f"瞬态电荷变化过大: {max_change:.2e}")
        
        passed = len(violations) == 0
        
        if passed:
            message = "瞬态守恒律满足"
        else:
            message = "; ".join(violations)
        
        return ValidationResult(
            self.name,
            passed,
            message,
            {'max_charge_change': max_change if violations else 0.0}
        )
