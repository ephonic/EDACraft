"""skills.noc — 8x8 mesh Network-on-Chip with XY routing."""


def __getattr__(name: str):
    """Lazy-load submodules to avoid circular import with rtlgen."""
    for _mod_name in ("dsl_modules", "models", "behaviors", "arch_templates", "skeleton_templates"):
        try:
            import importlib
            mod = importlib.import_module(f".{_mod_name}", __name__)
            val = getattr(mod, name, None)
            if val is not None:
                return val
        except ImportError:
            pass
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    """List available attributes for tab completion."""
    names = set()
    for _mod_name in ("dsl_modules", "models", "behaviors", "arch_templates", "skeleton_templates"):
        try:
            import importlib
            mod = importlib.import_module(f".{_mod_name}", __name__)
            names.update(dir(mod))
        except ImportError:
            pass
    return sorted(names)
