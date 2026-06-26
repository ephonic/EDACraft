"""Tests for design partition system."""
import tempfile
from pathlib import Path

from src.analysis.module_graph import (
    ModuleGraph, ModuleNode, ModuleMetrics,
    PartitionDecision, TimingCriticality,
)
from src.analysis.hierarchy_analyzer import HierarchyAnalyzer
from src.analysis.partition_engine import PartitionEngine, PartitionConfig
from src.analysis.floorplan_advisor import FloorplanAdvisor
from src.analysis.sub_partition_advisor import SubPartitionAdvisor
from src.analysis.partition_orchestrator import PartitionOrchestrator


def _build_test_hierarchy() -> ModuleGraph:
    """Build a test hierarchy with 6M gates (exceeds 4M limit)."""
    graph = ModuleGraph(design_name="test_soc")
    graph.gate_limit = 4_000_000

    root = ModuleNode(
        name="test_soc",
        instance_path="test_soc",
        metrics=ModuleMetrics(
            gate_count=0,  # Glue logic
            area_um2=0.0,
            num_ports=200,
            clock_domains=["clk", "clk_mem"],
        ),
    )

    # CPU subsystem: 2.5M gates
    cpu = ModuleNode(
        name="u_cpu",
        instance_path="test_soc/u_cpu",
        metrics=ModuleMetrics(
            gate_count=0,
            area_um2=0.0,
            num_ports=150,
            num_seq_cells=800_000,
            num_comb_cells=1_700_000,
            timing_criticality=TimingCriticality.CRITICAL,
            clock_domains=["clk"],
        ),
    )
    root.add_child(cpu)

    # ALU: 800k gates
    alu = ModuleNode(
        name="u_alu",
        instance_path="test_soc/u_cpu/u_alu",
        metrics=ModuleMetrics(
            gate_count=800_000,
            area_um2=800_000.0,
            num_ports=80,
            timing_criticality=TimingCriticality.CRITICAL,
        ),
    )
    cpu.add_child(alu)

    # Register file: 600k gates
    regfile = ModuleNode(
        name="u_regfile",
        instance_path="test_soc/u_cpu/u_regfile",
        metrics=ModuleMetrics(
            gate_count=600_000,
            area_um2=600_000.0,
            num_ports=120,
        ),
    )
    cpu.add_child(regfile)

    # Control: 500k gates
    control = ModuleNode(
        name="u_control",
        instance_path="test_soc/u_cpu/u_control",
        metrics=ModuleMetrics(
            gate_count=50_000,  # Glue logic
            area_um2=50_000.0,
            num_ports=60,
        ),
    )
    cpu.add_child(control)

    # Cache: 600k gates
    cache = ModuleNode(
        name="u_cache",
        instance_path="test_soc/u_cpu/u_cache",
        metrics=ModuleMetrics(
            gate_count=600_000,
            area_um2=600_000.0,
            num_ports=100,
            num_macros=4,
        ),
    )
    cpu.add_child(cache)

    # Memory subsystem: 2M gates
    mem = ModuleNode(
        name="u_mem",
        instance_path="test_soc/u_mem",
        metrics=ModuleMetrics(
            gate_count=0,
            area_um2=0.0,
            num_ports=128,
            num_macros=8,
            clock_domains=["clk_mem"],
        ),
    )
    root.add_child(mem)

    # Memory controller: 800k gates
    mem_ctrl = ModuleNode(
        name="u_mem_ctrl",
        instance_path="test_soc/u_mem/u_mem_ctrl",
        metrics=ModuleMetrics(
            gate_count=800_000,
            area_um2=800_000.0,
            num_ports=80,
        ),
    )
    mem.add_child(mem_ctrl)

    # SRAM array: 1.2M gates (macro-heavy)
    sram = ModuleNode(
        name="u_sram",
        instance_path="test_soc/u_mem/u_sram",
        metrics=ModuleMetrics(
            gate_count=1_200_000,
            area_um2=1_200_000.0,
            num_ports=64,
            num_macros=8,
        ),
    )
    mem.add_child(sram)

    # Peripherals: 1M gates
    periph = ModuleNode(
        name="u_periph",
        instance_path="test_soc/u_periph",
        metrics=ModuleMetrics(
            gate_count=0,
            area_um2=0.0,
            num_ports=256,
        ),
    )
    root.add_child(periph)

    # UART: 200k gates
    uart = ModuleNode(
        name="u_uart",
        instance_path="test_soc/u_periph/u_uart",
        metrics=ModuleMetrics(
            gate_count=200_000,
            area_um2=200_000.0,
            num_ports=32,
        ),
    )
    periph.add_child(uart)

    # SPI: 300k gates
    spi = ModuleNode(
        name="u_spi",
        instance_path="test_soc/u_periph/u_spi",
        metrics=ModuleMetrics(
            gate_count=300_000,
            area_um2=300_000.0,
            num_ports=48,
        ),
    )
    periph.add_child(spi)

    # GPIO: 500k gates
    gpio = ModuleNode(
        name="u_gpio",
        instance_path="test_soc/u_periph/u_gpio",
        metrics=ModuleMetrics(
            gate_count=50_000,  # Glue logic
            area_um2=50_000.0,
            num_ports=200,
        ),
    )
    periph.add_child(gpio)

    graph.root = root
    return graph


def test_module_graph_basic():
    """Test ModuleGraph basic operations."""
    graph = _build_test_hierarchy()

    assert graph.design_name == "test_soc"
    assert graph.total_gate_count() == 4_600_000
    assert graph.needs_partition() is True  # 6M > 4M limit


def test_module_graph_no_partition_needed():
    """Test ModuleGraph when design fits."""
    graph = ModuleGraph(design_name="small")
    graph.gate_limit = 10_000_000

    root = ModuleNode(
        name="small",
        metrics=ModuleMetrics(gate_count=500_000),
    )
    graph.root = root

    assert graph.needs_partition() is False


def test_module_tree_operations():
    """Test ModuleNode tree operations."""
    root = ModuleNode(name="top")
    child1 = ModuleNode(name="child1", metrics=ModuleMetrics(gate_count=100))
    child2 = ModuleNode(name="child2", metrics=ModuleMetrics(gate_count=200))

    root.add_child(child1)
    root.add_child(child2)

    assert child1.parent == root
    assert len(root.children) == 2
    assert root.total_gate_count() == 300
    assert child1.depth() == 1
    assert root.depth() == 0


def test_hierarchy_analyzer_dc_report():
    """Test hierarchy analyzer with synthetic DC area report."""
    tmpdir = tempfile.mkdtemp()
    report_file = Path(tmpdir) / "area.rpt"

    # Synthetic DC hierarchical area report
    report_text = """
-----------------------------------------------------------
Hierarchy                    Cell Area  Combinational  Sequential
-----------------------------------------------------------
top                          12345.6    5678           1234
  u_cpu                      8000.0     4000           800
    u_alu                    3000.0     2000           200
    u_regfile                2500.0     500            400
  u_mem                      2000.0     200            300
  u_periph                   1000.0     478            134
-----------------------------------------------------------
Total cell area: 12345.6
"""
    report_file.write_text(report_text)

    analyzer = HierarchyAnalyzer()
    graph = analyzer.analyze(dc_area_report=report_file, design_name="top")

    assert graph.root is not None
    assert graph.root.name == "top"
    assert len(graph.root.children) >= 2  # u_cpu, u_mem, u_periph


def test_hierarchy_analyzer_rtl():
    """Test hierarchy analyzer with synthetic RTL."""
    tmpdir = tempfile.mkdtemp()
    rtl_file = Path(tmpdir) / "top.v"

    rtl_text = """
module top (
    input clk,
    input rst,
    input [31:0] data_in,
    output [31:0] data_out
);
    wire [31:0] cpu_out;
    wire [31:0] mem_out;

    cpu u_cpu (
        .clk(clk),
        .rst(rst),
        .data_in(data_in),
        .data_out(cpu_out)
    );

    memory u_mem (
        .clk(clk),
        .addr(cpu_out),
        .data_out(mem_out)
    );

    assign data_out = mem_out;
endmodule

module cpu (
    input clk,
    input rst,
    input [31:0] data_in,
    output [31:0] data_out
);
    wire [31:0] alu_out;

    alu u_alu (
        .a(data_in),
        .b(data_in),
        .out(alu_out)
    );

    assign data_out = alu_out;
endmodule

module alu (
    input [31:0] a,
    input [31:0] b,
    output [31:0] out
);
    assign out = a + b;
endmodule

module memory (
    input clk,
    input [31:0] addr,
    output [31:0] data_out
);
    assign data_out = 32'h0;
endmodule
"""
    rtl_file.write_text(rtl_text)

    analyzer = HierarchyAnalyzer()
    graph = analyzer.analyze(rtl_files=[rtl_file], design_name="top")

    assert graph.root is not None
    assert graph.root.name == "top"


def test_partition_engine_needs_split():
    """Test partition engine detects oversized design."""
    graph = _build_test_hierarchy()
    config = PartitionConfig(gate_limit=4_000_000)
    engine = PartitionEngine(config)

    result = engine.partition(graph)

    # Root should be marked as SPLIT (6M > 4M)
    assert graph.root.decision == PartitionDecision.SPLIT
    assert len(result.split_modules) >= 1


def test_partition_engine_harden_candidates():
    """Test partition engine identifies harden candidates."""
    graph = _build_test_hierarchy()
    config = PartitionConfig(
        gate_limit=4_000_000,
        min_harden_gates=200_000,
    )
    engine = PartitionEngine(config)

    result = engine.partition(graph)

    # Memory subsystem has macros, should be hardened
    mem_node = graph.root.find("u_mem")
    assert mem_node is not None
    assert mem_node.decision == PartitionDecision.HARDEN
    assert mem_node.harden_priority > 0


def test_partition_engine_flatten_critical():
    """Test partition engine flattens critical path modules."""
    graph = _build_test_hierarchy()
    config = PartitionConfig(
        gate_limit=4_000_000,
        critical_path_flatten=True,
    )
    engine = PartitionEngine(config)

    result = engine.partition(graph)

    # ALU is critical, should be flattened
    alu_node = graph.root.find("u_alu")
    assert alu_node is not None
    assert alu_node.decision == PartitionDecision.FLATTEN


def test_partition_engine_split_suggestions():
    """Test partition engine generates split suggestions."""
    graph = _build_test_hierarchy()
    config = PartitionConfig(gate_limit=4_000_000)
    engine = PartitionEngine(config)

    result = engine.partition(graph)

    # Root should have split suggestions
    assert len(graph.root.split_suggestions) > 0


def test_floorplan_advisor():
    """Test floorplan advisor generates placements."""
    graph = _build_test_hierarchy()
    config = PartitionConfig(gate_limit=4_000_000)
    engine = PartitionEngine(config)

    partition_result = engine.partition(graph)

    advisor = FloorplanAdvisor()
    advice = advisor.advise(
        partition_result,
        die_width_um=2900.0,
        die_height_um=1900.0,
    )

    if partition_result.hardened_blocks:
        assert len(advice.block_placements) > 0
        assert advice.die_width_um == 2900.0
        assert advice.die_height_um == 1900.0


def test_sub_partition_advisor():
    """Test sub-partition advisor for oversized module."""
    graph = _build_test_hierarchy()

    advisor = SubPartitionAdvisor(gate_limit=4_000_000)

    # Root is oversized (6M gates)
    advice = advisor.advise(graph.root)

    assert advice.parent_module == "test_soc"
    assert advice.parent_gate_count == 4_600_000
    assert advice.num_splits_needed == 2
    assert len(advice.suggested_partitions) > 0


def test_sub_partition_balanced():
    """Test sub-partition advisor with balanced split."""
    # Create a module with no children (forced balanced split)
    node = ModuleNode(
        name="big_module",
        metrics=ModuleMetrics(gate_count=8_000_000),
    )

    advisor = SubPartitionAdvisor(gate_limit=4_000_000)
    advice = advisor.advise(node)

    assert advice.num_splits_needed == 2
    assert len(advice.suggested_partitions) == 2


def test_partition_orchestrator_end_to_end():
    """Test complete partition workflow."""
    tmpdir = tempfile.mkdtemp()

    # Create synthetic DC area report
    report_file = Path(tmpdir) / "area.rpt"
    report_text = """
-----------------------------------------------------------
Hierarchy                    Cell Area  Combinational  Sequential
-----------------------------------------------------------
top                          6000000.0  3000000        1000000
  u_cpu                      2500000.0  1500000        500000
    u_alu                    800000.0   500000         200000
    u_regfile                600000.0   200000         300000
  u_mem                      2000000.0  800000         400000
  u_periph                   1500000.0  700000         100000
-----------------------------------------------------------
Total cell area: 6000000.0
"""
    report_file.write_text(report_text)

    orchestrator = PartitionOrchestrator(
        gate_limit=4_000_000,
        die_width_um=2900.0,
        die_height_um=1900.0,
    )

    report = orchestrator.run(
        dc_area_report=report_file,
        design_name="top",
    )

    assert report.design_name == "top"
    assert report.total_gates > 0
    assert report.needs_partition is True
    assert report.partition_result is not None
    assert report.summary is not None
    assert len(report.summary) > 0


def test_partition_orchestrator_no_partition():
    """Test partition workflow when no partition needed."""
    tmpdir = tempfile.mkdtemp()

    report_file = Path(tmpdir) / "area.rpt"
    report_text = """
-----------------------------------------------------------
Hierarchy                    Cell Area  Combinational  Sequential
-----------------------------------------------------------
top                          1000000.0  500000         200000
  u_cpu                      600000.0   300000         100000
  u_mem                      400000.0   200000         100000
-----------------------------------------------------------
Total cell area: 1000000.0
"""
    report_file.write_text(report_text)

    orchestrator = PartitionOrchestrator(gate_limit=4_000_000)

    report = orchestrator.run(
        dc_area_report=report_file,
        design_name="top",
    )

    assert report.needs_partition is False


def test_partition_generate_scripts():
    """Test script generation from partition result."""
    tmpdir = tempfile.mkdtemp()
    graph = _build_test_hierarchy()
    config = PartitionConfig(gate_limit=4_000_000)
    engine = PartitionEngine(config)

    partition_result = engine.partition(graph)

    # Generate synthesis script
    script_path = Path(tmpdir) / "partition_synthesis.tcl"
    engine.generate_partition_script(partition_result, script_path)

    assert script_path.exists()
    script_text = script_path.read_text()
    assert "Hierarchical Synthesis Script" in script_text


def test_module_graph_save():
    """Test module graph JSON serialization."""
    tmpdir = tempfile.mkdtemp()
    graph = _build_test_hierarchy()

    json_path = Path(tmpdir) / "graph.json"
    graph.save(json_path)

    assert json_path.exists()
    import json
    data = json.loads(json_path.read_text())
    assert data["design_name"] == "test_soc"
    assert data["total_gates"] == 4_600_000
    assert data["needs_partition"] is True
