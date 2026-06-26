#!/usr/bin/env python3
"""
Demo: PG Network Planning for a Large SoC

This demo shows the PG network advisor analyzing a 2W design
and generating pad placement recommendations.
"""
import tempfile
from pathlib import Path
from src.analysis.pg_network_advisor import (
    PGNetworkAdvisor,
    PowerConfig,
    PadSpec,
    PadType,
    PlacementStrategy,
)

def demo_basic_planning():
    """Basic PG network planning demo."""
    print("=" * 70)
    print("Demo 1: Basic PG Network Planning")
    print("=" * 70)
    print()
    
    # Design parameters
    power_config = PowerConfig(
        vdd_voltage=0.9,
        total_power_w=2.0,
        core_power_w=1.5,
        io_power_w=0.5,
    )
    
    pad_spec = PadSpec(
        pad_type=PadType.PG_PAD,
        width_um=80.0,
        height_um=80.0,
        pitch_um=100.0,
        max_current_a=0.1,
    )
    
    print(f"Design: 2W SoC at 0.9V")
    print(f"Die size: 2900 x 1900 um")
    print(f"Pad size: 80 x 80 um")
    print(f"Max current per pad: 0.1A")
    print()
    
    advisor = PGNetworkAdvisor()
    plan = advisor.plan_pg_network(
        power_config=power_config,
        pad_spec=pad_spec,
        die_width_um=2900.0,
        die_height_um=1900.0,
        num_io_pads=150,
        num_bond_pads=50,
        placement_strategy=PlacementStrategy.UNIFORM,
    )
    
    print(plan.summary)
    print()

def demo_high_power():
    """High-power design demo."""
    print("=" * 70)
    print("Demo 2: High-Power Design (5W)")
    print("=" * 70)
    print()
    
    power_config = PowerConfig(
        vdd_voltage=0.9,
        total_power_w=5.0,
        core_power_w=4.0,
        io_power_w=1.0,
        num_power_domains=2,
        power_domain_names=["VDD_CORE", "VDD_IO"],
    )
    
    pad_spec = PadSpec(
        pad_type=PadType.PG_PAD,
        width_um=100.0,  # Larger pads for high current
        height_um=100.0,
        pitch_um=120.0,
        max_current_a=0.15,
    )
    
    print(f"Design: 5W high-performance SoC at 0.9V")
    print(f"Die size: 4000 x 3000 um")
    print(f"Pad size: 100 x 100 um (larger for high current)")
    print(f"Max current per pad: 0.15A")
    print(f"Power domains: 2 (VDD_CORE, VDD_IO)")
    print()
    
    advisor = PGNetworkAdvisor()
    plan = advisor.plan_pg_network(
        power_config=power_config,
        pad_spec=pad_spec,
        die_width_um=4000.0,
        die_height_um=3000.0,
        num_io_pads=250,
        num_bond_pads=100,
        placement_strategy=PlacementStrategy.CLUSTERED,
    )
    
    print(plan.summary)
    print()

def demo_comparison():
    """Compare different placement strategies."""
    print("=" * 70)
    print("Demo 3: Placement Strategy Comparison")
    print("=" * 70)
    print()
    
    power_config = PowerConfig(
        vdd_voltage=0.9,
        total_power_w=1.5,
    )
    
    pad_spec = PadSpec(
        pad_type=PadType.PG_PAD,
        width_um=80.0,
        height_um=80.0,
        pitch_um=100.0,
        max_current_a=0.1,
    )
    
    strategies = [
        PlacementStrategy.UNIFORM,
        PlacementStrategy.CLUSTERED,
        PlacementStrategy.CORNER,
    ]
    
    advisor = PGNetworkAdvisor()
    
    for strategy in strategies:
        plan = advisor.plan_pg_network(
            power_config=power_config,
            pad_spec=pad_spec,
            die_width_um=2900.0,
            die_height_um=1900.0,
            num_io_pads=100,
            placement_strategy=strategy,
        )
        
        print(f"Strategy: {strategy.value.upper()}")
        print(f"  PG pads: {plan.total_pg_pads_needed}")
        print(f"  IR-drop: {plan.estimated_ir_drop_mv:.2f} mV")
        print(f"  Recommendations: {len(plan.recommendations)}")
        if plan.recommendations:
            print(f"    - {plan.recommendations[0]}")
        print()

def main():
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  PG Network Planning System Demo".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    # Run demos
    demo_basic_planning()
    demo_high_power()
    demo_comparison()
    
    print("=" * 70)
    print("Demo Complete!")
    print("=" * 70)
    print()
    print("Key Takeaways:")
    print("  1. PG pad count is calculated based on power and current limits")
    print("  2. Different placement strategies optimize for different goals")
    print("  3. IR-drop estimation helps validate the design")
    print("  4. System provides actionable recommendations")
    print()
    print("For more information, see PG_NETWORK_GUIDE.md")
    print()

if __name__ == "__main__":
    main()
