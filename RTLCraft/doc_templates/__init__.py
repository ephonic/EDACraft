"""Document templates for RTLCraft design and verification artifacts.

This package provides industry-pattern markdown templates for:

- Top-level SoC / subsystem specification
- Module / IP specification
- Verification test plan
- Verification test report

Templates use ``{{ placeholder }}`` syntax and can be rendered with Python's
``str.format()`` or Jinja2.  A lightweight renderer is included for convenience.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


_TEMPLATE_DIR = os.path.dirname(os.path.abspath(__file__))


@dataclass
class TemplateInfo:
    """Metadata for a document template."""

    name: str
    path: str
    description: str
    default_variables: Dict[str, Any] = field(default_factory=dict)


_AVAILABLE_TEMPLATES: Dict[str, TemplateInfo] = {
    "top_level_spec": TemplateInfo(
        name="Top-Level Design Specification",
        path=os.path.join(_TEMPLATE_DIR, "top_level_spec.md"),
        description="SoC or subsystem level design specification.",
    ),
    "module_spec": TemplateInfo(
        name="Module / IP Design Specification",
        path=os.path.join(_TEMPLATE_DIR, "module_spec.md"),
        description="Module or IP block level design specification.",
    ),
    "test_plan": TemplateInfo(
        name="Verification Test Plan",
        path=os.path.join(_TEMPLATE_DIR, "test_plan.md"),
        description="Plan for verifying a DUT at unit/integration/system levels.",
    ),
    "test_report": TemplateInfo(
        name="Verification Test Report",
        path=os.path.join(_TEMPLATE_DIR, "test_report.md"),
        description="Report of verification execution results and sign-off status.",
    ),
    "layer_spec": TemplateInfo(
        name="IR Layer Specification",
        path=os.path.join(_TEMPLATE_DIR, "layer_spec.md"),
        description="Per-IR-layer design specification used inside module directories.",
    ),
}


def list_templates() -> List[str]:
    """Return the names of available templates."""
    return list(_AVAILABLE_TEMPLATES.keys())


def get_template_info(name: str) -> TemplateInfo:
    """Return metadata for a named template."""
    if name not in _AVAILABLE_TEMPLATES:
        raise KeyError(f"Unknown template '{name}'. Available: {list_templates()}")
    return _AVAILABLE_TEMPLATES[name]


def read_template(name: str) -> str:
    """Read the raw markdown content of a template."""
    info = get_template_info(name)
    with open(info.path, "r", encoding="utf-8") as f:
        return f.read()


def render_template(name: str, variables: Optional[Dict[str, Any]] = None) -> str:
    """Render a template with the supplied variables.

    Placeholders of the form ``{{ key }}`` are replaced by ``str.format``.
    Missing keys are left as-is so they can be filled in later.

    Args:
        name: Template name, e.g. ``"module_spec"``.
        variables: Mapping of placeholder names to values.

    Returns:
        Rendered markdown string.
    """
    variables = variables or {}
    content = read_template(name)

    # Normalize ``{{ key }}`` to ``{key}`` for known variables and to a safe
    # sentinel for unknown variables.  This lets us use str.format while
    # preserving unfilled placeholders in the output.
    placeholder_pattern = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
    sentinel = "\x00{}\x00"

    def _replace_placeholder(match: re.Match) -> str:
        key = match.group(1)
        if key in variables:
            return "{" + key + "}"
        return sentinel.format(key)

    content = placeholder_pattern.sub(_replace_placeholder, content)

    try:
        content = content.format(**variables)
    except KeyError as exc:
        raise KeyError(
            f"Template '{name}' requires variable {exc}. "
            f"Supply it in `variables` or leave it as a placeholder."
        ) from exc

    # Restore unfilled placeholders to ``{{ key }}`` form.
    content = re.sub(
        re.escape("\x00") + r"([A-Za-z_][A-Za-z0-9_]*)" + re.escape("\x00"),
        r"{{ \1 }}",
        content,
    )
    content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
    return content


def render_to_file(
    name: str,
    output_path: str,
    variables: Optional[Dict[str, Any]] = None,
) -> None:
    """Render a template and write it to disk."""
    rendered = render_template(name, variables)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered)


def default_variables() -> Dict[str, Any]:
    """Return a dictionary of sensible default values for all templates.

    These defaults populate the document header and common metadata fields.
    """
    today = date.today().isoformat()
    return {
        "project_name": "Project Name",
        "module_name": "Module Name",
        "dut_name": "DUT Name",
        "doc_id": "DOC-000",
        "version": "0.1",
        "date": today,
        "author": "RTLCraft Agent",
        "owner": "Design Team",
        "status": "Draft",
        "purpose": "<!-- Describe the purpose of this document. -->",
        "scope": "<!-- Define the scope. -->",
    }


def render_all_defaults(output_dir: str) -> List[str]:
    """Render every template with default variables and write to ``output_dir``.

    Returns the list of written file paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    defaults = default_variables()
    written: List[str] = []
    for name in list_templates():
        output_path = os.path.join(output_dir, f"{name}.md")
        render_to_file(name, output_path, defaults)
        written.append(output_path)
    return written
