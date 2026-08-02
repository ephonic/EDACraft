"""Compatibility re-export for legacy ``rtlgen.codegen`` imports."""

from rtlgen.dsl.codegen import (
    EmitProfile,
    ModuleDocTemplate,
    VerilogEmitter,
    fill_doc_template,
    inject_doc_all_modules,
    inject_doc_comments,
)

__all__ = [
    "EmitProfile",
    "ModuleDocTemplate",
    "VerilogEmitter",
    "fill_doc_template",
    "inject_doc_all_modules",
    "inject_doc_comments",
]

