"""
rtlgen.decomposition_rules — Hierarchical Decomposition Engine & Rule Registry

Framework core provides:
  - RuleRegistry: pluggable rule registration per domain
  - DecompositionEngine: recursive tree expansion driven by strategy constraints
  - PrePPAAnalyzer: structural pre-PPA estimation before DSL generation

Domain knowledge (KO-2, arbitration trees, processor pipelines, etc.) is injected
via plugins in skills/<domain>/decomposition_rules.py, NOT hardcoded here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

# Import lightweight metadata classes from decomposition.py to avoid circular deps
from rtlgen.decomposition import (
    BehavioralSpec,
    StrategySpec,
    Transform,
    PhysicalHint,
    PPAViolation,
)


# =====================================================================
# 1. PPA Violation / Suggestion for pre-PPA feedback
# =====================================================================

# PPAViolation lives in decomposition.py


# =====================================================================
# 2. Rule Registry — domain plugins register here
# =====================================================================

@dataclass
class DecompositionRule:
    """A single decomposition rule registered by a domain plugin."""
    operation: str
    apply: Callable[[BehavioralSpec, StrategySpec], Optional[BehavioralSpec]]
    domain: str = "generic"


class RuleRegistry:
    """Global registry for decomposition rules.

    Usage in domain plugins:
        from rtlgen.decomposition_rules import RuleRegistry, DecompositionRule

        @RuleRegistry.register(domain="arithmetic", operation="multiplication")
        def expand_multiplication(node, strategy):
            ...
    """
    _rules: Dict[str, List[DecompositionRule]] = {}

    @classmethod
    def register(cls, domain: str, operation: str):
        """Decorator to register a decomposition rule."""
        def decorator(fn: Callable):
            rule = DecompositionRule(operation=operation, apply=fn, domain=domain)
            cls._rules.setdefault(domain, []).append(rule)
            return fn
        return decorator

    @classmethod
    def get_rules(cls, domain: Optional[str] = None, operation: Optional[str] = None) -> List[DecompositionRule]:
        """Get all rules, optionally filtered by domain and/or operation."""
        rules: List[DecompositionRule] = []
        if domain:
            rules = list(cls._rules.get(domain, []))
        else:
            for r in cls._rules.values():
                rules.extend(r)
        if operation:
            rules = [r for r in rules if r.operation == operation]
        return rules

    @classmethod
    def find_matching_rule(cls, node: BehavioralSpec, strategy: StrategySpec
                          ) -> Optional[DecompositionRule]:
        """Find first rule whose operation matches node's physical.operation."""
        op = node.physical.operation if node.physical else ""
        for domain, rules in cls._rules.items():
            for rule in rules:
                if rule.operation == op:
                    return rule
        return None


# =====================================================================
# 3. DecompositionEngine — recursive expansion driven by constraints
# =====================================================================

class DecompositionEngine:
    """Recursively expand a decomposition tree until all leaf nodes satisfy
    strategy constraints.

    The engine is domain-agnostic.  It delegates concrete expansion logic
    to registered DecompositionRule plugins.
    """

    def __init__(self, root: BehavioralSpec, strategy: StrategySpec):
        self.root = root
        self.strategy = strategy
        self.violations: List[PPAViolation] = []
        self._expanded_nodes: set = set()

    def expand(self) -> BehavioralSpec:
        """Expand the full tree and return the new root."""
        self.root = self._expand_node(self.root, depth=0)
        return self.root

    def _expand_node(self, node: BehavioralSpec, depth: int = 0) -> BehavioralSpec:
        """Recursively expand a single node."""
        if id(node) in self._expanded_nodes:
            return node
        self._expanded_nodes.add(id(node))

        # 1. Try to apply a matching decomposition rule
        rule = RuleRegistry.find_matching_rule(node, self.strategy)
        if rule is not None:
            result = rule.apply(node, self.strategy)
            if result is not None:
                node = result

        # 2. Recurse into children (if any were created by the rule)
        if node.children:
            node.children = [self._expand_node(child, depth + 1) for child in node.children]

        # 3. Recompute latency from children
        node.latency = self._compute_latency(node)

        # 4. Structural pre-PPA check on THIS node
        self._check_node_constraints(node)

        return node

    @staticmethod
    def _compute_latency(node: BehavioralSpec) -> int:
        """Compute latency from children based on transform type.

        partition (e.g. KO-2 tree): latency = max(child.latency) + 1
        pipeline:                     latency = sum(child.latency) + 1
        parallelize:                  latency = max(child.latency)
        substitute / serialize:       latency = node.latency (user-defined)
        """
        if not node.children:
            return node.latency

        tx = node.transform
        if tx is None:
            return node.latency

        if tx.is_pipeline:
            return sum(c.latency for c in node.children) + 1
        if tx.is_partition:
            max_child = max(c.latency for c in node.children)
            for child in node.children:
                child.delay_cycles = max_child - child.latency
            return max_child + 1
        if tx.is_parallelize:
            return max(c.latency for c in node.children)
        return node.latency

    def _check_node_constraints(self, node: BehavioralSpec):
        """Run structural pre-PPA checks on a single node."""
        if node.physical is None:
            return

        strat = self.strategy
        if strat is None or not strat.constraints:
            return

        max_depth = strat.constraints.get("max_logic_depth")
        max_width = strat.constraints.get("max_comb_arithmetic_width")

        if node.latency == 0 and max_depth is not None:
            est_depth = node.physical.estimate_logic_depth()
            if est_depth > max_depth:
                self.violations.append(PPAViolation(
                    node_name=node.name,
                    issue=f"组合逻辑深度估算为 {est_depth}，超过目标 {max_depth}",
                    suggestion="考虑流水线化或进一步分解该节点",
                    severity="error",
                    auto_fixable=True,
                    estimated_logic_depth=est_depth,
                    target_logic_depth=max_depth,
                ))

        if node.latency == 0 and max_width is not None and node.physical.width > max_width:
            est_depth = node.physical.estimate_logic_depth()
            self.violations.append(PPAViolation(
                node_name=node.name,
                issue=f"组合算术单元位宽 {node.physical.width} 超过策略限制 {max_width}",
                suggestion="将该算术单元分解为流水线子模块或降低位宽",
                severity="error",
                auto_fixable=True,
                estimated_logic_depth=est_depth,
                target_logic_depth=max_depth or 0,
            ))

    def get_expansion_report(self) -> str:
        """Return a human-readable report of tree expansion + violations."""
        lines = ["# Decomposition Expansion Report", ""]
        lines.append(self._dump_tree(self.root))
        lines.append("")
        if self.violations:
            lines.append("## Pre-PPA Violations")
            lines.append("")
            for v in self.violations:
                lines.append(v.to_markdown())
        else:
            lines.append("✅ All nodes satisfy strategy constraints.")
        return "\n".join(lines)

    def _dump_tree(self, node: BehavioralSpec, indent: int = 0) -> str:
        """Pretty-print the decomposition tree."""
        prefix = "  " * indent
        tx_info = f" [{node.transform.type}]" if node.transform else ""
        phys = f" w={node.physical.width}" if node.physical and node.physical.width else ""
        lat = f" lat={node.latency}"
        line = f"{prefix}- {node.name}{tx_info}{phys}{lat}"
        parts = [line]
        for child in node.children:
            parts.append(self._dump_tree(child, indent + 1))
        return "\n".join(parts)


# =====================================================================
# 4. PrePPAAnalyzer — structural estimation on the decomposition tree
# =====================================================================

class PrePPAAnalyzer:
    """Fast structural PPA estimation based on the decomposition tree.

    This runs BEFORE DSL generation, giving the agent early feedback on
    whether the decomposition structure itself will meet timing/area goals.
    """

    def __init__(self, root: BehavioralSpec, strategy: StrategySpec):
        self.root = root
        self.strategy = strategy
        self.violations: List[PPAViolation] = []

    def analyze(self) -> List[PPAViolation]:
        """Traverse tree and collect all violations."""
        self.violations.clear()
        self._analyze_node(self.root)
        return self.violations

    def _analyze_node(self, node: BehavioralSpec):
        self._check_node(node)
        for child in node.children:
            self._analyze_node(child)

    def _check_node(self, node: BehavioralSpec):
        if node.physical is None or self.strategy is None:
            return

        constraints = self.strategy.constraints
        max_depth = constraints.get("max_logic_depth")
        max_width = constraints.get("max_comb_arithmetic_width")

        if node.latency == 0 and max_depth is not None:
            est = node.physical.estimate_logic_depth()
            if est > max_depth:
                self.violations.append(PPAViolation(
                    node_name=node.name,
                    issue=f"组合逻辑深度 {est} > 目标 {max_depth}",
                    suggestion="流水线化或进一步分解",
                    severity="error",
                    auto_fixable=True,
                    estimated_logic_depth=est,
                    target_logic_depth=max_depth,
                ))

        if node.latency == 0 and max_width is not None:
            if node.physical.width > max_width:
                est = node.physical.estimate_logic_depth()
                self.violations.append(PPAViolation(
                    node_name=node.name,
                    issue=f"组合算术位宽 {node.physical.width} > 限制 {max_width}",
                    suggestion="应用流水线分解规则",
                    severity="error",
                    auto_fixable=True,
                    estimated_logic_depth=est,
                    target_logic_depth=max_depth or 0,
                ))

    def summary(self) -> Dict[str, Any]:
        """Return a numeric summary of the tree."""
        total_nodes = 0
        leaf_nodes = 0
        max_leaf_width = 0
        max_leaf_depth = 0
        total_estimated_latency = 0

        def walk(n: BehavioralSpec):
            nonlocal total_nodes, leaf_nodes, max_leaf_width, max_leaf_depth, total_estimated_latency
            total_nodes += 1
            if not n.children:
                leaf_nodes += 1
                if n.physical:
                    max_leaf_width = max(max_leaf_width, n.physical.width)
                    max_leaf_depth = max(max_leaf_depth, n.physical.estimate_logic_depth())
                total_estimated_latency += n.latency
            for c in n.children:
                walk(c)

        walk(self.root)
        return {
            "total_nodes": total_nodes,
            "leaf_nodes": leaf_nodes,
            "max_leaf_width": max_leaf_width,
            "max_leaf_depth": max_leaf_depth,
            "root_latency": self.root.latency if self.root else 0,
            "violations": len(self.violations),
        }
