#!/usr/bin/env python3
"""
Demo: Design Partition Analysis for a Large SoC

This demo shows the partition system analyzing a 6M gate design that exceeds
the 4M gate tool capacity, and generates partition recommendations.
"""
import tempfile
from pathlib import Path
from src.analysis.partition_orchestrator import PartitionOrchestrator

def create_demo_area_report():
    """Create a realistic DC area report for a large SoC."""
    tmpdir = tempfile.mkdtemp()
    report_file = Path(tmpdir) / "area.rpt"
    
    # Realistic 6M gate SoC with multiple subsystems
    report_text = """
-----------------------------------------------------------
Hierarchy                    Cell Area  Combinational  Sequential
-----------------------------------------------------------
my_soc                       0.0        0              0
  u_cpu                      0.0        0              0
    u_alu                    800000.0   500000         200000
    u_regfile                600000.0   200000         300000
    u_control                500000.0   400000         100000
    u_cache                  600000.0   200000         300000
  u_mem                      0.0        0              0
    u_mem_ctrl               800000.0   600000         200000
    u_sram                   1200000.0  200000         800000
  u_periph                   0.0        0              0
    u_uart                   200000.0   150000         50000
    u_spi                    300000.0   200000         100000
    u_gpio                   500000.0   400000         100000
-----------------------------------------------------------
Total cell area: 6000000.0
"""
    report_file.write_text(report_text)
    return report_file

def main():
    print("=" * 70)
    print("Design Partition Demo: 6M Gate SoC")
    print("=" * 70)
    print()
    
    # Create demo data
    area_report = create_demo_area_report()
    output_dir = tempfile.mkdtemp()
    
    print(f"Design: my_soc")
    print(f"Total gates: ~6,000,000")
    print(f"Tool capacity: 4,000,000 gates")
    print(f"Analysis: Design exceeds capacity, needs partitioning")
    print()
    
    # Run partition analysis
    print("Running partition analysis...")
    orchestrator = PartitionOrchestrator(
        gate_limit=4_000_000,
        die_width_um=2900.0,
        die_height_um=1900.0,
        target_utilization=0.7,
    )
    
    report = orchestrator.run(
        dc_area_report=area_report,
        design_name="my_soc",
    )
    
    # Print summary
    print()
    print(report.summary)
    
    # Generate scripts
    print()
    print("Generating partition scripts...")
    orchestrator.generate_scripts(report, output_dir)
    
    print()
    print("Generated files:")
    for file in Path(output_dir).glob("*"):
        print(f"  - {file.name}")
    
    print()
    print("=" * 70)
    print("Demo complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Review partition_report.rpt for detailed analysis")
    print("2. Use partition_synthesis.tcl for hierarchical synthesis")
    print("3. Use partition_floorplan.tcl for block placement")
    print()

if __name__ == "__main__":
    main()
