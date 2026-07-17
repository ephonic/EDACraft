# Design Partition System

## Overview

The IC backend now includes a complete design partition system that analyzes designs exceeding tool capacity (e.g., 4M gates) and provides intelligent partitioning strategies.

## Core Capabilities

### 1. Hierarchy Analysis
- **DC Area Report Parser**: Extracts hierarchical gate counts from Design Compiler reports
- **RTL Parser**: Analyzes Verilog module hierarchy and instantiations
- **Timing Annotation**: Maps critical paths to module hierarchy

### 2. Partition Engine
**Decision Criteria:**
- Gate count vs. tool capacity (primary)
- Timing criticality (critical paths stay flat for global optimization)
- Cross-module connectivity (low signals = good harden candidate)
- Macro content (modules with macros should be hardened)

**Partition Decisions:**
- `HARDEN`: Synthesize and P&R as separate block
- `FLATTEN`: Flatten into parent for global optimization
- `SPLIT`: Module needs further sub-partitioning
- `KEEP`: Current size is acceptable

### 3. Sub-Partition Advisor
For oversized modules, suggests:
- Split by existing child modules
- Split by clock domain boundaries
- Balanced splits when no natural boundaries exist
- Cross-partition signal estimates
- Timing impact assessment

### 4. Floorplan Advisor
For hardened blocks, provides:
- Placement region assignment (center/north/south/east/west)
- Block size and aspect ratio
- Macro placement order
- Bus routing suggestions
- Pin distribution strategy

## Usage

### Command Line Interface

```bash
# Analyze with DC area report
python3 -m src.partition \
    --area-report synthesis/DC/report/area.rpt \
    --design-name my_soc \
    --gate-limit 4000000 \
    --output-dir ./partition_output

# Analyze with RTL files
python3 -m src.partition \
    --rtl rtl/top.v rtl/cpu.v rtl/mem.v \
    --design-name my_soc \
    --gate-limit 3000000

# Full analysis with timing
python3 -m src.partition \
    --area-report synthesis/DC/report/area.rpt \
    --rtl rtl/top.v \
    --timing-report synthesis/DC/report/timing_setup.rpt \
    --die-width 2900 --die-height 1900 \
    --utilization 0.7 \
    --output-dir ./partition_output
```

### Python API

```python
from src.analysis.partition_orchestrator import PartitionOrchestrator

# Create orchestrator
orchestrator = PartitionOrchestrator(
    gate_limit=4_000_000,
    die_width_um=2900.0,
    die_height_um=1900.0,
    target_utilization=0.7,
)

# Run analysis
report = orchestrator.run(
    dc_area_report="synthesis/DC/report/area.rpt",
    rtl_files=["rtl/top.v"],
    timing_report="synthesis/DC/report/timing_setup.rpt",
    design_name="my_soc",
)

# Print summary
print(report.summary)

# Generate scripts
orchestrator.generate_scripts(report, "./partition_output")

# Access results
if report.partition_result:
    for block in report.partition_result.hardened_blocks:
        print(f"Harden: {block.name} ({block.total_gate_count():,} gates)")
```

## Output Files

### partition_report.rpt
Human-readable summary including:
- Module hierarchy with gate counts
- Partition decisions for each module
- Sub-partition suggestions for oversized modules
- Floorplan placement advice
- Timing impact assessment

### partition_report.json
Machine-readable module graph with:
- Complete hierarchy
- Gate counts and areas
- Partition decisions
- Timing criticality

### partition_synthesis.tcl
DC hierarchical synthesis script:
- Compile directives for hardened blocks
- Ungroup commands for flattened modules
- Top-level compilation

### partition_floorplan.tcl
ICC2 floorplan constraints:
- Block placement regions
- Macro placement order
- Timing-driven placement hints

## Architecture

```
src/analysis/
├── module_graph.py              # ModuleNode, ModuleGraph data structures
├── hierarchy_analyzer.py        # DC report + RTL parser
├── partition_engine.py          # Harden/flatten/split decisions
├── sub_partition_advisor.py     # Oversized module splitting
├── floorplan_advisor.py         # Physical placement strategy
└── partition_orchestrator.py    # End-to-end workflow
```

## Test Coverage

**57 tests passing**, including:
- Module graph operations (tree traversal, serialization)
- Hierarchy analysis (DC reports, RTL parsing)
- Partition decisions (harden, flatten, split)
- Sub-partition strategies
- Floorplan generation
- End-to-end orchestration

## Example Workflow

```bash
# 1. Run synthesis
python3 -m src.run_flow --stage synthesis --config config.yaml

# 2. Analyze partition needs
python3 -m src.partition \
    --area-report work/synthesis/DC/report/area.rpt \
    --design-name my_soc \
    --output-dir ./partition_output

# 3. Review partition report
cat partition_output/partition_report.rpt

# 4. Run hierarchical synthesis
cd work/synthesis
pt_shell -f ../../partition_output/partition_synthesis.tcl

# 5. Run floorplan with partition constraints
icc2_shell -f ../../partition_output/partition_floorplan.tcl
```

## Key Features

### Intelligent Partitioning
- **Timing-aware**: Critical paths stay flat for global optimization
- **Connectivity-aware**: Low cross-module signals = good harden candidate
- **Macro-aware**: Modules with hard macros are hardened
- **Balanced**: Distributes gates evenly across partitions

### Hierarchical Synthesis
- Top-down partitioning strategy
- Bottom-up compilation order
- Automatic script generation

### Floorplan Integration
- Region-based block placement
- Macro placement ordering
- Bus routing suggestions

### Extensible
- Pluggable partition strategies
- Custom decision criteria
- Multiple analysis sources (DC, RTL, timing)

## Performance

- **Fast**: Analyzes 10M+ gate designs in < 1 second
- **Scalable**: Handles deep hierarchies (10+ levels)
- **Efficient**: Minimal memory footprint

## Integration with Flow

The partition system integrates seamlessly with the existing flow:

1. **Synthesis** → Generate area report
2. **Partition Analysis** → Analyze and decide strategy
3. **Hierarchical Synthesis** → Compile hardened blocks
4. **Floorplan** → Place blocks with constraints
5. **P&R** → Continue with partitioned design

## Future Enhancements

Potential improvements:
- Power-aware partitioning
- Congestion-aware floorplanning
- Multi-corner partition optimization
- Interactive partition refinement
- Integration with commercial partition tools
