"""
Partition Advisor - combines RTL hierarchy + DC metrics for partition decisions
"""
import sys
from pathlib import Path
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.parsers.dc_parser import DCReportParser
from src.analysis.rtl_hierarchy import parse_rtl_files


def analyze_partition(rtl_files: list[str], dc_report_dir: str | None = None) -> dict:
    """
    Analyze design for partition recommendations.
    
    Args:
        rtl_files: List of Verilog file paths
        dc_report_dir: Optional DC report directory
        
    Returns:
        Analysis dict with partition recommendations
    """
    # Parse RTL hierarchy
    graph = parse_rtl_files(rtl_files)
    
    # Parse DC metrics if available
    dc_result = None
    if dc_report_dir and Path(dc_report_dir).exists():
        parser = DCReportParser(dc_report_dir)
        dc_result = parser.parse_all()
    
    # Analyze each module
    analysis = {
        "top": graph.top,
        "total_modules": len(graph.modules),
        "depth": graph.depth(graph.top),
        "modules": {},
        "recommendations": [],
        "dc_metrics": None
    }
    
    # Add DC metrics to analysis if available
    if dc_result:
        analysis["dc_metrics"] = {
            "cell_area": dc_result.cell_area,
            "comb_cells": dc_result.num_comb_cells,
            "seq_cells": dc_result.num_seq_cells,
            "total_cells": dc_result.num_comb_cells + dc_result.num_seq_cells,
            "wns_setup": dc_result.wns_setup,
            "tns_setup": dc_result.tns_setup,
        }
    
    # Find large modules (>100 instances)
    large_modules = []
    for name, mod in graph.modules.items():
        info = {
            "instances": len(mod.instances),
            "children": list(set(m for m, _, _ in mod.instances)),
            "io_bits": mod.total_io_bits,
        }
        
        analysis["modules"][name] = info
        
        # Identify partition candidates
        if len(mod.instances) > 100:
            large_modules.append((name, info))
    
    # Generate recommendations
    for name, info in large_modules:
        # Group children by module type
        child_groups = defaultdict(int)
        for child_name, _, _ in graph.modules[name].instances:
            child_groups[child_name] += 1
        
        # Find repeated structures
        repeated = [(mod, count) for mod, count in child_groups.items() if count > 4]
        
        if repeated:
            recommendation = {
                "module": name,
                "instances": info["instances"],
                "issue": f"Large module with {info['instances']} instances",
                "suggestion": "Consider partitioning by grouping repeated structures",
                "repeated_structures": [
                    {"module": mod, "count": count, "percentage": count / info["instances"] * 100}
                    for mod, count in sorted(repeated, key=lambda x: -x[1])
                ]
            }
            
            # Add DC metrics if available
            if dc_result and dc_result.cell_area:
                recommendation["total_area_um2"] = dc_result.cell_area
                recommendation["total_area_mm2"] = dc_result.cell_area / 1e6
                
            analysis["recommendations"].append(recommendation)
    
    return analysis


def print_analysis(analysis: dict):
    """Pretty print analysis results."""
    print("=" * 80)
    print("PARTITION ANALYSIS")
    print("=" * 80)
    print(f"Top module: {analysis['top']}")
    print(f"Total modules: {analysis['total_modules']}")
    print(f"Hierarchy depth: {analysis['depth']}")
    print()
    
    # Print DC metrics if available
    if analysis["dc_metrics"]:
        dc = analysis["dc_metrics"]
        print("DESIGN METRICS (from DC):")
        print("-" * 80)
        if dc["total_cells"]:
            print(f"Total cells: {dc['total_cells']:,} (comb: {dc['comb_cells']:,}, seq: {dc['seq_cells']:,})")
        if dc["cell_area"]:
            print(f"Cell area: {dc['cell_area']:,.0f} um² ({dc['cell_area']/1e6:.2f} mm²)")
        if dc["wns_setup"] is not None:
            print(f"WNS (setup): {dc['wns_setup']:.3f} ns")
        if dc["tns_setup"] is not None:
            print(f"TNS (setup): {dc['tns_setup']:.3f} ns")
        print()
    
    if not analysis["recommendations"]:
        print("✓ No partitioning needed - design is within tool capacity")
        return
    
    print("PARTITION CANDIDATES:")
    print("-" * 80)
    
    for i, rec in enumerate(analysis["recommendations"], 1):
        print(f"\n{i}. {rec['module']}")
        print(f"   Instances: {rec['instances']}")
        print(f"   Issue: {rec['issue']}")
        print(f"   Suggestion: {rec['suggestion']}")
        
        if "total_area_mm2" in rec:
            print(f"   Total area: {rec['total_area_mm2']:.2f} mm²")
        
        print(f"\n   Repeated structures:")
        for struct in rec["repeated_structures"][:5]:  # Show top 5
            print(f"     - {struct['module']}: {struct['count']}x ({struct['percentage']:.1f}%)")


if __name__ == "__main__":
    import glob
    
    rtl_files = glob.glob("syn/rtl/*.v")
    dc_report_dir = "syn/report"
    
    if not Path(dc_report_dir).exists():
        dc_report_dir = None
    
    analysis = analyze_partition(rtl_files, dc_report_dir)
    print_analysis(analysis)
