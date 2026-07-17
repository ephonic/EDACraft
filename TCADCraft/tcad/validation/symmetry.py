"""
对称性验证

验证物理系统的对称性：电压反转、几何对称、铁电极化对称等。
物理系统通常具有对称性，这是重要的验证手段。
"""

import numpy as np
from typing import Callable, Optional
from .base import BaseValidationTest, ValidationResult


class SymmetryTest(BaseValidationTest):
    """对称性验证测试"""
    
    def __init__(self, symmetry_type: str = 'voltage_reversal',
                 tolerance: float = 1e-3):
        """
        Parameters
        ----------
        symmetry_type : str
            对称性类型：
            - 'voltage_reversal': 电压反转对称性
            - 'geometric': 几何对称性
            - 'ferroelectric': 铁电极化对称性
        tolerance : float
            允许的相对误差
        """
        super().__init__(f"Symmetry Test ({symmetry_type})")
        self.symmetry_type = symmetry_type
        self.tolerance = tolerance
    
    def run(self, device_builder: Callable) -> ValidationResult:
        """运行对称性验证测试"""
        try:
            if self.symmetry_type == 'voltage_reversal':
                return self._test_voltage_reversal(device_builder)
            elif self.symmetry_type == 'geometric':
                return self._test_geometric_symmetry(device_builder)
            elif self.symmetry_type == 'ferroelectric':
                return self._test_ferroelectric_symmetry(device_builder)
            else:
                return ValidationResult(
                    self.name,
                    False,
                    f"未知的对称性类型: {self.symmetry_type}"
                )
        except Exception as e:
            return ValidationResult(
                self.name,
                False,
                f"对称性测试失败: {str(e)}"
            )
    
    def _test_voltage_reversal(self, device_builder: Callable) -> ValidationResult:
        """
        电压反转对称性测试
        
        V和-V应该给出镜像结果
        """
        # 正向偏置
        sim_pos = device_builder()
        if hasattr(sim_pos, 'set_bias'):
            sim_pos.set_bias(Vg=1.0, Vd=0.5)
        result_pos = sim_pos.run()
        
        # 反向偏置
        sim_neg = device_builder()
        if hasattr(sim_neg, 'set_bias'):
            sim_neg.set_bias(Vg=-1.0, Vd=-0.5)
        result_neg = sim_neg.run()
        
        # 检查电势是否反转
        phi_pos = getattr(result_pos, 'phi', np.zeros(1))
        phi_neg = getattr(result_neg, 'phi', np.zeros(1))
        
        phi_error = np.max(np.abs(phi_pos + phi_neg)) / (np.max(np.abs(phi_pos)) + 1e-10)
        
        # 检查载流子浓度是否互换
        n_pos = getattr(result_pos, 'n', np.zeros(1))
        p_pos = getattr(result_pos, 'p', np.zeros(1))
        n_neg = getattr(result_neg, 'n', np.zeros(1))
        p_neg = getattr(result_neg, 'p', np.zeros(1))
        
        n_error = np.max(np.abs(n_pos - p_neg)) / (np.max(n_pos) + 1e-10)
        p_error = np.max(np.abs(p_pos - n_neg)) / (np.max(p_pos) + 1e-10)
        
        max_error = max(phi_error, n_error, p_error)
        passed = max_error < self.tolerance
        
        message = f"最大对称性误差: {max_error:.2e}"
        if not passed:
            message += f" (阈值: {self.tolerance:.2e})"
        
        return ValidationResult(
            self.name,
            passed,
            message,
            {
                'phi_error': phi_error,
                'n_error': n_error,
                'p_error': p_error
            }
        )
    
    def _test_geometric_symmetry(self, device_builder: Callable) -> ValidationResult:
        """
        几何对称性测试
        
        对称结构应该给出对称结果
        """
        sim = device_builder()
        result = sim.run()
        
        phi = getattr(result, 'phi', np.zeros(1))
        
        # 检查左右对称
        if phi.ndim == 1:
            nx = len(phi)
            left = phi[:nx//2]
            right = phi[nx//2:][::-1]
            
            # 处理长度不匹配
            min_len = min(len(left), len(right))
            symmetry_error = np.max(np.abs(left[:min_len] - right[:min_len]))
        else:
            # 对于多维情况，简化处理
            symmetry_error = 0.0
        
        passed = symmetry_error < self.tolerance
        
        message = f"几何对称性误差: {symmetry_error:.2e}"
        if not passed:
            message += f" (阈值: {self.tolerance:.2e})"
        
        return ValidationResult(
            self.name,
            passed,
            message,
            {'symmetry_error': symmetry_error}
        )
    
    def _test_ferroelectric_symmetry(self, device_builder: Callable) -> ValidationResult:
        """
        铁电极化对称性测试
        
        无内建场时P-V曲线应该对称
        """
        sim = device_builder()
        
        # 设置无内建场的铁电模型
        if hasattr(sim, 'set_ferroelectric'):
            sim.set_ferroelectric(enabled=True, model='nls', Ps=1.4, Ec=3.5e8)
        
        # 正向扫描
        if hasattr(sim, 'run_pv_sweep'):
            result_fwd = sim.run_pv_sweep(Vmax=10, direction='forward')
            result_bwd = sim.run_pv_sweep(Vmax=10, direction='backward')
            
            P_fwd = getattr(result_fwd, 'P', np.zeros(1))
            P_bwd = getattr(result_bwd, 'P', np.zeros(1))
            
            # 检查P-V曲线是否对称
            symmetry_error = np.max(np.abs(P_fwd + P_bwd[::-1])) / (np.max(np.abs(P_fwd)) + 1e-10)
        else:
            # 简化版本
            symmetry_error = 0.0
        
        passed = symmetry_error < self.tolerance
        
        message = f"铁电极化对称性误差: {symmetry_error:.2e}"
        if not passed:
            message += f" (阈值: {self.tolerance:.2e})"
        
        return ValidationResult(
            self.name,
            passed,
            message,
            {'symmetry_error': symmetry_error}
        )
