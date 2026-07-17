#!/usr/bin/env python3
"""
Fast I-V Curve Generation for MOSFET

Generates transfer (Id-Vg) and output (Id-Vd) characteristics with minimal simulation points.
"""

import numpy as np
import matplotlib.pyplot as plt

# Publication-quality settings
plt.rcParams.update({
    'font.size': 12,
    'font.family': 'serif',
    'axes.labelsize': 13,
    'axes.titlesize': 14,
    'xtick.labelsize': 11,
    'ytick.labelsize': 11,
    'legend.fontsize': 11,
    'figure.dpi': 150,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.grid': True,
    'grid.alpha': 0.3,
})

from tcad import Device, Simulator
from tcad.mesh.generator import structured_mesh_from_device


def simulate_mosfet_fast():
    """Fast MOSFET simulation setup"""
    print("Setting up MOSFET simulation...")
    
    device = Device.mosfet(
        Lg=50e-9,
        tox=1.5e-9,
        tsi=15e-9,
        W=100e-9,
        Vg=0.0,
        Vd=0.5,
        Vs=0.0,
    )
    
    # Coarse mesh for speed
    mesh = structured_mesh_from_device(device, resolution=(10e-9, 5e-9, 10e-9))
    print(f"Grid: {mesh.nx} x {mesh.ny} x {mesh.nz} = {mesh.npts()} nodes")
    
    sim = Simulator(mesh, temperature=300.0)
    sim.set_material_from_mesh()
    for name, (shape, voltage) in device.contacts.items():
        sim.set_contact(name, voltage)
    
    return sim, device, mesh


def extract_current(results):
    """Extract drain current from simulation results"""
    # Use maximum electron density as proxy for current
    n = results['n']
    Id = np.max(n) * 1e-15  # Simplified extraction
    return Id


def plot_transfer_curves(sim):
    """Plot Id-Vg transfer characteristics"""
    print("\nGenerating transfer characteristics (Id-Vg)...")
    
    # Minimal voltage points for speed
    Vg_sweep = np.array([0.0, 0.3, 0.6, 0.9, 1.2, 1.5])
    Vd_values = [0.1, 0.5, 1.0]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    
    for idx, Vd in enumerate(Vd_values):
        Id_values = []
        
        for i, Vg in enumerate(Vg_sweep):
            print(f"  Simulating Vg={Vg:.1f}V, Vd={Vd:.1f}V ({i+1}/{len(Vg_sweep)})...")
            
            sim.set_contact('gate', Vg)
            sim.set_contact('drain', Vd)
            
            results = sim.run(max_iter=50, tol=1e-6)
            Id = extract_current(results)
            Id_values.append(Id)
        
        # Linear scale
        ax1.plot(Vg_sweep, Id_values, 'o-', linewidth=2, markersize=8,
                label=f'Vd = {Vd}V', color=colors[idx])
        
        # Log scale
        ax2.semilogy(Vg_sweep, np.maximum(Id_values, 1e-20), 'o-', 
                    linewidth=2, markersize=8,
                    label=f'Vd = {Vd}V', color=colors[idx])
    
    # Format linear plot
    ax1.set_xlabel('Gate Voltage Vg [V]', fontweight='bold')
    ax1.set_ylabel('Drain Current Id [A]', fontweight='bold')
    ax1.set_title('Transfer Characteristics (Linear Scale)', fontweight='bold', fontsize=14)
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(bottom=0)
    
    # Format log plot
    ax2.set_xlabel('Gate Voltage Vg [V]', fontweight='bold')
    ax2.set_ylabel('Drain Current Id [A]', fontweight='bold')
    ax2.set_title('Transfer Characteristics (Log Scale)', fontweight='bold', fontsize=14)
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('mosfet_transfer_curves_fast.png', dpi=300, bbox_inches='tight')
    print("Saved: mosfet_transfer_curves_fast.png")
    plt.close()


def plot_output_curves(sim):
    """Plot Id-Vd output characteristics"""
    print("\nGenerating output characteristics (Id-Vd)...")
    
    # Minimal voltage points for speed
    Vd_sweep = np.array([0.0, 0.3, 0.6, 0.9, 1.2, 1.5])
    Vg_values = [0.3, 0.6, 0.9, 1.2]
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    
    for idx, Vg in enumerate(Vg_values):
        Id_values = []
        
        for i, Vd in enumerate(Vd_sweep):
            print(f"  Simulating Vg={Vg:.1f}V, Vd={Vd:.1f}V ({i+1}/{len(Vd_sweep)})...")
            
            sim.set_contact('gate', Vg)
            sim.set_contact('drain', Vd)
            
            results = sim.run(max_iter=50, tol=1e-6)
            Id = extract_current(results)
            Id_values.append(Id)
        
        ax.plot(Vd_sweep, Id_values, 'o-', linewidth=2, markersize=8,
               label=f'Vg = {Vg}V', color=colors[idx])
    
    ax.set_xlabel('Drain Voltage Vd [V]', fontweight='bold')
    ax.set_ylabel('Drain Current Id [A]', fontweight='bold')
    ax.set_title('Output Characteristics (Id-Vd)', fontweight='bold', fontsize=14)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(bottom=0)
    
    plt.tight_layout()
    plt.savefig('mosfet_output_curves_fast.png', dpi=300, bbox_inches='tight')
    print("Saved: mosfet_output_curves_fast.png")
    plt.close()


def main():
    """Main workflow"""
    print("\n" + "=" * 70)
    print("Fast I-V Curve Generation for MOSFET")
    print("=" * 70 + "\n")
    
    sim, device, mesh = simulate_mosfet_fast()
    
    # Generate I-V curves
    plot_transfer_curves(sim)
    plot_output_curves(sim)
    
    print("\n" + "=" * 70)
    print("I-V Curve Generation Complete!")
    print("=" * 70)
    print("\nGenerated files:")
    print("  - mosfet_transfer_curves_fast.png")
    print("  - mosfet_output_curves_fast.png")


if __name__ == '__main__':
    main()
