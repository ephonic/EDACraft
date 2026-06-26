"""Device builder: assemble regions, materials, and doping into a Device."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Union
import numpy as np

from .shapes import Shape, Box


@dataclass
class Material:
    """Semiconductor or insulator material properties."""
    name: str
    epsilon_r: float = 11.7          # Relative permittivity
    Eg: float = 1.12                 # Band gap [eV]
    chi: float = 4.05                # Electron affinity [eV]
    Nc: float = 2.8e19               # Conduction band DOS [cm^-3]
    Nv: float = 1.04e19              # Valence band DOS [cm^-3]
    mu_n: float = 1400.0             # Electron mobility [cm^2/(V·s)]
    mu_p: float = 450.0              # Hole mobility [cm^2/(V·s)]
    tau_n: float = 1e-7              # Electron lifetime [s]
    tau_p: float = 1e-7              # Hole lifetime [s]
    # Quantum correction parameter b_n, b_p [m^4/s or similar, model dependent]
    b_n: float = 3.86e-6             # Density gradient coefficient for electrons [m^2]
    b_p: float = 3.86e-6             # Density gradient coefficient for holes [m^2]
    # Ferroelectric Landau-Khalatnikov parameters (for ferroelectric materials)
    fe_alpha: float = 0.0            # Landau alpha coefficient [m/F]
    fe_beta: float = 0.0             # Landau beta coefficient [m^5/(F·C^2)]


@dataclass
class DopingProfile:
    """Doping profile applied to a region."""
    Nd: float = 0.0   # Donor concentration [cm^-3]
    Na: float = 0.0   # Acceptor concentration [cm^-3]
    # Optional functional profile
    Nd_func: Optional[callable] = None
    Na_func: Optional[callable] = None

    def effective(self, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
        """Return net doping Nd - Na at each point."""
        nd = self.Nd_func(x, y, z) if self.Nd_func else np.full_like(x, self.Nd, dtype=float)
        na = self.Na_func(x, y, z) if self.Na_func else np.full_like(x, self.Na, dtype=float)
        return nd - na


@dataclass
class Region:
    """A spatial region with material and doping."""
    name: str
    shape: Shape
    material: Material
    doping: DopingProfile = field(default_factory=DopingProfile)


class Device:
    """
    Complete semiconductor device definition.

    Built from a list of regions.  Later regions override earlier ones
    (painters algorithm) so you can stack e.g. oxide on silicon.
    """

    def __init__(self, name: str = "device"):
        self.name = name
        self.regions: List[Region] = []
        self.contacts: Dict[str, Tuple[Shape, float]] = {}  # name -> (shape, workfunction/V)

    def add_region(self, region: Region) -> Device:
        self.regions.append(region)
        return self

    def add_contact(self, name: str, shape: Shape, voltage: float = 0.0, workfunction: float = 4.0) -> Device:
        """Add an electrode/contact.  voltage [V], workfunction [eV]."""
        self.contacts[name] = (shape, voltage)
        return self

    def bbox(self) -> Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]:
        """Overall bounding box of all regions."""
        if not self.regions:
            return ((0.0, 1.0), (0.0, 1.0), (0.0, 1.0))
        bboxes = [r.shape.bbox() for r in self.regions]
        xmin = min(b[0][0] for b in bboxes)
        xmax = max(b[0][1] for b in bboxes)
        ymin = min(b[1][0] for b in bboxes)
        ymax = max(b[1][1] for b in bboxes)
        zmin = min(b[2][0] for b in bboxes)
        zmax = max(b[2][1] for b in bboxes)
        return (xmin, xmax), (ymin, ymax), (zmin, zmax)

    def sample_on_grid(self, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Sample material IDs, epsilon, and doping on a given grid.
        Returns arrays of shape x.shape.
        """
        out = {
            "material_id": np.full(x.shape, -1, dtype=np.int32),
            "epsilon": np.zeros(x.shape, dtype=float),
            "doping": np.zeros(x.shape, dtype=float),
            "Eg": np.zeros(x.shape, dtype=float),
            "chi": np.zeros(x.shape, dtype=float),
            "Nc": np.zeros(x.shape, dtype=float),
            "Nv": np.zeros(x.shape, dtype=float),
            "mu_n": np.zeros(x.shape, dtype=float),
            "mu_p": np.zeros(x.shape, dtype=float),
        }
        for rid, region in enumerate(self.regions):
            mask = region.shape.contains(x, y, z)
            out["material_id"][mask] = rid
            out["epsilon"][mask] = region.material.epsilon_r * 8.854187817e-12  # F/m
            out["doping"][mask] = region.doping.effective(x[mask], y[mask], z[mask])
            out["Eg"][mask] = region.material.Eg
            out["chi"][mask] = region.material.chi
            out["Nc"][mask] = region.material.Nc
            out["Nv"][mask] = region.material.Nv
            out["mu_n"][mask] = region.material.mu_n * 1e-4  # m^2/(V·s)
            out["mu_p"][mask] = region.material.mu_p * 1e-4  # m^2/(V·s)
        return out

    def get_contacts_on_grid(self, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> Dict[str, np.ndarray]:
        """Return boolean masks for each contact on the given grid."""
        contact_masks = {}
        for name, (shape, voltage) in self.contacts.items():
            contact_masks[name] = shape.contains(x, y, z)
        return contact_masks

    @staticmethod
    def mosfet(
        Lg: float = 50e-9,
        tox: float = 1.5e-9,
        tsi: float = 10e-9,
        W: float = 100e-9,
        Lsd: float = 50e-9,
        Vg: float = 0.0,
        Vd: float = 0.0,
        Vs: float = 0.0,
    ) -> Device:
        """
        Generate a simple planar MOSFET device template.
        All dimensions in meters.  Returns a Device ready for meshing.
        """
        dev = Device("mosfet")
        x_total = 2 * Lsd + Lg

        # Substrate (silicon bulk)
        si = Material("Silicon", epsilon_r=11.7, Eg=1.12)
        # Channel / body (lightly p-doped)
        body = Region(
            "body",
            Box(0, x_total, 0, W, 0, tsi),
            si,
            DopingProfile(Nd=0.0, Na=1e16),  # cm^-3
        )
        dev.add_region(body)

        # Source (n+ doped) - extend to full height so there is no vacuum above it
        source = Region(
            "source",
            Box(0, Lsd, 0, W, 0, tsi + tox + 10e-9),
            si,
            DopingProfile(Nd=1e20, Na=0.0),
        )
        dev.add_region(source)

        # Drain (n+ doped) - extend to full height so there is no vacuum above it
        drain = Region(
            "drain",
            Box(x_total - Lsd, x_total, 0, W, 0, tsi + tox + 10e-9),
            si,
            DopingProfile(Nd=1e20, Na=0.0),
        )
        dev.add_region(drain)

        # Gate oxide (insulator: zero mobility)
        oxide = Material("SiO2", epsilon_r=3.9, Eg=9.0, mu_n=0.0, mu_p=0.0)
        gate_oxide = Region(
            "gate_oxide",
            Box(Lsd, Lsd + Lg, 0, W, tsi, tsi + tox),
            oxide,
        )
        dev.add_region(gate_oxide)

        # Gate contact (metal: zero mobility)
        gate = Region(
            "gate_metal",
            Box(Lsd, Lsd + Lg, 0, W, tsi + tox, tsi + tox + 10e-9),
            Material("GateMetal", epsilon_r=1.0, mu_n=0.0, mu_p=0.0),
        )
        dev.add_region(gate)

        # Contacts
        dev.add_contact("source", Box(0, Lsd, 0, W, -5e-9, 0), voltage=Vs)
        dev.add_contact("drain", Box(x_total - Lsd, x_total, 0, W, -5e-9, 0), voltage=Vd)
        dev.add_contact("gate", Box(Lsd, Lsd + Lg, 0, W, tsi + tox, tsi + tox + 5e-9), voltage=Vg)

        return dev

    @staticmethod
    def finfet(
        Lg: float = 30e-9,
        tox: float = 1.5e-9,
        tsi: float = 10e-9,
        Hfin: float = 30e-9,
        Lsd: float = 30e-9,
        tgate: float = 10e-9,
        Vg: float = 0.0,
        Vd: float = 0.0,
        Vs: float = 0.0,
    ) -> Device:
        """
        Generate a double-gate FinFET device template.

        The fin runs along the x-direction (source → drain).
        The gate wraps around the fin in the y-direction (both sides).
        All dimensions in meters.
        """
        dev = Device("finfet")
        x_total = 2 * Lsd + Lg

        si = Material("Silicon", epsilon_r=11.7, Eg=1.12)

        # Fin body (lightly p-doped)
        body = Region(
            "body",
            Box(0, x_total, 0, tsi, 0, Hfin),
            si,
            DopingProfile(Nd=0.0, Na=1e16),
        )
        dev.add_region(body)

        # Source (n+ doped)
        source = Region(
            "source",
            Box(0, Lsd, 0, tsi, 0, Hfin),
            si,
            DopingProfile(Nd=1e20, Na=0.0),
        )
        dev.add_region(source)

        # Drain (n+ doped)
        drain = Region(
            "drain",
            Box(x_total - Lsd, x_total, 0, tsi, 0, Hfin),
            si,
            DopingProfile(Nd=1e20, Na=0.0),
        )
        dev.add_region(drain)

        # Gate oxide (insulator)
        oxide = Material("SiO2", epsilon_r=3.9, Eg=9.0, mu_n=0.0, mu_p=0.0)
        gate_oxide_left = Region(
            "gate_oxide_left",
            Box(Lsd, Lsd + Lg, -tox, 0, 0, Hfin),
            oxide,
        )
        gate_oxide_right = Region(
            "gate_oxide_right",
            Box(Lsd, Lsd + Lg, tsi, tsi + tox, 0, Hfin),
            oxide,
        )
        dev.add_region(gate_oxide_left)
        dev.add_region(gate_oxide_right)

        # Gate metal (both sides)
        gate_metal_left = Region(
            "gate_metal_left",
            Box(Lsd, Lsd + Lg, -tox - tgate, -tox, 0, Hfin),
            Material("GateMetal", epsilon_r=1.0, mu_n=0.0, mu_p=0.0),
        )
        gate_metal_right = Region(
            "gate_metal_right",
            Box(Lsd, Lsd + Lg, tsi + tox, tsi + tox + tgate, 0, Hfin),
            Material("GateMetal", epsilon_r=1.0, mu_n=0.0, mu_p=0.0),
        )
        dev.add_region(gate_metal_left)
        dev.add_region(gate_metal_right)

        # Contacts
        dev.add_contact("source", Box(0, Lsd, 0, tsi, -5e-9, 0), voltage=Vs)
        dev.add_contact("drain", Box(x_total - Lsd, x_total, 0, tsi, -5e-9, 0), voltage=Vd)
        dev.add_contact("gate", Box(Lsd, Lsd + Lg, -tox - tgate, tsi + tox + tgate, -5e-9, 0), voltage=Vg)

        return dev

    @staticmethod
    def gaa(
        Lg: float = 20e-9,
        tox: float = 1.5e-9,
        t_sheet: float = 5e-9,
        W_sheet: float = 30e-9,
        Lsd: float = 30e-9,
        t_gate: float = 10e-9,
        t_box: float = 10e-9,
        Vg: float = 0.0,
        Vd: float = 0.0,
        Vs: float = 0.0,
    ) -> Device:
        """
        Generate a Gate-All-Around (GAA) nanosheet device template.

        The nanosheet runs along the x-direction (source -> drain).
        The gate wraps around the nanosheet on all four sides (top, bottom,
        left, right).  The device sits on a buried oxide (BOX) layer over
        a silicon substrate.

        All dimensions in meters.
        """
        dev = Device("gaa")
        x_total = 2 * Lsd + Lg
        y_total = W_sheet + 2 * tox + 2 * t_gate
        z_top = t_sheet + tox + t_gate

        si = Material("Silicon", epsilon_r=11.7, Eg=1.12)
        oxide = Material("SiO2", epsilon_r=3.9, Eg=9.0, mu_n=0.0, mu_p=0.0)
        metal = Material("GateMetal", epsilon_r=1.0, mu_n=0.0, mu_p=0.0)

        # Substrate (silicon bulk underneath BOX)
        substrate = Region(
            "substrate",
            Box(0, x_total, -tox - t_gate, W_sheet + tox + t_gate,
                -t_box - 50e-9, -t_box),
            si,
            DopingProfile(Nd=0.0, Na=1e18),
        )
        dev.add_region(substrate)

        # Buried oxide (BOX)
        box = Region(
            "box",
            Box(0, x_total, -tox - t_gate, W_sheet + tox + t_gate,
                -t_box, 0),
            oxide,
        )
        dev.add_region(box)

        # Nanosheet channel (lightly p-doped)
        channel = Region(
            "channel",
            Box(Lsd, Lsd + Lg, 0, W_sheet, 0, t_sheet),
            si,
            DopingProfile(Nd=0.0, Na=1e16),
        )
        dev.add_region(channel)

        # Source (n+ doped)
        source = Region(
            "source",
            Box(0, Lsd, 0, W_sheet, 0, t_sheet),
            si,
            DopingProfile(Nd=1e20, Na=0.0),
        )
        dev.add_region(source)

        # Drain (n+ doped)
        drain = Region(
            "drain",
            Box(Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet),
            si,
            DopingProfile(Nd=1e20, Na=0.0),
        )
        dev.add_region(drain)

        # Gate oxide (four sides wrapping the channel)
        gate_oxide_top = Region(
            "gate_oxide_top",
            Box(Lsd, Lsd + Lg, 0, W_sheet, t_sheet, t_sheet + tox),
            oxide,
        )
        gate_oxide_bottom = Region(
            "gate_oxide_bottom",
            Box(Lsd, Lsd + Lg, 0, W_sheet, -tox, 0),
            oxide,
        )
        gate_oxide_left = Region(
            "gate_oxide_left",
            Box(Lsd, Lsd + Lg, -tox, 0, -tox, t_sheet + tox),
            oxide,
        )
        gate_oxide_right = Region(
            "gate_oxide_right",
            Box(Lsd, Lsd + Lg, W_sheet, W_sheet + tox, -tox, t_sheet + tox),
            oxide,
        )
        dev.add_region(gate_oxide_top)
        dev.add_region(gate_oxide_bottom)
        dev.add_region(gate_oxide_left)
        dev.add_region(gate_oxide_right)

        # Gate metal (four sides outside the oxide)
        gate_metal_top = Region(
            "gate_metal_top",
            Box(Lsd, Lsd + Lg, -tox, W_sheet + tox,
                t_sheet + tox, t_sheet + tox + t_gate),
            metal,
        )
        gate_metal_bottom = Region(
            "gate_metal_bottom",
            Box(Lsd, Lsd + Lg, -tox, W_sheet + tox,
                -tox - t_gate, -tox),
            metal,
        )
        gate_metal_left = Region(
            "gate_metal_left",
            Box(Lsd, Lsd + Lg, -tox - t_gate, -tox,
                -tox - t_gate, t_sheet + tox + t_gate),
            metal,
        )
        gate_metal_right = Region(
            "gate_metal_right",
            Box(Lsd, Lsd + Lg, W_sheet + tox, W_sheet + tox + t_gate,
                -tox - t_gate, t_sheet + tox + t_gate),
            metal,
        )
        dev.add_region(gate_metal_top)
        dev.add_region(gate_metal_bottom)
        dev.add_region(gate_metal_left)
        dev.add_region(gate_metal_right)

        # Contacts
        dev.add_contact("source", Box(0, Lsd, 0, W_sheet, -5e-9, 0), voltage=Vs)
        dev.add_contact("drain", Box(Lsd + Lg, x_total, 0, W_sheet, -5e-9, 0), voltage=Vd)
        dev.add_contact("gate", Box(Lsd, Lsd + Lg, -tox - t_gate, W_sheet + tox + t_gate,
                                     t_sheet + tox, t_sheet + tox + 5e-9), voltage=Vg)

        return dev

    @staticmethod
    def junctionless_fet(
        Lg: float = 15e-9,
        tox: float = 1.5e-9,
        t_wire: float = 5e-9,
        W_wire: float = 5e-9,
        Lsd: float = 15e-9,
        t_gate: float = 10e-9,
        doping: float = 1e19,
        Vg: float = 0.0,
        Vd: float = 0.0,
        Vs: float = 0.0,
    ) -> Device:
        """
        Generate a Junctionless Nanowire FET device template.

        Unlike conventional FETs, the entire nanowire (source, channel, drain)
        is uniformly doped at high concentration. The gate depletes the channel
        when off and allows a conducting core when on. This eliminates the need
        for ultra-shallow junctions and enables aggressive gate-length scaling.

        The nanowire runs along the x-direction (source -> drain).
        Gate-all-around geometry provides excellent electrostatic control.

        Parameters
        ----------
        Lg : float
            Gate length [m]. Sub-20 nm is typical.
        tox : float
            Gate oxide thickness [m].
        t_wire : float
            Nanowire thickness (z-direction) [m].
        W_wire : float
            Nanowire width (y-direction) [m].
        Lsd : float
            Source/drain extension length [m].
        t_gate : float
            Gate metal thickness [m].
        doping : float
            Uniform doping concentration [cm^-3]. n-type by default.
        Vg, Vd, Vs : float
            Gate, drain, source bias [V].
        """
        dev = Device("junctionless_fet")
        x_total = 2 * Lsd + Lg

        si = Material("Silicon", epsilon_r=11.7, Eg=1.12)
        oxide = Material("SiO2", epsilon_r=3.9, Eg=9.0, mu_n=0.0, mu_p=0.0)
        metal = Material("GateMetal", epsilon_r=1.0, mu_n=0.0, mu_p=0.0)

        # Entire nanowire: uniformly doped (no junctions)
        nanowire = Region(
            "nanowire",
            Box(0, x_total, 0, W_wire, 0, t_wire),
            si,
            DopingProfile(Nd=doping, Na=0.0),
        )
        dev.add_region(nanowire)

        # Gate oxide (four sides wrapping the entire wire)
        gate_oxide_top = Region(
            "gate_oxide_top",
            Box(Lsd, Lsd + Lg, 0, W_wire, t_wire, t_wire + tox),
            oxide,
        )
        gate_oxide_bottom = Region(
            "gate_oxide_bottom",
            Box(Lsd, Lsd + Lg, 0, W_wire, -tox, 0),
            oxide,
        )
        gate_oxide_left = Region(
            "gate_oxide_left",
            Box(Lsd, Lsd + Lg, -tox, 0, -tox, t_wire + tox),
            oxide,
        )
        gate_oxide_right = Region(
            "gate_oxide_right",
            Box(Lsd, Lsd + Lg, W_wire, W_wire + tox, -tox, t_wire + tox),
            oxide,
        )
        dev.add_region(gate_oxide_top)
        dev.add_region(gate_oxide_bottom)
        dev.add_region(gate_oxide_left)
        dev.add_region(gate_oxide_right)

        # Gate metal (four sides)
        gate_metal_top = Region(
            "gate_metal_top",
            Box(Lsd, Lsd + Lg, -tox, W_wire + tox,
                t_wire + tox, t_wire + tox + t_gate),
            metal,
        )
        gate_metal_bottom = Region(
            "gate_metal_bottom",
            Box(Lsd, Lsd + Lg, -tox, W_wire + tox,
                -tox - t_gate, -tox),
            metal,
        )
        gate_metal_left = Region(
            "gate_metal_left",
            Box(Lsd, Lsd + Lg, -tox - t_gate, -tox,
                -tox - t_gate, t_wire + tox + t_gate),
            metal,
        )
        gate_metal_right = Region(
            "gate_metal_right",
            Box(Lsd, Lsd + Lg, W_wire + tox, W_wire + tox + t_gate,
                -tox - t_gate, t_wire + tox + t_gate),
            metal,
        )
        dev.add_region(gate_metal_top)
        dev.add_region(gate_metal_bottom)
        dev.add_region(gate_metal_left)
        dev.add_region(gate_metal_right)

        # Contacts
        dev.add_contact("source", Box(0, Lsd, 0, W_wire, -5e-9, 0), voltage=Vs)
        dev.add_contact("drain", Box(Lsd + Lg, x_total, 0, W_wire, -5e-9, 0), voltage=Vd)
        dev.add_contact("gate", Box(Lsd, Lsd + Lg, -tox - t_gate, W_wire + tox + t_gate,
                                     t_wire + tox, t_wire + tox + 5e-9), voltage=Vg)

        return dev

    @staticmethod
    def gaa_highk(
        Lg: float = 12e-9,
        t_ox: float = 1.0e-9,
        t_sheet: float = 5e-9,
        W_sheet: float = 20e-9,
        Lsd: float = 20e-9,
        t_gate: float = 10e-9,
        kappa: float = 25.0,
        Vg: float = 0.0,
        Vd: float = 0.0,
        Vs: float = 0.0,
    ) -> Device:
        """
        Generate a Gate-All-Around nanosheet with high-k dielectric.

        Uses HfO2 (or other high-k) instead of SiO2, enabling a thicker
        physical oxide layer for the same equivalent oxide thickness (EOT).
        This reduces gate leakage while maintaining electrostatic control.

        Parameters
        ----------
        Lg : float
            Gate length [m].
        t_ox : float
            Physical high-k thickness [m]. The effective EOT = t_ox * 3.9 / kappa.
        t_sheet : float
            Nanosheet thickness [m].
        W_sheet : float
            Nanosheet width [m].
        Lsd : float
            Source/drain extension length [m].
        t_gate : float
            Gate metal thickness [m].
        kappa : float
            High-k relative permittivity (default 25 for HfO2).
        Vg, Vd, Vs : float
            Gate, drain, source bias [V].
        """
        dev = Device("gaa_highk")
        x_total = 2 * Lsd + Lg

        si = Material("Silicon", epsilon_r=11.7, Eg=1.12)
        highk = Material("HighK", epsilon_r=kappa, Eg=5.7, mu_n=0.0, mu_p=0.0)
        metal = Material("GateMetal", epsilon_r=1.0, mu_n=0.0, mu_p=0.0)

        # Nanosheet channel (lightly p-doped)
        channel = Region(
            "channel",
            Box(Lsd, Lsd + Lg, 0, W_sheet, 0, t_sheet),
            si,
            DopingProfile(Nd=0.0, Na=1e16),
        )
        dev.add_region(channel)

        # Source (n+ doped)
        source = Region(
            "source",
            Box(0, Lsd, 0, W_sheet, 0, t_sheet),
            si,
            DopingProfile(Nd=1e20, Na=0.0),
        )
        dev.add_region(source)

        # Drain (n+ doped)
        drain = Region(
            "drain",
            Box(Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet),
            si,
            DopingProfile(Nd=1e20, Na=0.0),
        )
        dev.add_region(drain)

        # High-k gate dielectric (four sides)
        gate_oxide_top = Region(
            "gate_oxide_top",
            Box(Lsd, Lsd + Lg, 0, W_sheet, t_sheet, t_sheet + t_ox),
            highk,
        )
        gate_oxide_bottom = Region(
            "gate_oxide_bottom",
            Box(Lsd, Lsd + Lg, 0, W_sheet, -t_ox, 0),
            highk,
        )
        gate_oxide_left = Region(
            "gate_oxide_left",
            Box(Lsd, Lsd + Lg, -t_ox, 0, -t_ox, t_sheet + t_ox),
            highk,
        )
        gate_oxide_right = Region(
            "gate_oxide_right",
            Box(Lsd, Lsd + Lg, W_sheet, W_sheet + t_ox, -t_ox, t_sheet + t_ox),
            highk,
        )
        dev.add_region(gate_oxide_top)
        dev.add_region(gate_oxide_bottom)
        dev.add_region(gate_oxide_left)
        dev.add_region(gate_oxide_right)

        # Gate metal (four sides)
        gate_metal_top = Region(
            "gate_metal_top",
            Box(Lsd, Lsd + Lg, -t_ox, W_sheet + t_ox,
                t_sheet + t_ox, t_sheet + t_ox + t_gate),
            metal,
        )
        gate_metal_bottom = Region(
            "gate_metal_bottom",
            Box(Lsd, Lsd + Lg, -t_ox, W_sheet + t_ox,
                -t_ox - t_gate, -t_ox),
            metal,
        )
        gate_metal_left = Region(
            "gate_metal_left",
            Box(Lsd, Lsd + Lg, -t_ox - t_gate, -t_ox,
                -t_ox - t_gate, t_sheet + t_ox + t_gate),
            metal,
        )
        gate_metal_right = Region(
            "gate_metal_right",
            Box(Lsd, Lsd + Lg, W_sheet + t_ox, W_sheet + t_ox + t_gate,
                -t_ox - t_gate, t_sheet + t_ox + t_gate),
            metal,
        )
        dev.add_region(gate_metal_top)
        dev.add_region(gate_metal_bottom)
        dev.add_region(gate_metal_left)
        dev.add_region(gate_metal_right)

        # Contacts
        dev.add_contact("source", Box(0, Lsd, 0, W_sheet, -5e-9, 0), voltage=Vs)
        dev.add_contact("drain", Box(Lsd + Lg, x_total, 0, W_sheet, -5e-9, 0), voltage=Vd)
        dev.add_contact("gate", Box(Lsd, Lsd + Lg, -t_ox - t_gate, W_sheet + t_ox + t_gate,
                                     t_sheet + t_ox, t_sheet + t_ox + 5e-9), voltage=Vg)

        return dev

    @staticmethod
    def gaa_fefet(
        Lg: float = 15e-9,
        t_fe: float = 5e-9,
        t_ox: float = 1.0e-9,
        t_sheet: float = 5e-9,
        W_sheet: float = 20e-9,
        Lsd: float = 20e-9,
        t_gate: float = 10e-9,
        kappa_fe: float = 35.0,
        Vg: float = 0.0,
        Vd: float = 0.0,
        Vs: float = 0.0,
    ) -> Device:
        """
        Generate a Gate-All-Around FeFET (Ferroelectric FET) device template.

        Gate stack (outer to inner): metal gate | ferroelectric (HfZrO) |
        thin interfacial SiO2 | Si nanosheet channel.

        The ferroelectric layer provides negative capacitance amplification,
        enabling sub-60 mV/dec subthreshold swing and non-volatile memory
        operation. Fully compatible with Si back-end processing.

        Parameters
        ----------
        Lg : float
            Gate length [m].
        t_fe : float
            Ferroelectric layer thickness [m].
        t_ox : float
            Interfacial SiO2 thickness [m] (prevents direct FE-Si contact).
        t_sheet : float
            Nanosheet thickness [m].
        W_sheet : float
            Nanosheet width [m].
        Lsd : float
            Source/drain extension length [m].
        t_gate : float
            Gate metal thickness [m].
        kappa_fe : float
            Ferroelectric relative permittivity (~30-40 for HfZrO).
        Vg, Vd, Vs : float
            Gate, drain, source bias [V].
        """
        dev = Device("gaa_fefet")
        x_total = 2 * Lsd + Lg

        si = Material("Silicon", epsilon_r=11.7, Eg=1.12)
        fe = Material("HfZrO", epsilon_r=kappa_fe, Eg=5.5, mu_n=0.0, mu_p=0.0,
                      fe_alpha=-5.0e8, fe_beta=1.5e10)
        oxide = Material("SiO2", epsilon_r=3.9, Eg=9.0, mu_n=0.0, mu_p=0.0)
        metal = Material("GateMetal", epsilon_r=1.0, mu_n=0.0, mu_p=0.0)

        # Nanosheet channel (lightly p-doped)
        channel = Region(
            "channel",
            Box(Lsd, Lsd + Lg, 0, W_sheet, 0, t_sheet),
            si,
            DopingProfile(Nd=0.0, Na=1e16),
        )
        dev.add_region(channel)

        # Source (n+ doped)
        source = Region(
            "source",
            Box(0, Lsd, 0, W_sheet, 0, t_sheet),
            si,
            DopingProfile(Nd=1e20, Na=0.0),
        )
        dev.add_region(source)

        # Drain (n+ doped)
        drain = Region(
            "drain",
            Box(Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet),
            si,
            DopingProfile(Nd=1e20, Na=0.0),
        )
        dev.add_region(drain)

        # Interfacial SiO2 (four sides, thin layer next to channel)
        il_oxide_top = Region(
            "il_oxide_top",
            Box(Lsd, Lsd + Lg, 0, W_sheet, t_sheet, t_sheet + t_ox),
            oxide,
        )
        il_oxide_bottom = Region(
            "il_oxide_bottom",
            Box(Lsd, Lsd + Lg, 0, W_sheet, -t_ox, 0),
            oxide,
        )
        il_oxide_left = Region(
            "il_oxide_left",
            Box(Lsd, Lsd + Lg, -t_ox, 0, -t_ox, t_sheet + t_ox),
            oxide,
        )
        il_oxide_right = Region(
            "il_oxide_right",
            Box(Lsd, Lsd + Lg, W_sheet, W_sheet + t_ox, -t_ox, t_sheet + t_ox),
            oxide,
        )
        dev.add_region(il_oxide_top)
        dev.add_region(il_oxide_bottom)
        dev.add_region(il_oxide_left)
        dev.add_region(il_oxide_right)

        # Ferroelectric layer (four sides, outside interfacial oxide)
        t_outer = t_ox + t_fe
        fe_top = Region(
            "fe_top",
            Box(Lsd, Lsd + Lg, 0, W_sheet, t_sheet + t_ox, t_sheet + t_outer),
            fe,
        )
        fe_bottom = Region(
            "fe_bottom",
            Box(Lsd, Lsd + Lg, 0, W_sheet, -t_outer, -t_ox),
            fe,
        )
        fe_left = Region(
            "fe_left",
            Box(Lsd, Lsd + Lg, -t_outer, -t_ox, -t_outer, t_sheet + t_outer),
            fe,
        )
        fe_right = Region(
            "fe_right",
            Box(Lsd, Lsd + Lg, W_sheet + t_ox, W_sheet + t_outer, -t_outer, t_sheet + t_outer),
            fe,
        )
        dev.add_region(fe_top)
        dev.add_region(fe_bottom)
        dev.add_region(fe_left)
        dev.add_region(fe_right)

        # Gate metal (four sides, outside ferroelectric)
        gate_metal_top = Region(
            "gate_metal_top",
            Box(Lsd, Lsd + Lg, -t_ox, W_sheet + t_ox,
                t_sheet + t_outer, t_sheet + t_outer + t_gate),
            metal,
        )
        gate_metal_bottom = Region(
            "gate_metal_bottom",
            Box(Lsd, Lsd + Lg, -t_ox, W_sheet + t_ox,
                -t_outer - t_gate, -t_outer),
            metal,
        )
        gate_metal_left = Region(
            "gate_metal_left",
            Box(Lsd, Lsd + Lg, -t_outer - t_gate, -t_outer,
                -t_outer - t_gate, t_sheet + t_outer + t_gate),
            metal,
        )
        gate_metal_right = Region(
            "gate_metal_right",
            Box(Lsd, Lsd + Lg, W_sheet + t_outer, W_sheet + t_outer + t_gate,
                -t_outer - t_gate, t_sheet + t_outer + t_gate),
            metal,
        )
        dev.add_region(gate_metal_top)
        dev.add_region(gate_metal_bottom)
        dev.add_region(gate_metal_left)
        dev.add_region(gate_metal_right)

        # Contacts
        dev.add_contact("source", Box(0, Lsd, 0, W_sheet, -5e-9, 0), voltage=Vs)
        dev.add_contact("drain", Box(Lsd + Lg, x_total, 0, W_sheet, -5e-9, 0), voltage=Vd)
        dev.add_contact("gate", Box(Lsd, Lsd + Lg, -t_outer - t_gate, W_sheet + t_outer + t_gate,
                                     t_sheet + t_outer, t_sheet + t_outer + 5e-9), voltage=Vg)

        return dev

    @staticmethod
    def pnjunction(
        L: float = 1e-6,
        W: float = 1e-6,
        H: float = 1e-6,
        x_junction: float = 0.5e-6,
        Na: float = 1e16,
        Nd: float = 1e16,
    ) -> Device:
        """Simple 1D-like pn junction in 3D.

        The contacts cover a thin boundary layer at each end so that the
        Dirichlet BCs (potential + carrier densities) are applied only at the
        terminal faces, leaving the quasi-neutral interior free for the
        continuity solver.  The contact thickness scales with ``L`` (capped at
        100 nm) so that short devices are not entirely consumed by the contact
        masks — e.g. for L=200 nm each contact spans 10 nm, not the 100 nm a
        fixed 0.1 µm thickness would give (which would cover the whole device
        and pin every interior node).
        """
        dev = Device("pn_junction")
        si = Material("Silicon", epsilon_r=11.7)
        dev.add_region(Region("p_side", Box(0, x_junction, 0, W, 0, H), si, DopingProfile(Na=Na)))
        dev.add_region(Region("n_side", Box(x_junction, L, 0, W, 0, H), si, DopingProfile(Nd=Nd)))
        # Contact thickness: 5% of L, capped at 100 nm, and never more than 1/4
        # of either side so contacts stay on their own doping region.
        t_contact = min(0.1e-6, 0.05 * L, 0.25 * x_junction, 0.25 * (L - x_junction))
        # Contacts span the full y-z cross-section (ohmic terminal faces at x=0
        # and x=L), not just a thin z=0 layer.  A small z-overshoot (-1 nm..H+1nm)
        # ensures all boundary nodes are captured even with grid snapping.
        dev.add_contact("p_contact", Box(0, t_contact, 0, W, -1e-9, H + 1e-9), voltage=0.0)
        dev.add_contact("n_contact", Box(L - t_contact, L, 0, W, -1e-9, H + 1e-9), voltage=0.0)
        return dev

    @staticmethod
    def bspdn_gaa(
        Lg: float = 20e-9,
        tox: float = 1.5e-9,
        t_sheet: float = 5e-9,
        W_sheet: float = 30e-9,
        Lsd: float = 30e-9,
        t_gate: float = 10e-9,
        t_bs_metal: float = 20e-9,     # Backside power rail thickness
        t_via: float = 50e-9,           # Backside via height
        t_substrate: float = 30e-9,     # Thinned substrate thickness
        Vdd: float = 0.7,               # Supply voltage for backside rail
        Vg: float = 0.0,
        Vd: float = 0.0,
        Vs: float = 0.0,
    ) -> Device:
        """Gate-All-Around nanosheet with backside power delivery network (BSPDN).

        Unlike conventional GAA where power is delivered through top-side
        source/drain contacts, BSPDN routes VSS/VDD through the backside.
        The device features:

        - Standard GAA nanosheet (source, channel, drain, wrapping gate)
        - Thinned substrate underneath the active region
        - Backside via connecting source to the backside power rail
        - Backside metal power rail at the very bottom

        This enables reduced IR drop in the power grid and smaller cell
        footprint by eliminating top-side power rails.

        All dimensions in meters.
        """
        dev = Device("bspdn_gaa")
        x_total = 2 * Lsd + Lg
        z_top = t_sheet + tox + t_gate

        si = Material("Silicon", epsilon_r=11.7, Eg=1.12)
        oxide = Material("SiO2", epsilon_r=3.9, Eg=9.0, mu_n=0.0, mu_p=0.0)
        metal = Material("GateMetal", epsilon_r=1.0, mu_n=0.0, mu_p=0.0)
        bs_metal = Material("BacksideMetal", epsilon_r=1.0, mu_n=0.0, mu_p=0.0)

        # Nanosheet channel (lightly p-doped)
        channel = Region(
            "channel",
            Box(Lsd, Lsd + Lg, 0, W_sheet, 0, t_sheet),
            si,
            DopingProfile(Nd=0.0, Na=1e16),
        )
        dev.add_region(channel)

        # Source (n+ doped)
        source = Region(
            "source",
            Box(0, Lsd, 0, W_sheet, 0, t_sheet),
            si,
            DopingProfile(Nd=1e20, Na=0.0),
        )
        dev.add_region(source)

        # Drain (n+ doped)
        drain = Region(
            "drain",
            Box(Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet),
            si,
            DopingProfile(Nd=1e20, Na=0.0),
        )
        dev.add_region(drain)

        # Gate oxide (four sides wrapping the channel)
        gate_oxide_top = Region(
            "gate_oxide_top",
            Box(Lsd, Lsd + Lg, 0, W_sheet, t_sheet, t_sheet + tox),
            oxide,
        )
        gate_oxide_bottom = Region(
            "gate_oxide_bottom",
            Box(Lsd, Lsd + Lg, 0, W_sheet, -tox, 0),
            oxide,
        )
        gate_oxide_left = Region(
            "gate_oxide_left",
            Box(Lsd, Lsd + Lg, -tox, 0, -tox, t_sheet + tox),
            oxide,
        )
        gate_oxide_right = Region(
            "gate_oxide_right",
            Box(Lsd, Lsd + Lg, W_sheet, W_sheet + tox, -tox, t_sheet + tox),
            oxide,
        )
        for r in [gate_oxide_top, gate_oxide_bottom, gate_oxide_left, gate_oxide_right]:
            dev.add_region(r)

        # Gate metal (four sides outside the oxide)
        gate_metal_top = Region(
            "gate_metal_top",
            Box(Lsd, Lsd + Lg, -tox, W_sheet + tox,
                t_sheet + tox, t_sheet + tox + t_gate),
            metal,
        )
        gate_metal_bottom = Region(
            "gate_metal_bottom",
            Box(Lsd, Lsd + Lg, -tox, W_sheet + tox,
                -tox - t_gate, -tox),
            metal,
        )
        gate_metal_left = Region(
            "gate_metal_left",
            Box(Lsd, Lsd + Lg, -tox - t_gate, -tox,
                -tox - t_gate, t_sheet + tox + t_gate),
            metal,
        )
        gate_metal_right = Region(
            "gate_metal_right",
            Box(Lsd, Lsd + Lg, W_sheet + tox, W_sheet + tox + t_gate,
                -tox - t_gate, t_sheet + tox + t_gate),
            metal,
        )
        for r in [gate_metal_top, gate_metal_bottom, gate_metal_left, gate_metal_right]:
            dev.add_region(r)

        # Thinned substrate (below the active region)
        substrate = Region(
            "substrate",
            Box(0, x_total, -tox - t_gate, W_sheet + tox + t_gate,
                -t_substrate, 0),
            si,
            DopingProfile(Nd=0.0, Na=1e18),
        )
        dev.add_region(substrate)

        # Backside via: connects source region to backside power rail
        # Placed under the source side of the channel
        via_width = min(Lsd * 0.6, W_sheet * 0.5)
        via_x_start = Lsd * 0.2
        via_y_start = (W_sheet - via_width) / 2.0
        backside_via = Region(
            "bs_via",
            Box(via_x_start, via_x_start + via_width,
                via_y_start, via_y_start + via_width,
                -t_substrate - t_via, -t_substrate),
            si,
            DopingProfile(Nd=1e20, Na=0.0),
        )
        dev.add_region(backside_via)

        # Backside power rail (metal at the very bottom)
        bs_rail = Region(
            "bs_power_rail",
            Box(0, x_total, 0, W_sheet,
                -t_substrate - t_via - t_bs_metal, -t_substrate - t_via),
            bs_metal,
        )
        dev.add_region(bs_rail)

        # Contacts
        dev.add_contact("drain", Box(Lsd + Lg, x_total, 0, W_sheet, -5e-9, 0), voltage=Vd)
        dev.add_contact("gate", Box(Lsd, Lsd + Lg, -tox - t_gate, W_sheet + tox + t_gate,
                                     t_sheet + tox, t_sheet + tox + 5e-9), voltage=Vg)
        dev.add_contact("bs_power", Box(0, x_total, 0, W_sheet,
                                         -t_substrate - t_via - t_bs_metal - 5e-9,
                                         -t_substrate - t_via),
                        voltage=Vdd)

        return dev

    @staticmethod
    def dirac_source_fet(
        Lg: float = 20e-9,
        tox: float = 1.5e-9,
        t_sheet: float = 5e-9,
        W_sheet: float = 30e-9,
        Lsd: float = 30e-9,
        t_gate: float = 10e-9,
        t_box: float = 10e-9,
        source_doping: float = 1e18,
        channel_doping: float = 1e16,
        drain_doping: float = 1e20,
        Vg: float = 0.0,
        Vd: float = 0.3,
        Vs: float = 0.0,
    ) -> Device:
        """
        Generate a Dirac-Source FET (DSFET) device template.

        The DSFET uses a graphene (or other Dirac-material) source to exploit
        the unique DOS(E) ~ |E-E_D| profile, which suppresses the high-energy
        thermal tail of electron injection and enables steep subthreshold
        switching beyond the conventional 60 mV/dec Boltzmann limit.

        This template implements a GAA-nanosheet geometry where the source
        region is graphene and the channel/drain are silicon, forming a
        graphene/silicon heterojunction source.

        All dimensions in meters.
        """
        dev = Device("dirac_source_fet")
        x_total = 2 * Lsd + Lg
        y_total = W_sheet + 2 * tox + 2 * t_gate
        z_top = t_sheet + tox + t_gate

        # Materials
        si = Material("Silicon", epsilon_r=11.7, Eg=1.12)
        # Graphene source with a small effective bandgap (~0.2 eV) to avoid
        # numerical instabilities at the graphene/Si heterojunction while
        # preserving the low effective DOS that gives the cold-source effect.
        graphene = Material(
            "Graphene",
            epsilon_r=2.5,
            Eg=0.2,
            chi=4.5,
            Nc=1.0e17,       # Effective low DOS for cold-source injection
            Nv=1.0e17,
            mu_n=200000.0,
            mu_p=200000.0,
        )
        oxide = Material("SiO2", epsilon_r=3.9, Eg=9.0, mu_n=0.0, mu_p=0.0)
        metal = Material("GateMetal", epsilon_r=1.0, mu_n=0.0, mu_p=0.0)

        # Substrate (silicon bulk underneath BOX)
        substrate = Region(
            "substrate",
            Box(0, x_total, -tox - t_gate, W_sheet + tox + t_gate,
                -t_box - 50e-9, -t_box),
            si,
            DopingProfile(Nd=0.0, Na=1e18),
        )
        dev.add_region(substrate)

        # Buried oxide (BOX)
        box = Region(
            "box",
            Box(0, x_total, -tox - t_gate, W_sheet + tox + t_gate,
                -t_box, 0),
            oxide,
        )
        dev.add_region(box)

        # Channel (lightly doped silicon)
        channel = Region(
            "channel",
            Box(Lsd, Lsd + Lg, 0, W_sheet, 0, t_sheet),
            si,
            DopingProfile(Nd=0.0, Na=channel_doping),
        )
        dev.add_region(channel)

        # Source (graphene Dirac source)
        source = Region(
            "source",
            Box(0, Lsd, 0, W_sheet, 0, t_sheet),
            graphene,
            DopingProfile(Nd=source_doping, Na=0.0),
        )
        dev.add_region(source)

        # Drain (n+ doped silicon)
        drain = Region(
            "drain",
            Box(Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet),
            si,
            DopingProfile(Nd=drain_doping, Na=0.0),
        )
        dev.add_region(drain)

        # Gate oxide (four sides wrapping the channel)
        gate_oxide_top = Region(
            "gate_oxide_top",
            Box(Lsd, Lsd + Lg, 0, W_sheet, t_sheet, t_sheet + tox),
            oxide,
        )
        gate_oxide_bottom = Region(
            "gate_oxide_bottom",
            Box(Lsd, Lsd + Lg, 0, W_sheet, -tox, 0),
            oxide,
        )
        gate_oxide_left = Region(
            "gate_oxide_left",
            Box(Lsd, Lsd + Lg, -tox, 0, -tox, t_sheet + tox),
            oxide,
        )
        gate_oxide_right = Region(
            "gate_oxide_right",
            Box(Lsd, Lsd + Lg, W_sheet, W_sheet + tox, -tox, t_sheet + tox),
            oxide,
        )
        dev.add_region(gate_oxide_top)
        dev.add_region(gate_oxide_bottom)
        dev.add_region(gate_oxide_left)
        dev.add_region(gate_oxide_right)

        # Gate metal (four sides outside the oxide)
        gate_metal_top = Region(
            "gate_metal_top",
            Box(Lsd, Lsd + Lg, -tox, W_sheet + tox,
                t_sheet + tox, t_sheet + tox + t_gate),
            metal,
        )
        gate_metal_bottom = Region(
            "gate_metal_bottom",
            Box(Lsd, Lsd + Lg, -tox, W_sheet + tox,
                -tox - t_gate, -tox),
            metal,
        )
        gate_metal_left = Region(
            "gate_metal_left",
            Box(Lsd, Lsd + Lg, -tox - t_gate, -tox,
                -tox - t_gate, t_sheet + tox + t_gate),
            metal,
        )
        gate_metal_right = Region(
            "gate_metal_right",
            Box(Lsd, Lsd + Lg, W_sheet + tox, W_sheet + tox + t_gate,
                -tox - t_gate, t_sheet + tox + t_gate),
            metal,
        )
        dev.add_region(gate_metal_top)
        dev.add_region(gate_metal_bottom)
        dev.add_region(gate_metal_left)
        dev.add_region(gate_metal_right)

        # Contacts (extend into device regions to ensure mesh node overlap)
        dev.add_contact("source", Box(0, Lsd, 0, W_sheet, 0, t_sheet), voltage=Vs)
        dev.add_contact("drain", Box(Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet), voltage=Vd)
        dev.add_contact("gate", Box(Lsd, Lsd + Lg, -tox - t_gate, W_sheet + tox + t_gate,
                                     t_sheet + tox, t_sheet + tox + t_gate), voltage=Vg)

        return dev

    @staticmethod
    def dirac_source_fefet(
        Lg: float = 20e-9,
        t_fe: float = 4e-9,
        t_ox: float = 1.0e-9,
        t_sheet: float = 5e-9,
        W_sheet: float = 30e-9,
        Lsd: float = 30e-9,
        t_gate: float = 10e-9,
        kappa_fe: float = 35.0,
        source_doping: float = 1e18,
        channel_doping: float = 1e16,
        drain_doping: float = 1e20,
        Vg: float = 0.0,
        Vd: float = 0.3,
        Vs: float = 0.0,
    ) -> Device:
        """
        Graphene-Source Negative-Capacitance Nanosheet FET (GS-NC-NSFET).

        Novel device concept combining two steep-slope mechanisms:
        1. **Dirac-source cold injection** — graphene source with suppressed
           effective DOS (Nc=Nv~1e17 cm-3) mimics the linear DOS(E) of Dirac
           cones, cutting the high-energy thermal tail of carrier injection.
        2. **Ferroelectric negative capacitance** — HfZrO gate stack provides
           voltage amplification via the Landau-Khalatnikov effect, further
           lowering subthreshold swing below the Boltzmann limit.

        The combination yields ultra-steep switching with CMOS-compatible
        materials (GAA nanosheet + HfZrO ferroelectric + CVD graphene).

        Stack (outer -> inner): metal gate | HfZrO FE | SiO2 IL | Si channel
        Source: graphene (p+ doped), Channel: lightly doped Si, Drain: n+ Si
        """
        dev = Device("dirac_source_fefet")
        x_total = 2 * Lsd + Lg

        si = Material("Silicon", epsilon_r=11.7, Eg=1.12)
        graphene = Material(
            "Graphene",
            epsilon_r=2.5,
            Eg=0.2,
            chi=4.5,
            Nc=1.0e17,
            Nv=1.0e17,
            mu_n=200000.0,
            mu_p=200000.0,
        )
        fe = Material("HfZrO", epsilon_r=kappa_fe, Eg=5.5, mu_n=0.0, mu_p=0.0,
                      fe_alpha=-5.0e8, fe_beta=1.5e10)
        oxide = Material("SiO2", epsilon_r=3.9, Eg=9.0, mu_n=0.0, mu_p=0.0)
        metal = Material("GateMetal", epsilon_r=1.0, mu_n=0.0, mu_p=0.0)

        # Channel (lightly doped silicon)
        channel = Region(
            "channel",
            Box(Lsd, Lsd + Lg, 0, W_sheet, 0, t_sheet),
            si,
            DopingProfile(Nd=0.0, Na=channel_doping),
        )
        dev.add_region(channel)

        # Source (graphene Dirac source)
        source = Region(
            "source",
            Box(0, Lsd, 0, W_sheet, 0, t_sheet),
            graphene,
            DopingProfile(Nd=source_doping, Na=0.0),
        )
        dev.add_region(source)

        # Drain (n+ doped silicon)
        drain = Region(
            "drain",
            Box(Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet),
            si,
            DopingProfile(Nd=drain_doping, Na=0.0),
        )
        dev.add_region(drain)

        # Interfacial SiO2 (four sides, thin layer next to channel)
        il_oxide_top = Region(
            "il_oxide_top",
            Box(Lsd, Lsd + Lg, 0, W_sheet, t_sheet, t_sheet + t_ox),
            oxide,
        )
        il_oxide_bottom = Region(
            "il_oxide_bottom",
            Box(Lsd, Lsd + Lg, 0, W_sheet, -t_ox, 0),
            oxide,
        )
        il_oxide_left = Region(
            "il_oxide_left",
            Box(Lsd, Lsd + Lg, -t_ox, 0, -t_ox, t_sheet + t_ox),
            oxide,
        )
        il_oxide_right = Region(
            "il_oxide_right",
            Box(Lsd, Lsd + Lg, W_sheet, W_sheet + t_ox, -t_ox, t_sheet + t_ox),
            oxide,
        )
        dev.add_region(il_oxide_top)
        dev.add_region(il_oxide_bottom)
        dev.add_region(il_oxide_left)
        dev.add_region(il_oxide_right)

        # Ferroelectric layer (four sides, outside interfacial oxide)
        t_outer = t_ox + t_fe
        fe_top = Region(
            "fe_top",
            Box(Lsd, Lsd + Lg, 0, W_sheet, t_sheet + t_ox, t_sheet + t_outer),
            fe,
        )
        fe_bottom = Region(
            "fe_bottom",
            Box(Lsd, Lsd + Lg, 0, W_sheet, -t_outer, -t_ox),
            fe,
        )
        fe_left = Region(
            "fe_left",
            Box(Lsd, Lsd + Lg, -t_outer, -t_ox, -t_outer, t_sheet + t_outer),
            fe,
        )
        fe_right = Region(
            "fe_right",
            Box(Lsd, Lsd + Lg, W_sheet + t_ox, W_sheet + t_outer, -t_outer, t_sheet + t_outer),
            fe,
        )
        dev.add_region(fe_top)
        dev.add_region(fe_bottom)
        dev.add_region(fe_left)
        dev.add_region(fe_right)

        # Gate metal (four sides, outside ferroelectric)
        gate_metal_top = Region(
            "gate_metal_top",
            Box(Lsd, Lsd + Lg, -t_outer, W_sheet + t_outer,
                t_sheet + t_outer, t_sheet + t_outer + t_gate),
            metal,
        )
        gate_metal_bottom = Region(
            "gate_metal_bottom",
            Box(Lsd, Lsd + Lg, -t_outer, W_sheet + t_outer,
                -t_outer - t_gate, -t_outer),
            metal,
        )
        gate_metal_left = Region(
            "gate_metal_left",
            Box(Lsd, Lsd + Lg, -t_outer - t_gate, -t_outer,
                -t_outer - t_gate, t_sheet + t_outer + t_gate),
            metal,
        )
        gate_metal_right = Region(
            "gate_metal_right",
            Box(Lsd, Lsd + Lg, W_sheet + t_outer, W_sheet + t_outer + t_gate,
                -t_outer - t_gate, t_sheet + t_outer + t_gate),
            metal,
        )
        dev.add_region(gate_metal_top)
        dev.add_region(gate_metal_bottom)
        dev.add_region(gate_metal_left)
        dev.add_region(gate_metal_right)

        # Contacts
        dev.add_contact("source", Box(0, Lsd, 0, W_sheet, 0, t_sheet), voltage=Vs)
        dev.add_contact("drain", Box(Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet), voltage=Vd)
        dev.add_contact("gate", Box(Lsd, Lsd + Lg, -t_outer - t_gate, W_sheet + t_outer + t_gate,
                                     t_sheet + t_outer, t_sheet + t_outer + t_gate), voltage=Vg)

        return dev

    @staticmethod
    def tfet(
        Lg: float = 20e-9,
        tox: float = 1.5e-9,
        t_sheet: float = 5e-9,
        W_sheet: float = 20e-9,
        Lsd: float = 20e-9,
        t_gate: float = 10e-9,
        source_doping: float = 5e20,
        channel_doping: float = 1e15,
        drain_doping: float = 1e20,
        Vg: float = 0.0,
        Vd: float = 0.5,
        Vs: float = 0.0,
    ) -> Device:
        """
        Generate a Gate-All-Around n-TFET (Tunnel FET) device template.

        TFETs use band-to-band tunneling (BTBT) as the carrier injection
        mechanism instead of thermionic emission. This enables sub-60 mV/dec
        subthreshold swing and ultra-low-voltage operation.

        n-TFET structure (along x):
          p+ source -> intrinsic/lightly-p channel -> n+ drain

        When the gate raises the channel potential, the source valence band
        aligns with the channel conduction band, creating a tunneling window.
        Electrons tunnel from the p+ source valence band into the channel
        conduction band, then drift to the n+ drain.

        The key advantage over MOSFETs: the turn-on mechanism is quantum
        tunneling rather than thermal emission, so the subthreshold swing
        is not limited by kT/q (~60 mV/dec at 300K).

        Parameters
        ----------
        Lg : float
            Gate length [m]. Sub-20 nm is typical for TFETs.
        tox : float
            Gate oxide thickness [m].
        t_sheet : float
            Nanosheet thickness [m]. Thin sheets improve electrostatic control.
        W_sheet : float
            Nanosheet width [m].
        Lsd : float
            Source/drain extension length [m].
        t_gate : float
            Gate metal thickness [m].
        source_doping : float
            p+ source acceptor concentration [cm^-3]. High doping narrows
            the tunneling barrier for higher I_on.
        channel_doping : float
            Channel acceptor concentration [cm^-3]. Light doping keeps the
            channel depleted and maximizes gate control.
        drain_doping : float
            n+ drain donor concentration [cm^-3].
        Vg, Vd, Vs : float
            Gate, drain, source bias [V].
        """
        dev = Device("tfet")
        x_total = 2 * Lsd + Lg

        si = Material("Silicon", epsilon_r=11.7, Eg=1.12)
        oxide = Material("SiO2", epsilon_r=3.9, Eg=9.0, mu_n=0.0, mu_p=0.0)
        metal = Material("GateMetal", epsilon_r=1.0, mu_n=0.0, mu_p=0.0)

        # p+ source region (reversed vs MOSFET: p+ instead of n+)
        source = Region(
            "source",
            Box(0, Lsd, 0, W_sheet, 0, t_sheet),
            si,
            DopingProfile(Nd=0.0, Na=source_doping),
        )
        dev.add_region(source)

        # Intrinsic / lightly p-doped channel
        channel = Region(
            "channel",
            Box(Lsd, Lsd + Lg, 0, W_sheet, 0, t_sheet),
            si,
            DopingProfile(Nd=0.0, Na=channel_doping),
        )
        dev.add_region(channel)

        # n+ drain region
        drain = Region(
            "drain",
            Box(Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet),
            si,
            DopingProfile(Nd=drain_doping, Na=0.0),
        )
        dev.add_region(drain)

        # Gate oxide (four sides, GAA geometry)
        gate_oxide_top = Region(
            "gate_oxide_top",
            Box(Lsd, Lsd + Lg, 0, W_sheet, t_sheet, t_sheet + tox),
            oxide,
        )
        gate_oxide_bottom = Region(
            "gate_oxide_bottom",
            Box(Lsd, Lsd + Lg, 0, W_sheet, -tox, 0),
            oxide,
        )
        gate_oxide_left = Region(
            "gate_oxide_left",
            Box(Lsd, Lsd + Lg, -tox, 0, -tox, t_sheet + tox),
            oxide,
        )
        gate_oxide_right = Region(
            "gate_oxide_right",
            Box(Lsd, Lsd + Lg, W_sheet, W_sheet + tox, -tox, t_sheet + tox),
            oxide,
        )
        for r in [gate_oxide_top, gate_oxide_bottom, gate_oxide_left, gate_oxide_right]:
            dev.add_region(r)

        # Gate metal (four sides)
        gate_metal_top = Region(
            "gate_metal_top",
            Box(Lsd, Lsd + Lg, 0, W_sheet, t_sheet + tox, t_sheet + tox + t_gate),
            metal,
        )
        gate_metal_bottom = Region(
            "gate_metal_bottom",
            Box(Lsd, Lsd + Lg, 0, W_sheet, -tox - t_gate, -tox),
            metal,
        )
        gate_metal_left = Region(
            "gate_metal_left",
            Box(Lsd, Lsd + Lg, -tox - t_gate, -tox, -tox - t_gate, t_sheet + tox + t_gate),
            metal,
        )
        gate_metal_right = Region(
            "gate_metal_right",
            Box(Lsd, Lsd + Lg, W_sheet + tox, W_sheet + tox + t_gate,
                -tox - t_gate, t_sheet + tox + t_gate),
            metal,
        )
        for r in [gate_metal_top, gate_metal_bottom, gate_metal_left, gate_metal_right]:
            dev.add_region(r)

        # Contacts (extend into the silicon for proper node coverage)
        dev.add_contact("source", Box(0, Lsd, 0, W_sheet, 0, t_sheet * 0.3), voltage=Vs)
        dev.add_contact("drain", Box(Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet * 0.3), voltage=Vd)
        dev.add_contact("gate", Box(Lsd, Lsd + Lg, -tox - t_gate, W_sheet + tox + t_gate,
                                     t_sheet + tox, t_sheet + 50e-9), voltage=Vg)

        return dev

    @staticmethod
    def heterojunction_tfet(
        Lg: float = 20e-9,
        tox: float = 1.5e-9,
        t_sheet: float = 5e-9,
        W_sheet: float = 20e-9,
        Lsd: float = 20e-9,
        L_source_hj: float = 10e-9,  # Heterojunction source region length
        t_gate: float = 10e-9,
        ge_fraction: float = 0.4,
        source_doping: float = 5e20,
        channel_doping: float = 1e15,
        drain_doping: float = 1e20,
        Vg: float = 0.0,
        Vd: float = 0.5,
        Vs: float = 0.0,
    ) -> Device:
        """
        Generate a Heterojunction n-TFET with SiGe source.

        A SiGe source region (lower bandgap) is placed at the source-channel
        junction. This narrows the BTBT tunneling barrier compared to pure Si,
        significantly increasing I_on while maintaining low I_off.

        The SiGe/Si heterojunction also creates a straddling (type-I) or
        staggered (type-II) band alignment that further enhances tunneling
        efficiency.

        n-HJ-TFET structure (along x):
          p+ SiGe source -> SiGe/Si heterojunction -> Si channel -> n+ Si drain

        Parameters
        ----------
        Lg : float
            Gate length [m].
        L_source_hj : float
            SiGe heterojunction source region length [m]. Should be thin
            enough for good tunneling but thick enough to provide the
            bandgap advantage (~5-15 nm).
        ge_fraction : float
            Ge mole fraction in SiGe source (0-0.5). Higher Ge reduces
            bandgap but increases lattice strain.
        Other parameters: same as tfet().
        """
        dev = Device("heterojunction_tfet")
        x_total = 2 * Lsd + Lg

        si = Material("Silicon", epsilon_r=11.7, Eg=1.12)
        sige = Material(
            name=f"SiGe_x{ge_fraction:.2f}",
            epsilon_r=11.7 + 4.3 * ge_fraction,
            Eg=1.12 - 0.75 * ge_fraction + 0.35 * ge_fraction * ge_fraction,
            chi=4.05 + 0.5 * ge_fraction,
            Nc=2.8e19,
            Nv=1.04e19 * (1 + 2.0 * ge_fraction),
            mu_n=1400.0 - 800.0 * ge_fraction,
            mu_p=450.0 + 1200.0 * ge_fraction,
        )
        oxide = Material("SiO2", epsilon_r=3.9, Eg=9.0, mu_n=0.0, mu_p=0.0)
        metal = Material("GateMetal", epsilon_r=1.0, mu_n=0.0, mu_p=0.0)

        # Bulk SiGe source (deep in source region, away from junction)
        source_bulk = Region(
            "source_bulk",
            Box(0, Lsd - L_source_hj, 0, W_sheet, 0, t_sheet),
            sige,
            DopingProfile(Nd=0.0, Na=source_doping),
        )
        dev.add_region(source_bulk)

        # SiGe at the tunneling junction (heterojunction region)
        source_hj = Region(
            "source_hj",
            Box(Lsd - L_source_hj, Lsd, 0, W_sheet, 0, t_sheet),
            sige,
            DopingProfile(Nd=0.0, Na=source_doping),
        )
        dev.add_region(source_hj)

        # Si channel
        channel = Region(
            "channel",
            Box(Lsd, Lsd + Lg, 0, W_sheet, 0, t_sheet),
            si,
            DopingProfile(Nd=0.0, Na=channel_doping),
        )
        dev.add_region(channel)

        # n+ Si drain
        drain = Region(
            "drain",
            Box(Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet),
            si,
            DopingProfile(Nd=drain_doping, Na=0.0),
        )
        dev.add_region(drain)

        # Gate oxide (four sides, only under gate region)
        gate_oxide_top = Region(
            "gate_oxide_top",
            Box(Lsd, Lsd + Lg, 0, W_sheet, t_sheet, t_sheet + tox),
            oxide,
        )
        gate_oxide_bottom = Region(
            "gate_oxide_bottom",
            Box(Lsd, Lsd + Lg, 0, W_sheet, -tox, 0),
            oxide,
        )
        gate_oxide_left = Region(
            "gate_oxide_left",
            Box(Lsd, Lsd + Lg, -tox, 0, -tox, t_sheet + tox),
            oxide,
        )
        gate_oxide_right = Region(
            "gate_oxide_right",
            Box(Lsd, Lsd + Lg, W_sheet, W_sheet + tox, -tox, t_sheet + tox),
            oxide,
        )
        for r in [gate_oxide_top, gate_oxide_bottom, gate_oxide_left, gate_oxide_right]:
            dev.add_region(r)

        # Gate metal (four sides)
        gate_metal_top = Region(
            "gate_metal_top",
            Box(Lsd, Lsd + Lg, 0, W_sheet, t_sheet + tox, t_sheet + tox + t_gate),
            metal,
        )
        gate_metal_bottom = Region(
            "gate_metal_bottom",
            Box(Lsd, Lsd + Lg, 0, W_sheet, -tox - t_gate, -tox),
            metal,
        )
        gate_metal_left = Region(
            "gate_metal_left",
            Box(Lsd, Lsd + Lg, -tox - t_gate, -tox, -tox - t_gate, t_sheet + tox + t_gate),
            metal,
        )
        gate_metal_right = Region(
            "gate_metal_right",
            Box(Lsd, Lsd + Lg, W_sheet + tox, W_sheet + tox + t_gate,
                -tox - t_gate, t_sheet + tox + t_gate),
            metal,
        )
        for r in [gate_metal_top, gate_metal_bottom, gate_metal_left, gate_metal_right]:
            dev.add_region(r)

        # Contacts (extend into the silicon for proper node coverage)
        dev.add_contact("source", Box(0, Lsd, 0, W_sheet, 0, t_sheet * 0.3), voltage=Vs)
        dev.add_contact("drain", Box(Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet * 0.3), voltage=Vd)
        dev.add_contact("gate", Box(Lsd, Lsd + Lg, -tox - t_gate, W_sheet + tox + t_gate,
                                     t_sheet + tox, t_sheet + 50e-9), voltage=Vg)

        return dev

    @staticmethod
    def tunnel_diode(
        Lp: float = 20e-9,
        Ln: float = 20e-9,
        W: float = 20e-9,
        H: float = 20e-9,
        Na: float = 5e20,
        Nd: float = 5e20,
    ) -> Device:
        """Esaki / tunnel diode with negative differential resistance.

        A heavily doped p+/n+ junction where band-to-band tunneling (BTBT)
        dominates transport. The extreme doping (~5e20 cm^-3) narrows the
        depletion region to ~5-10 nm, enabling strong quantum tunneling.

        I-V characteristics:
          - Low forward bias: bands overlap -> strong tunneling -> high current
          - Moderate bias: overlap decreases -> current drops -> NDR region
          - Higher bias: normal diode diffusion current dominates

        This 2-terminal device enables multi-valued logic, GHz oscillators,
        and compact SRAM cells --- fundamentally different from 3-terminal FETs.

        Parameters
        ----------
        Lp : float
            p+ region length [m]. ~20 nm typical.
        Ln : float
            n+ region length [m]. ~20 nm typical.
        W : float
            Device width [m].
        H : float
            Device height [m].
        Na : float
            p+ acceptor doping [cm^-3]. Degenerate: >= 1e20 for strong NDR.
        Nd : float
            n+ donor doping [cm^-3]. Degenerate: >= 1e20 for strong NDR.
        """
        dev = Device("tunnel_diode")
        x_total = Lp + Ln

        si = Material("Silicon", epsilon_r=11.7, Eg=1.12)

        # p+ region
        p_side = Region(
            "p_side",
            Box(0, Lp, 0, W, 0, H),
            si,
            DopingProfile(Nd=0.0, Na=Na),
        )
        dev.add_region(p_side)

        # n+ region
        n_side = Region(
            "n_side",
            Box(Lp, x_total, 0, W, 0, H),
            si,
            DopingProfile(Nd=Nd, Na=0.0),
        )
        dev.add_region(n_side)

        # Two terminal contacts
        dev.add_contact("anode", Box(0, Lp * 0.5, 0, W, -0.01e-6, 0), voltage=0.0)
        dev.add_contact("cathode", Box(x_total - Ln * 0.5, x_total, 0, W, -0.01e-6, 0), voltage=0.0)

        return dev

    @staticmethod
    def graphene_source_tfet(
        Lg: float = 15e-9,
        tox: float = 1.0e-9,
        t_sheet: float = 5e-9,
        W_sheet: float = 20e-9,
        Lsd: float = 20e-9,
        t_gate: float = 10e-9,
        t_box: float = 10e-9,
        source_doping: float = 5e20,
        channel_doping: float = 1e15,
        drain_doping: float = 1e20,
        Vg: float = 0.0,
        Vd: float = 0.3,
        Vs: float = 0.0,
    ) -> Device:
        """Graphene-Source Tunnel FET (GS-TFET).

        Combines two steep-slope mechanisms in a single device:
        1. **BTBT tunneling** — carriers tunnel from the source valence band
           into the channel conduction band, bypassing the thermionic limit.
        2. **Cold-source effect** — graphene's linear DOS(E) ~ |E-E_D|
           suppresses the high-energy thermal tail, sharpening the turn-on.

        n-GS-TFET structure (along x):
          p+ graphene source -> Si channel -> n+ Si drain

        Unlike a standard TFET (Si source), the graphene source reduces the
        number of electrons with enough thermal energy to contribute to
        off-state leakage, lowering I_off.  Unlike a DSFET (thermionic), the
        switching is governed by BTBT rather than thermal emission, enabling
        sub-60 mV/dec even without DOS engineering alone.

        All materials (Si, SiO2, HfO2, CVD graphene) are CMOS-compatible.

        Parameters
        ----------
        Lg : float
            Gate length [m].
        tox : float
            Gate oxide thickness [m].
        t_sheet : float
            Nanosheet thickness [m].
        W_sheet : float
            Nanosheet width [m].
        Lsd : float
            Source/drain extension length [m].
        t_gate : float
            Gate metal thickness [m].
        t_box : float
            Buried oxide thickness [m].
        source_doping : float
            p+ graphene source acceptor concentration [cm^-3].
        channel_doping : float
            Channel acceptor concentration [cm^-3].
        drain_doping : float
            n+ Si drain donor concentration [cm^-3].
        Vg, Vd, Vs : float
            Gate, drain, source bias [V].
        """
        dev = Device("graphene_source_tfet")
        x_total = 2 * Lsd + Lg

        si = Material("Silicon", epsilon_r=11.7, Eg=1.12)
        graphene = Material(
            "Graphene",
            epsilon_r=2.5,
            Eg=0.2,
            chi=4.5,
            Nc=1.0e17,
            Nv=1.0e17,
            mu_n=200000.0,
            mu_p=200000.0,
        )
        oxide = Material("SiO2", epsilon_r=3.9, Eg=9.0, mu_n=0.0, mu_p=0.0)
        metal = Material("GateMetal", epsilon_r=1.0, mu_n=0.0, mu_p=0.0)

        # Substrate
        substrate = Region(
            "substrate",
            Box(0, x_total, -tox - t_gate, W_sheet + tox + t_gate,
                -t_box - 50e-9, -t_box),
            si,
            DopingProfile(Nd=0.0, Na=1e18),
        )
        dev.add_region(substrate)

        # Buried oxide
        box = Region(
            "box",
            Box(0, x_total, -tox - t_gate, W_sheet + tox + t_gate,
                -t_box, 0),
            oxide,
        )
        dev.add_region(box)

        # p+ graphene source
        source = Region(
            "source",
            Box(0, Lsd, 0, W_sheet, 0, t_sheet),
            graphene,
            DopingProfile(Nd=0.0, Na=source_doping),
        )
        dev.add_region(source)

        # Si channel (lightly p-doped)
        channel = Region(
            "channel",
            Box(Lsd, Lsd + Lg, 0, W_sheet, 0, t_sheet),
            si,
            DopingProfile(Nd=0.0, Na=channel_doping),
        )
        dev.add_region(channel)

        # n+ Si drain
        drain = Region(
            "drain",
            Box(Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet),
            si,
            DopingProfile(Nd=drain_doping, Na=0.0),
        )
        dev.add_region(drain)

        # Gate oxide (four sides, GAA)
        gate_oxide_top = Region(
            "gate_oxide_top",
            Box(Lsd, Lsd + Lg, 0, W_sheet, t_sheet, t_sheet + tox),
            oxide,
        )
        gate_oxide_bottom = Region(
            "gate_oxide_bottom",
            Box(Lsd, Lsd + Lg, 0, W_sheet, -tox, 0),
            oxide,
        )
        gate_oxide_left = Region(
            "gate_oxide_left",
            Box(Lsd, Lsd + Lg, -tox, 0, -tox, t_sheet + tox),
            oxide,
        )
        gate_oxide_right = Region(
            "gate_oxide_right",
            Box(Lsd, Lsd + Lg, W_sheet, W_sheet + tox, -tox, t_sheet + tox),
            oxide,
        )
        for r in [gate_oxide_top, gate_oxide_bottom, gate_oxide_left, gate_oxide_right]:
            dev.add_region(r)

        # Gate metal (four sides)
        gate_metal_top = Region(
            "gate_metal_top",
            Box(Lsd, Lsd + Lg, 0, W_sheet, t_sheet + tox, t_sheet + tox + t_gate),
            metal,
        )
        gate_metal_bottom = Region(
            "gate_metal_bottom",
            Box(Lsd, Lsd + Lg, 0, W_sheet, -tox - t_gate, -tox),
            metal,
        )
        gate_metal_left = Region(
            "gate_metal_left",
            Box(Lsd, Lsd + Lg, -tox - t_gate, -tox, -tox - t_gate, t_sheet + tox + t_gate),
            metal,
        )
        gate_metal_right = Region(
            "gate_metal_right",
            Box(Lsd, Lsd + Lg, W_sheet + tox, W_sheet + tox + t_gate,
                -tox - t_gate, t_sheet + tox + t_gate),
            metal,
        )
        for r in [gate_metal_top, gate_metal_bottom, gate_metal_left, gate_metal_right]:
            dev.add_region(r)

        # Contacts
        dev.add_contact("source", Box(0, Lsd, 0, W_sheet, 0, t_sheet * 0.3), voltage=Vs)
        dev.add_contact("drain", Box(Lsd + Lg, x_total, 0, W_sheet, 0, t_sheet * 0.3), voltage=Vd)
        dev.add_contact("gate", Box(Lsd, Lsd + Lg, -tox - t_gate, W_sheet + tox + t_gate,
                                     t_sheet + tox, t_sheet + 50e-9), voltage=Vg)

        return dev
