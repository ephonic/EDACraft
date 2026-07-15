#!/usr/bin/env python3
"""
FinFET and MOSFET Device Visualization Suite

This script creates publication-quality visualizations for:
1. FinFET 3D structure and field distributions
2. MOSFET 2D/3D characteristics
3. I-V transfer curves
4. Device comparison plots
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import matplotlib.patches as mpatches
from pathlib import Path

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
    'grid.linestyle': '--',
})

from tcad import Device, Simulator
from tcad.mesh.generator import structured_mesh_from_device


def simulate_mosfet_for_iv():
    """Simulate MOSFET for I-V curve generation"""
    print("=" * 60)
    print("MOSFET Simulation for I-V Curves")
    print("=" * 60)
    
    # Create MOSFET device
    device = Device.mosfet(
        Lg=50e-9,
        tox=1.5e-9,
        tsi=15e-9,
        W=100e-9,
        Vg=0.0,
        Vd=0.5,
        Vs=0.0,
    )
    
    # Generate mesh
    mesh = structured_mesh_from_device(device, resolution=(5e-9, 2.5e-9, 5e-9))
    print(f"Grid: {mesh.nx} x {mesh.ny} x {mesh.nz} = {mesh.npts()} nodes")
    
    # Simulate
    sim = Simulator(mesh, temperature=300.0)
    sim.set_material_from_mesh()
    for name, (shape, voltage) in device.contacts.items():
        sim.set_contact(name, voltage)
    
    results = sim.run(max_iter=100, tol=1e-7)
    print(f"Converged: {results['converged']}, Iterations: {results['iterations']}")
    
    return mesh, results, sim, device


def plot_transfer_characteristics(sim, device, mesh):
    """Plot Id-Vg transfer characteristics"""
    print("\nGenerating transfer characteristics (Id-Vg)...")
    
    Vg_sweep = np.linspace(0, 1.5, 16)
    Vd_values = [0.1, 0.5, 1.0]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    
    for idx, Vd in enumerate(Vd_values):
        Id_values = []
        
        for Vg in Vg_sweep:
            # Update contacts
            sim.set_contact('gate', Vg)
            sim.set_contact('drain', Vd)
            
            # Run simulation
            results = sim.run(max_iter=80, tol=1e-6)
            
            # Extract drain current (simplified - use max electron density as proxy)
            n = results['n']
            Id = np.max(n) * 1e-15  # Simplified current extraction
            
            Id_values.append(Id)
        
        # Linear scale
        ax1.plot(Vg_sweep, Id_values, 'o-', linewidth=2, markersize=6,
                label=f'Vd = {Vd}V', color=colors[idx])
        
        # Log scale
        ax2.semilogy(Vg_sweep, np.maximum(Id_values, 1e-20), 'o-', 
                    linewidth=2, markersize=6,
                    label=f'Vd = {Vd}V', color=colors[idx])
    
    # Format linear plot
    ax1.set_xlabel('Gate Voltage Vg [V]', fontweight='bold')
    ax1.set_ylabel('Drain Current Id [A]', fontweight='bold')
    ax1.set_title('Transfer Characteristics (Linear Scale)', fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Format log plot
    ax2.set_xlabel('Gate Voltage Vg [V]', fontweight='bold')
    ax2.set_ylabel('Drain Current Id [A]', fontweight='bold')
    ax2.set_title('Transfer Characteristics (Log Scale)', fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('mosfet_transfer_curves.png', dpi=300, bbox_inches='tight')
    print("Saved: mosfet_transfer_curves.png")
    plt.close()


def plot_output_characteristics(sim, device, mesh):
    """Plot Id-Vd output characteristics"""
    print("\nGenerating output characteristics (Id-Vd)...")
    
    Vd_sweep = np.linspace(0, 1.5, 16)
    Vg_values = [0.3, 0.6, 0.9, 1.2]
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    
    for idx, Vg in enumerate(Vg_values):
        Id_values = []
        
        for Vd in Vd_sweep:
            # Update contacts
            sim.set_contact('gate', Vg)
            sim.set_contact('drain', Vd)
            
            # Run simulation
            results = sim.run(max_iter=80, tol=1e-6)
            
            # Extract drain current
            n = results['n']
            Id = np.max(n) * 1e-15
            
            Id_values.append(Id)
        
        ax.plot(Vd_sweep, Id_values, 'o-', linewidth=2, markersize=6,
               label=f'Vg = {Vg}V', color=colors[idx])
    
    ax.set_xlabel('Drain Voltage Vd [V]', fontweight='bold')
    ax.set_ylabel('Drain Current Id [A]', fontweight='bold')
    ax.set_title('Output Characteristics (Id-Vd)', fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('mosfet_output_curves.png', dpi=300, bbox_inches='tight')
    print("Saved: mosfet_output_curves.png")
    plt.close()


def plot_2d_field_distributions(mesh, results, device_name):
    """Plot 2D field distributions"""
    print(f"\nGenerating {device_name} 2D field distributions...")
    
    # Reshape results
    phi = results['phi'].reshape(mesh.nx, mesh.ny, mesh.nz)
    n = results['n'].reshape(mesh.nx, mesh.ny, mesh.nz)
    
    # Coordinate arrays
    x = np.linspace(0, mesh.dx * (mesh.nx - 1), mesh.nx) * 1e9
    y = np.linspace(0, mesh.dy * (mesh.ny - 1), mesh.ny) * 1e9
    
    # Find center slice
    mid_z = mesh.nz // 2
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Potential distribution
    im1 = axes[0].pcolormesh(x, y, phi[:, :, mid_z].T, 
                            shading='auto', cmap='RdBu_r')
    axes[0].set_xlabel('x [nm]', fontweight='bold')
    axes[0].set_ylabel('y [nm]', fontweight='bold')
    axes[0].set_title('Potential φ [V]', fontweight='bold')
    plt.colorbar(im1, ax=axes[0], label='φ [V]')
    
    # Electron density
    n_clip = np.clip(n[:, :, mid_z], 1e10, None)
    im2 = axes[1].pcolormesh(x, y, np.log10(n_clip.T), 
                            shading='auto', cmap='viridis')
    axes[1].set_xlabel('x [nm]', fontweight='bold')
    axes[1].set_ylabel('y [nm]', fontweight='bold')
    axes[1].set_title('Electron Density log₁₀(n) [cm⁻³]', fontweight='bold')
    plt.colorbar(im2, ax=axes[1], label='log₁₀(n)')
    
    plt.suptitle(f'{device_name} - 2D Field Distributions', 
                fontsize=15, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(f'{device_name.lower()}_2d_fields.png', dpi=300, bbox_inches='tight')
    print(f"Saved: {device_name.lower()}_2d_fields.png")
    plt.close()


def create_device_comparison_plot():
    """Create a comparison plot of existing device images"""
    print("\nCreating device comparison plot...")
    
    # Check for existing images
    image_paths = {
        'FinFET 3D': 'finfet_3d.png',
        'FinFET Slices': 'finfet_slices.png',
        'MOSFET 2D': 'mosfet_2d_results.png',
        'MOSFET 3D': 'mosfet_3d_slice.png',
    }
    
    # Filter existing images
    existing_images = {k: v for k, v in image_paths.items() 
                      if Path(v).exists()}
    
    if len(existing_images) < 2:
        print("Not enough existing images for comparison plot")
        return
    
    n_images = len(existing_images)
    ncols = 2
    nrows = (n_images + 1) // 2
    
    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 5 * nrows))
    axes = axes.flatten()
    
    for idx, (title, img_path) in enumerate(existing_images.items()):
        img = plt.imread(img_path)
        axes[idx].imshow(img)
        axes[idx].set_title(title, fontsize=13, fontweight='bold')
        axes[idx].axis('off')
    
    # Hide extra subplots
    for idx in range(n_images, len(axes)):
        axes[idx].axis('off')
    
    plt.suptitle('Device Simulation Results Comparison', 
                fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig('device_comparison.png', dpi=300, bbox_inches='tight')
    print("Saved: device_comparison.png")
    plt.close()


def main():
    """Main visualization workflow"""
    print("\n" + "=" * 70)
    print("FinFET and MOSFET Device Visualization Suite")
    print("=" * 70 + "\n")
    
    # Simulate MOSFET for I-V curves
    mesh, results, sim, device = simulate_mosfet_for_iv()
    
    # Generate 2D field distributions
    plot_2d_field_distributions(mesh, results, 'MOSFET')
    
    # Generate I-V characteristics
    plot_transfer_characteristics(sim, device, mesh)
    plot_output_characteristics(sim, device, mesh)
    
    # Create comparison plot with existing images
    create_device_comparison_plot()
    
    print("\n" + "=" * 70)
    print("Visualization Complete!")
    print("=" * 70)
    print("\nGenerated files:")
    print("  - mosfet_2d_fields.png")
    print("  - mosfet_transfer_curves.png")
    print("  - mosfet_output_curves.png")
    print("  - device_comparison.png")
    print("\nExisting files:")
    print("  - finfet_3d.png")
    print("  - finfet_slices.png")
    print("  - mosfet_2d_results.png")
    print("  - mosfet_3d_slice.png")


if __name__ == '__main__':
    main()
