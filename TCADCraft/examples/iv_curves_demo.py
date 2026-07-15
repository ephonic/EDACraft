#!/usr/bin/env python3
"""
Publication-Quality I-V Curve Plotting Demo

This script demonstrates how to create beautiful I-V characteristic plots
using simulated data. The plotting style can be applied to actual simulation results.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

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


def generate_transfer_data():
    """Generate simulated transfer characteristics data"""
    Vg = np.linspace(0, 1.5, 20)
    
    # Simulate Id-Vg curves for different Vd
    Vd_values = [0.1, 0.5, 1.0]
    Id_data = {}
    
    for Vd in Vd_values:
        # Simplified MOSFET model
        Vth = 0.4  # Threshold voltage
        mu = 0.1   # Mobility factor
        Id = np.where(Vg > Vth, 
                     mu * (Vg - Vth) * Vd * 1e-3,  # Linear region
                     1e-12)  # Subthreshold
        Id_data[Vd] = Id
    
    return Vg, Id_data


def generate_output_data():
    """Generate simulated output characteristics data"""
    Vd = np.linspace(0, 1.5, 20)
    
    # Simulate Id-Vd curves for different Vg
    Vg_values = [0.5, 0.8, 1.1, 1.4]
    Id_data = {}
    
    for Vg in Vg_values:
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
        
        Id_data[Vg] = Id
    
    return Vd, Id_data


def plot_transfer_curves():
    """Plot transfer characteristics"""
    print("Generating transfer characteristics...")
    
    Vg, Id_data = generate_transfer_data()
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    markers = ['o', 's', '^']
    
    for idx, (Vd, Id) in enumerate(Id_data.items()):
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
    plt.savefig('iv_transfer_characteristics.png', dpi=300, bbox_inches='tight')
    print("Saved: iv_transfer_characteristics.png")
    plt.close()


def plot_output_curves():
    """Plot output characteristics"""
    print("Generating output characteristics...")
    
    Vd, Id_data = generate_output_data()
    
    fig, ax = plt.subplots(figsize=(9, 7))
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    markers = ['o', 's', '^', 'D']
    
    for idx, (Vg, Id) in enumerate(Id_data.items()):
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
    plt.savefig('iv_output_characteristics.png', dpi=300, bbox_inches='tight')
    print("Saved: iv_output_characteristics.png")
    plt.close()


def plot_comparison():
    """Create a comparison plot showing both characteristics"""
    print("Generating comparison plot...")
    
    Vg_transfer, Id_transfer = generate_transfer_data()
    Vd_output, Id_output = generate_output_data()
    
    fig = plt.figure(figsize=(16, 12))
    gs = GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3)
    
    # Transfer characteristics - Linear
    ax1 = fig.add_subplot(gs[0, 0])
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    for idx, (Vd, Id) in enumerate(Id_transfer.items()):
        ax1.plot(Vg_transfer, Id, 'o-', linewidth=2, markersize=6,
                label=f'Vd = {Vd}V', color=colors[idx])
    ax1.set_xlabel('Vg [V]', fontweight='bold')
    ax1.set_ylabel('Id [A]', fontweight='bold')
    ax1.set_title('Transfer (Linear)', fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Transfer characteristics - Log
    ax2 = fig.add_subplot(gs[0, 1])
    for idx, (Vd, Id) in enumerate(Id_transfer.items()):
        ax2.semilogy(Vg_transfer, np.maximum(Id, 1e-15), 'o-', 
                    linewidth=2, markersize=6,
                    label=f'Vd = {Vd}V', color=colors[idx])
    ax2.set_xlabel('Vg [V]', fontweight='bold')
    ax2.set_ylabel('Id [A]', fontweight='bold')
    ax2.set_title('Transfer (Log)', fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Output characteristics
    ax3 = fig.add_subplot(gs[1, :])
    colors_out = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    for idx, (Vg, Id) in enumerate(Id_output.items()):
        ax3.plot(Vd_output, Id, 'o-', linewidth=2, markersize=6,
                label=f'Vg = {Vg}V', color=colors_out[idx])
    ax3.set_xlabel('Vd [V]', fontweight='bold')
    ax3.set_ylabel('Id [A]', fontweight='bold')
    ax3.set_title('Output Characteristics', fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    plt.suptitle('MOSFET I-V Characteristics', 
                fontsize=16, fontweight='bold', y=0.995)
    plt.savefig('iv_characteristics_comparison.png', dpi=300, bbox_inches='tight')
    print("Saved: iv_characteristics_comparison.png")
    plt.close()


def main():
    """Main workflow"""
    print("\n" + "=" * 70)
    print("Publication-Quality I-V Curve Plotting Demo")
    print("=" * 70 + "\n")
    
    plot_transfer_curves()
    plot_output_curves()
    plot_comparison()
    
    print("\n" + "=" * 70)
    print("Plot Generation Complete!")
    print("=" * 70)
    print("\nGenerated files:")
    print("  - iv_transfer_characteristics.png")
    print("  - iv_output_characteristics.png")
    print("  - iv_characteristics_comparison.png")
    print("\nNote: These plots use simulated data to demonstrate the plotting style.")
    print("Apply the same plotting code to your actual simulation results.")


if __name__ == '__main__':
    main()
