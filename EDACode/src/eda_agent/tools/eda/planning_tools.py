"""Task planning tools for analog circuit design workflows.

Provides structured design planning based on circuit type, helping the agent
decide which EDA tools to call and in what order.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from eda_agent.tools.base import EDATool, ToolProgress, ToolResult


class TaskPlanTool(EDATool):
    """Generate a structured task plan for analog circuit design.

    Understands common analog circuit types (op-amp, comparator, LDO, bandgap,
    ADC, PLL, etc.) and maps them to appropriate EDA SDK tool sequences.
    The plan is advisory — the agent decides whether to follow it.
    """

    name = "task_plan"
    aliases = ["plan", "design_plan"]
    input_schema = {
        "type": "object",
        "properties": {
            "design_type": {
                "type": "string",
                "description": (
                    "Circuit type to design. Supported: opamp (运算放大器), comparator (比较器), "
                    "ldo (低压差线性稳压器), bandgap (带隙基准), adc (模数转换器), "
                    "pll (锁相环), switch_capacitor (开关电容), filter (滤波器), "
                    "buffer (缓冲器), mixer (混频器), vco (压控振荡器), "
                    "custom (自定义/其他)."
                ),
            },
            "goal": {
                "type": "string",
                "description": "High-level design goal (e.g., 'two-stage Miller-compensated op-amp with 60dB gain').",
            },
            "constraints": {
                "type": "string",
                "description": "Optional constraints: process node, supply voltage, bandwidth, power budget, area limit, etc.",
            },
            "lib_name": {
                "type": "string",
                "description": "Target library name for the design.",
            },
            "cell_name": {
                "type": "string",
                "description": "Target cell name for the design.",
            },
        },
        "required": ["design_type", "goal"],
    }

    # Circuit-type → recommended workflow (all via Python scripts)
    _WORKFLOWS: Dict[str, List[Dict[str, Any]]] = {
        "opamp": [
            {"phase": "topology", "description": "选择拓扑结构（两级米勒补偿 / 套筒式 / 折叠共源共栅）", "tools": ["file_write", "bash"]},
            {"phase": "sizing", "description": "手工计算晶体管尺寸（W/L, 偏置电流）", "tools": ["bash"]},
            {"phase": "schematic", "description": "编写Python脚本绘制原理图并放置器件", "tools": ["file_write", "bash"]},
            {"phase": "simulation", "description": "编写Python脚本进行DC/AC/Transient仿真验证增益、带宽、相位裕度", "tools": ["file_write", "bash"]},
            {"phase": "layout", "description": "编写Python脚本绘制版图（匹配、对称、guard ring）", "tools": ["file_write", "bash"]},
            {"phase": "verification", "description": "编写Python脚本进行DRC / LVS / PEX后仿真", "tools": ["file_write", "bash"]},
        ],
        "comparator": [
            {"phase": "topology", "description": "选择比较器结构（两级开环 / 锁存器 / 动态）", "tools": ["file_write", "bash"]},
            {"phase": "sizing", "description": "计算失调、速度、功耗的折中", "tools": ["bash"]},
            {"phase": "schematic", "description": "编写Python脚本绘制原理图", "tools": ["file_write", "bash"]},
            {"phase": "simulation", "description": "编写Python脚本进行Transient仿真验证延迟、失调", "tools": ["file_write", "bash"]},
            {"phase": "layout", "description": "编写Python脚本绘制版图（输入对匹配、交叉耦合）", "tools": ["file_write", "bash"]},
            {"phase": "verification", "description": "编写Python脚本进行DRC / LVS / PEX", "tools": ["file_write", "bash"]},
        ],
        "ldo": [
            {"phase": "topology", "description": "选择LDO结构（PMOS pass / NMOS pass / 电容-less）", "tools": ["file_write", "bash"]},
            {"phase": "sizing", "description": "计算环路稳定性、负载调整率、压差", "tools": ["bash"]},
            {"phase": "schematic", "description": "编写Python脚本绘制原理图（误差放大器、功率管、反馈网络）", "tools": ["file_write", "bash"]},
            {"phase": "simulation", "description": "编写Python脚本进行AC/Transient/Load step仿真", "tools": ["file_write", "bash"]},
            {"phase": "layout", "description": "编写Python脚本绘制版图（功率器件散热、电流路径）", "tools": ["file_write", "bash"]},
            {"phase": "verification", "description": "编写Python脚本进行DRC / LVS / PEX", "tools": ["file_write", "bash"]},
        ],
        "bandgap": [
            {"phase": "topology", "description": "选择带隙结构（CTAT+PTAT / 曲率补偿）", "tools": ["file_write", "bash"]},
            {"phase": "sizing", "description": "计算零温度系数点、输出电压", "tools": ["bash"]},
            {"phase": "schematic", "description": "编写Python脚本绘制原理图（BJT/电阻网络、运放）", "tools": ["file_write", "bash"]},
            {"phase": "simulation", "description": "编写Python脚本进行DC sweep（温度、工艺角）仿真", "tools": ["file_write", "bash"]},
            {"phase": "layout", "description": "编写Python脚本绘制版图（BJT匹配、电阻匹配）", "tools": ["file_write", "bash"]},
            {"phase": "verification", "description": "编写Python脚本进行DRC / LVS / PEX", "tools": ["file_write", "bash"]},
        ],
        "adc": [
            {"phase": "architecture", "description": "选择ADC架构（SAR / Pipeline / Sigma-Delta / Flash）", "tools": ["file_write", "bash"]},
            {"phase": "sizing", "description": "计算分辨率、采样率、功耗预算", "tools": ["bash"]},
            {"phase": "schematic", "description": "编写Python脚本绘制子模块原理图（SAR logic, CDAC, comparator）", "tools": ["file_write", "bash"]},
            {"phase": "simulation", "description": "编写Python脚本进行FFT / INL / DNL / SNDR仿真", "tools": ["file_write", "bash"]},
            {"phase": "layout", "description": "编写Python脚本绘制版图（电容阵列匹配、数字模拟隔离）", "tools": ["file_write", "bash"]},
            {"phase": "verification", "description": "编写Python脚本进行DRC / LVS / PEX / 寄生后仿真", "tools": ["file_write", "bash"]},
        ],
        "pll": [
            {"phase": "architecture", "description": "选择PLL结构（Integer-N / Fractional-N）", "tools": ["file_write", "bash"]},
            {"phase": "sizing", "description": "计算环路带宽、相位噪声、锁定时间", "tools": ["bash"]},
            {"phase": "schematic", "description": "编写Python脚本绘制子模块（PFD, CP, VCO, Divider）", "tools": ["file_write", "bash"]},
            {"phase": "simulation", "description": "编写Python脚本进行Transient / Phase noise仿真", "tools": ["file_write", "bash"]},
            {"phase": "layout", "description": "编写Python脚本绘制版图（VCO电感匹配、数字模拟隔离）", "tools": ["file_write", "bash"]},
            {"phase": "verification", "description": "编写Python脚本进行DRC / LVS / PEX / EMIR", "tools": ["file_write", "bash"]},
        ],
        "custom": [
            {"phase": "explore", "description": "调研电路原理和参考设计", "tools": ["bash", "file_read"]},
            {"phase": "topology", "description": "确定电路拓扑", "tools": ["file_write", "bash"]},
            {"phase": "schematic", "description": "编写Python脚本绘制原理图", "tools": ["file_write", "bash"]},
            {"phase": "simulation", "description": "编写Python脚本进行仿真验证", "tools": ["file_write", "bash"]},
            {"phase": "layout", "description": "编写Python脚本绘制版图", "tools": ["file_write", "bash"]},
            {"phase": "verification", "description": "编写Python脚本进行物理验证与寄生后仿真", "tools": ["file_write", "bash"]},
        ],
    }

    def description(self) -> str:
        return (
            "Generate a structured task plan for analog circuit design based on circuit type. "
            "Understands op-amp, comparator, LDO, bandgap, ADC, PLL, and custom circuits. "
            "Returns a recommended workflow with phases, descriptions, and suggested EDA tools. "
            "Use this before starting a complex design to establish a clear roadmap."
        )

    async def call(
        self,
        args: Dict[str, Any],
        context: Any,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult:
        design_type = args.get("design_type", "custom").lower().strip()
        goal = args.get("goal", "")
        constraints = args.get("constraints", "")
        lib_name = args.get("lib_name", "")
        cell_name = args.get("cell_name", "")

        # Normalize design type
        type_map = {
            "opamp": "opamp", "op-amp": "opamp", "运算放大器": "opamp",
            "comparator": "comparator", "比较器": "comparator",
            "ldo": "ldo", "低压差": "ldo", "稳压器": "ldo",
            "bandgap": "bandgap", "带隙": "bandgap", "基准": "bandgap",
            "adc": "adc", "模数转换": "adc",
            "pll": "pll", "锁相环": "pll",
            "switch_capacitor": "custom", "开关电容": "custom",
            "filter": "custom", "滤波器": "custom",
            "buffer": "custom", "缓冲器": "custom",
            "mixer": "custom", "混频器": "custom",
            "vco": "custom", "压控振荡器": "custom",
        }
        normalized = type_map.get(design_type, "custom")

        workflow = self._WORKFLOWS.get(normalized, self._WORKFLOWS["custom"])

        plan = {
            "design_type": normalized,
            "goal": goal,
            "constraints": constraints or "None specified",
            "lib_name": lib_name or "(to be determined)",
            "cell_name": cell_name or "(to be determined)",
            "phases": [
                {
                    "index": i + 1,
                    "phase": step["phase"],
                    "description": step["description"],
                    "suggested_tools": step["tools"],
                    "status": "pending",
                }
                for i, step in enumerate(workflow)
            ],
            "recommended_first_steps": [],
        }

        # Provide concrete first-step recommendations (all via Python scripts)
        if lib_name and cell_name:
            plan["recommended_first_steps"] = [
                f"file_write: create a Python script that imports pyAether, initializes db, and opens '{lib_name}/{cell_name}'",
                f"bash: run the script with python3 to create the design",
            ]
        else:
            plan["recommended_first_steps"].append(
                "bash: list available PDKs / tech libs to decide lib_name and cell_name"
            )

        if normalized == "opamp":
            plan["key_metrics"] = ["DC gain (dB)", "Gain-Bandwidth Product (MHz)", "Phase Margin (°)", "Slew Rate (V/μs)", "CMRR/PSRR", "Input-referred noise (nV/√Hz)", "Power (mW)"]
            plan["recommended_first_steps"].extend([
                "bash: check design docs for topology reference",
                "file_write: write a Python script using the EDA SDK to place input differential pair, active load, second stage, compensation capacitor",
                "bash: run the schematic script",
            ])
        elif normalized == "comparator":
            plan["key_metrics"] = ["Propagation delay (ns)", "Input offset (mV)", "Hysteresis (mV)", "Kickback noise", "Power (μW)"]
        elif normalized == "ldo":
            plan["key_metrics"] = ["Dropout voltage (mV)", "Load regulation (mV/mA)", "Line regulation (mV/V)", "PSRR (dB)", "Settling time (μs)", "Quiescent current (μA)"]
        elif normalized == "bandgap":
            plan["key_metrics"] = ["Temperature coefficient (ppm/°C)", "Output voltage (V)", "PSRR (dB)", "Startup time (μs)", "Power (μW)"]
        elif normalized == "adc":
            plan["key_metrics"] = ["Resolution (bits)", "SNDR (dB)", "ENOB", "INL/DNL (LSB)", "Sampling rate (MS/s)", "Power (mW)"]
        elif normalized == "pll":
            plan["key_metrics"] = ["Phase noise (dBc/Hz)", "Jitter (fs rms)", "Lock time (μs)", "Frequency range (MHz)", "Spur level (dBc)"]

        return ToolResult(data=plan)
