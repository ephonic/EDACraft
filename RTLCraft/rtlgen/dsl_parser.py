"""
rtlgen.dsl_parser — Load Python DSL code into Module AST.

DSL files are plain Python — this module provides two paths:
1. load_dsl_module(filepath) — direct import via importlib (preferred)
2. parse_dsl_code(code_text) — exec with custom namespace (for LLM responses)
"""
from __future__ import annotations

import ast
import importlib.util
import re
import textwrap
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ParseResult:
    """Result of DSL code parsing."""
    success: bool = False
    module: Any = None  # RTLCraft Module instance
    module_name: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    line_count: int = 0


def extract_code_block(text: str) -> str:
    """Extract Python code from markdown code block.

    Handles:
    - ```python ... ``` blocks
    - Plain text (no code block markers)
    - Multiple code blocks (returns first class definition found)
    """
    # Try to extract from ```python ... ``` blocks
    pattern = r'```python\s*\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    if matches:
        return "\n\n".join(matches)

    # Try generic ``` ... ``` blocks
    pattern2 = r'```\s*\n(.*?)```'
    matches2 = re.findall(pattern2, text, re.DOTALL)
    if matches2:
        return "\n\n".join(matches2)

    # No code block — return raw text
    return text


def sanitize_dsl_code(code: str) -> str:
    """Sanitize DSL code for safe evaluation.

    - Removes imports (we provide our own namespace)
    - Removes test code after class definitions
    - Removes non-DSL Python code
    """
    lines = code.split("\n")
    result_lines = []
    in_class = False
    class_indent = 0

    for line in lines:
        stripped = line.strip()

        # Skip imports
        if stripped.startswith("import ") or stripped.startswith("from "):
            continue

        # Skip comments-only lines at top level
        if not in_class and stripped.startswith("#"):
            continue

        # Skip print statements
        if stripped.startswith("print("):
            continue

        # Detect class definition start
        if stripped.startswith("class ") and "(Module)" in stripped:
            in_class = True
            class_indent = len(line) - len(line.lstrip())
            result_lines.append(line)
            continue

        # If in class, include the code
        if in_class:
            # Check if we've exited the class (back to top-level)
            if line.strip() and not line[0].isspace() and not line[0].isspace():
                in_class = False
                continue

            result_lines.append(line)

    return "\n".join(result_lines)


def load_dsl_module(filepath: str, module_name: Optional[str] = None) -> ParseResult:
    """Load a DSL Python file directly via importlib.

    Since DSL files are plain Python with correct imports from rtlgen.core,
    they can be imported as regular modules — no exec or sanitization needed.

    Args:
        filepath: Path to the .py DSL file
        module_name: Optional expected module name (for validation)

    Returns:
        ParseResult with Module instance or errors
    """
    result = ParseResult()

    try:
        spec = importlib.util.spec_from_file_location("dsl_mod", filepath)
        if spec is None or spec.loader is None:
            result.errors.append(f"Cannot load module from {filepath}")
            return result

        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:
        result.errors.append(f"Import error: {e}")
        return result

    # Find the Module subclass
    from rtlgen.core import Module
    for name, obj in vars(mod).items():
        if isinstance(obj, type) and issubclass(obj, Module) and obj is not Module:
            try:
                result.module = obj(name=module_name) if module_name else obj()
                result.module_name = obj.__name__
                result.success = True
                return result
            except Exception as e:
                result.errors.append(f"Instantiation error: {e}")
                return result

    result.errors.append("No Module subclass found in DSL file")
    return result


def parse_dsl_code(code: str, module_name: Optional[str] = None) -> ParseResult:
    """Parse DSL code text and return a Module instance.

    Args:
        code: Python DSL code text (raw or in markdown block)
        module_name: Optional expected module name

    Returns:
        ParseResult with Module instance or errors
    """
    result = ParseResult()

    # Extract code from markdown block
    code = extract_code_block(code)
    if not code.strip():
        result.errors.append("No code found in input text")
        return result

    result.line_count = code.count("\n") + 1

    # Sanitize code
    code = sanitize_dsl_code(code)
    if not code.strip():
        result.errors.append("No class definition found after sanitization")
        return result

    # Verify it's valid Python syntax before executing
    try:
        ast.parse(code)
    except SyntaxError as e:
        result.errors.append(f"Syntax error in generated code: {e}")
        return result

    # Find the class name
    try:
        tree = ast.parse(code)
        class_names = [
            node.name for node in ast.iter_child_nodes(tree)
            if isinstance(node, ast.ClassDef)
        ]
        if not class_names:
            result.errors.append("No class definition found in code")
            return result
        class_name = class_names[0]
        result.module_name = class_name
    except Exception as e:
        result.errors.append(f"Failed to parse class definition: {e}")
        return result

    # Build safe evaluation namespace with DSL imports
    from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const
    from rtlgen.logic import If, Else, Elif, Switch, Mux, Cat, Rep, SRA

    safe_globals = {
        "Module": Module,
        "Input": Input,
        "Output": Output,
        "Wire": Wire,
        "Reg": Reg,
        "Array": Array,
        "Const": Const,
        "If": If,
        "Else": Else,
        "Elif": Elif,
        "Switch": Switch,
        "Mux": Mux,
        "Cat": Cat,
        "Rep": Rep,
        "SRA": SRA,
        "__builtins__": {
            "__build_class__": __build_class__,
            "__name__": "dsl_generated",
            "len": len,
            "range": range,
            "max": max,
            "min": min,
            "sum": sum,
            "abs": abs,
            "int": int,
            "str": str,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "True": True,
            "False": False,
            "None": None,
            "enumerate": enumerate,
            "zip": zip,
            "sorted": sorted,
            "isinstance": isinstance,
            "hasattr": hasattr,
            "getattr": getattr,
            "setattr": setattr,
            "super": super,
            "property": property,
        },
    }

    # Execute the code
    try:
        exec(code, safe_globals)
    except Exception as e:
        result.errors.append(f"Execution error: {e}")
        return result

    # Instantiate the module class
    try:
        cls = safe_globals.get(class_name)
        if cls is None:
            result.errors.append(f"Class '{class_name}' not found after execution")
            return result

        # Create instance with optional name override; fall back to no-arg
        try:
            module_instance = cls(name=module_name) if module_name else cls()
        except TypeError:
            # Module __init__ doesn't accept 'name' kwarg — fall back
            module_instance = cls()

        result.module = module_instance
        result.success = True
    except Exception as e:
        result.errors.append(f"Instantiation error: {e}")
        return result

    return result


def parse_batch_dsl_code(text: str) -> List[ParseResult]:
    """Parse multiple DSL modules from a single batch response.

    Splits on code block boundaries and parses each separately.
    """
    results: List[ParseResult] = []

    # Split on class definitions
    # Find all class definitions
    pattern = r'class\s+(\w+)\s*\(Module\)'
    class_positions = [(m.start(), m.group(1)) for m in re.finditer(pattern, text)]

    if not class_positions:
        # Try to parse as single module
        return [parse_dsl_code(text)]

    for i, (pos, class_name) in enumerate(class_positions):
        if i < len(class_positions) - 1:
            next_pos = class_positions[i + 1][0]
            code = text[pos:next_pos]
        else:
            code = text[pos:]

        result = parse_dsl_code(code, module_name=class_name)
        results.append(result)

    return results
