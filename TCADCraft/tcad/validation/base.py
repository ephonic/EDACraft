"""
验证测试基类

定义所有验证测试的通用接口和工具函数。
"""

import numpy as np
from collections.abc import Mapping
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
        val1, val2 = comparison_fields(result1, result2, field)
        # Normalize before subtraction; do not hide tiny signals behind a
        # unit-dependent absolute floor or overflow opposite large values.
        scale = np.maximum(np.abs(val1), np.abs(val2))
        scale = np.where(scale == 0., 1., scale)
        with np.errstate(under='ignore', over='ignore', divide='ignore', invalid='ignore'):
            a, b = val1/scale, val2/scale
            difference = np.abs(a-b)
            error = np.where(difference == 0., 0., difference/np.abs(a))
        return float(np.max(error))
    
    def _compute_l2_error(self, result1: Any, result2: Any, 
                          field: str = 'phi') -> float:
        """计算两个结果的L2误差"""
        val1, val2 = comparison_fields(result1, result2, field)
        scale = float(max(np.max(np.abs(val1)), np.max(np.abs(val2))))
        if scale == 0.:
            return 0.
        with np.errstate(under='ignore'):
            rms = float(np.sqrt(np.mean((val1/scale-val2/scale)**2)))
        if rms > 1. and scale > np.finfo(float).max/rms:
            return float('inf')
        return rms*scale
    
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


_MISSING = object()


def _get(result, name):
    return result.get(name, _MISSING) if isinstance(result, Mapping) else getattr(result, name, _MISSING)


def measured_field(result, field):
    """Require actual finite real measurements and respect supplied failure flags.

    Legacy objects without flags remain usable. Any supplied flag must be an
    explicit true boolean. Raw histories require caller-specified extraction.
    """
    for flag in ('converged', 'valid'):
        value = _get(result, flag)
        if value is not _MISSING and (not isinstance(value, (bool, np.bool_)) or not value):
            raise ValueError(f'comparison requires {flag}=True when supplied')
    value = _get(result, field)
    if value is _MISSING:
        raise ValueError(f'comparison requires measured field {field}')
    original = np.asarray(value)
    if original.dtype.kind not in 'iuf' or not original.size:
        raise ValueError(f'{field} must be a nonempty real numeric array')
    with np.errstate(over='ignore', under='ignore', invalid='ignore'):
        values = original.astype(float)
    if (not np.all(np.isfinite(values)) or
            np.any((values == 0.) & (original != 0))):
        raise ValueError(f'{field} must be finite and representable as float64')
    return values


def comparison_fields(left, right, field):
    """Require matching measurement shapes and clocks when provided."""
    a, b = measured_field(left, field), measured_field(right, field)
    if a.shape != b.shape:
        raise ValueError(f'{field} comparison requires identical shapes; align explicitly')
    for clock in ('time_s', 'times_s'):
        x, y = _get(left, clock), _get(right, clock)
        if x is _MISSING and y is _MISSING:
            continue
        x, y = measured_field(left, clock), measured_field(right, clock)
        if x.shape != y.shape or not np.array_equal(x, y):
            raise ValueError('comparison requires matching clocks; align explicitly')
        if np.any(x < 0.):
            raise ValueError('comparison clocks must be nonnegative')
        if clock == 'time_s' and x.shape != ():
            raise ValueError('time_s must be a scalar snapshot clock')
        if clock == 'times_s' and (x.ndim != 1 or not a.ndim or len(x) != a.shape[0]
                or not np.all(x[1:] > x[:-1])):
            raise ValueError('times_s must increase strictly and match the first measurement dimension')
    return a, b


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
