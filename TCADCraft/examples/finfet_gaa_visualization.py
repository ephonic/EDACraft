#!/usr/bin/env python3
"""
FinFET and GAA Device Visualization - Using Existing Results

This script creates publication-quality visualizations using existing simulation data.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
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


def plot_existing_finfet_results():
    """Plot existing FinFET simulation results"""
    print("Creating FinFET visualization from existing results...")
    
    # Check for existing images
    finfet_3d = Path('finfet_3d.png')
    finfet_slices = Path('finfet_slices.png')
    
    if not finfet_3d.exists():
        print("Warning: finfet_3d.png not found")
        return
    
    # Create figure with existing images
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # Plot 3D structure
    img_3d = plt.imread(finfet_3d)
    axes[0].imshow(img_3d)
    axes[0].set_title('FinFET 3D Electron Density', fontweight='bold', fontsize=14)
    axes[0].axis('off')
    
    # Plot slices
    if finfet_slices.exists():
        img_slices = plt.imread(finfet_slices)
        axes[1].imshow(img_slices)
        axes[1].set_title('FinFET 2D Field Slices', fontweight='bold', fontsize=14)
        axes[1].axis('off')
    
    plt.suptitle('FinFET Device Simulation Results', 
                fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig('finfet_visualization.png', dpi=300, bbox_inches='tight')
    print("Saved: finfet_visualization.png")
    plt.close()


def plot_output_characteristics_demo():
    """Plot output characteristics using simulated data"""
    print("\nGenerating output characteristics...")
    
    # Generate simulated output characteristics
    Vd = np.linspace(0, 1.5, 30)
    Vg_values = [0.5, 0.8, 1.1, 1.4]
    
    fig, ax = plt.subplots(figsize=(9, 7))
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    markers = ['o', 's', '^', 'D']
    
    for idx, Vg in enumerate(Vg_values):
        # Simplified MOSFET model with saturation
        Vth = 0.4
        mu = 0.1
        Id = np.zeros_like(Vd)
        
        for i, v in enumerate(Vd):
            if Vg > Vth:
                if v < (Vg - Vth):  # Linear region
                    Id[i] = mu * ((Vg - Vth) * v - 0.5 * v**2) * 1e-3
                else:  # Saturation region
                    Id[i] = 0.5 * mu * (Vg - Vth)**2 * 1e-3
            else:
                Id[i] = 1e-12
        
        ax.plot(Vd, Id, marker=markers[idx], linewidth=2.5, markersize=8,
               label=f'Vg = {Vg}V', color=colors[idx], alpha=0.8)
    
    ax.set_xlabel('Drain Voltage Vd [V]', fontweight='bold', fontsize=13)
    ax.set_ylabel('Drain Current Id [A]', fontweight='bold', fontsize=13)
    ax.set_title('Output Characteristics (Id-Vd)', 
                fontweight='bold', fontsize=14, pad=15)
    ax.legend(fontsize=12, loc='upper left', framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_ylim(bottom=0)
    ax.set_xlim(left=0)
    
    # Add saturation region annotation
    ax.axvline(x=0.7, color='gray', linestyle=':', alpha=0.5, linewidth=1.5)
    ax.annotate('Saturation\nRegion', xy=(1.0, 0.3e-3), 
                fontsize=11, color='gray', fontweight='bold',
                ha='center')
    
    plt.tight_layout()
    plt.savefig('output_characteristics.png', dpi=300, bbox_inches='tight')
    print("Saved: output_characteristics.png")
    plt.close()


def plot_device_comparison():
    """Create device comparison plot"""
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


def plot_transfer_curves():
    """Plot transfer characteristics"""
    print("\nGenerating transfer characteristics...")
    
    Vg = np.linspace(0, 1.5, 30)
    Vd_values = [0.1, 0.5, 1.0]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    markers = ['o', 's', '^']
    
    for idx, Vd in enumerate(Vd_values):
        # Simplified MOSFET model
        Vth = 0.4
        mu = 0.1
        Id = np.where(Vg > Vth, 
                     mu * (Vg - Vth) * Vd * 1e-3,
                     1e-12)
        
        # Linear scale
        ax1.plot(Vg, Id, marker=markers[idx], linewidth=2.5, markersize=8,
                label=f'Vd = {Vd}V', color=colors[idx], alpha=0.8)
        
        # Log scale
        ax2.semilogy(Vg, np.maximum(Id, 1e-15), marker=markers[idx], 
                    linewidth=2.5, markersize=8,
                    label=f'Vd = {Vd}V', color=colors[idx], alpha=0.8)
    
    # Format linear plot
    ax1.set_xlabel('Gate Voltage Vg [V]', fontweight='bold', fontsize=13)
    ax1.set_ylabel('Drain Current Id [A]', fontweight='bold', fontsize=13)
    ax1.set_title('Transfer Characteristics (Linear Scale)', 
                 fontweight='bold', fontsize=14, pad=15)
    ax1.legend(fontsize=12, loc='upper left', framealpha=0.9)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.set_ylim(bottom=0)
    ax1.set_xlim(left=0)
    
    # Format log plot
    ax2.set_xlabel('Gate Voltage Vg [V]', fontweight='bold', fontsize=13)
    ax2.set_ylabel('Drain Current Id [A]', fontweight='bold', fontsize=13)
    ax2.set_title('Transfer Characteristics (Log Scale)', 
                 fontweight='bold', fontsize=14, pad=15)
    ax2.legend(fontsize=12, loc='upper left', framealpha=0.9)
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.set_xlim(left=0)
    
    # Add threshold voltage annotation
    ax1.axvline(x=0.4, color='red', linestyle='--', alpha=0.5, linewidth=1.5)
    ax1.annotate('Vth', xy=(0.4, 0.5e-3), xytext=(0.5, 1e-3),
                fontsize=11, color='red', fontweight='bold',
                arrowprops=dict(arrowstyle='->', color='red', lw=1.5))
    
    plt.tight_layout()
    plt.savefig('transfer_characteristics.png', dpi=300, bbox_inches='tight')
    print("Saved: transfer_characteristics.png")
    plt.close()


def main():
    """Main visualization workflow"""
    print("\n" + "=" * 70)
    print("FinFET and GAA Device Visualization Suite")
    print("=" * 70 + "\n")
    
    # Plot existing FinFET results
    plot_existing_finfet_results()
    
    # Generate I-V characteristics
    plot_transfer_curves()
    plot_output_characteristics_demo()
    
    # Create device comparison
    plot_device_comparison()
    
    print("\n" + "=" * 70)
    print("Visualization Complete!")
    print("=" * 70)
    print("\nGenerated files:")
    print("  - finfet_visualization.png")
    print("  - transfer_characteristics.png")
    print("  - output_characteristics.png")
    print("  - device_comparison.png")


if __name__ == '__main__':
    main()
