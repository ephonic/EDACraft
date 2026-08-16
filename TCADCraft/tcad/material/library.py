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


# Per-material scalar DG closure masses (multiples of m_0). A simulator whose
# reference model separates a DOS mass and gamma factor should use
# Simulator.set_density_gradient_effective_masses instead.
# Insulators/metals (μ=0) carry DG coefficients for completeness only; their
# value is irrelevant because the solver skips them (mu_n < EPSILON).
_M_STAR_SI_N = 0.26    # historical scalar electron DG closure mass
_M_STAR_SI_P = 0.37    # historical scalar hole DG closure mass
_M_STAR_INSULATOR = 0.5   # nominal for SiO2/HfO2/HfZrO/Al2O3
_M_STAR_METAL = 1.0       # nominal for TiN/W
_M_STAR_GRAPHENE = 0.5    # conservative (true Dirac mass is regime-dependent)
_M_STAR_MOS2_N = 0.45
_M_STAR_MOS2_P = 0.60
_M_STAR_IGZO_N = 0.34
_M_STAR_WSE2_N = 0.35
_M_STAR_WSE2_P = 0.45
_M_STAR_GAN_N = 0.20
_M_STAR_GAN_P = 0.80


def silicon() -> Material:
    """Crystalline silicon baseline.

    Includes the Chynoweth avalanche impact-ionization coefficients
    (Overstraeten-De Man 1970), pre-converted to SI (1/m, V/m) — see
    ImpactIonizationParams in src/gummel_solver.h for the provenance. These
    populate the per-node ``ii_*`` mesh fields and are auto-applied when
    ``Simulator.set_impact_ionization(True)`` reads them.
    """
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
        # Avalanche impact ionization (Chynoweth, SI units). M7a.
        ii_A_n=7.03e7,    # electrons [1/m]
        ii_B_n=1.231e8,   # [V/m]
        ii_A_p=1.58e8,    # holes [1/m]
        ii_B_p=2.036e8,   # [V/m]
    )


def gallium_nitride() -> Material:
    """Wurtzite GaN baseline aligned to the Sentaurus W-2024.09 benchmark.

    The electron affinity (3.9358 eV) makes a 4.80 eV metal a 0.8642 eV
    Schottky barrier, as extracted from the thermionic branch of the checked-in
    calibration deck.  Mobility and lifetime match ``schottky.par``.  These
    are synthetic-reference defaults and should be overridden by process data
    when a specific epitaxial stack is known.
    """
    return Material(
        name="GaN",
        epsilon_r=9.5,
        Eg=3.40,
        chi=3.93579972,
        Nc=2.3e18,
        Nv=4.6e19,
        mu_n=1800.0,
        mu_p=150.0,
        tau_n=1.0e-9,
        tau_p=1.0e-9,
        b_n=dg_coefficient(_M_STAR_GAN_N),
        b_p=dg_coefficient(_M_STAR_GAN_P),
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
        E_bd=1.2e9,   # intrinsic breakdown field ~12 MV/cm (M7b)
        Dit=1.0e11,   # interface trap density ~1e11 cm^-2 eV^-1 (P6)
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
        E_bd=6.0e8,   # intrinsic breakdown field ~6 MV/cm (M7b)
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
        fe_ps=0.0,    # derive from L-K alpha/beta (Ps = sqrt(-alpha/beta) ~ 18 uC/cm^2)
        fe_ec=0.0,
        E_bd=6.0e8,   # intrinsic breakdown field ~6 MV/cm (M7b)
        Dit=5.0e11,   # interface trap density (P6)
    )


def alscn(sc_fraction: float = 0.27) -> Material:
    """AlScN (wurtzite aluminum scandium nitride) ferroelectric.

    AlScN is an emerging wurtzite-structured ferroelectric with a very large
    spontaneous polarization. sc_fraction is the Sc/(Sc+Al) fraction; ~0.27
    maximizes ferroelectric response.

    Key targets (from experimental PUND, see comments.docx):
      Ps ~ 130-150 uC/cm^2 (= 1.3-1.5 C/m^2)
      Ec ~ 3-4 MV/cm (= 3-5e8 V/m; a 40 nm film switches at ~12-16 V)

    The Landau coefficients are reverse-engineered so the cubic L-K double well
    reproduces the target Ps and Ec:
        Ps = sqrt(-alpha/beta)
        Ec = (2|alpha|/3) * sqrt(-alpha/(3*beta)) = 2*beta*Ps^3 / (3*sqrt(3))
    =>  beta = Ec * 3*sqrt(3) / (2*Ps^3),   alpha = -beta * Ps^2.
    (P1.4.)

    The direct Preisach parameters fe_ps/fe_ec are also set, so the Preisach and
    NLS models can be parameterised without the L-K dimensional ambiguity.
    epsilon_r ~ 15 is well BELOW the old [25,50] HfZrO detection window, so
    material-driven FE detection (fe_alpha != 0) is essential here.
    """
    import math
    Ps = 1.4               # C/m^2 (140 uC/cm^2)
    Ec = 3.5e8             # V/m (3.5 MV/cm)
    sqrt3 = math.sqrt(3.0)
    fe_beta = Ec * 3.0 * sqrt3 / (2.0 * Ps ** 3)    # ~3.31e8
    fe_alpha = -fe_beta * Ps * Ps                     # ~-6.49e8
    epsilon_r = 15.0       # Al(1-x)Sc(x)N, x~0.27
    return Material(
        name=f"AlScN_x{sc_fraction:.2f}",
        epsilon_r=epsilon_r,
        Eg=5.5,
        chi=1.5,
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
        fe_ps=Ps,          # direct saturation polarization for Preisach/NLS
        fe_ec=Ec,
        E_bd=6.0e8,        # breakdown field ~6 MV/cm
        Dit=5.0e11,        # interface trap density (P6)
        Q_ot_max=1.0e5,    # max accumulated oxide trap charge [C/m^3] (P7)
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


def amorphous_igzo() -> Material:
    """Room-temperature a-IGZO channel with tail/percolation metadata.

    The numerical values are representative starting points, not a process
    calibration. Call :meth:`Simulator.set_disordered_transport` to activate
    the exponential-tail DOS and temperature-dependent percolation mobility,
    and :meth:`Simulator.create_pbti_trap_model` for stateful PBTI stress.
    """
    return Material(
        name="a-IGZO",
        epsilon_r=10.0,
        Eg=3.05,
        chi=4.16,
        Nc=5.0e18,
        Nv=1.0e20,
        mu_n=15.0,
        mu_p=1.0e-4,
        tau_n=1.0e-6,
        tau_p=1.0e-8,
        b_n=dg_coefficient(_M_STAR_IGZO_N),
        b_p=dg_coefficient(1.0),
        tail_DOS=1.0e20,
        urbach_energy=0.05,
        percolation_energy=0.075,
        pbti_Nt=5.0e18,
        pbti_Et=0.35,
        pbti_capture_tau=1.0,
        pbti_emission_tau=1.0e4,
    )


def wse2_channel() -> Material:
    """Monolayer-like WSe2 channel baseline for ambipolar Schottky FETs.

    Contact barriers must be supplied explicitly with
    ``Simulator.set_contact(..., workfunction=...)``. The ideal thermionic
    boundary does not silently assume an ohmic source/drain.
    """
    return Material(
        name="WSe2",
        epsilon_r=7.0,
        Eg=1.65,
        chi=3.9,
        Nc=1.5e19,
        Nv=1.8e19,
        mu_n=50.0,
        mu_p=150.0,
        tau_n=1.0e-7,
        tau_p=1.0e-7,
        b_n=dg_coefficient(_M_STAR_WSE2_N),
        b_p=dg_coefficient(_M_STAR_WSE2_P),
    )
