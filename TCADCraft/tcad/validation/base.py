"""
验证测试基类

定义所有验证测试的通用接口和工具函数。
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Callable, Any, Dict, List, Optional, Tuple


class ValidationResult:
    """验证测试结果"""
    
    def __init__(self, test_name: str, passed: bool, message: str = "", 
                 details: Optional[Dict[str, Any]] = None):
        self.test_name = test_name
        self.passed = passed
        self.message = message
        self.details = details or {}
    
    def __str__(self):
        status = "✓ PASS" if self.passed else "✗ FAIL"
        msg = f"{status}: {self.test_name}"
        if self.message:
            msg += f"\n  {self.message}"
        if self.details:
            msg += f"\n  Details: {self.details}"
        return msg


class BaseValidationTest(ABC):
    """验证测试基类"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def run(self, device_builder: Callable) -> ValidationResult:
        """
        运行验证测试
        
        Parameters
        ----------
        device_builder : Callable
            构建设备的函数，返回 Simulator 对象
            
        Returns
        -------
        ValidationResult
            测试结果
        """
        pass
    
    def _compute_relative_error(self, result1: Any, result2: Any, 
                                field: str = 'phi') -> float:
        """计算两个结果的相对误差"""
        # 支持字典和对象两种访问方式
        if isinstance(result1, dict):
            val1 = result1.get(field, np.zeros(1))
        else:
            val1 = getattr(result1, field, np.zeros(1))
        
        if isinstance(result2, dict):
            val2 = result2.get(field, np.zeros(1))
        else:
            val2 = getattr(result2, field, np.zeros(1))
        
        # 避免除零
        denominator = np.maximum(np.abs(val1), 1e-10)
        relative_error = np.abs(val1 - val2) / denominator
        
        return float(np.max(relative_error))
    
    def _compute_l2_error(self, result1: Any, result2: Any, 
                          field: str = 'phi') -> float:
        """计算两个结果的L2误差"""
        # 支持字典和对象两种访问方式
        if isinstance(result1, dict):
            val1 = result1.get(field, np.zeros(1))
        else:
            val1 = getattr(result1, field, np.zeros(1))
        
        if isinstance(result2, dict):
            val2 = result2.get(field, np.zeros(1))
        else:
            val2 = getattr(result2, field, np.zeros(1))
        
        l2_error = np.sqrt(np.mean((val1 - val2) ** 2))
        return float(l2_error)
    
    def _compute_convergence_rate(self, errors: List[float], 
                                  refinements: List[float]) -> float:
        """
        计算收敛阶
        
        假设误差 E ~ h^p，其中 h 是网格尺寸
        则 p = log(E1/E2) / log(h1/h2)
        """
        if len(errors) < 2 or len(refinements) < 2:
            return 0.0
        
        rates = []
        for i in range(1, len(errors)):
            if errors[i-1] > 0 and errors[i] > 0:
                rate = np.log(errors[i-1] / errors[i]) / \
                       np.log(refinements[i-1] / refinements[i])
                rates.append(rate)
        
        return float(np.mean(rates)) if rates else 0.0


def compute_total_charge(result: Any) -> float:
    """计算总电荷"""
    n = getattr(result, 'n', np.zeros(1))
    p = getattr(result, 'p', np.zeros(1))
    
    # 假设单位体积
    charge = np.sum(n - p)
    return float(charge)


def compute_total_energy(result: Any) -> float:
    """计算总能量（简化版本）"""
    phi = getattr(result, 'phi', np.zeros(1))
    n = getattr(result, 'n', np.zeros(1))
    p = getattr(result, 'p', np.zeros(1))
    
    # 电场能量 + 载流子能量
    # 这里只是示意，实际需要根据具体物理模型定义
    energy = 0.5 * np.sum(phi ** 2) + np.sum(n + p)
    return float(energy)


def compute_boundary_current(result: Any) -> float:
    """计算边界电流（简化版本）"""
    # 这里只是示意，实际需要根据边界条件计算
    return 0.0
