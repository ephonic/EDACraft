"""Conditional Knowledge Base for EDA tool and circuit design expertise.

Provides fine-grained knowledge injection based on user intent detection.
Loads pyAE.md (EDA tool API) and ckt.md (circuit design methodology) and
injects only the relevant sections into the system prompt, keeping token
usage minimal while maximizing task relevance.

Usage:
    kb = KnowledgeBase.from_project_root("/path/to/eda-code")
    relevant = kb.retrieve(user_input="帮我画一个运放的版图")
    # Returns matching KnowledgeChunks from both pyAE and ckt
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class KnowledgeChunk:
    """A single piece of domain knowledge with intent-matching keywords."""

    chunk_id: str
    title: str
    content: str
    keywords: Set[str] = field(default_factory=set)
    source: str = ""  # "pyae" | "ckt" | "common"
    weight: float = 1.0

    def match_score(self, query: str) -> float:
        """Calculate relevance score for a user query.

        Simple but effective keyword matching:
        - Each matched keyword contributes 1.0 * weight
        - Partial word matches (e.g., "schematic" in "schematics") count at 0.5
        """
        if not query or not self.keywords:
            return 0.0
        q = query.lower()
        score = 0.0
        for kw in self.keywords:
            kw_lower = kw.lower()
            if kw_lower in q:
                # Full keyword match
                score += 1.0 * self.weight
            else:
                # Check if any query word contains the keyword
                # or keyword contains any query word (partial match)
                q_words = set(re.findall(r"[a-zA-Z0-9_\u4e00-\u9fff]+", q))
                for qw in q_words:
                    if kw_lower in qw or qw in kw_lower:
                        if len(kw_lower) >= 3 or len(qw) >= 3:
                            score += 0.5 * self.weight
                        break
        return score


class KnowledgeBase:
    """Conditional knowledge base for EDA SDK and circuit design."""

    # File names relative to project root
    PYAE_FILENAME = "pyAE.md"
    CKT_FILENAME = "ckt.md"

    def __init__(self, chunks: List[KnowledgeChunk]) -> None:
        self.chunks = chunks
        self._injected_ids: Set[str] = set()

    @classmethod
    def from_project_root(cls, project_root: str) -> "KnowledgeBase":
        """Load and parse pyAE.md and ckt.md from the project root."""
        chunks: List[KnowledgeChunk] = []

        pyae_path = os.path.join(project_root, cls.PYAE_FILENAME)
        if os.path.exists(pyae_path):
            chunks.extend(cls._parse_pyae(pyae_path))

        ckt_path = os.path.join(project_root, cls.CKT_FILENAME)
        if os.path.exists(ckt_path):
            chunks.extend(cls._parse_ckt(ckt_path))

        return cls(chunks)

    @classmethod
    def _parse_pyae(cls, filepath: str) -> List[KnowledgeChunk]:
        """Parse pyAE.md into themed chunks."""
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        chunks: List[KnowledgeChunk] = []

        # Define sections with their keyword triggers
        sections = [
            {
                "id": "pyae:init",
                "title": "EDA SDK 初始化",
                "keywords": {
                    "init", "初始化", "emyinit", "pyaether", "import pyaether",
                    "启动", "环境", "tcl", "database", "数据库",
                },
                "patterns": [
                    r"## 1\. 初始化.*?(?=## 2\.)",
                ],
            },
            {
                "id": "pyae:dm",
                "title": "EDA SDK 设计管理（DM）",
                "keywords": {
                    "library", "lib", "库", "cell", "单元", "view", "视图",
                    "dbopenlib", "dbcreatelib", "dbopencellview", "cellview",
                    "设计管理", "dm", "lib.defs",
                },
                "patterns": [
                    r"## 2\. 设计管理.*?## 3\. 原理图",
                ],
            },
            {
                "id": "pyae:schematic",
                "title": "EDA SDK 原理图构建",
                "keywords": {
                    "schematic", "原理图", "sch", "symbol", "符号",
                    "dbcreateinst", "dbcrtinst", "dbcrtwire", "dbaddfigtonet",
                    "连线", "器件", "instance", "net", "终端", "引脚",
                    "dbcrtschwire", "dbcrtschin", "dbcrterm",
                },
                "patterns": [
                    r"## 3\. 原理图构建.*?## 4\. 版图构建",
                ],
            },
            {
                "id": "pyae:layout",
                "title": "EDA SDK 版图构建",
                "keywords": {
                    "layout", "版图", "mask", "place", "route", "布线",
                    "dbcreatepath", "dbcrtpath", "guardring", "aeguardring",
                    "via", "打孔", "过孔", "金属", "metal", "层",
                    "形状", "shape", "polygon", "矩形", "rect",
                },
                "patterns": [
                    r"## 4\. 版图构建.*?## 5\. 符号构建",
                ],
            },
            {
                "id": "pyae:symbol",
                "title": "EDA SDK 符号构建",
                "keywords": {
                    "symbol", "符号", "schematicsymbol", "pinsymbol",
                    "dbcrtsymbolpin", "dbcrtsymbolpolygon", "dbcrtsymbollabel",
                    "引脚符号", "选择框", "椭圆", "反相器",
                },
                "patterns": [
                    r"## 5\. 符号构建.*?## 6\. 参数提取",
                ],
            },
            {
                "id": "pyae:netlist",
                "title": "EDA SDK 网表与参数提取",
                "keywords": {
                    "netlist", "网表", "cdf", "siminfo", "仿真信息",
                    "param", "参数", "extraction", "提取", "layout extraction",
                    "cdl", "spectre", "hspice", "aucdl", "寄生参数",
                    "alps", "snapshot", "argus", "svrf2pvrs",
                    "rce", "rcexplorer", "pex", "dspf", "spef",
                },
                "patterns": [
                    r"## 6\. 参数提取.*?## 7\. 仿真",
                ],
            },
            {
                "id": "pyae:simulation",
                "title": "EDA SDK 仿真与 MDE",
                "keywords": {
                    "simulation", "仿真", "mde", "testbench", "test bench",
                    "mdesession", "netlistandrun", "result", "波形",
                    "tran", "dc", "ac", "noise", "corner", "monte carlo",
                    "alps", "spice", "spectre", "hspice", "iwave",
                },
                "patterns": [
                    r"## 7\. 仿真.*?## 8\. 验证",
                ],
            },
            {
                "id": "pyae:verification",
                "title": "EDA SDK 验证（DRC/LVS）",
                "keywords": {
                    "drc", "lvs", "verification", "验证", "物理验证",
                    "argus", "check", "检查", "sdl", "schematic driven layout",
                    "dbcheckandsavedesign", "dbsecheckdesigninfo",
                    "design rule", "规则检查",
                },
                "patterns": [
                    r"## 8\. 验证.*?## 9\. 实用工具",
                ],
            },
            {
                "id": "pyae:utils",
                "title": "EDA SDK 实用工具与技巧",
                "keywords": {
                    "utility", "工具", "highlight", "高亮", "annotation", "标注",
                    "group", "组", "smash", "打散", "array", "阵列",
                    "editinplace", "层级", "hierarchy", "tech", "工艺",
                    "callback", "回调", "bindkey", "快捷键",
                },
                "patterns": [
                    r"## 9\. 实用工具.*?## 10\. 常见",
                ],
            },
            {
                "id": "pyae:pitfalls",
                "title": "EDA SDK 常见注意事项",
                "keywords": {
                    "note", "注意", "pitfall", "陷阱", "warning", "警告",
                    "坐标", "单位", "dbu", "uu", "参数格式", "方向",
                    "save", "close", "保存", "关闭",
                },
                "patterns": [
                    r"## 10\. 常见注意事项.*",
                ],
            },
        ]

        for sec in sections:
            content = ""
            for pat in sec["patterns"]:
                match = re.search(pat, text, re.DOTALL)
                if match:
                    content = match.group(0)
                    break
            if content:
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=sec["id"],
                        title=sec["title"],
                        content=content.strip(),
                        keywords=sec["keywords"],
                        source="pyae",
                        weight=1.0,
                    )
                )

        return chunks

    @classmethod
    def _parse_ckt(cls, filepath: str) -> List[KnowledgeChunk]:
        """Parse ckt.md into themed chunks."""
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        chunks: List[KnowledgeChunk] = []

        sections = [
            {
                "id": "ckt:workflow",
                "title": "设计流程总览",
                "keywords": {
                    "流程", "workflow", "设计流程", "迭代", "闭环",
                    "前仿真", "后仿真", "pre-sim", "post-sim",
                    "design", "circuit", "analog", "电路", "设计",
                    "three-stage", "three stage", "opamp", "运放",
                },
                "patterns": [r"## 1\. 设计流程总览.*?## 2\. 电路级"],
            },
            {
                "id": "ckt:behavioral",
                "title": "行为级建模与零极点分析",
                "keywords": {
                    "behavioral", "行为级", "零极点", "pole", "zero",
                    "传递函数", "transfer function", "gbw", "增益带宽",
                    "相位裕度", "pm", "压摆率", "sr", "建立时间",
                },
                "patterns": [r"#### Step 1：行为级建模.*?#### Step 2"],
            },
            {
                "id": "ckt:gm_id",
                "title": "gm/ID 方法定尺寸",
                "keywords": {
                    "gm/id", "gmoverid", "跨导效率", "反型区", "inversion",
                    "归一化电流", "sizing", "定尺寸", "晶体管尺寸",
                    "w/l", "沟道长度", "l", "w", "弱反型", "强反型",
                },
                "patterns": [r"#### Step 2：gm/ID 方法.*?#### Step 3"],
            },
            {
                "id": "ckt:diff_pair",
                "title": "差分对设计策略",
                "keywords": {
                    "diff pair", "差分对", "differential", "cmfb",
                    "共模反馈", "对称性", "tail current", "尾电流",
                    "共模输入范围", "cmrr",
                },
                "patterns": [r"### 2\.2 差分设计策略.*?## 3\. 模块级"],
            },
            {
                "id": "ckt:current_mirror",
                "title": "电流镜设计策略",
                "keywords": {
                    "current mirror", "电流镜", "cascode", "增益自举",
                    "regulated cascode", "偏置", "bias", "电流分配",
                },
                "patterns": [r"#### 2\.2\.2 电流镜.*?#### 2\.2\.3"],
            },
            {
                "id": "ckt:opamp",
                "title": "运放/LDO/比较器/S&H 设计策略",
                "keywords": {
                    "opamp", "运放", "运算放大器", "operational amplifier",
                    "ota", "两级运放", "折叠共源共栅", "telescopic",
                    "ldo", "低压差", " regulator", "比较器", "comparator",
                    "采样保持", "sample hold", "s/h", "s&h",
                },
                "patterns": [r"### 2\.1 通用设计流程.*?## 2\.2"],
            },
            {
                "id": "ckt:layout_matching",
                "title": "版图匹配技术",
                "keywords": {
                    "matching", "匹配", "common centroid", "共质心",
                    "interdigitized", "交叉指型", "dummy", "虚拟器件",
                    "unit cell", "梯度", "gradient", "mismatch", "失配",
                    "版图匹配", "layout matching", "器件匹配",
                },
                "patterns": [r"### 3\.2 匹配技术.*?### 3\.3"],
            },
            {
                "id": "ckt:layout_strategy",
                "title": "模块级版图布局策略",
                "keywords": {
                    "placement", "布局", "floorplan", "floor plan",
                    "compact", "压缩", "对称", "symmetry", "线长",
                    "guard ring", "保护环", "隔离", "shielding",
                    "版图布局", "模块版图", "布局策略", "版图设计",
                },
                "patterns": [r"### 3\.3 布局策略.*?## 4\. 系统级"],
            },
            {
                "id": "ckt:adc",
                "title": "ADC 系统设计策略",
                "keywords": {
                    "adc", "模数转换器", "pipeline", "sar", "sigma-delta",
                    "sndr", "enob", "采样保持", "s/h", "mdac",
                    "比较器", "comparator", "参考源", "数字校准",
                },
                "patterns": [r"\*\*ADC 指标分解.*?\*\*PLL"],
            },
            {
                "id": "ckt:pll",
                "title": "PLL 系统设计策略",
                "keywords": {
                    "pll", "锁相环", "vco", "pfd", "cp", "charge pump",
                    "环路滤波器", "loop filter", "divider", "分频器",
                    "相位噪声", "jitter", "锁定时间", "kvco",
                },
                "patterns": [r"\*\*PLL 指标分解.*?\*\*SerDes"],
            },
            {
                "id": "ckt:serdes",
                "title": "SerDes 系统设计策略",
                "keywords": {
                    "serdes", "cdr", "equalizer", "均衡器", "tx", "rx",
                    "driver", "预加重", "pre-emphasis", "ctle", "dfe",
                    "信道", "channel", "ber", "误码率", "抖动", "眼图",
                },
                "patterns": [r"\*\*SerDes 指标分解.*?## 4\.3"],
            },
            {
                "id": "ckt:system_arch",
                "title": "系统级架构与指标分解",
                "keywords": {
                    "architecture", "架构", "指标分解", "spec decomposition",
                    "behavioral modeling", "verilog-a", "matlab", "simulink",
                    "预算", "budget", "top-level", "子模块", "assembly",
                },
                "patterns": [r"### 4\.2 设计拆分.*?## 4\.3"],
            },
            {
                "id": "ckt:routing",
                "title": "版图布线与优化",
                "keywords": {
                    "routing", "布线", "route", "astar", "a*", "a-star",
                    "差分布线", "differential routing", "bus", "总线",
                    "全局布线", "详细布线", "global routing", "detailed routing",
                    "拥塞", "congestion", "电源布线", "power routing",
                    "ir drop", "shielding", "等长", "length matching",
                },
                "patterns": [r"## 5\. 版图布线与优化.*?## 6\. 迭代"],
            },
            {
                "id": "ckt:verification",
                "title": "迭代验证与后仿真",
                "keywords": {
                    "verification", "验证", "后仿真", "post-sim",
                    "drc", "lvs", "pex", "rc extraction", "寄生",
                    "寄生参数", "ir drop", "crosstalk", "串扰",
                    "前后差异", "迭代", "dspf", "spef",
                },
                "patterns": [r"## 6\. 迭代验证.*?## 7\. 尺寸"],
            },
            {
                "id": "ckt:optimization",
                "title": "尺寸微调与优化方法",
                "keywords": {
                    "optimization", "优化", "贝叶斯", "bayesian",
                    "sensitivity", "灵敏度", "alps", "monte carlo",
                    "corner", "工艺角", "良率", "yield", "turbo",
                    "pareto", "高斯过程", "gaussian process", "fo",
                },
                "patterns": [r"## 7\. 尺寸微调.*?## 附录"],
            },
        ]

        for sec in sections:
            content = ""
            for pat in sec["patterns"]:
                match = re.search(pat, text, re.DOTALL)
                if match:
                    content = match.group(0)
                    break
            if content:
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=sec["id"],
                        title=sec["title"],
                        content=content.strip(),
                        keywords=sec["keywords"],
                        source="ckt",
                        weight=1.0,
                    )
                )

        return chunks

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.5,
        max_tokens: int = 6000,
    ) -> List[KnowledgeChunk]:
        """Retrieve the most relevant knowledge chunks for a user query.

        Args:
            query: The user's input text.
            top_k: Maximum number of chunks to return.
            min_score: Minimum match score threshold.
            max_tokens: Approximate max total tokens to return (estimated).

        Returns:
            List of KnowledgeChunk sorted by relevance (highest first).
        """
        if not query:
            return []

        scored = [(chunk, chunk.match_score(query)) for chunk in self.chunks]
        scored = [(c, s) for c, s in scored if s >= min_score]
        scored.sort(key=lambda x: x[1], reverse=True)

        results: List[KnowledgeChunk] = []
        total_est_tokens = 0
        for chunk, score in scored[:top_k]:
            # Token estimate: CJK chars ≈ 1.0/token, Latin ≈ 0.25/token.
            # Use 0.35 as a safe upper-bound for mixed text.
            est_tokens = int(len(chunk.content) * 0.35)
            if total_est_tokens + est_tokens > max_tokens:
                break
            results.append(chunk)
            total_est_tokens += est_tokens

        return results

    def get_common_knowledge(self) -> str:
        """Return common/shared knowledge that applies to most EDA tasks.

        This is a lightweight, always-relevant summary that can be injected
        alongside conditional chunks.
        """
        return """## EDA Design Common Knowledge
- ALL analog design tasks use EDA SDK Python scripts (file_write + bash).
- Circuit sizing uses gm/ID methodology: gm/ID vs ID/(W/L) curves.
- Layout matching: common centroid, interdigitized, dummy devices.
- Verification flow: pre-sim → layout → DRC/LVS → PEX (RCExplorer) → post-sim.
- ALPS = SPICE simulator; Argus = DRC/LVS; RCExplorer = parasitic extraction.
"""

    def reset_injection_state(self) -> None:
        """Clear the record of which chunks have been injected."""
        self._injected_ids.clear()

    def mark_injected(self, chunk_ids: List[str]) -> None:
        """Mark chunks as already injected."""
        self._injected_ids.update(chunk_ids)

    def get_uninjected(self, chunks: List[KnowledgeChunk]) -> List[KnowledgeChunk]:
        """Filter out chunks that have already been injected."""
        return [c for c in chunks if c.chunk_id not in self._injected_ids]
