"""Unit tests for doc_templates package."""

import importlib
import json
import os
import tempfile

import pytest

from doc_templates import (
    get_template_info,
    list_templates,
    read_template,
    render_all_defaults,
    render_template,
    render_to_file,
)


class TestDocTemplates:
    def test_list_templates(self):
        names = list_templates()
        assert isinstance(names, list)
        assert "top_level_spec" in names
        assert "module_spec" in names
        assert "test_plan" in names
        assert "test_report" in names

    def test_get_template_info(self):
        info = get_template_info("module_spec")
        assert info.name == "Module / IP Design Specification"
        assert os.path.exists(info.path)

    def test_read_template(self):
        content = read_template("top_level_spec")
        assert "# {{ project_name }}" in content
        assert "## 1. Purpose and Scope" in content

    def test_render_template_fills_variables(self):
        content = render_template(
            "top_level_spec",
            {"project_name": "MySoC", "doc_id": "DOC-001", "version": "1.0"},
        )
        assert "# MySoC — Top-Level Design Specification" in content
        assert "| DOC-001 |" in content
        assert "| 1.0 |" in content

    def test_render_template_preserves_unfilled_placeholders(self):
        content = render_template(
            "module_spec",
            {"module_name": "MyIP"},
        )
        assert "# MyIP — Module Design Specification" in content
        assert "{{ purpose }}" in content
        assert "{{ theory_of_operation }}" in content

    def test_render_template_raises_on_unexpected_key_format(self):
        # Variables that exist should be filled; variables that do not should
        # remain as placeholders.  A malformed placeholder should not crash.
        content = render_template("test_report", {"project_name": "P"})
        assert "# P — Verification Test Report" in content
        assert "{{ dut_name }}" in content

    def test_render_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "out.md")
            render_to_file("test_plan", path, {"project_name": "PlanX"})
            assert os.path.exists(path)
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            assert "# PlanX — Verification Test Plan" in text

    def test_render_all_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = render_all_defaults(tmpdir)
            assert len(paths) == len(list_templates())
            for p in paths:
                assert os.path.exists(p)
                assert os.path.getsize(p) > 0

    def test_unknown_template_raises(self):
        with pytest.raises(KeyError):
            get_template_info("no_such_template")

    def test_earphone_flow_imports_without_entrypoint_failure(self):
        flow = importlib.import_module("earphone.flow")
        assert hasattr(flow, "main")
        assert hasattr(flow, "run_module_layer_tests")
        assert hasattr(flow, "run_module")

    def test_rv32_package_exports_behavior_and_dsl(self):
        from earphone.modules.rv32 import EarphoneRV32, RV32IM_ISS

        assert RV32IM_ISS.__name__ == "RV32IM_ISS"
        assert EarphoneRV32.__name__ == "EarphoneRV32"

    def test_rv32_module_docs_generate_without_stub_feedback(self):
        from earphone.docgen import generate_module_docs

        with tempfile.TemporaryDirectory() as tmpdir:
            output_base = os.path.join(tmpdir, "rv32")
            written = generate_module_docs("rv32", output_base=output_base, strict=True)

            feedback_path = os.path.join(output_base, "specs", "docgen_feedback.json")
            with open(feedback_path, "r", encoding="utf-8") as f:
                feedback = json.load(f)
            markdown = ""
            for path in written:
                if path.endswith(".md"):
                    with open(path, "r", encoding="utf-8") as f:
                        markdown += f.read()

            assert feedback_path in written
            assert feedback["issue_count"] == 0
            assert feedback["blocker_count"] == 0
            assert "TBD" not in markdown
            assert "{{" not in markdown
            assert "See DSL implementation" not in markdown
            assert "RV32-L2_CYCLE-001" in markdown
            assert "RV32-L2_CYCLE-TP-001" in markdown
            assert "RV32-L2_CYCLE-TR-001" in markdown

    def test_docgen_discovers_earphone_modules(self):
        from earphone.docgen import discover_modules

        modules = discover_modules()
        assert "rv32" in modules
        assert "simd16" in modules
        assert "common" not in modules


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
