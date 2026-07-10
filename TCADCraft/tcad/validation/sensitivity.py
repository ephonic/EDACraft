"""
敏感性分析

参数敏感性分析：
- 结果应该随参数平滑变化
- 不应该出现突然的跳变（除相变外）
- 识别关键参数
"""

import numpy as np
from typing import Callable, List, Optional, Any
from .base import BaseValidationTest, ValidationResult


class SensitivityTest(BaseValidationTest):
    """敏感性分析测试"""
    
    def __init__(self, param_name: str, param_range: tuple,
                 num_points: int = 10,
                 check_smoothness: bool = True,
                 check_no_jumps: bool = True,
                 tolerance: float = 0.1):
        """
        Parameters
        ----------
        param_name : str
            参数名称，例如 'Ps', 'Ec', 'Dit'
        param_range : tuple
            参数范围 (min, max)
        num_points : int
            采样点数
        check_smoothness : bool
            是否检查平滑性
        check_no_jumps : bool
            是否检查无跳变
        tolerance : float
            允许的相对变化
        """
        super().__init__(f"Sensitivity Test ({param_name})")
        self.param_name = param_name
        self.param_range = param_range
        self.num_points = num_points
        self.check_smoothness = check_smoothness
        self.check_no_jumps = check_no_jumps
        self.tolerance = tolerance
    
    def run(self, device_builder: Callable) -> ValidationResult:
        """运行敏感性分析测试"""
        # 生成参数值列表
        param_values = np.linspace(self.param_range[0], 
                                   self.param_range[1], 
                                   self.num_points)
        
        results = []
        metrics = []
        
        for value in param_values:
            try:
                sim = device_builder(**{self.param_name: value})
                result = sim.run()
                results.append(result)
                
                # 提取关键指标
                metric = self._extract_metric(result)
                metrics.append(metric)
                
            except Exception as e:
                return ValidationResult(
                    self.name,
                    False,
                    f"参数 {self.param_name}={value} 时仿真失败: {str(e)}"
                )
        
        violations = []
        details = {
            'param_values': param_values.tolist(),
            'metrics': metrics
        }
        
        # 检查平滑性
        if self.check_smoothness:
            smoothness_violation = self._check_smoothness(metrics)
            details['smoothness_violation'] = smoothness_violation
            if smoothness_violation > self.tolerance:
                violations.append(f"平滑性违反: {smoothness_violation:.2e}")
        
        # 检查无跳变
        if self.check_no_jumps:
            jump_violation = self._check_no_jumps(metrics)
            details['jump_violation'] = jump_violation
            if jump_violation > 0:
                violations.append(f"检测到跳变: {jump_violation:.2e}")
        
        passed = len(violations) == 0
        
        if passed:
            message = f"参数 {self.param_name} 的敏感性分析通过"
        else:
            message = "; ".join(violations)
        
        return ValidationResult(
            self.name,
            passed,
            message,
            details
        )
    
    def _extract_metric(self, result) -> float:
        """提取关键指标（简化版本）"""
        # 这里可以根据具体需求提取不同的指标
        # 例如：阈值电压、记忆窗口、最大电流等
        
        # 简化版本：使用电势的最大值作为指标
        phi = getattr(result, 'phi', np.zeros(1))
        return float(np.max(phi))
    
    def _check_smoothness(self, metrics: List[float]) -> float:
        """检查平滑性"""
        if len(metrics) < 3:
            return 0.0
        
        # 计算二阶差分
        first_diff = np.diff(metrics)
        second_diff = np.diff(first_diff)
        
        # 二阶差分应该小（平滑）
        max_second_diff = np.max(np.abs(second_diff))
        
        # 归一化
        max_metric = np.max(np.abs(metrics))
        if max_metric > 0:
            smoothness_violation = max_second_diff / max_metric
        else:
            smoothness_violation = 0.0
        
        return float(smoothness_violation)
    
    def _check_no_jumps(self, metrics: List[float]) -> float:
        """检查无跳变"""
        if len(metrics) < 2:
            return 0.0
        
        # 计算一阶差分
        first_diff = np.diff(metrics)
        
        # 检查是否有异常大的跳变
        max_diff = np.max(np.abs(first_diff))
        mean_diff = np.mean(np.abs(first_diff))
        
        # 如果最大差分远大于平均差分，可能存在跳变
        if mean_diff > 0:
            jump_ratio = max_diff / mean_diff
            if jump_ratio > 10:  # 最大差分是平均差分的10倍以上
                return float(max_diff)
        
        return 0.0


class ParameterImportanceTest(BaseValidationTest):
    """参数重要性测试"""
    
    def __init__(self, param_names: List[str],
                 param_ranges: dict,
                 num_samples: int = 20):
        """
        Parameters
        ----------
        param_names : List[str]
            参数名称列表
        param_ranges : dict
            参数范围字典 {param_name: (min, max)}
        num_samples : int
            采样数
        """
        super().__init__("Parameter Importance Test")
        self.param_names = param_names
        self.param_ranges = param_ranges
        self.num_samples = num_samples
    
    def run(self, device_builder: Callable) -> ValidationResult:
        """运行参数重要性测试"""
        # 对每个参数进行敏感性分析
        sensitivities = {}
        
        for param_name in self.param_names:
            if param_name not in self.param_ranges:
                continue
            
            param_range = self.param_ranges[param_name]
            param_values = np.linspace(param_range[0], param_range[1], 
                                      self.num_samples)
            
            metrics = []
            for value in param_values:
                try:
                    sim = device_builder(**{param_name: value})
                    result = sim.run()
                    metric = self._extract_metric(result)
                    metrics.append(metric)
                except:
                    pass
            
            if len(metrics) > 1:
                # 计算敏感性（标准差/均值）
                mean_metric = np.mean(metrics)
                std_metric = np.std(metrics)
                
                if mean_metric > 0:
                    sensitivity = std_metric / mean_metric
                else:
                    sensitivity = 0.0
                
                sensitivities[param_name] = sensitivity
        
        # 按敏感性排序
        sorted_params = sorted(sensitivities.items(), 
                              key=lambda x: x[1], 
                              reverse=True)
        
        message = "参数重要性排序:\n"
        for param, sensitivity in sorted_params:
            message += f"  {param}: {sensitivity:.3f}\n"
        
        return ValidationResult(
            self.name,
            True,  # 参数重要性测试总是通过，只是提供信息
            message,
            {'sensitivities': sensitivities, 'sorted_params': sorted_params}
        )
    
    def _extract_metric(self, result) -> float:
        """提取关键指标"""
        phi = getattr(result, 'phi', np.zeros(1))
        return float(np.max(phi))
