"""
验证报告生成

生成格式化的验证报告，包括：
- 测试结果汇总
- 详细信息
- 可视化建议
"""

from typing import List, Dict, Any
from datetime import datetime
from .base import ValidationResult


class ValidationReport:
    """验证报告生成器"""
    
    def __init__(self, title: str = "TCAD 验证报告"):
        """
        Parameters
        ----------
        title : str
            报告标题
        """
        self.title = title
        self.results: List[ValidationResult] = []
        self.timestamp = datetime.now()
    
    def add_result(self, result: ValidationResult):
        """添加测试结果"""
        self.results.append(result)
    
    def add_results(self, results: List[ValidationResult]):
        """批量添加测试结果"""
        self.results.extend(results)
    
    def generate_text_report(self) -> str:
        """生成文本格式的报告"""
        lines = []
        
        # 标题
        lines.append("=" * 70)
        lines.append(f"{self.title}")
        lines.append(f"生成时间: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        lines.append("")
        
        # 汇总统计
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        lines.append("【测试结果汇总】")
        lines.append(f"总测试数: {total}")
        lines.append(f"通过: {passed} ({100*passed/total:.1f}%)")
        lines.append(f"失败: {failed} ({100*failed/total:.1f}%)")
        lines.append("")
        
        # 详细结果
        lines.append("【详细测试结果】")
        lines.append("-" * 70)
        
        for i, result in enumerate(self.results, 1):
            status = "✓ PASS" if result.passed else "✗ FAIL"
            lines.append(f"\n{i}. {status}: {result.test_name}")
            
            if result.message:
                lines.append(f"   {result.message}")
            
            if result.details:
                lines.append("   详细信息:")
                for key, value in result.details.items():
                    if isinstance(value, (list, tuple)):
                        lines.append(f"     {key}: {value}")
                    elif isinstance(value, float):
                        lines.append(f"     {key}: {value:.6e}")
                    else:
                        lines.append(f"     {key}: {value}")
        
        lines.append("")
        lines.append("=" * 70)
        
        # 失败测试列表
        if failed > 0:
            lines.append("\n【失败的测试】")
            lines.append("-" * 70)
            for result in self.results:
                if not result.passed:
                    lines.append(f"  ✗ {result.test_name}")
                    if result.message:
                        lines.append(f"    原因: {result.message}")
        
        # 建议
        lines.append("\n【建议】")
        lines.append("-" * 70)
        if failed == 0:
            lines.append("  ✓ 所有验证测试通过，代码质量良好")
        else:
            lines.append(f"  ✗ {failed} 个测试失败，需要修复后再进行验证")
            lines.append("  建议:")
            lines.append("    1. 检查失败测试的详细信息")
            lines.append("    2. 修复代码中的问题")
            lines.append("    3. 重新运行验证测试")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def generate_summary(self) -> Dict[str, Any]:
        """生成摘要信息"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        return {
            'title': self.title,
            'timestamp': self.timestamp.isoformat(),
            'total_tests': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': 100 * passed / total if total > 0 else 0,
            'all_passed': failed == 0,
            'failed_tests': [r.test_name for r in self.results if not r.passed]
        }
    
    def save_to_file(self, filename: str):
        """保存报告到文件"""
        report = self.generate_text_report()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"验证报告已保存到: {filename}")
    
    def print_report(self):
        """打印报告到控制台"""
        print(self.generate_text_report())
    
    def __str__(self):
        return self.generate_text_report()


def create_validation_report(results: List[ValidationResult], 
                            title: str = "TCAD 验证报告") -> ValidationReport:
    """
    创建验证报告的便捷函数
    
    Parameters
    ----------
    results : List[ValidationResult]
        测试结果列表
    title : str
        报告标题
    
    Returns
    -------
    ValidationReport
        验证报告对象
    """
    report = ValidationReport(title)
    report.add_results(results)
    return report
