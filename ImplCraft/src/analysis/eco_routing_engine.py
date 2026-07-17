"""
ECO Routing Engine — core capabilities for DRC/LVS fix loop.

Design philosophy:
- Provide atomic operations: setup / execute / verify
- Support multiple toolchains (ICC2, Innovus, custom)
- Toolchain is user-configurable via ToolchainConfig
- Closed-loop iteration is delegated to AI agents

Architecture:
    ToolchainConfig (user-defined)
         ↓
    ECORoutingEngine (core operations)
         ↓
    setup() → ECOSession
    execute(session, fixes) → ExecutionResult
    verify(session) → VerificationResult
         ↓
    AI Agent (decides: continue, rollback, adjust, stop)

Key classes:
    FixSuggestion — concrete fix instruction (what, where, how, why)
    ToolchainConfig — user-configurable tool chain definition
    ECORoutingEngine — setup/execute/verify atomic operations
    FixSuggester — enhanced analyzer producing FixSuggestion objects
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, List, Dict, Optional, Callable
import yaml

from .drc_lvs_fixer import (
    DRCError,
    LVSError,
    ErrorAnalysis,
    ErrorSeverity,
    Fixability,
    FixType,
)

logger = logging.getLogger("ic_backend")


# ---------------------------------------------------------------------------
# FixSuggestion — concrete fix instruction
# ---------------------------------------------------------------------------

class SuggestionAction(Enum):
    """Concrete action types for a fix suggestion."""
    # DRC fixes
    INCREASE_SPACING = "increase_spacing"
    INCREASE_WIDTH = "increase_width"
    ADD_FILLER = "add_filler"
    REROUTE_NET = "reroute_net"
    ADD_VIA = "add_via"
    REMOVE_VIA = "remove_via"
    DETOUR_AROUND = "detour_around"
    LAYER_CHANGE = "layer_change"
    ADD_SHIELD = "add_shield"
    
    # LVS fixes
    RESIZE_DEVICE = "resize_device"
    RECONNECT_NET = "reconnect_net"
    ADD_MISSING_DEVICE = "add_missing_device"
    REMOVE_EXTRA_DEVICE = "remove_extra_device"
    FIX_PROPERTY = "fix_property"
    
    # Placement fixes
    MOVE_CELL = "move_cell"
    SWAP_CELL = "swap_cell"
    LEGALIZE = "legalize"
    
    # Generic
    MANUAL_REVIEW = "manual_review"
    CUSTOM_COMMAND = "custom_command"


@dataclass
class FixSuggestion:
    """
    Concrete fix suggestion with detailed instructions.
    
    This is what the AI agent receives and acts on.
    The agent can:
    - Accept as-is and execute
    - Modify parameters before execution
    - Reject and try alternative
    - Group multiple suggestions into a batch
    """
    suggestion_id: str = ""
    
    # What to fix
    error_rule: str = ""
    error_type: str = ""  # drc or lvs
    
    # Where
    target_objects: List[str] = field(default_factory=list)  # net names, cell names
    target_layer: str = ""
    target_region: Optional[tuple] = None  # (x1, y1, x2, y2)
    
    # How — the concrete action
    action: SuggestionAction = SuggestionAction.MANUAL_REVIEW
    parameters: Dict[str, Any] = field(default_factory=dict)
    command_template: str = ""  # Tool-specific command (filled by engine)
    
    # Why — context for agent decision
    confidence: float = 0.0  # 0.0-1.0, how confident we are this will work
    expected_reduction: int = 0  # Expected error count reduction
    side_effects: List[str] = field(default_factory=list)
    rollback_strategy: str = ""
    
    # Dependencies
    depends_on: List[str] = field(default_factory=list)  # Other suggestion IDs
    conflicts_with: List[str] = field(default_factory=list)
    
    # Priority and grouping
    priority: int = 0  # Higher = more important
    batch_group: str = ""  # Suggestions that should be applied together
    
    # Execution state (filled by engine)
    status: str = "pending"  # pending, executed, verified, failed, skipped
    execution_result: str = ""
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d["action"] = self.action.value
        return d
    
    @classmethod
    def from_dict(cls, data: dict) -> FixSuggestion:
        data = dict(data)
        data["action"] = SuggestionAction(data.get("action", "manual_review"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def summary(self) -> str:
        lines = [
            f"Suggestion {self.suggestion_id}:",
            f"  Action: {self.action.value}",
            f"  Target: {', '.join(self.target_objects[:5])}"
            f"{'...' if len(self.target_objects) > 5 else ''}",
            f"  Layer: {self.target_layer or 'any'}",
            f"  Confidence: {self.confidence:.0%}",
            f"  Expected reduction: {self.expected_reduction} errors",
        ]
        if self.parameters:
            lines.append(f"  Parameters: {self.parameters}")
        if self.side_effects:
            lines.append(f"  Side effects: {', '.join(self.side_effects)}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# ToolchainConfig — user-configurable tool chain
# ---------------------------------------------------------------------------

class ToolName(Enum):
    ICC2 = "icc2"
    INNOVUS = "innovus"
    CUSTOM = "custom"


@dataclass
class ToolchainConfig:
    """
    User-configurable toolchain definition.
    
    Users can define their own toolchain by:
    - Setting tool name and version
    - Overriding command templates
    - Adding custom pre/post hooks
    - Specifying environment variables
    
    Example:
        config = ToolchainConfig.from_preset("icc2")
        config.command_templates["eco_setup"] = "my_custom_setup"
        config.environment["LICENSE_SERVER"] = "27000@myserver"
    """
    name: str = "icc2"
    version: str = ""
    
    # Command templates — the core of toolchain abstraction
    # Each template is a string that will be formatted with parameters
    command_templates: Dict[str, str] = field(default_factory=dict)
    
    # Environment variables
    environment: Dict[str, str] = field(default_factory=dict)
    
    # Pre/post hooks — custom scripts to run before/after operations
    pre_hooks: Dict[str, str] = field(default_factory=dict)
    post_hooks: Dict[str, str] = field(default_factory=dict)
    
    # Tool-specific settings
    settings: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_preset(cls, tool: str) -> ToolchainConfig:
        """Create config from built-in preset."""
        presets = {
            "icc2": cls._icc2_preset(),
            "innovus": cls._innovus_preset(),
        }
        if tool.lower() in presets:
            return presets[tool.lower()]
        return cls(name=tool)
    
    @classmethod
    def from_file(cls, path: str | Path) -> ToolchainConfig:
        """Load toolchain config from YAML/JSON file."""
        path = Path(path)
        if path.suffix in [".yaml", ".yml"]:
            with open(path) as f:
                data = yaml.safe_load(f)
        else:
            with open(path) as f:
                data = json.load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def save(self, path: str | Path):
        """Save toolchain config to file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        if path.suffix in [".yaml", ".yml"]:
            with open(path, "w") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        else:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
    
    def get_command(self, operation: str, **kwargs) -> str:
        """
        Get formatted command for an operation.
        
        Args:
            operation: Operation name (e.g., "eco_setup", "eco_route")
            **kwargs: Parameters to format into the template
            
        Returns:
            Formatted command string
        """
        template = self.command_templates.get(operation, "")
        if not template:
            logger.warning(f"No command template for operation: {operation}")
            return ""
        
        # Safe formatting — missing keys become empty strings
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing parameter {e} for operation {operation}")
            return template
    
    @staticmethod
    def _icc2_preset() -> ToolchainConfig:
        return ToolchainConfig(
            name="icc2",
            version="",
            command_templates={
                # ECO setup — prepare design for ECO routing
                "eco_setup": (
                    "# ECO Setup\n"
                    "open_lib {lib_name}\n"
                    "open_cell {cell_name}\n"
                    "create_eco_snapshot -name {snapshot_name}\n"
                    "set_eco_mode -enable true\n"
                    "set_opt_eco_mode -physical true\n"
                ),
                
                # Spacing fix
                "fix_spacing": (
                    "# Fix spacing: {rule}\n"
                    "eco_opt_route -nets [get_nets {nets}]\n"
                    "    -effort high -drc_fix true\n"
                    "    -spacing_rule {rule}\n"
                ),
                
                # Width fix
                "fix_width": (
                    "# Fix width: {rule}\n"
                    "eco_opt_route -nets [get_nets {nets}]\n"
                    "    -effort high -drc_fix true\n"
                    "    -width_rule {rule}\n"
                ),
                
                # General reroute
                "reroute": (
                    "# Reroute nets\n"
                    "eco_opt_route -nets [get_nets {nets}]\n"
                    "    -effort {effort}\n"
                    "    -timing_driven {timing_driven}\n"
                    "    -drc_fix true\n"
                ),
                
                # Via operations
                "add_via": (
                    "# Add via at {location}\n"
                    "create_via -at {location} -type {via_type}\n"
                ),
                "remove_via": (
                    "# Remove via at {location}\n"
                    "remove_via -at {location}\n"
                ),
                
                # Cell operations
                "move_cell": (
                    "# Move cell {cell}\n"
                    "set_cell_location {cell} -x {x} -y {y}\n"
                ),
                "resize_cell": (
                    "# Resize cell {cell}\n"
                    "size_cell {cell} {new_master}\n"
                ),
                "swap_cell": (
                    "# Swap cell {cell}\n"
                    "change_cell {cell} -ref_name {new_master}\n"
                ),
                
                # Layer change
                "change_layer": (
                    "# Change net {net} to layer {layer}\n"
                    "eco_opt_route -nets [get_nets {net}]\n"
                    "    -layer_constraint {layer}\n"
                ),
                
                # Shield
                "add_shield": (
                    "# Add shield for net {net}\n"
                    "create_shield -net [get_nets {net}] -spacing {spacing}\n"
                ),
                
                # Detour
                "detour": (
                    "# Detour net {net} around region {region}\n"
                    "eco_opt_route -nets [get_nets {net}]\n"
                    "    -avoid_region {region}\n"
                    "    -effort high\n"
                ),
                
                # Legalize
                "legalize": (
                    "# Legalize placement\n"
                    "legalize_placement\n"
                ),
                
                # Verify
                "verify_drc": (
                    "# Verify DRC\n"
                    "check_design -drc\n"
                    "report_drc -file {report_file}\n"
                ),
                "verify_lvs": (
                    "# Verify LVS (requires external Calibre run)\n"
                    "write_gds {gds_file}\n"
                    "write_verilog -include pg {netlist_file}\n"
                ),
                
                # Execute (run the batch)
                "execute_batch": (
                    "# Execute ECO batch\n"
                    "source {script_file}\n"
                    "report_drc > {drc_report}\n"
                    "report_timing > {timing_report}\n"
                ),
                
                # Rollback
                "rollback": (
                    "# Rollback to snapshot\n"
                    "restore_eco_snapshot -name {snapshot_name}\n"
                ),
                
                # Close session
                "close": (
                    "# Close session\n"
                    "set_eco_mode -enable false\n"
                    "close_cell\n"
                    "close_lib\n"
                ),
                
                # Save
                "save": (
                    "# Save design\n"
                    "write -format verilog -output {netlist_file}\n"
                    "write_gds {gds_file}\n"
                ),
            },
            settings={
                "default_effort": "high",
                "timing_driven": "true",
                "max_eco_iterations": 10,
            },
        )
    
    @staticmethod
    def _innovus_preset() -> ToolchainConfig:
        return ToolchainConfig(
            name="innovus",
            version="",
            command_templates={
                "eco_setup": (
                    "# ECO Setup\n"
                    "defIn -file {def_file}\n"
                    "ecoDesign -begin\n"
                    "setEcoMode -ecoMode\n"
                ),
                "fix_spacing": (
                    "# Fix spacing: {rule}\n"
                    "ecoOptDesign -nets {nets}\n"
                    "    -drcFix -spacingRule {rule}\n"
                ),
                "fix_width": (
                    "# Fix width: {rule}\n"
                    "ecoOptDesign -nets {nets}\n"
                    "    -drcFix -widthRule {rule}\n"
                ),
                "reroute": (
                    "# Reroute nets\n"
                    "ecoOptDesign -nets {nets}\n"
                    "    -effort {effort}\n"
                ),
                "add_via": (
                    "# Add via\n"
                    "addVia -at {location} -type {via_type}\n"
                ),
                "move_cell": (
                    "# Move cell\n"
                    "setPlaceMode -moveCell {cell} {x} {y}\n"
                ),
                "resize_cell": (
                    "# Resize cell\n"
                    "resizeInst -inst {cell} -master {new_master}\n"
                ),
                "swap_cell": (
                    "# Swap cell\n"
                    "replaceInst -inst {cell} -cell {new_master}\n"
                ),
                "change_layer": (
                    "# Change layer\n"
                    "setLayerPreference {layer} -nets {nets}\n"
                ),
                "legalize": (
                    "# Legalize\n"
                    "legalizePin\n"
                    "legalizePlacement\n"
                ),
                "verify_drc": (
                    "# Verify DRC\n"
                    "verifyConnectivity -type all -report {report_file}\n"
                ),
                "verify_lvs": (
                    "# Export for LVS\n"
                    "defOut -netlist {netlist_file}\n"
                    "streamOut {gds_file}\n"
                ),
                "execute_batch": (
                    "# Execute ECO batch\n"
                    "source {script_file}\n"
                ),
                "rollback": (
                    "# Rollback\n"
                    "ecoDesign -abort\n"
                    "defIn -file {backup_def}\n"
                ),
                "close": (
                    "# Close\n"
                    "ecoDesign -end\n"
                ),
                "save": (
                    "# Save\n"
                    "defOut -all {def_file}\n"
                    "streamOut {gds_file}\n"
                ),
            },
            settings={
                "default_effort": "high",
                "max_eco_iterations": 10,
            },
        )


# ---------------------------------------------------------------------------
# ECOSession — tracks state of an ECO session
# ---------------------------------------------------------------------------

@dataclass
class ECOSession:
    """
    ECO session state — tracks what's happened in the current session.
    """
    session_id: str = ""
    toolchain: str = ""
    created_at: str = ""
    
    # Design state
    lib_name: str = ""
    cell_name: str = ""
    snapshot_name: str = ""
    
    # Working directory
    work_dir: str = ""
    
    # State tracking
    setup_done: bool = False
    fixes_applied: List[str] = field(default_factory=list)
    iteration: int = 0
    
    # Results tracking
    error_count_before: int = 0
    error_count_after: int = 0
    
    # Generated files
    generated_scripts: List[str] = field(default_factory=list)
    generated_reports: List[str] = field(default_factory=list)
    
    @property
    def errors_fixed(self) -> int:
        return max(0, self.error_count_before - self.error_count_after)


@dataclass
class ExecutionResult:
    """Result of executing fixes."""
    session_id: str = ""
    iteration: int = 0
    
    fixes_attempted: int = 0
    fixes_applied: int = 0
    fixes_failed: int = 0
    
    per_fix_results: List[Dict[str, Any]] = field(default_factory=list)
    script_path: str = ""
    log_path: str = ""
    
    warnings: List[str] = field(default_factory=list)
    
    def summary(self) -> str:
        return (
            f"Execution Result (iteration {self.iteration}):\n"
            f"  Attempted: {self.fixes_attempted}\n"
            f"  Applied: {self.fixes_applied}\n"
            f"  Failed: {self.fixes_failed}\n"
            f"  Script: {self.script_path}\n"
        )


@dataclass
class VerificationResult:
    """Result of verification (re-run DRC/LVS)."""
    session_id: str = ""
    check_type: str = "drc"  # drc or lvs
    
    # Error counts
    errors_before: int = 0
    errors_after: int = 0
    
    # Breakdown
    new_errors: List[str] = field(default_factory=list)
    fixed_errors: List[str] = field(default_factory=list)
    remaining_errors: Dict[str, int] = field(default_factory=dict)
    
    # Overall status
    is_clean: bool = False
    improvement_ratio: float = 0.0  # (before - after) / before
    
    report_path: str = ""
    
    def summary(self) -> str:
        status = "CLEAN" if self.is_clean else f"{self.errors_after} errors remaining"
        return (
            f"Verification ({self.check_type.upper()}):\n"
            f"  Status: {status}\n"
            f"  Before: {self.errors_before}\n"
            f"  After: {self.errors_after}\n"
            f"  Fixed: {len(self.fixed_errors)}\n"
            f"  New: {len(self.new_errors)}\n"
            f"  Improvement: {self.improvement_ratio:.1%}\n"
        )


# ---------------------------------------------------------------------------
# FixSuggester — produces concrete FixSuggestion objects
# ---------------------------------------------------------------------------

class FixSuggester:
    """
    Enhanced analyzer that produces concrete FixSuggestion objects.
    
    Unlike ErrorAnalyzer which classifies errors, FixSuggester
    generates actionable fix instructions that an agent can execute.
    """
    
    # Rule-to-action mapping (can be extended by user)
    RULE_ACTIONS: Dict[str, Dict[str, Any]] = {
        # Spacing rules
        "S": {
            "action": SuggestionAction.INCREASE_SPACING,
            "confidence": 0.85,
            "parameters": {"delta_um": 0.02},
            "side_effects": ["May increase wire length"],
        },
        "SP": {
            "action": SuggestionAction.INCREASE_SPACING,
            "confidence": 0.85,
            "parameters": {"delta_um": 0.02},
            "side_effects": ["May increase wire length"],
        },
        # Width rules
        "W": {
            "action": SuggestionAction.INCREASE_WIDTH,
            "confidence": 0.80,
            "parameters": {"delta_um": 0.01},
            "side_effects": ["May cause new spacing violations"],
        },
        # Min area
        "MIN": {
            "action": SuggestionAction.ADD_FILLER,
            "confidence": 0.70,
            "parameters": {},
            "side_effects": ["Increases metal density"],
        },
        "AREA": {
            "action": SuggestionAction.ADD_FILLER,
            "confidence": 0.70,
            "parameters": {},
            "side_effects": ["Increases metal density"],
        },
        # Antenna
        "ANT": {
            "action": SuggestionAction.ADD_VIA,
            "confidence": 0.60,
            "parameters": {"via_type": "antenna_diode"},
            "side_effects": ["Adds devices, may affect LVS"],
        },
        # EOD (End of Design)
        "EOD": {
            "action": SuggestionAction.DETOUR_AROUND,
            "confidence": 0.50,
            "parameters": {},
            "side_effects": ["May increase delay", "May cause congestion"],
        },
        # Metal density
        "DEN": {
            "action": SuggestionAction.ADD_FILLER,
            "confidence": 0.75,
            "parameters": {"filler_type": "metal_fill"},
            "side_effects": ["Increases capacitance"],
        },
    }
    
    def __init__(self, custom_rules: Optional[Dict] = None):
        """
        Initialize suggester with optional custom rules.
        
        Args:
            custom_rules: Additional rule-to-action mappings
                         (merged with built-in rules)
        """
        self.rules = dict(self.RULE_ACTIONS)
        if custom_rules:
            self.rules.update(custom_rules)
    
    def suggest_fixes(
        self,
        analysis: ErrorAnalysis,
        max_suggestions: int = 100,
        min_confidence: float = 0.0,
    ) -> List[FixSuggestion]:
        """
        Generate concrete fix suggestions from error analysis.
        
        Args:
            analysis: ErrorAnalysis from ErrorAnalyzer
            max_suggestions: Maximum suggestions to generate
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of FixSuggestion objects
        """
        suggestions = []
        suggestion_count = 0
        
        # Group errors by rule for batch suggestions
        rules_seen: Dict[str, List[DRCError]] = {}
        for error in analysis.drc_errors:
            if error.rule_name not in rules_seen:
                rules_seen[error.rule_name] = []
            rules_seen[error.rule_name].append(error)
        
        # Generate suggestions per rule group
        for rule, errors in rules_seen.items():
            if suggestion_count >= max_suggestions:
                break
            
            suggestion = self._suggest_for_rule(rule, errors)
            if suggestion and suggestion.confidence >= min_confidence:
                suggestion.suggestion_id = f"fix_{suggestion_count + 1:04d}"
                suggestions.append(suggestion)
                suggestion_count += 1
        
        # Generate LVS suggestions
        for error in analysis.lvs_errors:
            if suggestion_count >= max_suggestions:
                break
            
            suggestion = self._suggest_for_lvs_error(error)
            if suggestion and suggestion.confidence >= min_confidence:
                suggestion.suggestion_id = f"fix_{suggestion_count + 1:04d}"
                suggestions.append(suggestion)
                suggestion_count += 1
        
        # Sort by priority (confidence * expected_reduction)
        suggestions.sort(
            key=lambda s: s.confidence * s.expected_reduction,
            reverse=True,
        )
        
        # Assign batch groups (suggestions on same layer)
        self._assign_batch_groups(suggestions)
        
        return suggestions
    
    def _suggest_for_rule(
        self,
        rule: str,
        errors: List[DRCError],
    ) -> Optional[FixSuggestion]:
        """Generate suggestion for a DRC rule group."""
        if not errors:
            return None
        
        # Find matching action
        action_config = self._find_action_config(rule)
        if not action_config:
            return FixSuggestion(
                error_rule=rule,
                error_type="drc",
                target_layer=self._extract_layer(rule),
                action=SuggestionAction.MANUAL_REVIEW,
                confidence=0.3,
                expected_reduction=len(errors),
                side_effects=["Unknown rule — manual review required"],
            )
        
        layer = self._extract_layer(rule)
        nets = [f"net_{rule}_{i}" for i in range(min(len(errors), 50))]
        
        return FixSuggestion(
            error_rule=rule,
            error_type="drc",
            target_objects=nets,
            target_layer=layer,
            action=action_config["action"],
            parameters=action_config.get("parameters", {}),
            confidence=action_config.get("confidence", 0.5),
            expected_reduction=len(errors),
            side_effects=action_config.get("side_effects", []),
            rollback_strategy=f"Reroute {layer} nets to original state",
            priority=self._calculate_priority(rule, len(errors)),
        )
    
    def _suggest_for_lvs_error(self, error: LVSError) -> Optional[FixSuggestion]:
        """Generate suggestion for an LVS error."""
        if error.error_type == "property_error":
            return FixSuggestion(
                error_rule=error.error_type,
                error_type="lvs",
                target_objects=[error.layout_device] if error.layout_device else [],
                action=SuggestionAction.FIX_PROPERTY,
                parameters={
                    "layout_device": error.layout_device,
                    "source_device": error.source_device,
                },
                confidence=0.90,
                expected_reduction=1,
                side_effects=[],
                priority=3,
            )
        
        elif error.error_type == "net_mismatch":
            return FixSuggestion(
                error_rule=error.error_type,
                error_type="lvs",
                target_objects=[error.layout_net, error.source_net],
                action=SuggestionAction.RECONNECT_NET,
                parameters={
                    "layout_net": error.layout_net,
                    "source_net": error.source_net,
                },
                confidence=0.60,
                expected_reduction=1,
                side_effects=["May affect timing", "Verify connectivity manually"],
                priority=5,
                rollback_strategy="Restore original netlist connections",
            )
        
        elif error.error_type == "device_mismatch":
            return FixSuggestion(
                error_rule=error.error_type,
                error_type="lvs",
                action=SuggestionAction.MANUAL_REVIEW,
                confidence=0.30,
                expected_reduction=1,
                side_effects=["Requires netlist/schematic review"],
                priority=5,
            )
        
        return None
    
    def _find_action_config(self, rule: str) -> Optional[Dict]:
        """Find action config for a rule."""
        # Extract rule type
        parts = rule.split(".")
        if len(parts) >= 3:
            rule_type = parts[1]
        elif len(parts) == 2:
            rule_type = parts[0]
        else:
            rule_type = rule
        
        # Try exact match first, then prefix match
        if rule_type in self.rules:
            return self.rules[rule_type]
        
        for key, config in self.rules.items():
            if rule_type.startswith(key):
                return config
        
        return None
    
    def _extract_layer(self, rule: str) -> str:
        """Extract layer from rule name."""
        parts = rule.split(".")
        return parts[0] if parts else rule
    
    def _calculate_priority(self, rule: str, error_count: int) -> int:
        """Calculate fix priority."""
        # Critical rules get highest priority
        critical_rules = ["ANT", "LATCH", "EOD"]
        if any(rule.startswith(r) for r in critical_rules):
            return 5
        
        # High error count = high priority
        if error_count > 100:
            return 4
        elif error_count > 50:
            return 3
        elif error_count > 10:
            return 2
        return 1
    
    def _assign_batch_groups(self, suggestions: List[FixSuggestion]):
        """Assign batch groups (suggestions on same layer)."""
        layer_groups: Dict[str, List[FixSuggestion]] = {}
        for s in suggestions:
            layer = s.target_layer or "default"
            if layer not in layer_groups:
                layer_groups[layer] = []
            layer_groups[layer].append(s)
        
        for layer, group in layer_groups.items():
            if len(group) > 1:
                batch_id = f"batch_{layer}"
                for s in group:
                    s.batch_group = batch_id


# ---------------------------------------------------------------------------
# ECORoutingEngine — core operations
# ---------------------------------------------------------------------------

class ECORoutingEngine:
    """
    ECO Routing Engine — core capabilities for the DRC/LVS fix loop.
    
    Provides three atomic operations:
    - setup()    — prepare the design for ECO routing
    - execute()  — apply fixes (generate and optionally run scripts)
    - verify()   — check if fixes worked
    
    The agent decides:
    - Which fixes to apply
    - When to rollback
    - When to stop iterating
    - How to adjust parameters
    
    Usage:
        config = ToolchainConfig.from_preset("icc2")
        engine = ECORoutingEngine(config)
        
        session = engine.setup(lib_name="mylib", cell_name="top")
        
        # Agent decides which fixes to apply
        result = engine.execute(session, suggestions)
        
        # Agent checks results
        verification = engine.verify(session)
        
        if not verification.is_clean:
            # Agent adjusts and tries again
            ...
    """
    
    def __init__(
        self,
        config: ToolchainConfig,
        work_dir: str | Path = "./eco_work",
    ):
        self.config = config
        self.work_dir = Path(work_dir)
        self._suggester = FixSuggester()
    
    def setup(
        self,
        lib_name: str = "",
        cell_name: str = "",
        snapshot_name: str = "",
        error_count_before: int = 0,
    ) -> ECOSession:
        """
        Setup ECO session — prepare design for ECO routing.
        
        This generates the setup script and creates the session state.
        The agent runs the actual tool command.
        
        Args:
            lib_name: Library name
            cell_name: Cell/design name
            snapshot_name: Snapshot name for rollback (auto-generated if empty)
            error_count_before: Known error count before fixes
            
        Returns:
            ECOSession with setup_done=True
        """
        session_id = str(uuid.uuid4())[:8]
        
        if not snapshot_name:
            snapshot_name = f"eco_snapshot_{session_id}"
        
        session = ECOSession(
            session_id=session_id,
            toolchain=self.config.name,
            created_at=datetime.now().isoformat(),
            lib_name=lib_name,
            cell_name=cell_name,
            snapshot_name=snapshot_name,
            work_dir=str(self.work_dir),
            error_count_before=error_count_before,
            error_count_after=error_count_before,
        )
        
        # Create work directory
        session_dir = self.work_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate setup script
        setup_cmd = self.config.get_command(
            "eco_setup",
            lib_name=lib_name,
            cell_name=cell_name,
            snapshot_name=snapshot_name,
        )
        
        # Add pre-hooks
        pre_hook = self.config.pre_hooks.get("eco_setup", "")
        
        setup_script = ""
        if pre_hook:
            setup_script += f"# Pre-hook\n{pre_hook}\n\n"
        setup_script += setup_cmd
        
        setup_path = session_dir / "setup.tcl"
        setup_path.write_text(setup_script)
        session.generated_scripts.append(str(setup_path))
        
        session.setup_done = True
        
        logger.info(
            f"ECO session {session_id} setup: "
            f"lib={lib_name}, cell={cell_name}"
        )
        
        return session
    
    def execute(
        self,
        session: ECOSession,
        suggestions: List[FixSuggestion],
        dry_run: bool = False,
    ) -> ExecutionResult:
        """
        Execute fixes — apply suggestions to the design.
        
        This generates an execution script with all fix commands.
        The agent runs the actual tool command.
        
        Args:
            session: Active ECO session
            suggestions: List of FixSuggestion to apply
            dry_run: If True, generate script but don't mark as executed
            
        Returns:
            ExecutionResult with per-fix status
        """
        if not session.setup_done:
            raise RuntimeError("Session not set up. Call setup() first.")
        
        session.iteration += 1
        
        result = ExecutionResult(
            session_id=session.session_id,
            iteration=session.iteration,
            fixes_attempted=len(suggestions),
        )
        
        session_dir = self.work_dir / session.session_id
        
        # Generate execution script
        script_lines = [
            f"# ECO Execution Script — Iteration {session.iteration}",
            f"# Session: {session.session_id}",
            f"# Toolchain: {self.config.name}",
            f"# Fixes: {len(suggestions)}",
            "",
        ]
        
        # Pre-hook
        pre_hook = self.config.pre_hooks.get("execute", "")
        if pre_hook:
            script_lines.append(f"# Pre-hook\n{pre_hook}\n")
        
        # Generate commands for each suggestion
        for suggestion in suggestions:
            cmd = self._generate_fix_command(suggestion)
            if cmd:
                script_lines.append(f"# Fix {suggestion.suggestion_id}: "
                                   f"{suggestion.action.value}")
                script_lines.append(f"# Confidence: {suggestion.confidence:.0%}")
                script_lines.append(cmd)
                script_lines.append("")
                
                if not dry_run:
                    result.fixes_applied += 1
                    suggestion.status = "executed"
                    session.fixes_applied.append(suggestion.suggestion_id)
                    
                    result.per_fix_results.append({
                        "suggestion_id": suggestion.suggestion_id,
                        "action": suggestion.action.value,
                        "status": "applied",
                    })
            else:
                result.fixes_failed += 1
                suggestion.status = "failed"
                result.per_fix_results.append({
                    "suggestion_id": suggestion.suggestion_id,
                    "action": suggestion.action.value,
                    "status": "failed",
                    "reason": "No command template available",
                })
                result.warnings.append(
                    f"No command for {suggestion.action.value} "
                    f"(fix {suggestion.suggestion_id})"
                )
        
        # Post-hook
        post_hook = self.config.post_hooks.get("execute", "")
        if post_hook:
            script_lines.append(f"\n# Post-hook\n{post_hook}")
        
        # Write script
        script_name = f"execute_iter{session.iteration}.tcl"
        script_path = session_dir / script_name
        script_path.write_text("\n".join(script_lines))
        result.script_path = str(script_path)
        session.generated_scripts.append(str(script_path))
        
        logger.info(
            f"ECO session {session.session_id} iteration {session.iteration}: "
            f"{result.fixes_applied}/{result.fixes_attempted} fixes applied"
        )
        
        return result
    
    def verify(
        self,
        session: ECOSession,
        check_type: str = "drc",
        error_count_after: int = -1,
        new_errors: Optional[List[str]] = None,
        fixed_errors: Optional[List[str]] = None,
        remaining_errors: Optional[Dict[str, int]] = None,
    ) -> VerificationResult:
        """
        Verify fixes — check if the ECO routing worked.
        
        This generates the verification script. The agent runs the actual
        DRC/LVS check and provides the results back.
        
        Args:
            session: Active ECO session
            check_type: "drc" or "lvs"
            error_count_after: Error count after fixes (-1 to generate script only)
            new_errors: List of newly introduced error rules
            fixed_errors: List of fixed error rules
            remaining_errors: Dict of {rule: count} for remaining errors
            
        Returns:
            VerificationResult
        """
        if not session.setup_done:
            raise RuntimeError("Session not set up. Call setup() first.")
        
        session_dir = self.work_dir / session.session_id
        
        result = VerificationResult(
            session_id=session.session_id,
            check_type=check_type,
            errors_before=session.error_count_before,
            new_errors=new_errors or [],
            fixed_errors=fixed_errors or [],
            remaining_errors=remaining_errors or {},
        )
        
        # Generate verification script
        verify_cmd = self.config.get_command(
            f"verify_{check_type}",
            report_file=str(session_dir / f"{check_type}_report_iter{session.iteration}.rpt"),
            gds_file=str(session_dir / f"{check_type}_iter{session.iteration}.gds"),
            netlist_file=str(session_dir / f"{check_type}_iter{session.iteration}.v"),
        )
        
        pre_hook = self.config.pre_hooks.get("verify", "")
        
        verify_script = ""
        if pre_hook:
            verify_script += f"# Pre-hook\n{pre_hook}\n\n"
        verify_script += verify_cmd
        
        verify_name = f"verify_{check_type}_iter{session.iteration}.tcl"
        verify_path = session_dir / verify_name
        verify_path.write_text(verify_script)
        session.generated_scripts.append(str(verify_path))
        result.report_path = str(
            session_dir / f"{check_type}_report_iter{session.iteration}.rpt"
        )
        
        # Update session state if results provided
        if error_count_after >= 0:
            result.errors_after = error_count_after
            session.error_count_after = error_count_after
            
            if session.error_count_before > 0:
                result.improvement_ratio = (
                    (session.error_count_before - error_count_after)
                    / session.error_count_before
                )
            
            result.is_clean = error_count_after == 0
        
        logger.info(
            f"ECO session {session.session_id} verification ({check_type}): "
            f"{result.errors_after} errors remaining"
        )
        
        return result
    
    def rollback(self, session: ECOSession) -> str:
        """
        Generate rollback script to restore pre-ECO state.
        
        Args:
            session: Active ECO session
            
        Returns:
            Path to rollback script
        """
        session_dir = self.work_dir / session.session_id
        
        rollback_cmd = self.config.get_command(
            "rollback",
            snapshot_name=session.snapshot_name,
            backup_def=str(session_dir / "backup.def"),
        )
        
        rollback_path = session_dir / "rollback.tcl"
        rollback_path.write_text(rollback_cmd)
        session.generated_scripts.append(str(rollback_path))
        
        logger.info(f"ECO session {session.session_id}: rollback script generated")
        
        return str(rollback_path)
    
    def save(self, session: ECOSession) -> str:
        """
        Generate save script to persist current state.
        
        Args:
            session: Active ECO session
            
        Returns:
            Path to save script
        """
        session_dir = self.work_dir / session.session_id
        
        save_cmd = self.config.get_command(
            "save",
            netlist_file=str(session_dir / f"{session.cell_name}_eco.v"),
            gds_file=str(session_dir / f"{session.cell_name}_eco.gds"),
            def_file=str(session_dir / f"{session.cell_name}_eco.def"),
        )
        
        save_path = session_dir / "save.tcl"
        save_path.write_text(save_cmd)
        session.generated_scripts.append(str(save_path))
        
        return str(save_path)
    
    def close(self, session: ECOSession) -> str:
        """
        Generate close script to end ECO session.
        
        Args:
            session: Active ECO session
            
        Returns:
            Path to close script
        """
        close_cmd = self.config.get_command("close")
        
        session_dir = self.work_dir / session.session_id
        close_path = session_dir / "close.tcl"
        close_path.write_text(close_cmd)
        session.generated_scripts.append(str(close_path))
        
        return str(close_path)
    
    def suggest_fixes(
        self,
        analysis: ErrorAnalysis,
        max_suggestions: int = 100,
        min_confidence: float = 0.0,
    ) -> List[FixSuggestion]:
        """
        Convenience: generate fix suggestions from error analysis.
        
        Delegates to FixSuggester.
        """
        return self._suggester.suggest_fixes(
            analysis, max_suggestions, min_confidence
        )
    
    def _generate_fix_command(self, suggestion: FixSuggestion) -> str:
        """Generate tool-specific command for a fix suggestion."""
        action = suggestion.action
        
        # Map action to command template key
        action_to_template = {
            SuggestionAction.INCREASE_SPACING: "fix_spacing",
            SuggestionAction.INCREASE_WIDTH: "fix_width",
            SuggestionAction.REROUTE_NET: "reroute",
            SuggestionAction.ADD_VIA: "add_via",
            SuggestionAction.REMOVE_VIA: "remove_via",
            SuggestionAction.MOVE_CELL: "move_cell",
            SuggestionAction.CELL_RESIZE: "resize_cell",
            SuggestionAction.SWAP_CELL: "swap_cell",
            SuggestionAction.LAYER_CHANGE: "change_layer",
            SuggestionAction.ADD_SHIELD: "add_shield",
            SuggestionAction.DETOUR_AROUND: "detour",
            SuggestionAction.LEGALIZE: "legalize",
        }
        
        template_key = action_to_template.get(action)
        if not template_key:
            # For actions without direct template mapping
            if action == SuggestionAction.MANUAL_REVIEW:
                return (
                    f"# MANUAL REVIEW REQUIRED: {suggestion.error_rule}\n"
                    f"# Objects: {', '.join(suggestion.target_objects[:5])}"
                )
            elif action == SuggestionAction.CUSTOM_COMMAND:
                return suggestion.parameters.get("command", "# Custom command")
            return ""
        
        # Build parameters
        params = {
            "rule": suggestion.error_rule,
            "nets": " ".join(suggestion.target_objects[:20]),
            "layer": suggestion.target_layer,
            "effort": self.config.settings.get("default_effort", "high"),
            "timing_driven": self.config.settings.get("timing_driven", "true"),
        }
        params.update(suggestion.parameters)
        
        # Fill in defaults for missing params
        params.setdefault("location", "0 0")
        params.setdefault("via_type", "default")
        params.setdefault("cell", "")
        params.setdefault("new_master", "")
        params.setdefault("x", "0")
        params.setdefault("y", "0")
        params.setdefault("net", "")
        params.setdefault("region", "")
        params.setdefault("spacing", "0.1")
        
        return self.config.get_command(template_key, **params)
    
    def get_session_summary(self, session: ECOSession) -> str:
        """Generate session summary."""
        lines = [
            f"ECO Session Summary",
            f"{'=' * 60}",
            f"Session ID: {session.session_id}",
            f"Toolchain: {session.toolchain}",
            f"Created: {session.created_at}",
            f"Lib: {session.lib_name}, Cell: {session.cell_name}",
            f"Snapshot: {session.snapshot_name}",
            f"",
            f"Iterations: {session.iteration}",
            f"Fixes applied: {len(session.fixes_applied)}",
            f"Errors before: {session.error_count_before}",
            f"Errors after: {session.error_count_after}",
            f"Errors fixed: {session.errors_fixed}",
            f"",
            f"Generated scripts: {len(session.generated_scripts)}",
        ]
        
        for script in session.generated_scripts:
            lines.append(f"  - {Path(script).name}")
        
        return "\n".join(lines)
