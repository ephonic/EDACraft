#!/usr/bin/env python3
"""
FinFET and GAA Device Structure Visualization

This script generates high-quality 3D structure and mesh plots for
FinFET and GAA Nanosheet FET devices.
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.patches as mpatches

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
})

from tcad import Device
from tcad.mesh.generator import structured_mesh_from_device
from tcad import Simulator


def create_finfet_structure_plot():
    """Create high-quality 3D FinFET structure plot"""
    print("Creating FinFET structure...")
    
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
    
    mesh = structured_mesh_from_device(device, resolution=(5e-9, 2.5e-9, 5e-9))
    
    # Coordinate arrays
    x = np.linspace(0, mesh.dx * (mesh.nx - 1), mesh.nx) * 1e9
    y = np.linspace(0, mesh.dy * (mesh.ny - 1), mesh.ny) * 1e9
    z = np.linspace(0, mesh.dz * (mesh.nz - 1), mesh.nz) * 1e9
    
    # Run simulation
    print("Running FinFET simulation...")
    sim = Simulator(mesh, temperature=300.0)
    sim.set_material_from_mesh()
    for name, (shape, voltage) in device.contacts.items():
        sim.set_contact(name, voltage)
    
    results = sim.run(max_iter=120, tol=1e-8)
    print(f"FinFET converged: {results['converged']}")
    
    # Reshape results
    n = results['n'].reshape(mesh.nx, mesh.ny, mesh.nz)
    phi = results['phi'].reshape(mesh.nx, mesh.ny, mesh.nz)
    
    # Create figure with 2 subplots
    fig = plt.figure(figsize=(16, 7))
    
    # Subplot 1: 3D electron density
    ax1 = fig.add_subplot(121, projection='3d')
    
    # Subsample for clarity
    stride = max(1, min(mesh.nx, mesh.ny, mesh.nz) // 12)
    n_sub = n[::stride, ::stride, ::stride]
    n_log = np.log10(np.clip(n_sub, 1e10, None))
    
    X, Y, Z = np.meshgrid(x[::stride], y[::stride], z[::stride], indexing='ij')
    
    scatter = ax1.scatter(X.ravel(), Y.ravel(), Z.ravel(), 
                         c=n_log.ravel(), cmap='viridis', 
                         s=40, alpha=0.8, edgecolors='none')
    
    ax1.set_xlabel('x [nm]', fontsize=12, fontweight='bold')
    ax1.set_ylabel('y [nm]', fontsize=12, fontweight='bold')
    ax1.set_zlabel('z [nm]', fontsize=12, fontweight='bold')
    ax1.set_title('FinFET - 3D Electron Density', fontsize=14, fontweight='bold', pad=20)
    
    cbar = plt.colorbar(scatter, ax=ax1, shrink=0.6, pad=0.1)
    cbar.set_label('log₁₀(n) [cm⁻³]', fontsize=11, fontweight='bold')
    
    # Subplot 2: 3D potential
    ax2 = fig.add_subplot(122, projection='3d')
    
    phi_sub = phi[::stride, ::stride, ::stride]
    
    scatter2 = ax2.scatter(X.ravel(), Y.ravel(), Z.ravel(), 
                          c=phi_sub.ravel(), cmap='RdBu_r', 
                          s=40, alpha=0.8, edgecolors='none')
    
    ax2.set_xlabel('x [nm]', fontsize=12, fontweight='bold')
    ax2.set_ylabel('y [nm]', fontsize=12, fontweight='bold')
    ax2.set_zlabel('z [nm]', fontsize=12, fontweight='bold')
    ax2.set_title('FinFET - 3D Potential', fontsize=14, fontweight='bold', pad=20)
    
    cbar2 = plt.colorbar(scatter2, ax=ax2, shrink=0.6, pad=0.1)
    cbar2.set_label('φ [V]', fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('finfet_3d_structure.png', dpi=300, bbox_inches='tight')
    print("Saved: finfet_3d_structure.png")
    plt.close()
    
    return mesh, results


def create_gaa_structure_plot():
    """Create high-quality 3D GAA structure plot"""
    print("\nCreating GAA Nanosheet structure...")
    
    # Device parameters
    Lg = 20e-9
    tsi = 5e-9
    W = 10e-9
    tox = 1.2e-9
    Lsd = 20e-9
    tgate = 8e-9
    
    device = Device.gaa(
        Lg=Lg, tox=tox, tsi=tsi, W=W,
        Lsd=Lsd, tgate=tgate, Vg=0.7, Vd=0.1, Vs=0.0,
    )
    
    mesh = structured_mesh_from_device(device, resolution=(4e-9, 2e-9, 4e-9))
    
    # Coordinate arrays
    x = np.linspace(0, mesh.dx * (mesh.nx - 1), mesh.nx) * 1e9
    y = np.linspace(0, mesh.dy * (mesh.ny - 1), mesh.ny) * 1e9
    z = np.linspace(0, mesh.dz * (mesh.nz - 1), mesh.nz) * 1e9
    
    # Run simulation
    print("Running GAA simulation...")
    sim = Simulator(mesh, temperature=300.0)
    sim.set_material_from_mesh()
    for name, (shape, voltage) in device.contacts.items():
        sim.set_contact(name, voltage)
    
    results = sim.run(max_iter=120, tol=1e-8)
    print(f"GAA converged: {results['converged']}")
    
    # Reshape results
    n = results['n'].reshape(mesh.nx, mesh.ny, mesh.nz)
    phi = results['phi'].reshape(mesh.nx, mesh.ny, mesh.nz)
    
    # Create figure with 2 subplots
    fig = plt.figure(figsize=(16, 7))
    
    # Subplot 1: 3D electron density
    ax1 = fig.add_subplot(121, projection='3d')
    
    # Subsample for clarity
    stride = max(1, min(mesh.nx, mesh.ny, mesh.nz) // 12)
    n_sub = n[::stride, ::stride, ::stride]
    n_log = np.log10(np.clip(n_sub, 1e10, None))
    
    X, Y, Z = np.meshgrid(x[::stride], y[::stride], z[::stride], indexing='ij')
    
    scatter = ax1.scatter(X.ravel(), Y.ravel(), Z.ravel(), 
                         c=n_log.ravel(), cmap='viridis', 
                         s=40, alpha=0.8, edgecolors='none')
    
    ax1.set_xlabel('x [nm]', fontsize=12, fontweight='bold')
    ax1.set_ylabel('y [nm]', fontsize=12, fontweight='bold')
    ax1.set_zlabel('z [nm]', fontsize=12, fontweight='bold')
    ax1.set_title('GAA Nanosheet - 3D Electron Density', fontsize=14, fontweight='bold', pad=20)
    
    cbar = plt.colorbar(scatter, ax=ax1, shrink=0.6, pad=0.1)
    cbar.set_label('log₁₀(n) [cm⁻³]', fontsize=11, fontweight='bold')
    
    # Subplot 2: 3D potential
    ax2 = fig.add_subplot(122, projection='3d')
    
    phi_sub = phi[::stride, ::stride, ::stride]
    
    scatter2 = ax2.scatter(X.ravel(), Y.ravel(), Z.ravel(), 
                          c=phi_sub.ravel(), cmap='RdBu_r', 
                          s=40, alpha=0.8, edgecolors='none')
    
    ax2.set_xlabel('x [nm]', fontsize=12, fontweight='bold')
    ax2.set_ylabel('y [nm]', fontsize=12, fontweight='bold')
    ax2.set_zlabel('z [nm]', fontsize=12, fontweight='bold')
    ax2.set_title('GAA Nanosheet - 3D Potential', fontsize=14, fontweight='bold', pad=20)
    
    cbar2 = plt.colorbar(scatter2, ax=ax2, shrink=0.6, pad=0.1)
    cbar2.set_label('φ [V]', fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('gaa_3d_structure.png', dpi=300, bbox_inches='tight')
    print("Saved: gaa_3d_structure.png")
    plt.close()
    
    return mesh, results


def create_mesh_plots(finfet_mesh, gaa_mesh):
    """Create mesh discretization plots"""
    print("\nCreating mesh discretization plots...")
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 7), subplot_kw={'projection': '3d'})
    
    for ax, mesh, title in zip(axes, [finfet_mesh, gaa_mesh], 
                               ['FinFET Mesh', 'GAA Nanosheet Mesh']):
        # Coordinate arrays
        x = np.linspace(0, mesh.dx * (mesh.nx - 1), mesh.nx) * 1e9
        y = np.linspace(0, mesh.dy * (mesh.ny - 1), mesh.ny) * 1e9
        z = np.linspace(0, mesh.dz * (mesh.nz - 1), mesh.nz) * 1e9
        
        # Plot mesh grid lines
        stride_x = max(1, mesh.nx // 8)
        stride_y = max(1, mesh.ny // 8)
        stride_z = max(1, mesh.nz // 8)
        
        for i in range(0, mesh.nx, stride_x):
            for j in range(0, mesh.ny, stride_y):
                ax.plot(x[i] * np.ones(mesh.nz), y[j] * np.ones(mesh.nz), z, 
                       'b-', alpha=0.3, linewidth=0.8)
        
        for i in range(0, mesh.nx, stride_x):
            for k in range(0, mesh.nz, stride_z):
                ax.plot(x[i] * np.ones(mesh.ny), y, z[k] * np.ones(mesh.ny), 
                       'r-', alpha=0.3, linewidth=0.8)
        
        for j in range(0, mesh.ny, stride_y):
            for k in range(0, mesh.nz, stride_z):
                ax.plot(x, y[j] * np.ones(mesh.nx), z[k] * np.ones(mesh.nx), 
                       'g-', alpha=0.3, linewidth=0.8)
        
        # Plot nodes
        X_mesh, Y_mesh, Z_mesh = np.meshgrid(x, y, z, indexing='ij')
        ax.scatter(X_mesh.ravel(), Y_mesh.ravel(), Z_mesh.ravel(), 
                  c='gray', s=8, alpha=0.4)
        
        ax.set_xlabel('x [nm]', fontsize=12, fontweight='bold')
        ax.set_ylabel('y [nm]', fontsize=12, fontweight='bold')
        ax.set_zlabel('z [nm]', fontsize=12, fontweight='bold')
        ax.set_title(f'{title}\n({mesh.nx}×{mesh.ny}×{mesh.nz} = {mesh.npts()} nodes)', 
                    fontsize=13, fontweight='bold', pad=20)
    
    plt.tight_layout()
    plt.savefig('mesh_discretization.png', dpi=300, bbox_inches='tight')
    print("Saved: mesh_discretization.png")
    plt.close()


def main():
    """Main function"""
    print("=" * 70)
    print("FinFET and GAA Device Structure Visualization")
    print("=" * 70)
    
    # Create FinFET structure
    finfet_mesh, finfet_results = create_finfet_structure_plot()
    
    # Create GAA structure
    gaa_mesh, gaa_results = create_gaa_structure_plot()
    
    # Create mesh plots
    create_mesh_plots(finfet_mesh, gaa_mesh)
    
    print("\n" + "=" * 70)
    print("Visualization Complete!")
    print("=" * 70)
    print("\nGenerated files:")
    print("  - finfet_3d_structure.png")
    print("  - gaa_3d_structure.png")
    print("  - mesh_discretization.png")


if __name__ == '__main__':
    main()
