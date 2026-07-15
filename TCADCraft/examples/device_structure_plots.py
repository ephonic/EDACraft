#!/usr/bin/env python3
"""
FinFET and GAA 3D Structure Visualization

This script generates publication-quality 3D structure plots for:
1. FinFET device with electron density and potential distributions
2. GAA Nanosheet FET device
3. Mesh discretization visualization
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.gridspec as gridspec
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
})

from tcad import Device, Simulator
from tcad.mesh.generator import structured_mesh_from_device


def simulate_finfet():
    """Simulate FinFET device"""
    print("=" * 60)
    print("FinFET Simulation")
    print("=" * 60)
    
    # Device parameters
    Lg = 30e-9
    tsi = 10e-9
    Hfin = 30e-9
    tox = 1.5e-9
    Lsd = 30e-9
    tgate = 10e-9
    
    device = Device.finfet(
        Lg=Lg, tox=tox, tsi=tsi, Hfin=Hfin,
        Lsd=Lsd, tgate=tgate, Vg=0.7, Vd=0.1, Vs=0.0,
    )
    
    # Generate mesh
    mesh = structured_mesh_from_device(device, resolution=(8e-9, 4e-9, 8e-9))
    print(f"Grid: {mesh.nx} x {mesh.ny} x {mesh.nz} = {mesh.npts()} nodes")
    
    # Run simulation
    sim = Simulator(mesh, temperature=300.0)
    sim.set_material_from_mesh()
    for name, (shape, voltage) in device.contacts.items():
        sim.set_contact(name, voltage)
    
    results = sim.run(max_iter=80, tol=1e-6)
    print(f"Converged: {results['converged']}, Iterations: {results['iterations']}")
    
    return mesh, results, device


def simulate_gaa():
    """Simulate GAA Nanosheet FET device"""
    print("\n" + "=" * 60)
    print("GAA Nanosheet FET Simulation")
    print("=" * 60)
    
    # Device parameters
    Lg = 20e-9
    t_sheet = 5e-9
    W_sheet = 10e-9
    tox = 1.2e-9
    Lsd = 20e-9
    tgate = 8e-9
    t_box = 10e-9
    
    device = Device.gaa(
        Lg=Lg, tox=tox, t_sheet=t_sheet, W_sheet=W_sheet,
        Lsd=Lsd, t_gate=tgate, t_box=t_box, Vg=0.7, Vd=0.1, Vs=0.0,
    )
    
    # Generate mesh
    mesh = structured_mesh_from_device(device, resolution=(6e-9, 3e-9, 6e-9))
    print(f"Grid: {mesh.nx} x {mesh.ny} x {mesh.nz} = {mesh.npts()} nodes")
    
    # Run simulation
    sim = Simulator(mesh, temperature=300.0)
    sim.set_material_from_mesh()
    for name, (shape, voltage) in device.contacts.items():
        sim.set_contact(name, voltage)
    
    results = sim.run(max_iter=80, tol=1e-6)
    print(f"Converged: {results['converged']}, Iterations: {results['iterations']}")
    
    return mesh, results, device


def plot_3d_structure(mesh, results, device_name, filename):
    """Plot 3D device structure with electron density and potential"""
    print(f"\nCreating {device_name} 3D structure plot...")
    
    # Reshape results
    n = results['n'].reshape(mesh.nx, mesh.ny, mesh.nz)
    phi = results['phi'].reshape(mesh.nx, mesh.ny, mesh.nz)
    
    # Coordinate arrays
    x = np.linspace(0, mesh.dx * (mesh.nx - 1), mesh.nx) * 1e9
    y = np.linspace(0, mesh.dy * (mesh.ny - 1), mesh.ny) * 1e9
    z = np.linspace(0, mesh.dz * (mesh.nz - 1), mesh.nz) * 1e9
    
    fig = plt.figure(figsize=(16, 7))
    
    # Subsample for clarity
    stride = max(1, min(mesh.nx, mesh.ny, mesh.nz) // 10)
    
    # Plot 1: Electron density
    ax1 = fig.add_subplot(121, projection='3d')
    n_sub = n[::stride, ::stride, ::stride]
    n_log = np.log10(np.clip(n_sub, 1e10, None))
    
    X, Y, Z = np.meshgrid(x[::stride], y[::stride], z[::stride], indexing='ij')
    
    scatter = ax1.scatter(X.ravel(), Y.ravel(), Z.ravel(), 
                         c=n_log.ravel(), cmap='viridis', 
                         s=50, alpha=0.8, edgecolors='none')
    
    ax1.set_xlabel('x [nm]', fontsize=12, fontweight='bold')
    ax1.set_ylabel('y [nm]', fontsize=12, fontweight='bold')
    ax1.set_zlabel('z [nm]', fontsize=12, fontweight='bold')
    ax1.set_title(f'{device_name} - 3D Electron Density', 
                 fontsize=14, fontweight='bold', pad=20)
    
    cbar = plt.colorbar(scatter, ax=ax1, shrink=0.6, pad=0.1)
    cbar.set_label('log₁₀(n) [cm⁻³]', fontsize=11, fontweight='bold')
    
    # Plot 2: Potential
    ax2 = fig.add_subplot(122, projection='3d')
    phi_sub = phi[::stride, ::stride, ::stride]
    
    scatter2 = ax2.scatter(X.ravel(), Y.ravel(), Z.ravel(), 
                          c=phi_sub.ravel(), cmap='RdBu_r', 
                          s=50, alpha=0.8, edgecolors='none')
    
    ax2.set_xlabel('x [nm]', fontsize=12, fontweight='bold')
    ax2.set_ylabel('y [nm]', fontsize=12, fontweight='bold')
    ax2.set_zlabel('z [nm]', fontsize=12, fontweight='bold')
    ax2.set_title(f'{device_name} - 3D Potential', 
                 fontsize=14, fontweight='bold', pad=20)
    
    cbar2 = plt.colorbar(scatter2, ax=ax2, shrink=0.6, pad=0.1)
    cbar2.set_label('φ [V]', fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Saved: {filename}")
    plt.close()


def plot_mesh_discretization(finfet_mesh, gaa_mesh):
    """Plot mesh discretization for both devices"""
    print("\nCreating mesh discretization plots...")
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 7), subplot_kw={'projection': '3d'})
    
    for ax, mesh, title in zip(axes, [finfet_mesh, gaa_mesh], 
                               ['FinFET', 'GAA Nanosheet']):
        # Coordinate arrays
        x = np.linspace(0, mesh.dx * (mesh.nx - 1), mesh.nx) * 1e9
        y = np.linspace(0, mesh.dy * (mesh.ny - 1), mesh.ny) * 1e9
        z = np.linspace(0, mesh.dz * (mesh.nz - 1), mesh.nz) * 1e9
        
        # Plot mesh grid lines
        stride_x = max(1, mesh.nx // 6)
        stride_y = max(1, mesh.ny // 6)
        stride_z = max(1, mesh.nz // 6)
        
        # Draw grid lines
        for i in range(0, mesh.nx, stride_x):
            for j in range(0, mesh.ny, stride_y):
                ax.plot(x[i] * np.ones(mesh.nz), y[j] * np.ones(mesh.nz), z, 
                       'b-', alpha=0.3, linewidth=1)
        
        for i in range(0, mesh.nx, stride_x):
            for k in range(0, mesh.nz, stride_z):
                ax.plot(x[i] * np.ones(mesh.ny), y, z[k] * np.ones(mesh.ny), 
                       'r-', alpha=0.3, linewidth=1)
        
        for j in range(0, mesh.ny, stride_y):
            for k in range(0, mesh.nz, stride_z):
                ax.plot(x, y[j] * np.ones(mesh.nx), z[k] * np.ones(mesh.nx), 
                       'g-', alpha=0.3, linewidth=1)
        
        # Plot nodes
        X_mesh, Y_mesh, Z_mesh = np.meshgrid(x, y, z, indexing='ij')
        ax.scatter(X_mesh.ravel(), Y_mesh.ravel(), Z_mesh.ravel(), 
                  c='gray', s=10, alpha=0.5)
        
        ax.set_xlabel('x [nm]', fontsize=12, fontweight='bold')
        ax.set_ylabel('y [nm]', fontsize=12, fontweight='bold')
        ax.set_zlabel('z [nm]', fontsize=12, fontweight='bold')
        ax.set_title(f'{title} Mesh\n({mesh.nx}×{mesh.ny}×{mesh.nz} = {mesh.npts()} nodes)', 
                    fontsize=13, fontweight='bold', pad=20)
    
    plt.tight_layout()
    plt.savefig('mesh_discretization.png', dpi=300, bbox_inches='tight')
    print("Saved: mesh_discretization.png")
    plt.close()


def plot_2d_slices(mesh, results, device_name, filename):
    """Plot 2D slices of potential and carrier density"""
    print(f"\nCreating {device_name} 2D slices...")
    
    # Reshape results
    phi = results['phi'].reshape(mesh.nx, mesh.ny, mesh.nz)
    n = results['n'].reshape(mesh.nx, mesh.ny, mesh.nz)
    
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
    plt.colorbar(im, ax=axes[1, 2], label='log₁₀(n) [cm³]')
    
    plt.suptitle(f'{device_name} - 2D Field Slices', 
                fontsize=15, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Saved: {filename}")
    plt.close()


def main():
    """Main visualization workflow"""
    print("\n" + "=" * 70)
    print("FinFET and GAA 3D Structure Visualization")
    print("=" * 70 + "\n")
    
    # Simulate FinFET
    finfet_mesh, finfet_results, finfet_device = simulate_finfet()
    
    # Simulate GAA
    gaa_mesh, gaa_results, gaa_device = simulate_gaa()
    
    # Create 3D structure plots
    plot_3d_structure(finfet_mesh, finfet_results, 'FinFET', 'finfet_3d_structure.png')
    plot_3d_structure(gaa_mesh, gaa_results, 'GAA Nanosheet', 'gaa_3d_structure.png')
    
    # Create mesh discretization plots
    plot_mesh_discretization(finfet_mesh, gaa_mesh)
    
    # Create 2D slice plots
    plot_2d_slices(finfet_mesh, finfet_results, 'FinFET', 'finfet_2d_slices.png')
    plot_2d_slices(gaa_mesh, gaa_results, 'GAA Nanosheet', 'gaa_2d_slices.png')
    
    print("\n" + "=" * 70)
    print("Visualization Complete!")
    print("=" * 70)
    print("\nGenerated files:")
    print("  - finfet_3d_structure.png")
    print("  - gaa_3d_structure.png")
    print("  - mesh_discretization.png")
    print("  - finfet_2d_slices.png")
    print("  - gaa_2d_slices.png")


if __name__ == '__main__':
    main()
