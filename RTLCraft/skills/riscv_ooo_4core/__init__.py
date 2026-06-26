"""riscv_ooo_4core - 4-Core Out-of-Order RISC-V Processor."""
from rtlgen.registry import TemplateRegistry


def __getattr__(name: str):
    """Lazy-load submodules to avoid unnecessary heavy DSL imports."""
    for mod_name in ("dsl_modules", "arch_templates", "functional", "cycle_level", "behaviors"):
        try:
            import importlib

            mod = importlib.import_module(f".{mod_name}", __name__)
            value = getattr(mod, name, None)
            if value is not None:
                return value
        except ImportError:
            pass
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    names = set()
    for mod_name in ("dsl_modules", "arch_templates", "functional", "cycle_level", "behaviors"):
        try:
            import importlib

            mod = importlib.import_module(f".{mod_name}", __name__)
            names.update(dir(mod))
        except ImportError:
            pass
    return sorted(names)
