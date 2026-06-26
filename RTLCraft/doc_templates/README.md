# RTLCraft Document Templates

This directory contains industry-pattern markdown templates for hardware design and verification documentation.

## Available Templates

| Template | File | Purpose |
|----------|------|---------|
| `top_level_spec` | `top_level_spec.md` | SoC / subsystem design specification |
| `module_spec` | `module_spec.md` | IP / module design specification |
| `test_plan` | `test_plan.md` | Verification test plan |
| `test_report` | `test_report.md` | Verification test report |

## Usage

### Render a Single Template

```python
from doc_templates import render_template, default_variables

variables = default_variables()
variables["project_name"] = "Smart Earphone SoC"
variables["doc_id"] = "DOC-EARPHONE-001"
variables["version"] = "1.0"
variables["author"] = "RTLCraft Agent"

markdown = render_template("top_level_spec", variables)
print(markdown)
```

### Render and Save to File

```python
from doc_templates import render_to_file, default_variables

render_to_file(
    "module_spec",
    "earphone/specs/module_earphone_rv32.md",
    default_variables(),
)
```

### Render All Templates with Defaults

```python
from doc_templates import render_all_defaults

paths = render_all_defaults("generated/docs/templates")
print(paths)
```

## Placeholder Syntax

Templates use ``{{ variable_name }}`` placeholders. Unfilled placeholders are preserved in the output so documents can be incrementally completed.

## Industrial Patterns Followed

- **Top-Level Spec**: document control, references, definitions, system overview, architecture, interfaces, memory map, clock/reset/power, performance/power requirements, verification strategy, register map, deliverables, revision history.
- **Module Spec**: overview, features, interface signals, parameters, functional description, microarchitecture, timing, registers, power management, verification considerations, constraints/assumptions, synthesis notes, deliverables, revision history.
- **Test Plan**: DUT definition, verification strategy, testbench architecture, coverage strategy, directed/random/corner test cases, regression strategy, defect management, schedule, risks, sign-off criteria.
- **Test Report**: executive summary, environment, results by suite/level/priority, coverage results, issue tracking, waivers, regression history, sign-off table, appendices.
