"""Device grammar tree: structural primitives + connection rules + build().

Reverse-induces the 14 device templates in ``device_builder.Device`` into a
declarative, semantically-typed tree so that ``build(tree)`` reproduces each
template's exact region sequence and contact geometry (structural per-region
equivalence — the C1 truth-chain, plan0619.md §C1).

Design (confirmed with user):
- **Primitive-composition abstraction.** Nodes carry a semantic *kind*
  (Channel/Source/Drain/Oxide/HighK/Ferroelectric/IL_Oxide/Metal/Substrate/
  BOX/Via/Rail) plus *resolved* geometry (Box bounds) + material + doping.
  Geometry is resolved at ``tree_from_template`` time (which mirrors each
  template's parametric arithmetic) so ``build()`` is a pure ordered emitter
  and byte-equivalence is guaranteed by construction.
- **Structural per-region equivalence.** ``assert_devices_equal`` compares
  region count, per-region (material fields, doping Nd/Na, Box sextuple), and
  per-contact (name, Box sextuple, voltage). No solver runs needed.

The semantic *kind* is what makes C2 mutation meaningful ("swap the Source
material" / "insert a Ferroelectric layer") rather than operating on opaque
region indices, and is what ``validate()`` reasons over.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Tuple

from ..geometry import Box, Device, Material, Region, DopingProfile


# ---------------------------------------------------------------------------
# Semantic kinds
# ---------------------------------------------------------------------------

#: Region semantic kinds.  Used by ``validate`` and C2 mutation operators to
#: reason structurally rather than over opaque region indices.
KIND_CHANNEL = "channel"
KIND_SOURCE = "source"
KIND_DRAIN = "drain"
KIND_WIRE = "wire"          # junctionless: single uniform segment
KIND_P_SIDE = "p_side"      # pnjunction / tunnel_diode
KIND_N_SIDE = "n_side"
KIND_OXIDE = "oxide"        # gate dielectric (SiO2)
KIND_HIGHK = "highk"        # gate dielectric (high-k)
KIND_IL_OXIDE = "il_oxide"  # interfacial SiO2 under FE in FE gate stacks
KIND_FERROELECTRIC = "ferroelectric"
KIND_METAL = "metal"        # gate metal
KIND_SUBSTRATE = "substrate"
KIND_BOX = "box"            # buried oxide
KIND_VIA = "via"            # backside power via
KIND_RAIL = "rail"          # backside power rail

#: Gate-stack layer kinds, in the order they must appear (metal-side last).
GATE_DIELECTRIC_KINDS = (KIND_OXIDE, KIND_HIGHK, KIND_IL_OXIDE, KIND_FERROELECTRIC)

#: Wrap styles for a GateStack.
WRAP_NONE = "none"
WRAP_PLANAR_TOP = "planar_top"   # single top gate (mosfet)
WRAP_DOUBLE_Y = "double_y"       # left+right y-sides (finfet)
WRAP_FOUR_SIDE = "four_side"     # top+bottom+left+right (gaa family)


# ---------------------------------------------------------------------------
# Value specs
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MaterialSpec:
    """Pure-value material description; converts to ``device_builder.Material``.

    Covers all 14 fields of ``Material`` so dataclass ``__eq__`` is exact.
    """
    name: str = "Silicon"
    epsilon_r: float = 11.7
    Eg: float = 1.12
    chi: float = 4.05
    Nc: float = 2.8e19
    Nv: float = 1.04e19
    mu_n: float = 1400.0
    mu_p: float = 450.0
    tau_n: float = 1e-7
    tau_p: float = 1e-7
    b_n: float = 3.86e-6
    b_p: float = 3.86e-6
    fe_alpha: float = 0.0
    fe_beta: float = 0.0

    def to_material(self) -> Material:
        return Material(
            name=self.name, epsilon_r=self.epsilon_r, Eg=self.Eg, chi=self.chi,
            Nc=self.Nc, Nv=self.Nv, mu_n=self.mu_n, mu_p=self.mu_p,
            tau_n=self.tau_n, tau_p=self.tau_p, b_n=self.b_n, b_p=self.b_p,
            fe_alpha=self.fe_alpha, fe_beta=self.fe_beta,
        )


# Preset materials (match device_builder.py exactly).
SILICON = MaterialSpec("Silicon", epsilon_r=11.7, Eg=1.12)
SIO2 = MaterialSpec("SiO2", epsilon_r=3.9, Eg=9.0, mu_n=0.0, mu_p=0.0)
GATE_METAL = MaterialSpec("GateMetal", epsilon_r=1.0, mu_n=0.0, mu_p=0.0)
BACKSIDE_METAL = MaterialSpec("BacksideMetal", epsilon_r=1.0, mu_n=0.0, mu_p=0.0)


def highk_material(kappa: float, name: str = "HighK") -> MaterialSpec:
    """High-k dielectric (matches gaa_highk: epsilon_r=kappa, Eg=5.7)."""
    return MaterialSpec(name, epsilon_r=kappa, Eg=5.7, mu_n=0.0, mu_p=0.0)


def ferroelectric_material(kappa_fe: float, name: str = "HfZrO") -> MaterialSpec:
    """FE HfZrO (matches gaa_fefet: epsilon_r=kappa_fe, Eg=5.5, alpha=-5e8, beta=1.5e10)."""
    return MaterialSpec(
        name, epsilon_r=kappa_fe, Eg=5.5, mu_n=0.0, mu_p=0.0,
        fe_alpha=-5.0e8, fe_beta=1.5e10,
    )


GRAPHENE = MaterialSpec(
    "Graphene", epsilon_r=2.5, Eg=0.2, chi=4.5, Nc=1.0e17, Nv=1.0e17,
    mu_n=200000.0, mu_p=200000.0,
)


def sige_material(ge_fraction: float) -> MaterialSpec:
    """SiGe material parametric in Ge fraction (matches heterojunction_tfet)."""
    x = ge_fraction
    return MaterialSpec(
        name=f"SiGe_x{x:.2f}",
        epsilon_r=11.7 + 4.3 * x,
        Eg=1.12 - 0.75 * x + 0.35 * x * x,
        chi=4.05 + 0.5 * x,
        Nc=2.8e19,
        Nv=1.04e19 * (1.0 + 2.0 * x),
        mu_n=1400.0 - 800.0 * x,
        mu_p=450.0 + 1200.0 * x,
    )


@dataclass(frozen=True)
class DopingSpec:
    """Constant doping (Nd/Na in cm^-3).  14 templates use no functional doping."""
    Nd: float = 0.0
    Na: float = 0.0

    def to_profile(self) -> DopingProfile:
        return DopingProfile(Nd=self.Nd, Na=self.Na)


# ---------------------------------------------------------------------------
# Tree nodes
# ---------------------------------------------------------------------------

Box6 = Tuple[float, float, float, float, float, float]
#: A Box sextuple: (xmin, xmax, ymin, ymax, zmin, zmax).


@dataclass(frozen=True)
class RegionNode:
    """One declarative region: semantic kind + resolved geometry + material + doping.

    ``build()`` emits one ``Region`` per RegionNode in tree order (painter's
    algorithm — later regions override earlier where boxes overlap, matching
    ``Device.add_region`` semantics).

    Geometry is *resolved* (absolute Box bounds), not parametric: the
    parametric arithmetic lives in ``tree_from_template`` which mirrors each
    ``Device.<template>`` factory.  This guarantees ``build(tree)`` reproduces
    the factory's region list exactly.
    """
    kind: str
    name: str
    box: Box6
    material: MaterialSpec = SILICON
    doping: DopingSpec = DopingSpec()


@dataclass(frozen=True)
class ContactSpec:
    """One contact: resolved Box + voltage."""
    name: str
    box: Box6
    voltage: float = 0.0


@dataclass(frozen=True)
class GateStackMeta:
    """Metadata about the gate stack, for ``validate`` and C2 mutation.

    Carries the *intent* (wrap style, ordered layer kinds) separate from the
    resolved RegionNodes, so mutation operators can reason "insert an FE layer"
    without re-deriving geometry.
    """
    wrap: str = WRAP_NONE
    #: Ordered list of layer kinds as they appear from channel outward, e.g.
    #: ["oxide", "metal"] or ["il_oxide", "ferroelectric", "metal"].
    layer_kinds: Tuple[str, ...] = ()


@dataclass(frozen=True)
class DeviceTree:
    """A device described as an ordered list of RegionNodes + contacts + metadata.

    The ``region_nodes`` list is in painter's-algorithm emission order (the
    order ``Device.<template>`` calls ``add_region``).  ``gate_meta`` is
    optional structural metadata used by ``validate`` and C2; it is not
    required for ``build``.
    """
    name: str
    region_nodes: Tuple[RegionNode, ...]
    contacts: Tuple[ContactSpec, ...] = ()
    gate_meta: Optional[GateStackMeta] = None

    def regions(self) -> List[RegionNode]:
        return list(self.region_nodes)


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

def build(tree: DeviceTree) -> Device:
    """Emit a ``Device`` from a grammar tree.

    Iterates ``tree.region_nodes`` in order calling ``add_region`` (painter's
    algorithm), then adds contacts.  This is the inverse of
    ``tree_from_template``: ``build(tree_from_template(name, **p))`` must be
    structurally identical to ``Device.name(**p)``.
    """
    dev = Device(tree.name)
    for rn in tree.region_nodes:
        dev.add_region(Region(
            name=rn.name, shape=Box(*rn.box),
            material=rn.material.to_material(),
            doping=rn.doping.to_profile(),
        ))
    for c in tree.contacts:
        dev.add_contact(c.name, Box(*c.box), voltage=c.voltage)
    return dev


# ---------------------------------------------------------------------------
# Structural equivalence
# ---------------------------------------------------------------------------

def _box_of(dev: Device) -> List[Box]:
    return [r.shape for r in dev.regions]


def _box_sextuple(b: Box) -> Box6:
    return (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)


def _material_tuple(m: Material) -> tuple:
    return (
        m.name, m.epsilon_r, m.Eg, m.chi, m.Nc, m.Nv,
        m.mu_n, m.mu_p, m.tau_n, m.tau_p, m.b_n, m.b_p,
        m.fe_alpha, m.fe_beta,
    )


def assert_devices_equal(
    dev_a: Device,
    dev_b: Device,
    *,
    ignore_region_names: bool = False,
    ignore_region_order: bool = False,
) -> None:
    """Assert two Devices are structurally identical.

    Compares:
    - region count
    - per-region material (all 14 fields), doping (Nd/Na only — func ignored),
      and Box sextuple
    - per-contact name -> (Box sextuple, voltage)

    Parameters
    ----------
    ignore_region_names : bool
        If True, region ``name`` fields are not compared (they are cosmetic;
        painter's algorithm only depends on order + shape/material/doping).
    ignore_region_order : bool
        If True, regions are compared as a set (matched by Box+material+doping)
        rather than a sequence.  Use only for templates whose regions are
        mutually disjoint (e.g. pnjunction); the FET templates rely on order
        where S/D columns overlap the body.
    """
    ra, rb = dev_a.regions, dev_b.regions
    if len(ra) != len(rb):
        raise AssertionError(
            f"region count mismatch: {dev_a.name}={len(ra)} vs {dev_b.name}={len(rb)}"
        )

    def region_sig(r: Region):
        box = _box_sextuple(r.shape) if isinstance(r.shape, Box) else r.shape.bbox()
        mat = _material_tuple(r.material)
        dop = (r.doping.Nd, r.doping.Na)
        name = None if ignore_region_names else r.name
        return (name, box, mat, dop)

    sa = [region_sig(r) for r in ra]
    sb = [region_sig(r) for r in rb]
    if ignore_region_order:
        # Match each a-sig to a unique b-sig.
        sb_pool = list(sb)
        for i, sig in enumerate(sa):
            try:
                sb_pool.remove(sig)
            except ValueError:
                raise AssertionError(
                    f"region {i} of {dev_a.name} has no match in {dev_b.name}: {sig}"
                )
    else:
        for i, (ga, gb) in enumerate(zip(sa, sb)):
            if ga != gb:
                raise AssertionError(
                    f"region {i} mismatch between {dev_a.name} and {dev_b.name}:\n"
                    f"  direct : {ga}\n  built  : {gb}"
                )

    ca, cb = dev_a.contacts, dev_b.contacts
    if set(ca) != set(cb):
        raise AssertionError(
            f"contact name set mismatch: {set(ca)} vs {set(cb)}"
        )
    for name in ca:
        ba = _box_sextuple(ca[name][0]) if isinstance(ca[name][0], Box) else ca[name][0].bbox()
        bb = _box_sextuple(cb[name][0]) if isinstance(cb[name][0], Box) else cb[name][0].bbox()
        va = ca[name][1]
        vb = cb[name][1]
        if ba != bb:
            raise AssertionError(
                f"contact '{name}' box mismatch: {ba} vs {bb}"
            )
        if va != vb:
            raise AssertionError(
                f"contact '{name}' voltage mismatch: {va} vs {vb}"
            )


# ---------------------------------------------------------------------------
# validate (connection rules; used by C2 mutation post-check)
# ---------------------------------------------------------------------------

def validate(tree: DeviceTree) -> List[str]:
    """Return a list of connection-rule violations (empty if legal).

    Rules (plan0619.md §C2 line 97 — FE layer must be between dielectric and
    metal; here encoded as structural checks on the tree):
    - A gate stack (if ``gate_meta`` present) must have its layers ordered
      dielectric... (optional FE) ... metal, i.e. the first layer is a
      dielectric, the last is metal, and any ferroelectric layer is not the
      first or last.
    - Active segments (kinds channel/source/drain/wire/p_side/n_side) whose
      x-spans are adjacent must cover [0, x_total] without gaps or overlaps
      (the body/channel is allowed to underlap the full length only when there
      is no source/drain — e.g. mosfet body spans full x but S/D are
      sub-segments; we check the non-body active segments tile contiguously).
    - Contact names are drawn from the known set.
    """
    errors: List[str] = []
    meta = tree.gate_meta
    if meta is not None and meta.wrap != WRAP_NONE:
        kinds = meta.layer_kinds
        if not kinds:
            errors.append("gate stack has wrap but no layers")
        else:
            if kinds[0] not in (KIND_OXIDE, KIND_HIGHK, KIND_IL_OXIDE):
                errors.append(
                    f"gate stack first layer must be a dielectric, got {kinds[0]}"
                )
            if kinds[-1] != KIND_METAL:
                errors.append(
                    f"gate stack last layer must be metal, got {kinds[-1]}"
                )
            if KIND_FERROELECTRIC in kinds:
                fi = kinds.index(KIND_FERROELECTRIC)
                if fi == 0 or fi == len(kinds) - 1:
                    errors.append(
                        "ferroelectric layer must be between dielectric and metal, "
                        f"not at index {fi} of {kinds}"
                    )

    # Contact name whitelist.
    known = {
        "source", "drain", "gate", "bs_power",
        "p_contact", "n_contact", "anode", "cathode",
    }
    for c in tree.contacts:
        if c.name not in known:
            errors.append(f"unknown contact name '{c.name}'")

    return errors


# ---------------------------------------------------------------------------
# tree_from_template: reverse-induction of the 14 device templates
# ---------------------------------------------------------------------------

def _pnjunction_tree(
    L: float = 1e-6, W: float = 1e-6, H: float = 1e-6,
    x_junction: float = 0.5e-6, Na: float = 1e16, Nd: float = 1e16,
) -> DeviceTree:
    return DeviceTree(
        name="pn_junction",
        region_nodes=(
            RegionNode(KIND_P_SIDE, "p_side", (0, x_junction, 0, W, 0, H),
                       SILICON, DopingSpec(Na=Na)),
            RegionNode(KIND_N_SIDE, "n_side", (x_junction, L, 0, W, 0, H),
                       SILICON, DopingSpec(Nd=Nd)),
        ),
        contacts=(
            ContactSpec("p_contact", (0, 0.1e-6, 0, W, -0.01e-6, 0), 0.0),
            ContactSpec("n_contact", (L - 0.1e-6, L, 0, W, -0.01e-6, 0), 0.0),
        ),
    )


def _tunnel_diode_tree(
    Lp: float = 20e-9, Ln: float = 20e-9, W: float = 20e-9, H: float = 20e-9,
    Na: float = 5e20, Nd: float = 5e20,
) -> DeviceTree:
    x_total = Lp + Ln
    return DeviceTree(
        name="tunnel_diode",
        region_nodes=(
            RegionNode(KIND_P_SIDE, "p_side", (0, Lp, 0, W, 0, H),
                       SILICON, DopingSpec(Na=Na)),
            RegionNode(KIND_N_SIDE, "n_side", (Lp, x_total, 0, W, 0, H),
                       SILICON, DopingSpec(Nd=Nd)),
        ),
        contacts=(
            ContactSpec("anode", (0, Lp * 0.5, 0, W, -0.01e-6, 0), 0.0),
            ContactSpec("cathode", (x_total - Ln * 0.5, x_total, 0, W, -0.01e-6, 0), 0.0),
        ),
    )


def _mosfet_tree(
    Lg: float = 50e-9, tox: float = 1.5e-9, tsi: float = 10e-9,
    W: float = 100e-9, Lsd: float = 50e-9,
    Vg: float = 0.0, Vd: float = 0.0, Vs: float = 0.0,
) -> DeviceTree:
    x_total = 2 * Lsd + Lg
    ztop_metal = tsi + tox + 10e-9
    return DeviceTree(
        name="mosfet",
        region_nodes=(
            RegionNode(KIND_CHANNEL, "body", (0, x_total, 0, W, 0, tsi),
                       SILICON, DopingSpec(Na=1e16)),
            RegionNode(KIND_SOURCE, "source", (0, Lsd, 0, W, 0, ztop_metal),
                       SILICON, DopingSpec(Nd=1e20)),
            RegionNode(KIND_DRAIN, "drain", (x_total - Lsd, x_total, 0, W, 0, ztop_metal),
                       SILICON, DopingSpec(Nd=1e20)),
            RegionNode(KIND_OXIDE, "gate_oxide",
                       (Lsd, Lsd + Lg, 0, W, tsi, tsi + tox), SIO2),
            RegionNode(KIND_METAL, "gate_metal",
                       (Lsd, Lsd + Lg, 0, W, tsi + tox, tsi + tox + 10e-9), GATE_METAL),
        ),
        contacts=(
            ContactSpec("source", (0, Lsd, 0, W, -5e-9, 0), Vs),
            ContactSpec("drain", (x_total - Lsd, x_total, 0, W, -5e-9, 0), Vd),
            ContactSpec("gate", (Lsd, Lsd + Lg, 0, W, tsi + tox, tsi + tox + 5e-9), Vg),
        ),
        gate_meta=GateStackMeta(wrap=WRAP_PLANAR_TOP, layer_kinds=(KIND_OXIDE, KIND_METAL)),
    )


def _finfet_tree(
    Lg: float = 30e-9, tox: float = 1.5e-9, tsi: float = 10e-9,
    Hfin: float = 30e-9, Lsd: float = 30e-9, tgate: float = 10e-9,
    Vg: float = 0.0, Vd: float = 0.0, Vs: float = 0.0,
) -> DeviceTree:
    x_total = 2 * Lsd + Lg
    return DeviceTree(
        name="finfet",
        region_nodes=(
            RegionNode(KIND_CHANNEL, "body", (0, x_total, 0, tsi, 0, Hfin),
                       SILICON, DopingSpec(Na=1e16)),
            RegionNode(KIND_SOURCE, "source", (0, Lsd, 0, tsi, 0, Hfin),
                       SILICON, DopingSpec(Nd=1e20)),
            RegionNode(KIND_DRAIN, "drain", (x_total - Lsd, x_total, 0, tsi, 0, Hfin),
                       SILICON, DopingSpec(Nd=1e20)),
            RegionNode(KIND_OXIDE, "gate_oxide_left",
                       (Lsd, Lsd + Lg, -tox, 0, 0, Hfin), SIO2),
            RegionNode(KIND_OXIDE, "gate_oxide_right",
                       (Lsd, Lsd + Lg, tsi, tsi + tox, 0, Hfin), SIO2),
            RegionNode(KIND_METAL, "gate_metal_left",
                       (Lsd, Lsd + Lg, -tox - tgate, -tox, 0, Hfin), GATE_METAL),
            RegionNode(KIND_METAL, "gate_metal_right",
                       (Lsd, Lsd + Lg, tsi + tox, tsi + tox + tgate, 0, Hfin), GATE_METAL),
        ),
        contacts=(
            ContactSpec("source", (0, Lsd, 0, tsi, -5e-9, 0), Vs),
            ContactSpec("drain", (x_total - Lsd, x_total, 0, tsi, -5e-9, 0), Vd),
            ContactSpec("gate", (Lsd, Lsd + Lg, -tox - tgate, tsi + tox + tgate, -5e-9, 0), Vg),
        ),
        gate_meta=GateStackMeta(wrap=WRAP_DOUBLE_Y, layer_kinds=(KIND_OXIDE, KIND_METAL)),
    )


# ---------------------------------------------------------------------------
# GAA family helpers
# ---------------------------------------------------------------------------

def _four_side_oxide_regions(
    gate_x: Tuple[float, float], W: float, t_sheet: float, tox: float,
    material: MaterialSpec, name_prefix: str = "gate_oxide",
) -> List[RegionNode]:
    """Four-side wrapping oxide (top/bottom/left/right), gaa-family pattern.

    Matches the exact Box bounds used by gaa / junctionless_fet / bspdn_gaa /
    tfet / graphene_source_tfet / dirac_source_fet (all share this geometry).
    """
    x0, x1 = gate_x
    return [
        RegionNode(KIND_OXIDE, f"{name_prefix}_top",
                   (x0, x1, 0, W, t_sheet, t_sheet + tox), material),
        RegionNode(KIND_OXIDE, f"{name_prefix}_bottom",
                   (x0, x1, 0, W, -tox, 0), material),
        RegionNode(KIND_OXIDE, f"{name_prefix}_left",
                   (x0, x1, -tox, 0, -tox, t_sheet + tox), material),
        RegionNode(KIND_OXIDE, f"{name_prefix}_right",
                   (x0, x1, W, W + tox, -tox, t_sheet + tox), material),
    ]


def _four_side_metal_regions(
    gate_x: Tuple[float, float], W: float, t_sheet: float, tox: float,
    t_gate: float, metal_y_style: str, material: MaterialSpec = GATE_METAL,
) -> List[RegionNode]:
    """Four-side wrapping gate metal.

    ``metal_y_style`` selects the y-extent of top/bottom metal slabs:
    - "wide_ox"  : y in [-tox, W+tox]  (gaa/junctionless/bspdn/dsfet/gaa_fefet)
    - "narrow"   : y in [0, W]          (tfet/heterojunction_tfet/gs_tfet)
    - "wide_outer": y in [-t_outer, W+t_outer]  (dirac_source_fefet, t_outer=tox+t_fe)
    """
    x0, x1 = gate_x
    if metal_y_style == "narrow":
        y_lo, y_hi = 0.0, W
    elif metal_y_style == "wide_outer":
        y_lo, y_hi = -tox, W + tox   # here tox param carries t_outer
    else:  # "wide_ox"
        y_lo, y_hi = -tox, W + tox
    return [
        RegionNode(KIND_METAL, "gate_metal_top",
                   (x0, x1, y_lo, y_hi, t_sheet + tox, t_sheet + tox + t_gate), material),
        RegionNode(KIND_METAL, "gate_metal_bottom",
                   (x0, x1, y_lo, y_hi, -tox - t_gate, -tox), material),
        RegionNode(KIND_METAL, "gate_metal_left",
                   (x0, x1, -tox - t_gate, -tox, -tox - t_gate, t_sheet + tox + t_gate), material),
        RegionNode(KIND_METAL, "gate_metal_right",
                   (x0, x1, W + tox, W + tox + t_gate, -tox - t_gate, t_sheet + tox + t_gate), material),
    ]


def _gaa_tree(
    Lg: float = 20e-9, tox: float = 1.5e-9, t_sheet: float = 5e-9,
    W_sheet: float = 30e-9, Lsd: float = 30e-9, t_gate: float = 10e-9,
    t_box: float = 10e-9, Vg: float = 0.0, Vd: float = 0.0, Vs: float = 0.0,
) -> DeviceTree:
    x_total = 2 * Lsd + Lg
    gate_x = (Lsd, Lsd + Lg)
    nodes: List[RegionNode] = []
    # Substrate + BOX (under the active region).
    y_sub = -tox - t_gate
    y_sub_hi = W_sheet + tox + t_gate
    nodes.append(RegionNode(KIND_SUBSTRATE, "substrate",
                            (0, x_total, y_sub, y_sub_hi, -t_box - 50e-9, -t_box),
                            SILICON, DopingSpec(Na=1e18)))
    nodes.append(RegionNode(KIND_BOX, "box",
                            (0, x_total, y_sub, y_sub_hi, -t_box, 0), SIO2))
    # Active: channel, source, drain (gaa order: channel first).
    nodes.append(RegionNode(KIND_CHANNEL, "channel",
                            (gate_x[0], gate_x[1], 0, W_sheet, 0, t_sheet),
                            SILICON, DopingSpec(Na=1e16)))
    nodes.append(RegionNode(KIND_SOURCE, "source",
                            (0, Lsd, 0, W_sheet, 0, t_sheet),
                            SILICON, DopingSpec(Nd=1e20)))
    nodes.append(RegionNode(KIND_DRAIN, "drain",
                            (Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet),
                            SILICON, DopingSpec(Nd=1e20)))
    # Gate stack: 4-side SiO2 + 4-side metal (wide_ox y-extent).
    nodes += _four_side_oxide_regions(gate_x, W_sheet, t_sheet, tox, SIO2)
    nodes += _four_side_metal_regions(gate_x, W_sheet, t_sheet, tox, t_gate, "wide_ox")
    return DeviceTree(
        name="gaa",
        region_nodes=tuple(nodes),
        contacts=(
            ContactSpec("source", (0, Lsd, 0, W_sheet, -5e-9, 0), Vs),
            ContactSpec("drain", (Lsd + Lg, x_total, 0, W_sheet, -5e-9, 0), Vd),
            ContactSpec("gate", (gate_x[0], gate_x[1], -tox - t_gate, W_sheet + tox + t_gate,
                                 t_sheet + tox, t_sheet + tox + 5e-9), Vg),
        ),
        gate_meta=GateStackMeta(wrap=WRAP_FOUR_SIDE, layer_kinds=(KIND_OXIDE, KIND_METAL)),
    )


def _junctionless_fet_tree(
    Lg: float = 15e-9, tox: float = 1.5e-9, t_wire: float = 5e-9,
    W_wire: float = 5e-9, Lsd: float = 15e-9, t_gate: float = 10e-9,
    doping: float = 1e19, Vg: float = 0.0, Vd: float = 0.0, Vs: float = 0.0,
) -> DeviceTree:
    x_total = 2 * Lsd + Lg
    gate_x = (Lsd, Lsd + Lg)
    nodes: List[RegionNode] = [
        # Single uniform nanowire (no junctions), full length.
        RegionNode(KIND_WIRE, "nanowire", (0, x_total, 0, W_wire, 0, t_wire),
                   SILICON, DopingSpec(Nd=doping)),
    ]
    nodes += _four_side_oxide_regions(gate_x, W_wire, t_wire, tox, SIO2)
    nodes += _four_side_metal_regions(gate_x, W_wire, t_wire, tox, t_gate, "wide_ox")
    return DeviceTree(
        name="junctionless_fet",
        region_nodes=tuple(nodes),
        contacts=(
            ContactSpec("source", (0, Lsd, 0, W_wire, -5e-9, 0), Vs),
            ContactSpec("drain", (Lsd + Lg, x_total, 0, W_wire, -5e-9, 0), Vd),
            ContactSpec("gate", (gate_x[0], gate_x[1], -tox - t_gate, W_wire + tox + t_gate,
                                 t_wire + tox, t_wire + tox + 5e-9), Vg),
        ),
        gate_meta=GateStackMeta(wrap=WRAP_FOUR_SIDE, layer_kinds=(KIND_OXIDE, KIND_METAL)),
    )


def _gaa_highk_tree(
    Lg: float = 12e-9, t_ox: float = 1.0e-9, t_sheet: float = 5e-9,
    W_sheet: float = 20e-9, Lsd: float = 20e-9, t_gate: float = 10e-9,
    kappa: float = 25.0, Vg: float = 0.0, Vd: float = 0.0, Vs: float = 0.0,
) -> DeviceTree:
    x_total = 2 * Lsd + Lg
    gate_x = (Lsd, Lsd + Lg)
    hk = highk_material(kappa)
    nodes: List[RegionNode] = [
        RegionNode(KIND_CHANNEL, "channel", (gate_x[0], gate_x[1], 0, W_sheet, 0, t_sheet),
                   SILICON, DopingSpec(Na=1e16)),
        RegionNode(KIND_SOURCE, "source", (0, Lsd, 0, W_sheet, 0, t_sheet),
                   SILICON, DopingSpec(Nd=1e20)),
        RegionNode(KIND_DRAIN, "drain", (Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet),
                   SILICON, DopingSpec(Nd=1e20)),
    ]
    # 4-side high-k (same geometry as SiO2, different material/kind).
    nodes += _four_side_oxide_regions(gate_x, W_sheet, t_sheet, t_ox, hk, name_prefix="gate_oxide")
    nodes += _four_side_metal_regions(gate_x, W_sheet, t_sheet, t_ox, t_gate, "wide_ox")
    return DeviceTree(
        name="gaa_highk",
        region_nodes=tuple(nodes),
        contacts=(
            ContactSpec("source", (0, Lsd, 0, W_sheet, -5e-9, 0), Vs),
            ContactSpec("drain", (Lsd + Lg, x_total, 0, W_sheet, -5e-9, 0), Vd),
            ContactSpec("gate", (gate_x[0], gate_x[1], -t_ox - t_gate, W_sheet + t_ox + t_gate,
                                 t_sheet + t_ox, t_sheet + t_ox + 5e-9), Vg),
        ),
        gate_meta=GateStackMeta(wrap=WRAP_FOUR_SIDE, layer_kinds=(KIND_HIGHK, KIND_METAL)),
    )


def _gaa_fefet_tree(
    Lg: float = 15e-9, t_fe: float = 5e-9, t_ox: float = 1.0e-9,
    t_sheet: float = 5e-9, W_sheet: float = 20e-9, Lsd: float = 20e-9,
    t_gate: float = 10e-9, kappa_fe: float = 35.0,
    Vg: float = 0.0, Vd: float = 0.0, Vs: float = 0.0,
) -> DeviceTree:
    x_total = 2 * Lsd + Lg
    gate_x = (Lsd, Lsd + Lg)
    fe = ferroelectric_material(kappa_fe)
    t_outer = t_ox + t_fe
    x0, x1 = gate_x
    nodes: List[RegionNode] = [
        RegionNode(KIND_CHANNEL, "channel", (x0, x1, 0, W_sheet, 0, t_sheet),
                   SILICON, DopingSpec(Na=1e16)),
        RegionNode(KIND_SOURCE, "source", (0, Lsd, 0, W_sheet, 0, t_sheet),
                   SILICON, DopingSpec(Nd=1e20)),
        RegionNode(KIND_DRAIN, "drain", (Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet),
                   SILICON, DopingSpec(Nd=1e20)),
        # Interfacial SiO2 (4 sides, thin, next to channel).
        RegionNode(KIND_IL_OXIDE, "il_oxide_top",
                   (x0, x1, 0, W_sheet, t_sheet, t_sheet + t_ox), SIO2),
        RegionNode(KIND_IL_OXIDE, "il_oxide_bottom",
                   (x0, x1, 0, W_sheet, -t_ox, 0), SIO2),
        RegionNode(KIND_IL_OXIDE, "il_oxide_left",
                   (x0, x1, -t_ox, 0, -t_ox, t_sheet + t_ox), SIO2),
        RegionNode(KIND_IL_OXIDE, "il_oxide_right",
                   (x0, x1, W_sheet, W_sheet + t_ox, -t_ox, t_sheet + t_ox), SIO2),
        # Ferroelectric (4 sides, outside IL).
        RegionNode(KIND_FERROELECTRIC, "fe_top",
                   (x0, x1, 0, W_sheet, t_sheet + t_ox, t_sheet + t_outer), fe),
        RegionNode(KIND_FERROELECTRIC, "fe_bottom",
                   (x0, x1, 0, W_sheet, -t_outer, -t_ox), fe),
        RegionNode(KIND_FERROELECTRIC, "fe_left",
                   (x0, x1, -t_outer, -t_ox, -t_outer, t_sheet + t_outer), fe),
        RegionNode(KIND_FERROELECTRIC, "fe_right",
                   (x0, x1, W_sheet + t_ox, W_sheet + t_outer, -t_outer, t_sheet + t_outer), fe),
    ]
    # Gate metal: 4 sides, y-extent [-t_ox, W_sheet+t_ox] (wide_ox with tox=t_outer
    # would give [-t_outer, W+t_outer], but gaa_fefet uses [-t_ox, W+t_ox] for top/bottom).
    # So use wide_ox with the IL thickness t_ox for the y-extent, but t_outer for z.
    nodes += [
        RegionNode(KIND_METAL, "gate_metal_top",
                   (x0, x1, -t_ox, W_sheet + t_ox, t_sheet + t_outer, t_sheet + t_outer + t_gate), GATE_METAL),
        RegionNode(KIND_METAL, "gate_metal_bottom",
                   (x0, x1, -t_ox, W_sheet + t_ox, -t_outer - t_gate, -t_outer), GATE_METAL),
        RegionNode(KIND_METAL, "gate_metal_left",
                   (x0, x1, -t_outer - t_gate, -t_outer, -t_outer - t_gate, t_sheet + t_outer + t_gate), GATE_METAL),
        RegionNode(KIND_METAL, "gate_metal_right",
                   (x0, x1, W_sheet + t_outer, W_sheet + t_outer + t_gate,
                    -t_outer - t_gate, t_sheet + t_outer + t_gate), GATE_METAL),
    ]
    return DeviceTree(
        name="gaa_fefet",
        region_nodes=tuple(nodes),
        contacts=(
            ContactSpec("source", (0, Lsd, 0, W_sheet, -5e-9, 0), Vs),
            ContactSpec("drain", (Lsd + Lg, x_total, 0, W_sheet, -5e-9, 0), Vd),
            ContactSpec("gate", (x0, x1, -t_outer - t_gate, W_sheet + t_outer + t_gate,
                                 t_sheet + t_outer, t_sheet + t_outer + 5e-9), Vg),
        ),
        gate_meta=GateStackMeta(wrap=WRAP_FOUR_SIDE,
                                layer_kinds=(KIND_IL_OXIDE, KIND_FERROELECTRIC, KIND_METAL)),
    )


def _bspdn_gaa_tree(
    Lg: float = 20e-9, tox: float = 1.5e-9, t_sheet: float = 5e-9,
    W_sheet: float = 30e-9, Lsd: float = 30e-9, t_gate: float = 10e-9,
    t_bs_metal: float = 20e-9, t_via: float = 50e-9, t_substrate: float = 30e-9,
    Vdd: float = 0.7, Vg: float = 0.0, Vd: float = 0.0, Vs: float = 0.0,
) -> DeviceTree:
    x_total = 2 * Lsd + Lg
    gate_x = (Lsd, Lsd + Lg)
    via_width = min(Lsd * 0.6, W_sheet * 0.5)
    via_x_start = Lsd * 0.2
    via_y_start = (W_sheet - via_width) / 2.0
    nodes: List[RegionNode] = [
        RegionNode(KIND_CHANNEL, "channel", (gate_x[0], gate_x[1], 0, W_sheet, 0, t_sheet),
                   SILICON, DopingSpec(Na=1e16)),
        RegionNode(KIND_SOURCE, "source", (0, Lsd, 0, W_sheet, 0, t_sheet),
                   SILICON, DopingSpec(Nd=1e20)),
        RegionNode(KIND_DRAIN, "drain", (Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet),
                   SILICON, DopingSpec(Nd=1e20)),
    ]
    nodes += _four_side_oxide_regions(gate_x, W_sheet, t_sheet, tox, SIO2)
    nodes += _four_side_metal_regions(gate_x, W_sheet, t_sheet, tox, t_gate, "wide_ox")
    # Thinned substrate (no BOX), then backside via + rail.
    nodes.append(RegionNode(KIND_SUBSTRATE, "substrate",
                            (0, x_total, -tox - t_gate, W_sheet + tox + t_gate, -t_substrate, 0),
                            SILICON, DopingSpec(Na=1e18)))
    nodes.append(RegionNode(KIND_VIA, "bs_via",
                            (via_x_start, via_x_start + via_width,
                             via_y_start, via_y_start + via_width,
                             -t_substrate - t_via, -t_substrate),
                            SILICON, DopingSpec(Nd=1e20)))
    nodes.append(RegionNode(KIND_RAIL, "bs_power_rail",
                            (0, x_total, 0, W_sheet,
                             -t_substrate - t_via - t_bs_metal, -t_substrate - t_via),
                            BACKSIDE_METAL))
    return DeviceTree(
        name="bspdn_gaa",
        region_nodes=tuple(nodes),
        contacts=(
            ContactSpec("drain", (Lsd + Lg, x_total, 0, W_sheet, -5e-9, 0), Vd),
            ContactSpec("gate", (gate_x[0], gate_x[1], -tox - t_gate, W_sheet + tox + t_gate,
                                 t_sheet + tox, t_sheet + tox + 5e-9), Vg),
            ContactSpec("bs_power", (0, x_total, 0, W_sheet,
                                     -t_substrate - t_via - t_bs_metal - 5e-9,
                                     -t_substrate - t_via), Vdd),
        ),
        gate_meta=GateStackMeta(wrap=WRAP_FOUR_SIDE, layer_kinds=(KIND_OXIDE, KIND_METAL)),
    )


# ---------------------------------------------------------------------------
# TFET family
# ---------------------------------------------------------------------------

def _tfet_active_source_channel_drain(
    Lsd: float, Lg: float, x_total: float, W_sheet: float, t_sheet: float,
    source_mat: MaterialSpec, source_doping: DopingSpec,
    channel_doping: DopingSpec, drain_doping: DopingSpec,
) -> List[RegionNode]:
    """Active stack in tfet order: source -> channel -> drain.

    (Contrast gaa order: channel -> source -> drain.  Order matters where
    regions overlap; here they are x-disjoint so it is cosmetic, but we
    preserve it for byte-equivalence with ``Device.tfet``.)
    """
    return [
        RegionNode(KIND_SOURCE, "source", (0, Lsd, 0, W_sheet, 0, t_sheet),
                   source_mat, source_doping),
        RegionNode(KIND_CHANNEL, "channel", (Lsd, Lsd + Lg, 0, W_sheet, 0, t_sheet),
                   SILICON, channel_doping),
        RegionNode(KIND_DRAIN, "drain", (Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet),
                   SILICON, drain_doping),
    ]


def _tfet_tree(
    Lg: float = 20e-9, tox: float = 1.5e-9, t_sheet: float = 5e-9,
    W_sheet: float = 20e-9, Lsd: float = 20e-9, t_gate: float = 10e-9,
    source_doping: float = 5e20, channel_doping: float = 1e15, drain_doping: float = 1e20,
    Vg: float = 0.0, Vd: float = 0.5, Vs: float = 0.0,
) -> DeviceTree:
    x_total = 2 * Lsd + Lg
    gate_x = (Lsd, Lsd + Lg)
    nodes = _tfet_active_source_channel_drain(
        Lsd, Lg, x_total, W_sheet, t_sheet,
        SILICON, DopingSpec(Na=source_doping),
        DopingSpec(Na=channel_doping), DopingSpec(Nd=drain_doping),
    )
    nodes += _four_side_oxide_regions(gate_x, W_sheet, t_sheet, tox, SIO2)
    # tfet metal y-extent is [0, W_sheet] (narrow).
    x0, x1 = gate_x
    nodes += [
        RegionNode(KIND_METAL, "gate_metal_top",
                   (x0, x1, 0, W_sheet, t_sheet + tox, t_sheet + tox + t_gate), GATE_METAL),
        RegionNode(KIND_METAL, "gate_metal_bottom",
                   (x0, x1, 0, W_sheet, -tox - t_gate, -tox), GATE_METAL),
        RegionNode(KIND_METAL, "gate_metal_left",
                   (x0, x1, -tox - t_gate, -tox, -tox - t_gate, t_sheet + tox + t_gate), GATE_METAL),
        RegionNode(KIND_METAL, "gate_metal_right",
                   (x0, x1, W_sheet + tox, W_sheet + tox + t_gate,
                    -tox - t_gate, t_sheet + tox + t_gate), GATE_METAL),
    ]
    return DeviceTree(
        name="tfet",
        region_nodes=tuple(nodes),
        contacts=(
            ContactSpec("source", (0, Lsd, 0, W_sheet, 0, t_sheet * 0.3), Vs),
            ContactSpec("drain", (Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet * 0.3), Vd),
            ContactSpec("gate", (x0, x1, -tox - t_gate, W_sheet + tox + t_gate,
                                 t_sheet + tox, t_sheet + 50e-9), Vg),
        ),
        gate_meta=GateStackMeta(wrap=WRAP_FOUR_SIDE, layer_kinds=(KIND_OXIDE, KIND_METAL)),
    )


def _heterojunction_tfet_tree(
    Lg: float = 20e-9, tox: float = 1.5e-9, t_sheet: float = 5e-9,
    W_sheet: float = 20e-9, Lsd: float = 20e-9, L_source_hj: float = 10e-9,
    t_gate: float = 10e-9, ge_fraction: float = 0.4,
    source_doping: float = 5e20, channel_doping: float = 1e15, drain_doping: float = 1e20,
    Vg: float = 0.0, Vd: float = 0.5, Vs: float = 0.0,
) -> DeviceTree:
    x_total = 2 * Lsd + Lg
    gate_x = (Lsd, Lsd + Lg)
    sige = sige_material(ge_fraction)
    x0, x1 = gate_x
    nodes: List[RegionNode] = [
        # Two-segment SiGe source: bulk + heterojunction segment.
        RegionNode(KIND_SOURCE, "source_bulk",
                   (0, Lsd - L_source_hj, 0, W_sheet, 0, t_sheet),
                   sige, DopingSpec(Na=source_doping)),
        RegionNode(KIND_SOURCE, "source_hj",
                   (Lsd - L_source_hj, Lsd, 0, W_sheet, 0, t_sheet),
                   sige, DopingSpec(Na=source_doping)),
        RegionNode(KIND_CHANNEL, "channel", (x0, x1, 0, W_sheet, 0, t_sheet),
                   SILICON, DopingSpec(Na=channel_doping)),
        RegionNode(KIND_DRAIN, "drain", (Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet),
                   SILICON, DopingSpec(Nd=drain_doping)),
    ]
    nodes += _four_side_oxide_regions(gate_x, W_sheet, t_sheet, tox, SIO2)
    nodes += [
        RegionNode(KIND_METAL, "gate_metal_top",
                   (x0, x1, 0, W_sheet, t_sheet + tox, t_sheet + tox + t_gate), GATE_METAL),
        RegionNode(KIND_METAL, "gate_metal_bottom",
                   (x0, x1, 0, W_sheet, -tox - t_gate, -tox), GATE_METAL),
        RegionNode(KIND_METAL, "gate_metal_left",
                   (x0, x1, -tox - t_gate, -tox, -tox - t_gate, t_sheet + tox + t_gate), GATE_METAL),
        RegionNode(KIND_METAL, "gate_metal_right",
                   (x0, x1, W_sheet + tox, W_sheet + tox + t_gate,
                    -tox - t_gate, t_sheet + tox + t_gate), GATE_METAL),
    ]
    return DeviceTree(
        name="heterojunction_tfet",
        region_nodes=tuple(nodes),
        contacts=(
            ContactSpec("source", (0, Lsd, 0, W_sheet, 0, t_sheet * 0.3), Vs),
            ContactSpec("drain", (Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet * 0.3), Vd),
            ContactSpec("gate", (x0, x1, -tox - t_gate, W_sheet + tox + t_gate,
                                 t_sheet + tox, t_sheet + 50e-9), Vg),
        ),
        gate_meta=GateStackMeta(wrap=WRAP_FOUR_SIDE, layer_kinds=(KIND_OXIDE, KIND_METAL)),
    )


def _graphene_source_tfet_tree(
    Lg: float = 15e-9, tox: float = 1.0e-9, t_sheet: float = 5e-9,
    W_sheet: float = 20e-9, Lsd: float = 20e-9, t_gate: float = 10e-9,
    t_box: float = 10e-9, source_doping: float = 5e20, channel_doping: float = 1e15,
    drain_doping: float = 1e20, Vg: float = 0.0, Vd: float = 0.3, Vs: float = 0.0,
) -> DeviceTree:
    x_total = 2 * Lsd + Lg
    gate_x = (Lsd, Lsd + Lg)
    x0, x1 = gate_x
    y_sub = -tox - t_gate
    y_sub_hi = W_sheet + tox + t_gate
    nodes: List[RegionNode] = [
        RegionNode(KIND_SUBSTRATE, "substrate",
                   (0, x_total, y_sub, y_sub_hi, -t_box - 50e-9, -t_box),
                   SILICON, DopingSpec(Na=1e18)),
        RegionNode(KIND_BOX, "box", (0, x_total, y_sub, y_sub_hi, -t_box, 0), SIO2),
        # p+ graphene source -> Si channel -> n+ Si drain (tfet order).
        RegionNode(KIND_SOURCE, "source", (0, Lsd, 0, W_sheet, 0, t_sheet),
                   GRAPHENE, DopingSpec(Na=source_doping)),
        RegionNode(KIND_CHANNEL, "channel", (x0, x1, 0, W_sheet, 0, t_sheet),
                   SILICON, DopingSpec(Na=channel_doping)),
        RegionNode(KIND_DRAIN, "drain", (Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet),
                   SILICON, DopingSpec(Nd=drain_doping)),
    ]
    nodes += _four_side_oxide_regions(gate_x, W_sheet, t_sheet, tox, SIO2)
    nodes += [
        RegionNode(KIND_METAL, "gate_metal_top",
                   (x0, x1, 0, W_sheet, t_sheet + tox, t_sheet + tox + t_gate), GATE_METAL),
        RegionNode(KIND_METAL, "gate_metal_bottom",
                   (x0, x1, 0, W_sheet, -tox - t_gate, -tox), GATE_METAL),
        RegionNode(KIND_METAL, "gate_metal_left",
                   (x0, x1, -tox - t_gate, -tox, -tox - t_gate, t_sheet + tox + t_gate), GATE_METAL),
        RegionNode(KIND_METAL, "gate_metal_right",
                   (x0, x1, W_sheet + tox, W_sheet + tox + t_gate,
                    -tox - t_gate, t_sheet + tox + t_gate), GATE_METAL),
    ]
    return DeviceTree(
        name="graphene_source_tfet",
        region_nodes=tuple(nodes),
        contacts=(
            ContactSpec("source", (0, Lsd, 0, W_sheet, 0, t_sheet * 0.3), Vs),
            ContactSpec("drain", (Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet * 0.3), Vd),
            ContactSpec("gate", (x0, x1, -tox - t_gate, W_sheet + tox + t_gate,
                                 t_sheet + tox, t_sheet + 50e-9), Vg),
        ),
        gate_meta=GateStackMeta(wrap=WRAP_FOUR_SIDE, layer_kinds=(KIND_OXIDE, KIND_METAL)),
    )


def _dirac_source_fet_tree(
    Lg: float = 20e-9, tox: float = 1.5e-9, t_sheet: float = 5e-9,
    W_sheet: float = 30e-9, Lsd: float = 30e-9, t_gate: float = 10e-9,
    t_box: float = 10e-9, source_doping: float = 1e18, channel_doping: float = 1e16,
    drain_doping: float = 1e20, Vg: float = 0.0, Vd: float = 0.3, Vs: float = 0.0,
) -> DeviceTree:
    x_total = 2 * Lsd + Lg
    gate_x = (Lsd, Lsd + Lg)
    x0, x1 = gate_x
    y_sub = -tox - t_gate
    y_sub_hi = W_sheet + tox + t_gate
    nodes: List[RegionNode] = [
        RegionNode(KIND_SUBSTRATE, "substrate",
                   (0, x_total, y_sub, y_sub_hi, -t_box - 50e-9, -t_box),
                   SILICON, DopingSpec(Na=1e18)),
        RegionNode(KIND_BOX, "box", (0, x_total, y_sub, y_sub_hi, -t_box, 0), SIO2),
        # gaa order: channel -> source -> drain; source is n-type graphene.
        RegionNode(KIND_CHANNEL, "channel", (x0, x1, 0, W_sheet, 0, t_sheet),
                   SILICON, DopingSpec(Na=channel_doping)),
        RegionNode(KIND_SOURCE, "source", (0, Lsd, 0, W_sheet, 0, t_sheet),
                   GRAPHENE, DopingSpec(Nd=source_doping)),
        RegionNode(KIND_DRAIN, "drain", (Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet),
                   SILICON, DopingSpec(Nd=drain_doping)),
    ]
    nodes += _four_side_oxide_regions(gate_x, W_sheet, t_sheet, tox, SIO2)
    # gaa-style wide_ox metal y-extent.
    nodes += _four_side_metal_regions(gate_x, W_sheet, t_sheet, tox, t_gate, "wide_ox")
    return DeviceTree(
        name="dirac_source_fet",
        region_nodes=tuple(nodes),
        # Full-volume contacts (source/drain fill 0..t_sheet; gate fills metal slab).
        contacts=(
            ContactSpec("source", (0, Lsd, 0, W_sheet, 0, t_sheet), Vs),
            ContactSpec("drain", (Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet), Vd),
            ContactSpec("gate", (x0, x1, -tox - t_gate, W_sheet + tox + t_gate,
                                 t_sheet + tox, t_sheet + tox + t_gate), Vg),
        ),
        gate_meta=GateStackMeta(wrap=WRAP_FOUR_SIDE, layer_kinds=(KIND_OXIDE, KIND_METAL)),
    )


def _dirac_source_fefet_tree(
    Lg: float = 20e-9, t_fe: float = 4e-9, t_ox: float = 1.0e-9,
    t_sheet: float = 5e-9, W_sheet: float = 30e-9, Lsd: float = 30e-9,
    t_gate: float = 10e-9, kappa_fe: float = 35.0,
    source_doping: float = 1e18, channel_doping: float = 1e16, drain_doping: float = 1e20,
    Vg: float = 0.0, Vd: float = 0.3, Vs: float = 0.0,
) -> DeviceTree:
    x_total = 2 * Lsd + Lg
    gate_x = (Lsd, Lsd + Lg)
    x0, x1 = gate_x
    fe = ferroelectric_material(kappa_fe)
    t_outer = t_ox + t_fe
    nodes: List[RegionNode] = [
        RegionNode(KIND_CHANNEL, "channel", (x0, x1, 0, W_sheet, 0, t_sheet),
                   SILICON, DopingSpec(Na=channel_doping)),
        RegionNode(KIND_SOURCE, "source", (0, Lsd, 0, W_sheet, 0, t_sheet),
                   GRAPHENE, DopingSpec(Nd=source_doping)),
        RegionNode(KIND_DRAIN, "drain", (Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet),
                   SILICON, DopingSpec(Nd=drain_doping)),
        # IL SiO2 (4 sides).
        RegionNode(KIND_IL_OXIDE, "il_oxide_top",
                   (x0, x1, 0, W_sheet, t_sheet, t_sheet + t_ox), SIO2),
        RegionNode(KIND_IL_OXIDE, "il_oxide_bottom",
                   (x0, x1, 0, W_sheet, -t_ox, 0), SIO2),
        RegionNode(KIND_IL_OXIDE, "il_oxide_left",
                   (x0, x1, -t_ox, 0, -t_ox, t_sheet + t_ox), SIO2),
        RegionNode(KIND_IL_OXIDE, "il_oxide_right",
                   (x0, x1, W_sheet, W_sheet + t_ox, -t_ox, t_sheet + t_ox), SIO2),
        # FE (4 sides).
        RegionNode(KIND_FERROELECTRIC, "fe_top",
                   (x0, x1, 0, W_sheet, t_sheet + t_ox, t_sheet + t_outer), fe),
        RegionNode(KIND_FERROELECTRIC, "fe_bottom",
                   (x0, x1, 0, W_sheet, -t_outer, -t_ox), fe),
        RegionNode(KIND_FERROELECTRIC, "fe_left",
                   (x0, x1, -t_outer, -t_ox, -t_outer, t_sheet + t_outer), fe),
        RegionNode(KIND_FERROELECTRIC, "fe_right",
                   (x0, x1, W_sheet + t_ox, W_sheet + t_outer, -t_outer, t_sheet + t_outer), fe),
    ]
    # Gate metal: y-extent [-t_outer, W_sheet+t_outer] (wide_outer, unique to this template).
    nodes += [
        RegionNode(KIND_METAL, "gate_metal_top",
                   (x0, x1, -t_outer, W_sheet + t_outer,
                    t_sheet + t_outer, t_sheet + t_outer + t_gate), GATE_METAL),
        RegionNode(KIND_METAL, "gate_metal_bottom",
                   (x0, x1, -t_outer, W_sheet + t_outer,
                    -t_outer - t_gate, -t_outer), GATE_METAL),
        RegionNode(KIND_METAL, "gate_metal_left",
                   (x0, x1, -t_outer - t_gate, -t_outer,
                    -t_outer - t_gate, t_sheet + t_outer + t_gate), GATE_METAL),
        RegionNode(KIND_METAL, "gate_metal_right",
                   (x0, x1, W_sheet + t_outer, W_sheet + t_outer + t_gate,
                    -t_outer - t_gate, t_sheet + t_outer + t_gate), GATE_METAL),
    ]
    return DeviceTree(
        name="dirac_source_fefet",
        region_nodes=tuple(nodes),
        contacts=(
            ContactSpec("source", (0, Lsd, 0, W_sheet, 0, t_sheet), Vs),
            ContactSpec("drain", (Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet), Vd),
            ContactSpec("gate", (x0, x1, -t_outer - t_gate, W_sheet + t_outer + t_gate,
                                 t_sheet + t_outer, t_sheet + t_outer + t_gate), Vg),
        ),
        gate_meta=GateStackMeta(wrap=WRAP_FOUR_SIDE,
                                layer_kinds=(KIND_IL_OXIDE, KIND_FERROELECTRIC, KIND_METAL)),
    )


# Dispatch table.  Keys are the Device factory method names.
_TEMPLATE_BUILDERS: Dict[str, callable] = {
    "pnjunction": _pnjunction_tree,
    "tunnel_diode": _tunnel_diode_tree,
    "mosfet": _mosfet_tree,
    "finfet": _finfet_tree,
    "gaa": _gaa_tree,
    "junctionless_fet": _junctionless_fet_tree,
    "gaa_highk": _gaa_highk_tree,
    "gaa_fefet": _gaa_fefet_tree,
    "bspdn_gaa": _bspdn_gaa_tree,
    "tfet": _tfet_tree,
    "heterojunction_tfet": _heterojunction_tfet_tree,
    "graphene_source_tfet": _graphene_source_tfet_tree,
    "dirac_source_fet": _dirac_source_fet_tree,
    "dirac_source_fefet": _dirac_source_fefet_tree,
}


def tree_from_template(template_name: str, **params) -> DeviceTree:
    """Reverse-induce a device template into a grammar tree.

    ``build(tree_from_template(name, **p))`` is structurally identical to
    ``Device.name(**p)`` for every supported template (the C1 truth-chain).

    Parameters
    ----------
    template_name : str
        Name of the ``Device`` factory method (e.g. ``"mosfet"``).
    **params :
        Keyword arguments forwarded to the template factory.
    """
    try:
        builder = _TEMPLATE_BUILDERS[template_name]
    except KeyError:
        raise KeyError(
            f"unknown template '{template_name}'; known: "
            f"{sorted(_TEMPLATE_BUILDERS)}"
        )
    return builder(**params)


def supported_templates() -> List[str]:
    """Names of templates with a grammar reverse-induction."""
    return sorted(_TEMPLATE_BUILDERS)


def template_default_params(template_name: str) -> Dict[str, float]:
    """Default parameter dict for a template (from its builder signature).

    Used by the search loop so parameter mutation has perturbable knobs even
    when the caller seeds with no explicit params.  Voltage/bias knobs
    (``Vg``/``Vd``/``Vs``/``Vdd``) are excluded — those are swept, not mutated.
    """
    try:
        builder = _TEMPLATE_BUILDERS[template_name]
    except KeyError:
        raise KeyError(
            f"unknown template '{template_name}'; known: "
            f"{sorted(_TEMPLATE_BUILDERS)}"
        )
    sig = inspect.signature(builder)
    out: Dict[str, float] = {}
    for pname, p in sig.parameters.items():
        if p.default is inspect.Parameter.empty:
            continue
        if pname in ("Vg", "Vd", "Vs", "Vdd"):  # bias knobs, not geometry
            continue
        out[pname] = p.default
    return out
