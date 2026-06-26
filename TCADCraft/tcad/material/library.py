"""Predefined material library for Si-compatible CMOS devices."""

from __future__ import annotations
from tcad.geometry.device_builder import Material


# ---------------------------------------------------------------------------
# Density-gradient (DG) quantum-correction coefficient.
#
# Phase 3.5 fix (audit §16): the DG model computes
#     Qn = b_n · ∇²√n/√n        (density_gradient.cpp:57)
#     n_q = n · exp(-Qn / VT)   (line 74)
# so Qn MUST be in volts for exp(-Qn/VT) to be meaningful.  Since ∇²√n/√n has
# units m⁻², b_n must have units V·m².  The standard DG coefficient is
#     b = ħ² / (6 · q · m*)    [V·m²]
# (Ancona-Stafford, with the 1/6 from the DG closure).  The previous default
# 3.86e-6 was dimensionless, giving Qn ~ 1e10..1e12 and an exponent far
# outside the solver's [-10,10] clamp — so DG silently did nothing useful.
#
# `dg_coefficient(m_star_ratio)` returns b in V·m² for an effective mass
# expressed as a multiple of m_0.
# ---------------------------------------------------------------------------
_HBAR = 1.054571817e-34       # J·s
_QE = 1.602176634e-19         # C
_M0 = 9.1093837015e-31        # kg


def dg_coefficient(m_star_ratio: float) -> float:
    """DG b = ħ²/(6·q·m*) in V·m² for m* = m_star_ratio · m_0.

    Examples: Si electron (m*=0.26) -> 4.9e-20 V·m²;
    Si hole (m*=0.37) -> 3.4e-20 V·m².
    """
    return _HBAR * _HBAR / (6.0 * _QE * m_star_ratio * _M0)


# Per-material DOS effective masses (multiples of m_0).
# Insulators/metals (μ=0) carry DG coefficients for completeness only; their
# value is irrelevant because the solver skips them (mu_n < EPSILON).
_M_STAR_SI_N = 0.26    # Si electron DOS mass
_M_STAR_SI_P = 0.37    # Si hole DOS mass
_M_STAR_INSULATOR = 0.5   # nominal for SiO2/HfO2/HfZrO/Al2O3
_M_STAR_METAL = 1.0       # nominal for TiN/W
_M_STAR_GRAPHENE = 0.5    # conservative (true Dirac mass is regime-dependent)
_M_STAR_MOS2_N = 0.45
_M_STAR_MOS2_P = 0.60


def silicon() -> Material:
    """Crystalline silicon baseline."""
    return Material(
        name="Si",
        epsilon_r=11.7,
        Eg=1.12,
        chi=4.05,
        Nc=2.8e19,
        Nv=1.04e19,
        mu_n=1400.0,
        mu_p=450.0,
        tau_n=1e-6,
        tau_p=1e-6,
        b_n=dg_coefficient(_M_STAR_SI_N),
        b_p=dg_coefficient(_M_STAR_SI_P),
    )


def sio2() -> Material:
    """Silicon dioxide gate dielectric."""
    return Material(
        name="SiO2",
        epsilon_r=3.9,
        Eg=9.0,
        chi=0.9,
        Nc=1.0e19,
        Nv=1.0e19,
        mu_n=0.0,
        mu_p=0.0,
        tau_n=1e-7,
        tau_p=1e-7,
        b_n=dg_coefficient(_M_STAR_INSULATOR),
        b_p=dg_coefficient(_M_STAR_INSULATOR),
    )


def hfo2(kappa: float = 25.0) -> Material:
    """Hafnium oxide high-k dielectric.

    kappa: relative permittivity, typically 20–30 depending on processing.
    """
    return Material(
        name="HfO2",
        epsilon_r=kappa,
        Eg=5.7,
        chi=2.0,
        Nc=1.0e19,
        Nv=1.0e19,
        mu_n=0.0,
        mu_p=0.0,
        tau_n=1e-7,
        tau_p=1e-7,
        b_n=dg_coefficient(_M_STAR_INSULATOR),
        b_p=dg_coefficient(_M_STAR_INSULATOR),
    )


def hfzro(hf_ratio: float = 0.5) -> Material:
    """HfZrO ferroelectric dielectric.

    hf_ratio: Hf/(Hf+Zr) fraction. ~0.5 gives best ferroelectric properties.
    Returns a material with ferroelectric-like parameters.
    The ferroelectric behavior is modeled via Landau-Khalatnikov in the solver,
    not through static material parameters.
    """
    # HfZrO parameters: epsilon ~30-40, bandgap ~5.5 eV
    # Landau coefficients (quasi-static): alpha < 0, beta > 0
    # These are stored as extra attributes for the solver to pick up
    epsilon_r = 30.0 + 10.0 * hf_ratio
    # Landau coefficients (quasi-static): alpha < 0, beta > 0
    # Typical values for HfZrO ferroelectric phase
    fe_alpha = -5.0e8
    fe_beta = 1.5e10
    return Material(
        name=f"HfZrO_x{hf_ratio:.1f}",
        epsilon_r=epsilon_r,
        Eg=5.5,
        chi=1.9,
        Nc=1.0e19,
        Nv=1.0e19,
        mu_n=0.0,
        mu_p=0.0,
        tau_n=1e-7,
        tau_p=1e-7,
        b_n=dg_coefficient(_M_STAR_INSULATOR),
        b_p=dg_coefficient(_M_STAR_INSULATOR),
        fe_alpha=fe_alpha,
        fe_beta=fe_beta,
    )


def sige(ge_fraction: float = 0.3) -> Material:
    """Strained Si1-xGex alloy.

    ge_fraction: Ge mole fraction x (0–0.5 for strained layers on Si).
    Reduces bandgap and increases hole mobility vs pure Si.
    """
    # Vegard's law interpolation
    si = silicon()
    Eg_si = 1.12
    Eg_ge = 0.66  # Ge indirect gap
    x = min(ge_fraction, 0.5)
    # Strained SiGe on Si: additional strain-induced bandgap reduction
    Eg = Eg_si - 0.75 * x + 0.35 * x * x  # eV (empirical)
    # Mobility: hole mobility increases significantly with Ge
    mu_p = 450.0 + 1200.0 * x
    mu_n = 1400.0 - 800.0 * x
    return Material(
        name=f"SiGe_x{x:.2f}",
        epsilon_r=11.7 + 4.3 * x,
        Eg=Eg,
        chi=4.05 + 0.5 * x,  # electron affinity increases
        Nc=2.8e19,
        Nv=1.04e19 * (1 + 2.0 * x),
        mu_n=mu_n,
        mu_p=mu_p,
        tau_n=1e-6,
        tau_p=1e-6,
        b_n=dg_coefficient(_M_STAR_SI_N),   # SiGe ~ Si-like
        b_p=dg_coefficient(_M_STAR_SI_P),
    )


def al2o3() -> Material:
    """Aluminum oxide interfacial layer."""
    return Material(
        name="Al2O3",
        epsilon_r=9.0,
        Eg=8.8,
        chi=1.2,
        Nc=1.0e19,
        Nv=1.0e19,
        mu_n=0.0,
        mu_p=0.0,
        tau_n=1e-7,
        tau_p=1e-7,
        b_n=dg_coefficient(_M_STAR_INSULATOR),
        b_p=dg_coefficient(_M_STAR_INSULATOR),
    )


def titanium_nitride() -> Material:
    """TiN metal gate workfunction ~4.6 eV (n-type workfunction metal)."""
    return Material(
        name="TiN",
        epsilon_r=1.0,
        Eg=0.0,
        chi=4.6,
        Nc=1.0e19,
        Nv=1.0e19,
        mu_n=0.0,
        mu_p=0.0,
        tau_n=1e-7,
        tau_p=1e-7,
        b_n=dg_coefficient(_M_STAR_METAL),
        b_p=dg_coefficient(_M_STAR_METAL),
    )


def tungsten() -> Material:
    """Tungsten contact metal workfunction ~4.5 eV."""
    return Material(
        name="W",
        epsilon_r=1.0,
        Eg=0.0,
        chi=4.5,
        Nc=1.0e19,
        Nv=1.0e19,
        mu_n=0.0,
        mu_p=0.0,
        tau_n=1e-7,
        tau_p=1e-7,
        b_n=dg_coefficient(_M_STAR_METAL),
        b_p=dg_coefficient(_M_STAR_METAL),
    )


def graphene_source() -> Material:
    """Graphene Dirac-source material for DSFET.

    Graphene is a zero-gap semiconductor (semi-metal) with a linear
    dispersion relation. In a Dirac-Source FET, the unique DOS profile
    DOS(E) ~ |E-E_D| suppresses the high-energy thermal tail of electron
    injection, enabling steep subthreshold switching.

    For TCAD drift-diffusion modelling, we use an *effective* 3D DOS
    (Nc, Nv) that is much smaller than Si to approximate the cold-source
    injection effect in the subthreshold region.
    """
    return Material(
        name="Graphene",
        epsilon_r=2.5,          # Effective epsilon on SiO2/Si substrate
        Eg=0.0,                 # Zero bandgap (semi-metal)
        chi=4.5,                # Workfunction ~4.5 eV
        Nc=1.0e17,              # Effective 3D DOS [cm^-3], much smaller than Si
        Nv=1.0e17,
        mu_n=200000.0,          # Extremely high mobility [cm^2/(V·s)]
        mu_p=200000.0,
        tau_n=1e-7,
        tau_p=1e-7,
        b_n=dg_coefficient(_M_STAR_GRAPHENE),
        b_p=dg_coefficient(_M_STAR_GRAPHENE),
    )


def mos2_channel() -> Material:
    """Monolayer MoS2 channel material for 2D FETs.

    MoS2 is a transition metal dichalcogenide (TMD) with a direct
    bandgap (~1.8 eV) in monolayer form, offering excellent electrostatic
    control for ultra-scaled transistors.
    """
    return Material(
        name="MoS2",
        epsilon_r=4.5,
        Eg=1.8,
        chi=4.0,
        Nc=2.0e19,
        Nv=1.5e19,
        mu_n=200.0,
        mu_p=50.0,
        tau_n=1e-7,
        tau_p=1e-7,
        b_n=dg_coefficient(_M_STAR_MOS2_N),
        b_p=dg_coefficient(_M_STAR_MOS2_P),
    )
