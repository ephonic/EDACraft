"""
rtlgen.params — Centralized Configuration System

Inspired by XiangShan's Parameters pattern (XSCoreParameters + HasXSParameter),
this module provides a hierarchical, type-safe configuration system for
processor and IP design.

Key concepts:
  - ConfigSpec: A flat key-value specification of all parameters.
  - ConfigGroup: A named subset of parameters (e.g., "frontend", "backend").
  - Config: Composed configuration with groups and inheritance.
  - ParamAccessor: Mixin that gives modules typed access to parameters.

Usage:
    from rtlgen.params import ConfigSpec, Config

    spec = ConfigSpec(
        xlen=64,
        fetch_width=8,
        decode_width=6,
        rob_size=256,
        nr_phy_regs=192,
    )
    cfg = Config(spec)
    print(cfg.xlen)  # 64
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Union


# ============================================================================
# ConfigSpec — Flat key-value parameter specification
# ============================================================================

@dataclass
class ConfigSpec:
    """Flat key-value parameter specification.

    Each key represents a design parameter. Values can be int, float, bool,
    str, or any serializable type.

    Parameters are organized into implicit groups by naming convention:
        "frontend_<name>" → frontend group
        "backend_<name>"  → backend group
        "cache_<name>"    → cache group
        No prefix         → top-level group
    """

    _values: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Support kwargs-based construction
        if not self._values:
            object.__setattr__(self, "_values", {})

    def get(self, key: str, default: Any = None) -> Any:
        return self._values.get(key, default)

    def set(self, key: str, value: Any) -> "ConfigSpec":
        self._values[key] = value
        return self

    def has(self, key: str) -> bool:
        return key in self._values

    def keys(self):
        return self._values.keys()

    def items(self):
        return self._values.items()

    def group(self, prefix: str) -> Dict[str, Any]:
        """Get all parameters with the given prefix.

        Returns dict with prefix stripped from keys.
        """
        pfx = prefix.rstrip("_") + "_"
        return {
            k[len(pfx):]: v
            for k, v in self._values.items()
            if k.startswith(pfx)
        }

    def subset(self, keys: List[str]) -> "ConfigSpec":
        """Create a new ConfigSpec with only the specified keys."""
        return ConfigSpec(
            _values={k: self._values[k] for k in keys if k in self._values}
        )

    def merge(self, other: "ConfigSpec") -> "ConfigSpec":
        """Merge another ConfigSpec, overriding with other's values."""
        merged = ConfigSpec(_values=dict(self._values))
        merged._values.update(other._values)
        return merged

    def derive(self, **overrides) -> "ConfigSpec":
        """Create a new ConfigSpec with overrides."""
        merged = dict(self._values)
        merged.update(overrides)
        return ConfigSpec(_values=merged)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            return object.__getattribute__(self, name)
        if name in self._values:
            return self._values[name]
        raise AttributeError(f"ConfigSpec has no parameter '{name}'")

    def __setattr__(self, name: str, value: Any):
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            self._values[name] = value

    def __repr__(self) -> str:
        return f"ConfigSpec({self._values!r})"

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._values)

    def validate(self, rules: Optional[Dict[str, Callable]] = None) -> List[str]:
        """Validate parameters against rules.

        Args:
            rules: {param_name: validator_fn} — returns True if valid

        Returns:
            List of validation error messages (empty = all valid)
        """
        errors: List[str] = []
        if rules is None:
            return errors
        for param, fn in rules.items():
            if param in self._values:
                try:
                    if not fn(self._values[param]):
                        errors.append(
                            f"Validation failed for '{param}': "
                            f"value={self._values[param]!r}"
                        )
                except Exception as e:
                    errors.append(f"Validation error for '{param}': {e}")
        return errors


# ============================================================================
# Pre-built Parameter Templates
# ============================================================================

class PresetSpecs:
    """Pre-built ConfigSpec templates for common configurations."""

    @staticmethod
    def rv32_core() -> ConfigSpec:
        return ConfigSpec(
            _values={
                "isa": "riscv",
                "xlen": 32,
                "flen": 32,
                "m_extension": True,
                "c_extension": False,
                # Frontend
                "fetch_width": 2,
                "predict_width": 4,
                "btb_entries": 64,
                "bht_entries": 512,
                "ras_entries": 16,
                "ibuf_size": 16,
                # Backend
                "decode_width": 2,
                "rename_width": 2,
                "dispatch_width": 2,
                "rob_size": 32,
                "nr_phy_regs": 64,
                "issue_queue_size": 8,
                # Execution
                "alu_pipes": 1,
                "mul_pipe": True,
                "div_pipe": False,
                "fpu_pipes": 0,
                # Memory
                "load_pipes": 1,
                "store_pipes": 1,
                "lq_size": 16,
                "sq_size": 16,
                # Commit
                "commit_width": 2,
                # Interconnect
                "interconnect_type": "handshake",
                # Process
                "tech_node": "28nm",
                "target_freq_mhz": 1000,
            }
        )

    @staticmethod
    def rv64_core() -> ConfigSpec:
        return PresetSpecs.rv32_core().derive(
            xlen=64,
            flen=64,
            fetch_width=4,
            decode_width=4,
            dispatch_width=4,
            rob_size=128,
            nr_phy_regs=128,
            alu_pipes=2,
            div_pipe=True,
            fpu_pipes=1,
            load_pipes=2,
            store_pipes=2,
            commit_width=4,
        )

    @staticmethod
    def high_perf_core() -> ConfigSpec:
        """XiangShan-like high-performance core."""
        return PresetSpecs.rv64_core().derive(
            fetch_width=8,
            decode_width=6,
            rename_width=6,
            dispatch_width=6,
            rob_size=256,
            nr_phy_regs=192,
            issue_queue_size=16,
            alu_pipes=4,
            mul_pipe=True,
            div_pipe=True,
            fpu_pipes=4,
            load_pipes=2,
            store_pipes=2,
            lq_size=80,
            sq_size=64,
            commit_width=6,
            ibuf_size=48,
            tech_node="7nm",
            target_freq_mhz=2000,
        )

    @staticmethod
    def embedded_core() -> ConfigSpec:
        """Minimal embedded core (in-order, single issue)."""
        return ConfigSpec(
            _values={
                "isa": "riscv",
                "xlen": 32,
                "m_extension": True,
                "c_extension": True,
                "fetch_width": 1,
                "decode_width": 1,
                "dispatch_width": 1,
                "rob_size": 0,  # in-order, no ROB
                "nr_phy_regs": 32,  # architectural regs only
                "issue_queue_size": 0,
                "alu_pipes": 1,
                "mul_pipe": False,
                "div_pipe": False,
                "fpu_pipes": 0,
                "load_pipes": 1,
                "store_pipes": 1,
                "commit_width": 1,
                "tech_node": "65nm",
                "target_freq_mhz": 200,
            }
        )


# ============================================================================
# Config — Named, hierarchical configuration
# ============================================================================

@dataclass
class Config:
    """Named configuration built from a ConfigSpec.

    Provides dot-access to parameters and group-based access.

    Example:
        cfg = Config(PresetSpecs.rv64_core())
        print(cfg.xlen)           # 64
        print(cfg.group("cache")) # {size: 32768, ...}
    """

    name: str = "default"
    spec: ConfigSpec = field(default_factory=ConfigSpec)
    _parent: Optional["Config"] = field(default=None, repr=False)

    def get(self, key: str, default: Any = None) -> Any:
        if self.spec.has(key):
            return self.spec.get(key)
        if self._parent is not None:
            return self._parent.get(key, default)
        return default

    def has(self, key: str) -> bool:
        if self.spec.has(key):
            return True
        if self._parent is not None:
            return self._parent.has(key)
        return False

    def group(self, prefix: str) -> Dict[str, Any]:
        """Get parameters with the given prefix."""
        result = self.spec.group(prefix)
        if self._parent is not None:
            for k, v in self._parent.group(prefix).items():
                result.setdefault(k, v)
        return result

    def derive(self, name: str, **overrides) -> "Config":
        """Create a child config with overrides."""
        child_spec = self.spec.derive(**overrides)
        return Config(name=name, spec=child_spec, _parent=self)

    def to_dict(self) -> Dict[str, Any]:
        result = dict(self._parent.to_dict()) if self._parent else {}
        result.update(self.spec.to_dict())
        return result

    def summary(self) -> str:
        lines = [f"Config: {self.name}"]
        lines.append("-" * 40)
        for k, v in sorted(self.spec.to_dict().items()):
            lines.append(f"  {k:<25} {v}")
        if self._parent:
            lines.append(f"  (parent: {self._parent.name})")
        return "\n".join(lines)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            return object.__getattribute__(self, name)
        val = self.get(name)
        if val is not None:
            return val
        raise AttributeError(f"Config '{self.name}' has no parameter '{name}'")

    def __repr__(self) -> str:
        return f"Config('{self.name}', {len(self.spec.to_dict())} params)"


# ============================================================================
# ParamAccessor — Mixin for modules to access configuration
# ============================================================================

class ParamAccessor:
    """Mixin that gives a module typed access to a Config.

    Usage:
        class MyModule(Module, ParamAccessor):
            def __init__(self, cfg: Config):
                super().__init__("my_mod")
                self.init_params(cfg)
                xlen = self.param("xlen")
                fetch = self.param("fetch_width")
    """

    _config: Optional[Config] = None
    _param_prefix: str = ""

    def init_params(self, cfg: Config, prefix: str = ""):
        """Initialize parameter access with a Config."""
        self._config = cfg
        self._param_prefix = prefix

    def param(self, name: str, default: Any = None) -> Any:
        """Get a parameter value."""
        if self._config is None:
            raise RuntimeError("ParamAccessor not initialized. Call init_params() first.")
        key = f"{self._param_prefix}{name}" if self._param_prefix else name
        return self._config.get(key, default)

    def param_int(self, name: str, default: int = 0) -> int:
        return int(self.param(name, default))

    def param_bool(self, name: str, default: bool = False) -> bool:
        return bool(self.param(name, default))

    def has_param(self, name: str) -> bool:
        key = f"{self._param_prefix}{name}" if self._param_prefix else name
        if self._config is None:
            return False
        return self._config.has(key)

    def param_group(self, prefix: str) -> Dict[str, Any]:
        return self._config.group(prefix)

    def config_summary(self) -> str:
        if self._config is None:
            return "(no config)"
        return self._config.summary()


# ============================================================================
# PEParams — ProcessingElement-specific parameter builder
# ============================================================================

class PEParams:
    """Parameter builder for ProcessingElement configurations.

    Provides a fluent interface for defining PE parameters with validation.

    Example:
        params = (PEParams("IFU")
            .xlen(64)
            .fetch_width(3)
            .btb(64)
            .bht(512)
            .ras(16)
            .build())
    """

    def __init__(self, pe_name: str):
        self._name = pe_name
        self._values: Dict[str, Any] = {}

    def xlen(self, v: int) -> "PEParams":
        self._values["xlen"] = v
        return self

    def fetch_width(self, v: int) -> "PEParams":
        self._values["fetch_width"] = v
        return self

    def dispatch_width(self, v: int) -> "PEParams":
        self._values["dispatch_width"] = v
        return self

    def rob_size(self, v: int) -> "PEParams":
        self._values["rob_size"] = v
        return self

    def phy_regs(self, v: int) -> "PEParams":
        self._values["nr_phy_regs"] = v
        return self

    def alu_pipes(self, v: int) -> "PEParams":
        self._values["alu_pipes"] = v
        return self

    def load_pipes(self, v: int) -> "PEParams":
        self._values["load_pipes"] = v
        return self

    def store_pipes(self, v: int) -> "PEParams":
        self._values["store_pipes"] = v
        return self

    def btb(self, v: int) -> "PEParams":
        self._values["btb_entries"] = v
        return self

    def bht(self, v: int) -> "PEParams":
        self._values["bht_entries"] = v
        return self

    def ras(self, v: int) -> "PEParams":
        self._values["ras_entries"] = v
        return self

    def ibuf(self, v: int) -> "PEParams":
        self._values["ibuf_size"] = v
        return self

    def lq_size(self, v: int) -> "PEParams":
        self._values["lq_size"] = v
        return self

    def sq_size(self, v: int) -> "PEParams":
        self._values["sq_size"] = v
        return self

    def tech_node(self, v: str) -> "PEParams":
        self._values["tech_node"] = v
        return self

    def target_freq(self, v: int) -> "PEParams":
        self._values["target_freq_mhz"] = v
        return self

    def commit_width(self, v: int) -> "PEParams":
        self._values["commit_width"] = v
        return self

    def rename_width(self, v: int) -> "PEParams":
        self._values["rename_width"] = v
        return self

    def issue_queue_size(self, v: int) -> "PEParams":
        self._values["issue_queue_size"] = v
        return self

    def fpu_pipes(self, v: int) -> "PEParams":
        self._values["fpu_pipes"] = v
        return self

    def div_pipe(self, v: int) -> "PEParams":
        self._values["div_pipe"] = v
        return self

    def mul_pipe(self, v: int) -> "PEParams":
        self._values["mul_pipe"] = v
        return self

    def set(self, key: str, value: Any) -> "PEParams":
        self._values[key] = value
        return self

    def build(self) -> ConfigSpec:
        return ConfigSpec(_values=dict(self._values))

    def to_config(self, name: str = "") -> Config:
        return Config(name=name or self._name, spec=self.build())

    def __repr__(self) -> str:
        return f"PEParams('{self._name}', {len(self._values)} params)"
