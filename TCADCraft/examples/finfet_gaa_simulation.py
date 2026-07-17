#!/usr/bin/env python3
"""
FinFET and GAA Nanosheet FET Simulation with Publication-Quality Visualization

This script performs:
1. FinFET device simulation
2. GAA Nanosheet FET simulation
3. High-quality 3D structure visualization
4. Mesh/discretization plots
5. I-V characteristic curves (transfer and output)

Author: TCAD Team
Date: 2024
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

# Set publication-quality plot style
plt.rcParams.update({
    'font.size': 11,
    'font.family': 'serif',
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.dpi': 150,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.grid': True,
    'grid.alpha': 0.3,
    'grid.linestyle': '--',
})

from tcad import Device, Simulator
from tcad.mesh.generator import structured_mesh_from_device


def simulate_finfet(Lg=30e-9, tsi=10e-9, Hfin=30e-9, tox=1.5e-9, 
                    Lsd=30e-9, tgate=10e-9, Vg_range=None, Vd_range=None):
    """Simulate FinFET device and return results"""
    print("=" * 60)
    print("FinFET Simulation")
    print("=" * 60)
    print(f"Parameters: Lg={Lg*1e9:.0f}nm, tsi={tsi*1e9:.0f}nm, Hfin={Hfin*1e9:.0f}nm")
    
    # Build device
    device = Device.finfet(
        Lg=Lg, tox=tox, tsi=tsi, Hfin=Hfin,
        Lsd=Lsd, tgate=tgate, Vg=0.7, Vd=0.1, Vs=0.0,
    )
    
    # Generate mesh
    mesh = structured_mesh_from_device(device, resolution=(5e-9, 2.5e-9, 5e-9))
    print(f"Grid: {mesh.nx} x {mesh.ny} x {mesh.nz} = {mesh.npts()} nodes")
    
    # Run simulation
    sim = Simulator(mesh, temperature=300.0)
    sim.set_material_from_mesh()
    for name, (shape, voltage) in device.contacts.items():
        sim.set_contact(name, voltage)
    
    results = sim.run(max_iter=120, tol=1e-8)
    print(f"Converged: {results['converged']}, Iterations: {results['iterations']}")
    
    # Reshape results
    phi = results['phi'].reshape(mesh.nx, mesh.ny, mesh.nz)
    n = results['n'].reshape(mesh.nx, mesh.ny, mesh.nz)
    p = results['p'].reshape(mesh.nx, mesh.ny, mesh.nz)
    
    return {
        'device': device,
        'mesh': mesh,
        'sim': sim,
        'results': results,
        'phi': phi,
        'n': n,
        'p': p,
    }


def simulate_gaa(Lg=20e-9, tsi=5e-9, W=10e-9, tox=1.2e-9, 
                 Lsd=20e-9, tgate=8e-9, Vg_range=None, Vd_range=None):
    """Simulate GAA Nanosheet FET device and return results"""
    print("\n" + "=" * 60)
    print("GAA Nanosheet FET Simulation")
    print("=" * 60)
    print(f"Parameters: Lg={Lg*1e9:.0f}nm, tsi={tsi*1e9:.0f}nm, W={W*1e9:.0f}nm")
    
    # Build device
    device = Device.gaa(
        Lg=Lg, tox=tox, tsi=tsi, W=W,
        Lsd=Lsd, tgate=tgate, Vg=0.7, Vd=0.1, Vs=0.0,
    )
    
    # Generate mesh
    mesh = structured_mesh_from_device(device, resolution=(4e-9, 2e-9, 4e-9))
    print(f"Grid: {mesh.nx} x {mesh.ny} x {mesh.nz} = {mesh.npts()} nodes")
    
    # Run simulation
    sim = Simulator(mesh, temperature=300.0)
    sim.set_material_from_mesh()
    for name, (shape, voltage) in device.contacts.items():
        sim.set_contact(name, voltage)
    
    results = sim.run(max_iter=120, tol=1e-8)
    print(f"Converged: {results['converged']}, Iterations: {results['iterations']}")
    
    # Reshape results
    phi = results['phi'].reshape(mesh.nx, mesh.ny, mesh.nz)
    n = results['n'].reshape(mesh.nx, mesh.ny, mesh.nz)
    p = results['p'].reshape(mesh.nx, mesh.ny, mesh.nz)
    
    return {
        'device': device,
        'mesh': mesh,
        'sim': sim,
        'results': results,
        'phi': phi,
        'n': n,
        'p': p,
    }


def plot_device_structure_3d(data, device_name, save_path):
    """Plot 3D device structure with mesh"""
    mesh = data['mesh']
    device = data['device']
    
    fig = plt.figure(figsize=(14, 6))
    
    # Coordinate arrays
    x = np.linspace(0, mesh.dx * (mesh.nx - 1), mesh.nx) * 1e9
    y = np.linspace(0, mesh.dy * (mesh.ny - 1), mesh.ny) * 1e9
    z = np.linspace(0, mesh.dz * (mesh.nz - 1), mesh.nz) * 1e9
    
    # Plot 1: Device structure (electron density)
    ax1 = fig.add_subplot(121, projection='3d')
    n = data['n']
    
    # Subsample for clarity
    stride = max(1, min(mesh.nx, mesh.ny, mesh.nz) // 15)
    n_sub = n[::stride, ::stride, ::stride]
    n_log = np.log10(np.clip(n_sub, 1e10, None))
    
    X, Y, Z = np.meshgrid(x[::stride], y[::stride], z[::stride], indexing='ij')
    
    scatter = ax1.scatter(X.ravel(), Y.ravel(), Z.ravel(), 
                         c=n_log.ravel(), cmap='viridis', 
                         s=30, alpha=0.7, edgecolors='none')
    
    ax1.set_xlabel('x [nm]', fontsize=11)
    ax1.set_ylabel('y [nm]', fontsize=11)
    ax1.set_zlabel('z [nm]', fontsize=11)
    ax1.set_title(f'{device_name} - 3D Electron Density', fontsize=13, fontweight='bold')
    
    cbar = plt.colorbar(scatter, ax=ax1, shrink=0.6, pad=0.1)
    cbar.set_label('log₁₀(n) [cm⁻³]', fontsize=10)
    
    # Plot 2: Mesh discretization
    ax2 = fig.add_subplot(122, projection='3d')
    
    # Plot mesh grid lines
    for i in range(0, mesh.nx, max(1, mesh.nx // 10)):
        for j in range(0, mesh.ny, max(1, mesh.ny // 10)):
            ax2.plot(x[i] * np.ones(mesh.nz), y[j] * np.ones(mesh.nz), z, 
                    'b-', alpha=0.2, linewidth=0.5)
    
    for i in range(0, mesh.nx, max(1, mesh.nx // 10)):
        for k in range(0, mesh.nz, max(1, mesh.nz // 10)):
            ax2.plot(x[i] * np.ones(mesh.ny), y, z[k] * np.ones(mesh.ny), 
                    'r-', alpha=0.2, linewidth=0.5)
    
    for j in range(0, mesh.ny, max(1, mesh.ny // 10)):
        for k in range(0, mesh.nz, max(1, mesh.nz // 10)):
            ax2.plot(x, y[j] * np.ones(mesh.nx), z[k] * np.ones(mesh.nx), 
                    'g-', alpha=0.2, linewidth=0.5)
    
    # Plot nodes
    X_mesh, Y_mesh, Z_mesh = np.meshgrid(x, y, z, indexing='ij')
    ax2.scatter(X_mesh.ravel(), Y_mesh.ravel(), Z_mesh.ravel(), 
               c='gray', s=5, alpha=0.3)
    
    ax2.set_xlabel('x [nm]', fontsize=11)
    ax2.set_ylabel('y [nm]', fontsize=11)
    ax2.set_zlabel('z [nm]', fontsize=11)
    ax2.set_title(f'{device_name} - Mesh Discretization', fontsize=13, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Saved 3D structure plot to {save_path}")
    plt.close()


def plot_2d_slices(data, device_name, save_path):
    """Plot 2D slices of potential and carrier density"""
    mesh = data['mesh']
    phi = data['phi']
    n = data['n']
    
    # Coordinate arrays
    x = np.linspace(0, mesh.dx * (mesh.nx - 1), mesh.nx) * 1e9
    y = np.linspace(0, mesh.dy * (mesh.ny - 1), mesh.ny) * 1e9
    z = np.linspace(0, mesh.dz * (mesh.nz - 1), mesh.nz) * 1e9
    
    # Find center slices
    mid_x = mesh.nx // 2
    mid_y = mesh.ny // 2
    mid_z = mesh.nz // 2
    
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    
    # Potential slices
    im = axes[0, 0].pcolormesh(x, y, phi[:, :, mid_z].T, shading='auto', cmap='RdBu_r')
    axes[0, 0].set_title(f'Potential φ (z={z[mid_z]:.1f}nm)', fontweight='bold')
    axes[0, 0].set_xlabel('x [nm]')
    axes[0, 0].set_ylabel('y [nm]')
    plt.colorbar(im, ax=axes[0, 0], label='φ [V]')
    
    im = axes[0, 1].pcolormesh(x, z, phi[:, mid_y, :].T, shading='auto', cmap='RdBu_r')
    axes[0, 1].set_title(f'Potential φ (y={y[mid_y]:.1f}nm)', fontweight='bold')
    axes[0, 1].set_xlabel('x [nm]')
    axes[0, 1].set_ylabel('z [nm]')
    plt.colorbar(im, ax=axes[0, 1], label='φ [V]')
    
    im = axes[0, 2].pcolormesh(y, z, phi[mid_x, :, :].T, shading='auto', cmap='RdBu_r')
    axes[0, 2].set_title(f'Potential φ (x={x[mid_x]:.1f}nm)', fontweight='bold')
    axes[0, 2].set_xlabel('y [nm]')
    axes[0, 2].set_ylabel('z [nm]')
    plt.colorbar(im, ax=axes[0, 2], label='φ [V]')
    
    # Electron density slices
    n_clip = np.clip(n[:, :, mid_z], 1e10, None)
    im = axes[1, 0].pcolormesh(x, y, np.log10(n_clip.T), shading='auto', cmap='viridis')
    axes[1, 0].set_title(f'log₁₀(n) (z={z[mid_z]:.1f}nm)', fontweight='bold')
    axes[1, 0].set_xlabel('x [nm]')
    axes[1, 0].set_ylabel('y [nm]')
    plt.colorbar(im, ax=axes[1, 0], label='log₁₀(n) [cm⁻³]')
    
    n_clip = np.clip(n[:, mid_y, :], 1e10, None)
    im = axes[1, 1].pcolormesh(x, z, np.log10(n_clip.T), shading='auto', cmap='viridis')
    axes[1, 1].set_title(f'log₁₀(n) (y={y[mid_y]:.1f}nm)', fontweight='bold')
    axes[1, 1].set_xlabel('x [nm]')
    axes[1, 1].set_ylabel('z [nm]')
    plt.colorbar(im, ax=axes[1, 1], label='log₁₀(n) [cm⁻³]')
    
    n_clip = np.clip(n[mid_x, :, :], 1e10, None)
    im = axes[1, 2].pcolormesh(y, z, np.log10(n_clip.T), shading='auto', cmap='viridis')
    axes[1, 2].set_title(f'log₁₀(n) (x={x[mid_x]:.1f}nm)', fontweight='bold')
    axes[1, 2].set_xlabel('y [nm]')
    axes[1, 2].set_ylabel('z [nm]')
    plt.colorbar(im, ax=axes[1, 2], label='log₁₀(n) [cm⁻³]')
    
    plt.suptitle(f'{device_name} - 2D Field Slices', fontsize=15, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Saved 2D slices plot to {save_path}")
    plt.close()


def plot_iv_curves(finfet_data, gaa_data, save_path):
    """Plot I-V characteristic curves for both devices"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    
    # Transfer characteristics (Id-Vg)
    Vg_sweep = np.linspace(0, 1.0, 11)
    Vd_fixed = 0.1
    
    finfet_ids = []
    gaa_ids = []
    
    print("\nSweeping Vg for transfer characteristics...")
    
    for Vg in Vg_sweep:
        # FinFET
        finfet_data['sim'].set_contact('gate', Vg)
        result = finfet_data['sim'].run(max_iter=120, tol=1e-8)
        Id = result['current']['drain']
        finfet_ids.append(abs(Id))
        
        # GAA
        gaa_data['sim'].set_contact('gate', Vg)
        result = gaa_data['sim'].run(max_iter=120, tol=1e-8)
        Id = result['current']['drain']
        gaa_ids.append(abs(Id))
    
    # Linear scale
    axes[0, 0].plot(Vg_sweep, finfet_ids, 'o-', linewidth=2, markersize=8, 
                    label='FinFET', color='#1f77b4')
    axes[0, 0].plot(Vg_sweep, gaa_ids, 's-', linewidth=2, markersize=8, 
                    label='GAA', color='#ff7f0e')
    axes[0, 0].set_xlabel('Gate Voltage Vg [V]')
    axes[0, 0].set_ylabel('Drain Current Id [A]')
    axes[0, 0].set_title('Transfer Characteristics (Linear)', fontweight='bold')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # Log scale
    axes[0, 1].semilogy(Vg_sweep, finfet_ids, 'o-', linewidth=2, markersize=8, 
                        label='FinFET', color='#1f77b4')
    axes[0, 1].semilogy(Vg_sweep, gaa_ids, 's-', linewidth=2, markersize=8, 
                        label='GAA', color='#ff7f0e')
    axes[0, 1].set_xlabel('Gate Voltage Vg [V]')
    axes[0, 1].set_ylabel('Drain Current Id [A]')
    axes[0, 1].set_title('Transfer Characteristics (Log Scale)', fontweight='bold')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    
    # Output characteristics (Id-Vd)
    Vd_sweep = np.linspace(0, 1.0, 11)
    Vg_values = [0.3, 0.5, 0.7, 0.9]
    
    print("Sweeping Vd for output characteristics...")
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    
    for idx, Vg in enumerate(Vg_values):
        finfet_ids_vd = []
        gaa_ids_vd = []
        
        for Vd in Vd_sweep:
            # FinFET
            finfet_data['sim'].set_contact('gate', Vg)
            finfet_data['sim'].set_contact('drain', Vd)
            result = finfet_data['sim'].run(max_iter=120, tol=1e-8)
            Id = result['current']['drain']
            finfet_ids_vd.append(abs(Id))
            
            # GAA
            gaa_data['sim'].set_contact('gate', Vg)
            gaa_data['sim'].set_contact('drain', Vd)
            result = gaa_data['sim'].run(max_iter=120, tol=1e-8)
            Id = result['current']['drain']
            gaa_ids_vd.append(abs(Id))
        
        # FinFET output
        axes[1, 0].plot(Vd_sweep, finfet_ids_vd, '-', linewidth=2, 
                        label=f'FinFET Vg={Vg}V', color=colors[idx])
        
        # GAA output
        axes[1, 1].plot(Vd_sweep, gaa_ids_vd, '-', linewidth=2, 
                        label=f'GAA Vg={Vg}V', color=colors[idx])
    
    axes[1, 0].set_xlabel('Drain Voltage Vd [V]')
    axes[1, 0].set_ylabel('Drain Current Id [A]')
    axes[1, 0].set_title('FinFET Output Characteristics', fontweight='bold')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    axes[1, 1].set_xlabel('Drain Voltage Vd [V]')
    axes[1, 1].set_ylabel('Drain Current Id [A]')
    axes[1, 1].set_title('GAA Output Characteristics', fontweight='bold')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.suptitle('I-V Characteristic Comparison', fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Saved I-V curves to {save_path}")
    plt.close()


def main():
    """Main simulation workflow"""
    print("\n" + "=" * 70)
    print("FinFET and GAA Nanosheet FET Simulation Suite")
    print("=" * 70 + "\n")
    
    # Simulate FinFET
    finfet_data = simulate_finfet()
    
    # Simulate GAA
    gaa_data = simulate_gaa()
    
    # Plot 3D structures
    print("\nGenerating 3D structure plots...")
    plot_device_structure_3d(finfet_data, 'FinFET', 'finfet_3d_structure.png')
    plot_device_structure_3d(gaa_data, 'GAA Nanosheet', 'gaa_3d_structure.png')
    
    # Plot 2D slices
    print("\nGenerating 2D field slice plots...")
    plot_2d_slices(finfet_data, 'FinFET', 'finfet_2d_slices.png')
    plot_2d_slices(gaa_data, 'GAA Nanosheet', 'gaa_2d_slices.png')
    
    # Plot I-V curves
    print("\nGenerating I-V characteristic curves...")
    plot_iv_curves(finfet_data, gaa_data, 'iv_curves_comparison.png')
    
    print("\n" + "=" * 70)
    print("Simulation Complete!")
    print("=" * 70)
    print("\nGenerated files:")
    print("  - finfet_3d_structure.png")
    print("  - gaa_3d_structure.png")
    print("  - finfet_2d_slices.png")
    print("  - gaa_2d_slices.png")
    print("  - iv_curves_comparison.png")


if __name__ == '__main__':
    main()
