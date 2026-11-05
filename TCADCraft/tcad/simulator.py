"""High-level Python API for 3D quantum-corrected device simulation."""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import warnings
from contextlib import contextmanager
from copy import deepcopy
import numpy as np

from tcad.geometry.device_builder import Device
from tcad.mesh.structured_grid import StructuredGrid
from tcad.solver.unstructured_simulator import UnstructuredSimulator
from tcad.mesh.cut_cell import compute_edge_permittivity
from tcad.mesh.generator import structured_mesh_from_device
from tcad.mesh.adaptive_refiner import AdaptiveRefiner
from tcad.core import PyDeviceSimulator, SolverType, native_constants
from tcad.configuration import RecordingBackend, install_configuration_recording


class Simulator:
    """
    End-to-end device simulator.

    Workflow
    --------
    1. Build a :class:`tcad.geometry.Device` (or use templates like ``Device.mosfet()``).
    2. Generate a mesh (structured Cartesian recommended for C++ solver).
    3. Create ``Simulator(mesh)`` and call ``run()``.
    4. Inspect results and visualize.
    """

    def __init__(self, mesh: StructuredGrid, temperature: float = 300.0):
        if not isinstance(mesh, StructuredGrid):
            raise TypeError("C++ solver currently only supports StructuredGrid")
        self.mesh = mesh
        self.temperature = temperature
        self.VT = 8.617333262e-5 * temperature  # kB/q [V]
        self._elementary_charge_C = float(native_constants()['elementary_charge_C'])

        axes = mesh.axis_coordinates()
        g = mesh.to_cxx_grid()
        self._sim = PyDeviceSimulator(g["nx"], g["ny"], g["nz"],
                                      g["dx"], g["dy"], g["dz"])
        # Adaptive grids retain average dx/dy/dz as metadata. The native
        # operator must instead use actual edge lengths on nonuniform axes.
        # Leave uniform axes in the existing native uniform mode.
        for axis, coords in zip('xyz', axes):
            if not np.array_equal(coords, np.linspace(coords[0], coords[-1], len(coords))):
                getattr(self._sim, f'set_{axis}_positions')(coords)
        self.results: Optional[Dict[str, np.ndarray]] = None
        self._accepted_initial_guess = None
        self._accepted_contact_voltages: Dict[str, float] = {}
        self._contact_voltages: Dict[str, float] = {}
        self._transient_contact_waveforms = None
        self._contact_workfunctions: Dict[str, float] = {}
        self._schottky_contact_models: Dict[str, object] = {}
        self._pending_contact_ramps: Dict[str, Tuple[float, float]] = {}
        self._btbt_enabled = False
        self._fe_polar_axis = 0
        self._fe_node_mask = None
        self._fe_nls_tau0 = 1.0e-6
        self._fe_nls_E0 = 2.0e9
        self._fe_nls_dt = 1.0e-6
        self._fe_model_int = 0
        self._fe_base_ps = 0.0
        self._fe_ec = 0.0
        self._fe_escale = 0.0
        self._auto_newton_for_hetero_dos = False

        # Default arrays
        npts = mesh.npts()
        self._sim.set_permittivity(np.ones(npts, dtype=float) * 8.854187817e-12 * 11.7)
        self._sim.set_mobility(np.ones(npts, dtype=float) * 1400e-4,
                               np.ones(npts, dtype=float) * 450e-4)
        self._sim.set_doping(np.zeros(npts, dtype=float))
        self._sim.set_temperature(temperature)
        self._configuration_calls = []
        self._configuration_depth = 0
        self._configuration_state_advanced = False
        self._sim = RecordingBackend(self, self._sim)

    @property
    def elementary_charge_C(self) -> float:
        """Shared charge [C] of the loaded native solver, fixed at construction."""
        return self._elementary_charge_C

    def configuration_snapshot(self):
        """Return an owned copy of explicit setter calls, excluding solve internals."""
        return deepcopy(self._configuration_calls)

    def clone_on_mesh(self, mesh: StructuredGrid, *, include_initial_guess: bool = True,
                      fe_history=None, max_landau_energy_change_J=None):
        """Inherit configuration on another mesh; see :mod:`tcad.configuration`."""
        from tcad.configuration import clone_on_mesh
        return clone_on_mesh(self, mesh, include_initial_guess=include_initial_guess,
            fe_history=fe_history,max_landau_energy_change_J=max_landau_energy_change_J)

    def to_three_temperature(self, initial_state, *, valleys_n, valleys_p, Ec_J, Eh_J,
                             heat_capacity_J_m3_K, relaxation_time_n_s, relaxation_time_p_s,
                             relaxation_law_n=None, relaxation_law_p=None,
                             intercarrier_conductance_W_m3_K=0.,
                             pair_generation_rate_m3_s=0.,pair_generation_kinetic_n_J=0.,pair_generation_kinetic_p_J=0.,
                             charge_atol_C=2e-28, particle_atol=1e-9, energy_atol_J=1e-27):
        """Conservatively initialize an independent FD device on primal cells.

        Requires complete named terminal planes, explicit nodal three-temperature
        state and new energy-transport parameters. Native fixed coefficients/BCs
        are copied. Particle and material energies are audited before returning;
        electrostatics is reinitialized. This creates an owned device snapshot
        without changing this Simulator's state or the legacy run() method.
        """
        from tcad.solver.structured_three_temperature import migrate_structured_three_temperature
        return migrate_structured_three_temperature(self, initial_state, valleys_n=valleys_n,
            valleys_p=valleys_p, Ec_J=Ec_J, Eh_J=Eh_J, heat_capacity_J_m3_K=heat_capacity_J_m3_K,
            relaxation_time_n_s=relaxation_time_n_s, relaxation_time_p_s=relaxation_time_p_s,
            relaxation_law_n=relaxation_law_n, relaxation_law_p=relaxation_law_p,
            intercarrier_conductance_W_m3_K=intercarrier_conductance_W_m3_K,
            pair_generation_rate_m3_s=pair_generation_rate_m3_s,
            pair_generation_kinetic_n_J=pair_generation_kinetic_n_J,pair_generation_kinetic_p_J=pair_generation_kinetic_p_J,
            charge_atol_C=charge_atol_C, particle_atol=particle_atol, energy_atol_J=energy_atol_J)

    def run_three_temperature(self, initial_state, output_times_s, *,
                              valleys_n, valleys_p, Ec_J, Eh_J, heat_capacity_J_m3_K,
                              relaxation_time_n_s, relaxation_time_p_s,
                              initial_step_s, maximum_step_s, minimum_step_s,
                              temperature_atol_K, temperature_rtol, density_atol_m3, density_rtol,
                              charge_atol_C, particle_atol, energy_atol_J,
                              cumulative_energy_atol_J=None, cumulative_particle_atol=None,
                              cumulative_charge_atol_C=None,
                              relaxation_law_n=None, relaxation_law_p=None,
                              intercarrier_conductance_W_m3_K=0.,
                              pair_generation_rate_m3_s=0.,pair_generation_kinetic_n_J=0.,pair_generation_kinetic_p_J=0.,
                              max_intervals=10000, max_retries=12, max_nfev=600):
        """Migrate nodal three-temperature data and run an audited trajectory.

        Returns exact-time primal-cell ``output_states``, all adaptive trial
        reports, the conservative ``migration_report`` and an owned ``device``
        that can continue the trajectory. Fixed material/contact configuration
        is inherited subject to to_three_temperature's restrictions. This
        Simulator retains its nodal state and results; cell fields are returned
        explicitly rather than assigned to its differently sized nodal arrays.
        Optional cumulative_energy_atol_J, cumulative_particle_atol and
        cumulative_charge_atol_C set separate final whole-path budgets;
        it does not change migration/per-substep budgets or request refinement.
        None retains the sum of accepted substep budgets.
        """
        from .solver.adaptive_three_temperature import _scalar
        cumulative = (None if cumulative_energy_atol_J is None else
                      _scalar(cumulative_energy_atol_J, 'cumulative energy budget'))
        cumulative_particle = (None if cumulative_particle_atol is None else
                               _scalar(cumulative_particle_atol, 'cumulative particle budget'))
        cumulative_charge = (None if cumulative_charge_atol_C is None else
                             _scalar(cumulative_charge_atol_C, 'cumulative charge budget'))
        device = self.to_three_temperature(initial_state, valleys_n=valleys_n, valleys_p=valleys_p,
            Ec_J=Ec_J, Eh_J=Eh_J, heat_capacity_J_m3_K=heat_capacity_J_m3_K,
            relaxation_time_n_s=relaxation_time_n_s, relaxation_time_p_s=relaxation_time_p_s,
            relaxation_law_n=relaxation_law_n, relaxation_law_p=relaxation_law_p,
            intercarrier_conductance_W_m3_K=intercarrier_conductance_W_m3_K,
            pair_generation_rate_m3_s=pair_generation_rate_m3_s,
            pair_generation_kinetic_n_J=pair_generation_kinetic_n_J,pair_generation_kinetic_p_J=pair_generation_kinetic_p_J,
            charge_atol_C=charge_atol_C, particle_atol=particle_atol, energy_atol_J=energy_atol_J)
        result = device.run_transient(output_times_s, initial_step_s=initial_step_s,
            maximum_step_s=maximum_step_s, minimum_step_s=minimum_step_s,
            temperature_atol_K=temperature_atol_K, temperature_rtol=temperature_rtol,
            density_atol_m3=density_atol_m3, density_rtol=density_rtol,
            charge_atol_C=charge_atol_C, particle_atol=particle_atol, energy_atol_J=energy_atol_J,
            cumulative_energy_atol_J=cumulative,
            cumulative_particle_atol=cumulative_particle,
            cumulative_charge_atol_C=cumulative_charge,
            max_intervals=max_intervals, max_retries=max_retries, max_nfev=max_nfev)
        result.update(device=device, migration_report=device.migration_report,
                      Simulator_three_temperature_entry_integrated=True,
                      legacy_StructuredGrid_three_temperature_integrated=True)
        return result

    def fe_history_transfer_report(self):
        """Owned conservation/remesh-energy report, or None before migration."""
        return deepcopy(getattr(self,'_fe_history_transfer_report',None))

    def audit_material_energy(self, history, permittivity_F_m=None, *, zero_d_faces='', **options):
        """Audit restricted carrier-free coupled LK energy on this mesh.

        Supply the actual native nodal epsilon and explicit absence-of-charge,
        boundary coverage and fixed energy/field/charge budgets. See
        :func:`tcad.postprocess.material_energy.audit_material_device_energy`.
        """
        from tcad.postprocess.material_energy import audit_material_device_energy
        if permittivity_F_m is None:
            permittivity_F_m=self._sim.get_permittivity()
        return audit_material_device_energy(history,self.mesh.axis_coordinates(),
            (self.mesh.dx,self.mesh.dy,self.mesh.dz),permittivity_F_m,
            zero_d_faces=zero_d_faces,**options)

    def set_transient_start_time(self, time_s: float = 0.) -> None:
        """Set absolute initial time for an explicitly restored transient state."""
        self._sim.set_transient_start_time(time_s)

    def set_material_from_mesh(self):
        """Populate permittivity and mobility from mesh fields."""
        if "epsilon" in self.mesh.fields:
            self._sim.set_permittivity(self.mesh.fields["epsilon"].astype(float))
        if "mu_n" in self.mesh.fields:
            self._sim.set_mobility(
                self.mesh.fields["mu_n"].astype(float),
                self.mesh.fields["mu_p"].astype(float),
            )
        if "doping" in self.mesh.fields:
            # Convert from cm^-3 to m^-3
            doping = self.mesh.fields["doping"].astype(float) * 1e6
            self._sim.set_doping(doping)
        if "Nc" in self.mesh.fields and "Nv" in self.mesh.fields:
            # Convert DOS from cm^-3 to m^-3
            Nc = self.mesh.fields["Nc"].astype(float)
            Nv = self.mesh.fields["Nv"].astype(float)
            self._sim.set_effective_dos(
                Nc * 1e6,
                Nv * 1e6,
            )
            finite_dos = np.concatenate([
                Nc[np.isfinite(Nc) & (Nc > 0.0)],
                Nv[np.isfinite(Nv) & (Nv > 0.0)],
            ])
            if finite_dos.size:
                dos_min = float(finite_dos.min())
                dos_max = float(finite_dos.max())
                if dos_min < 1.0e18 or dos_max / max(dos_min, 1.0) > 20.0:
                    self._auto_newton_for_hetero_dos = True
        if "Eg" in self.mesh.fields:
            Eg = self.mesh.fields["Eg"].astype(float)
            self._sim.set_bandgap(Eg)
        if "charge_volume_fraction" in self.mesh.fields:
            self.set_charge_volume_fraction(
                self.mesh.fields["charge_volume_fraction"]
            )

    def set_charge_volume_fraction(self, fraction) -> None:
        """Set charged-material occupancy of node-centred control volumes.

        Values are dimensionless in ``[0, 1]``. The default is one. Use a
        fractional value only for an explicitly constructed cut cell whose
        control volume straddles a semiconductor/dielectric interface; it
        scales mobile and dopant charge in Poisson without changing transport
            density or mobility. Fractional occupancy therefore disables the
            native transient mobile-charge ledger until cut-cell transport has
            matching storage and face geometry. Optical/SRH pair sources cancel
            in net mobile charge. Neutral empty paired-zero-mobility regions
            are allowed only on the validated material-side 1-D LK path; legacy
            mixed-material geometries do not expose this full-volume ledger.
        """
        values = np.ascontiguousarray(fraction, dtype=float).ravel()
        if values.size != self.mesh.npts():
            raise ValueError(
                f"charge volume fraction has {values.size} values; "
                f"expected {self.mesh.npts()}"
            )
        if not np.all(np.isfinite(values)):
            raise ValueError("charge volume fraction must be finite")
        self._sim.set_charge_volume_fraction(values)

    def set_disordered_transport(self, enabled: bool = True,
                                 reference_temperature: float = 300.0) -> None:
        """Apply exponential-tail DOS and percolation mobility metadata.

        This opt-in model is intended for amorphous oxide semiconductors such
        as a-IGZO. The integrated tail DOS ``g_tail*E_U`` augments ``Nc`` and
        the mobility follows an Arrhenius percolation law normalized to the
        material's stated value at ``reference_temperature``. Nodes without
        disorder metadata are unchanged.
        """
        required = ("mu_n", "mu_p", "Nc", "Nv", "tail_DOS",
                    "urbach_energy", "percolation_energy")
        missing = [name for name in required if name not in self.mesh.fields]
        if missing:
            raise RuntimeError(f"mesh lacks disordered-transport fields: {missing}")
        if not np.isfinite(reference_temperature) or reference_temperature <= 0.0:
            raise ValueError("reference_temperature must be finite and > 0")
        mu_n = self.mesh.fields["mu_n"].astype(float).ravel().copy()
        mu_p = self.mesh.fields["mu_p"].astype(float).ravel().copy()
        Nc = self.mesh.fields["Nc"].astype(float).ravel().copy()
        Nv = self.mesh.fields["Nv"].astype(float).ravel().copy()
        if enabled:
            tail = self.mesh.fields["tail_DOS"].astype(float).ravel()
            eu = self.mesh.fields["urbach_energy"].astype(float).ravel()
            ea = self.mesh.fields["percolation_energy"].astype(float).ravel()
            disordered = (tail > 0.0) & (eu > 0.0)
            Nc[disordered] += tail[disordered] * eu[disordered]
            exponent = -ea / 8.617333262e-5 * (
                1.0 / self.temperature - 1.0 / reference_temperature
            )
            mu_n[disordered] *= np.exp(np.clip(exponent[disordered], -50.0, 50.0))
        self._sim.set_mobility(mu_n, mu_p)
        self._sim.set_effective_dos(Nc * 1e6, Nv * 1e6)

    def create_pbti_trap_model(self, field_acceleration: float = 0.0):
        """Create a stateful :class:`TrapKinetics` from mesh PBTI metadata."""
        from tcad.physics.reliability import TrapKinetics

        required = ("pbti_Nt", "pbti_Et", "pbti_capture_tau", "pbti_emission_tau")
        missing = [name for name in required if name not in self.mesh.fields]
        if missing:
            raise RuntimeError(f"mesh lacks PBTI fields: {missing}")
        nt = self.mesh.fields["pbti_Nt"].astype(float).ravel()
        mask = nt > 0.0
        if not np.any(mask):
            raise RuntimeError("mesh contains no material with pbti_Nt > 0")
        return TrapKinetics(
            density=float(np.median(nt[mask])) * 1e6,
            trap_energy=float(np.median(self.mesh.fields["pbti_Et"].ravel()[mask])),
            capture_tau=float(np.median(self.mesh.fields["pbti_capture_tau"].ravel()[mask])),
            emission_tau=float(np.median(self.mesh.fields["pbti_emission_tau"].ravel()[mask])),
            field_acceleration=float(field_acceleration),
            mask=mask,
        )

    def set_contact(self, name: str, voltage: float, workfunction: Optional[float] = None):
        """
        Apply Dirichlet BC to a named contact.
        The mesh must contain a field ``contact_<name>``.

        Supplying ``workfunction`` on a semiconductor source/drain enables an
        ideal Schottky-Mott thermionic boundary. Omitting it keeps the ohmic
        Boltzmann charge-neutral boundary, including intrinsic contacts:
        n - p = Nd - Na and n*p = ni**2. Image-force lowering, Fermi-level pinning and
        contact tunnelling require calibrated extensions and are not implied.
        Each call replaces the contact's boundary mode: ``workfunction=None``
        clears any previously supplied workfunction. Inputs and computed
        boundaries are validated before this call writes to the native solver.
        """
        for label, value in (("voltage", voltage), ("workfunction", workfunction)):
            if value is None and label == "workfunction":
                continue
            scalar = np.asarray(value)
            if (scalar.shape != () or scalar.dtype.kind not in "iuf"
                    or not np.isfinite(scalar)):
                raise ValueError(f"Contact {label} must be a finite real scalar")
        voltage = float(voltage)
        workfunction = None if workfunction is None else float(workfunction)
        field_name = f"contact_{name}"
        if field_name not in self.mesh.fields:
            raise KeyError(f"Contact '{name}' not found in mesh fields. Available: {list(self.mesh.fields.keys())}")
        # A wrap gate is represented by several disjoint contact shapes
        # (gate, gate_r, gate_l, gate_b).  Treat setting the canonical "gate"
        # voltage as setting the complete equipotential electrode; requiring
        # callers to remember every face left FinFET/GAA side gates floating.
        gate_fields = ([key for key in self.mesh.fields
                        if key == "contact_gate" or key.startswith("contact_gate_")]
                       if name == "gate" else [field_name])
        mask = np.zeros(self.mesh.npts(), dtype=bool)
        for key in gate_fields:
            values = np.asarray(self.mesh.fields[key])
            if (values.size != mask.size or values.dtype.kind not in "biuf"
                    or not np.all((values == 0) | (values == 1))):
                raise ValueError(f"Contact mask '{key}' must contain one binary value per mesh node")
            mask |= values.astype(bool).ravel()
        indices = np.nonzero(mask.ravel())[0].astype(np.int64)
        # B档修复 (Bug 4): a contact that hits zero mesh nodes (thinner than a
        # cell, or outside the region bbox) would leave phi_bc empty and the C++
        # solver would silently apply NO Dirichlet BC — the contact floats,
        # producing wrong physics with no error (the devsim-2D failure mode).
        # Fail loudly instead.
        if len(indices) == 0:
            raise ValueError(
                f"Contact '{name}' matches zero mesh nodes. The contact Box is "
                f"likely thinner than one cell or lies outside the device bbox; "
                f"refine the mesh or widen the contact region.")

        # Equilibrium carrier densities at contacts. A supplied metal
        # workfunction selects an ideal thermionic Schottky boundary on a
        # semiconductor contact; otherwise the legacy ohmic boundary is used.
        if "doping" not in self.mesh.fields:
            raise RuntimeError("Doping field required to set carrier BCs")
        if workfunction is not None and "chi" not in self.mesh.fields:
            raise RuntimeError("Electron-affinity field 'chi' is required for Schottky contacts")
        doping = self.mesh.fields["doping"].astype(float) * 1e6  # m^-3
        VT = self.VT
        # Per-node Nc, Nv, Eg for accurate contact ni
        Nc = self.mesh.fields.get("Nc", np.full_like(doping, 2.8e19, dtype=float)) * 1e6
        Nv = self.mesh.fields.get("Nv", np.full_like(doping, 1.04e19, dtype=float)) * 1e6
        Eg = self.mesh.fields.get("Eg", np.full_like(doping, 1.12, dtype=float))
        n_bc = {}
        p_bc = {}
        phi_bc = {}
        # Metal/insulator contacts (mu_n == 0) only get potential BCs,
        # not carrier BCs, since carriers are not defined in those regions.
        mu_n_contact = self.mesh.fields.get("mu_n", np.ones_like(doping)).ravel()
        for idx in indices:
            idx_i = int(idx)
            # A named electrode may span semiconductor and insulating nodes.
            # Apply the existing mobility-based region policy node by node.
            is_metal = float(mu_n_contact[idx_i]) < 1e-12
            C = doping[idx_i]
            # Intrinsic concentration at this node
            ni = float(np.sqrt(Nc[idx_i] * Nv[idx_i]) * np.exp(-Eg[idx_i] / (2 * VT)))
            if workfunction is not None and not is_metal:
                # Schottky-Mott barriers (before image-force lowering or
                # tunnelling): phi_bn=Phi_m-chi, phi_bp=Eg-phi_bn. Negative
                # barriers are clamped to zero, i.e. an accumulation/ohmic
                # limit rather than an unphysical density above the DOS.
                phi_bn = max(float(workfunction) - float(self.mesh.fields["chi"].ravel()[idx_i]), 0.0)
                phi_bp = max(float(Eg[idx_i]) - phi_bn, 0.0)
                n_bc[idx_i] = float(Nc[idx_i] * np.exp(np.clip(-phi_bn / VT, -80.0, 0.0)))
                p_bc[idx_i] = float(Nv[idx_i] * np.exp(np.clip(-phi_bp / VT, -80.0, 0.0)))
                intrinsic_wf = (
                    float(self.mesh.fields["chi"].ravel()[idx_i])
                    + 0.5 * float(Eg[idx_i])
                    - 0.5 * VT * np.log(max(float(Nv[idx_i] / Nc[idx_i]), 1e-300))
                )
                phi_eq = intrinsic_wf - float(workfunction)
            elif is_metal:
                # Preserve the existing potential-only metal/insulator offset.
                phi_eq = (float(VT * np.log(max(C, ni) / ni)) if C > 0 else
                          float(-VT * np.log(max(abs(C), ni) / ni)) if C < 0 else 0.0)
            else:
                if not np.isfinite(C) or not np.isfinite(ni) or ni <= 0.0:
                    raise ValueError("Ohmic contacts require finite doping and positive finite intrinsic density")
                half_doping = 0.5 * abs(C)
                majority = half_doping + np.hypot(half_doping, ni)
                minority = (ni / majority) * ni
                if (not np.isfinite(majority) or not np.isfinite(minority)
                        or minority <= 0.0):
                    raise ValueError("Ohmic equilibrium carrier densities are not representable")
                # Choose the larger quadratic root and derive the smaller one
                # from mass action, avoiding subtraction of nearly equal roots.
                if C >= 0.0:
                    n_bc[idx_i], p_bc[idx_i] = float(majority), float(minority)
                else:
                    n_bc[idx_i], p_bc[idx_i] = float(minority), float(majority)
                # asinh retains the small built-in offset near intrinsic; the
                # logarithmic form avoids overflowing a large doping/ni ratio.
                offset = (np.arcsinh(half_doping / ni) if half_doping <= ni else
                          np.log(majority) - np.log(ni))
                phi_eq = float(np.copysign(VT * offset, C))
            # Applied voltage shifts equilibrium potential
            phi_bc[idx_i] = float(voltage + phi_eq)
        if (not all(np.isfinite(value) for value in phi_bc.values())
                or not all(np.isfinite(value) and value > 0.0
                           for value in (*n_bc.values(), *p_bc.values()))):
            raise ValueError("Contact boundary values must be finite; carrier densities must be positive")
        self._sim.set_dirichlet_potential(phi_bc)
        if n_bc:
            self._sim.set_electron_bc(n_bc)
            self._sim.set_hole_bc(p_bc)
        self._contact_voltages[name] = float(voltage)
        if workfunction is not None:
            self._contact_workfunctions[name] = float(workfunction)
        else:
            self._contact_workfunctions.pop(name, None)

    def set_quantum(self, enabled: bool = True):
        """Enable/disable density-gradient quantum correction."""
        self._sim.set_quantum_enabled(enabled)

    def set_density_gradient_coefficients(self, bn: float, bp: float):
        """Set density-gradient coefficients ``b_n``/``b_p`` in V*m^2.

        This supports reproducible Sentaurus calibration and material-specific
        effective masses without rebuilding TCADCraft.  Both values must be
        finite and strictly positive.
        """
        if not np.isfinite(bn) or not np.isfinite(bp) or bn <= 0.0 or bp <= 0.0:
            raise ValueError("density-gradient coefficients must be finite and positive")
        self._sim.set_density_gradient_coefficients(float(bn), float(bp))

    def set_density_gradient_effective_masses(
        self,
        electron_dos_mass: float,
        hole_dos_mass: float,
        electron_gamma: float = 1.0,
        hole_gamma: float = 1.0,
    ) -> Tuple[float, float]:
        """Configure DG from DOS masses and dimensionless fit factors.

        Masses are relative to the free-electron mass.  The conversion is
        ``b = gamma*hbar**2/(6*q*m_DOS)`` in V*m^2, matching the density form
        of the Sentaurus quantum-potential equation for constant temperature
        and Boltzmann statistics.  Returning the resolved coefficients makes
        calibration metadata independent of hidden library defaults.
        """
        values = (
            electron_dos_mass,
            hole_dos_mass,
            electron_gamma,
            hole_gamma,
        )
        if any(not np.isfinite(value) or value <= 0.0 for value in values):
            raise ValueError(
                "density-gradient DOS masses and gamma factors must be "
                "finite and positive"
            )
        hbar = 1.054571817e-34
        elementary_charge = 1.602176634e-19
        electron_mass = 9.1093837015e-31
        prefactor = hbar * hbar / (
            6.0 * elementary_charge * electron_mass
        )
        bn = prefactor * float(electron_gamma) / float(electron_dos_mass)
        bp = prefactor * float(hole_gamma) / float(hole_dos_mass)
        self.set_density_gradient_coefficients(bn, bp)
        return bn, bp

    def set_density_gradient_silicon_multivalley(
        self,
        enabled: bool = True,
        longitudinal_mass: float = 0.916,
        transverse_mass: float = 0.190,
        subbands: int = 4,
    ):
        """Enable the Si ``<100>`` Delta-valley/multi-subband DG closure.

        Masses are relative to the free-electron mass. Two valleys use the
        longitudinal confinement mass and four use the transverse mass; their
        2-D density of states and thermal subband occupations determine the
        local electron DG coefficient. The model is opt-in so non-Si material
        calibrations retain the scalar ``b_n`` behavior.
        """
        if (
            not np.isfinite(longitudinal_mass)
            or not np.isfinite(transverse_mass)
            or longitudinal_mass <= 0.0
            or transverse_mass <= 0.0
        ):
            raise ValueError("silicon DG effective masses must be finite and positive")
        if isinstance(subbands, bool) or int(subbands) != subbands:
            raise ValueError("silicon DG subbands must be an integer")
        if not 1 <= int(subbands) <= 32:
            raise ValueError("silicon DG subbands must be in [1,32]")
        self._sim.set_density_gradient_silicon_multivalley(
            bool(enabled), float(longitudinal_mass), float(transverse_mass),
            int(subbands)
        )

    def set_density_gradient_interface_distance_factor(self, factor: float):
        """Set the interface-boundary calibration factor.

        The factor scales only the distance from a semiconductor interface
        node to an inactive neighboring node in the DG boundary stencil. It
        is global for a simulation and must be calibrated to a fixed material
        interface/reference boundary model; it is never changed implicitly by
        film thickness or node count. ``1`` uses the literal mesh distance.
        """
        if not np.isfinite(factor) or factor <= 0.0:
            raise ValueError(
                "density-gradient interface distance factor must be finite "
                "and positive"
            )
        self._sim.set_density_gradient_interface_distance_factor(float(factor))

    def set_density_gradient_potential_form(self, enabled: bool = True):
        """Select the opt-in Sentaurus potential-form DG fixed-point solve.

        The mode reconstructs the lagged quasi-Fermi source and solves the
        quantum-potential PDE. When the material-step boundary is enabled,
        its nonlinear closure is imposed in the same discrete system.
        """
        self._sim.set_density_gradient_potential_form(bool(enabled))

    def set_density_gradient_step_boundary(
        self,
        enabled: bool = True,
        electron_barrier_eV: float = 3.1727,
        hole_barrier_eV: float = 4.70314,
        electron_barrier_mass: float = 0.42,
        hole_barrier_mass: float = 1.0,
        electron_gamma: float = 1.0,
        hole_gamma: float = 1.0,
        electron_theta: float = 0.5,
        hole_theta: float = 0.5,
    ):
        """Enable the analytic material-step DG boundary closure.

        This is the inhomogeneous Neumann closure used by the potential-form
        density-gradient equation at a semiconductor/non-metal interface.
        Barrier energies are in eV and barrier masses are relative to ``m0``.
        In accordance with Sentaurus Device equation (250), ``gamma`` and
        ``theta`` are properties of the non-solved barrier (the ``0+`` side),
        not the semiconductor. Defaults reproduce the explicitly exported
        W-2024.09 Si/SiO2 values at 300 K; callers must supply material-specific
        values for other interfaces. The model is opt-in and never inferred
        from geometry.
        """
        values = (
            electron_barrier_eV, hole_barrier_eV,
            electron_barrier_mass, hole_barrier_mass,
            electron_gamma, hole_gamma, electron_theta, hole_theta,
        )
        if any(not np.isfinite(value) or value <= 0.0 for value in values):
            raise ValueError(
                "density-gradient step-boundary parameters must be finite "
                "and positive"
            )
        self._sim.set_density_gradient_step_boundary(
            bool(enabled), float(electron_barrier_eV), float(hole_barrier_eV),
            float(electron_barrier_mass), float(hole_barrier_mass),
            float(electron_gamma), float(hole_gamma),
            float(electron_theta), float(hole_theta),
        )

    def set_schottky_tunneling(
        self,
        name: str,
        effective_mass_ratio: float,
        area_m2: float,
        tunneling_barrier_lowering_eV: float,
        series_resistance_ohm: float = 0.0,
        ideality_factor: float = 1.0,
        richardson_multiplier: float = 1.0,
        pinning_factor: float = 1.0,
        charge_neutrality_level_eV: Optional[float] = None,
        tunneling_window_center_eV: Optional[float] = None,
        tunneling_window_width_eV: float = 0.025,
        transport_saturation_current_A: Optional[float] = None,
        tunneling_cutoff_energy_eV: Optional[float] = None,
        tunneling_decay_exponent: float = 1.0,
    ):
        """Attach a calibrated NLM-equivalent injection model to a contact.

        Call :meth:`set_contact` with a workfunction first.  The Schottky-Mott
        barrier is then derived from that workfunction and the semiconductor
        electron affinity at the contact.  Supplying ``pinning_factor`` and
        ``charge_neutrality_level_eV`` replaces the ideal barrier with a
        calibrated Fermi-level-pinned barrier while preserving the existing
        default.  The returned model evaluates thermionic-only and
        thermionic+tunnelling terminal currents without changing the
        drift--diffusion boundary state.
        """
        from tcad.physics.contact import (
            SchottkyContactModel,
            pinned_schottky_barrier_height,
        )

        if name not in self._contact_workfunctions:
            raise RuntimeError(
                f"Contact '{name}' has no workfunction; call set_contact(..., "
                "workfunction=...) before enabling Schottky tunnelling"
            )
        field = f"contact_{name}"
        mask = self.mesh.fields[field].astype(bool).ravel()
        chi = self.mesh.fields.get("chi")
        if chi is None:
            raise RuntimeError("Electron-affinity field 'chi' is required")
        barrier = pinned_schottky_barrier_height(
            self._contact_workfunctions[name],
            float(np.median(np.asarray(chi).ravel()[mask])),
            pinning_factor=pinning_factor,
            charge_neutrality_level_eV=charge_neutrality_level_eV,
        )
        model = SchottkyContactModel(
            barrier_height_eV=barrier,
            effective_mass_ratio=effective_mass_ratio,
            area_m2=area_m2,
            series_resistance_ohm=series_resistance_ohm,
            ideality_factor=ideality_factor,
            richardson_multiplier=richardson_multiplier,
            tunneling_barrier_lowering_eV=tunneling_barrier_lowering_eV,
            tunneling_window_center_eV=tunneling_window_center_eV,
            tunneling_window_width_eV=tunneling_window_width_eV,
            transport_saturation_current_A=transport_saturation_current_A,
            tunneling_cutoff_energy_eV=tunneling_cutoff_energy_eV,
            tunneling_decay_exponent=tunneling_decay_exponent,
        )
        self._schottky_contact_models[name] = model
        return model

    def set_wse2_schottky_contact(
        self,
        name: str,
        area_m2: float,
        *,
        effective_mass_ratio: float = 0.36,
        pinning_factor: float = 1.0,
        charge_neutrality_level_eV: Optional[float] = None,
        tunneling_barrier_lowering_eV: float = 0.0,
        series_resistance_ohm: float = 0.0,
        ideality_factor: float = 1.0,
        richardson_multiplier: float = 1.0,
        tunneling_window_center_eV: Optional[float] = None,
        tunneling_window_width_eV: float = 0.025,
        transport_saturation_current_A: Optional[float] = None,
        tunneling_cutoff_energy_eV: Optional[float] = None,
        tunneling_decay_exponent: float = 1.0,
    ):
        """Attach a WSe2 Schottky/NLM contact model.

        This is a convenience wrapper around :meth:`set_schottky_tunneling`
        with WSe2-oriented defaults and explicit Fermi-level pinning controls.
        It is calibrated-interface infrastructure; omitting pinning and NLM
        parameters recovers the Schottky-Mott thermionic limit.
        """
        return self.set_schottky_tunneling(
            name,
            effective_mass_ratio=effective_mass_ratio,
            area_m2=area_m2,
            tunneling_barrier_lowering_eV=tunneling_barrier_lowering_eV,
            series_resistance_ohm=series_resistance_ohm,
            ideality_factor=ideality_factor,
            richardson_multiplier=richardson_multiplier,
            pinning_factor=pinning_factor,
            charge_neutrality_level_eV=charge_neutrality_level_eV,
            tunneling_window_center_eV=tunneling_window_center_eV,
            tunneling_window_width_eV=tunneling_window_width_eV,
            transport_saturation_current_A=transport_saturation_current_A,
            tunneling_cutoff_energy_eV=tunneling_cutoff_energy_eV,
            tunneling_decay_exponent=tunneling_decay_exponent,
        )

    def schottky_contact_current(
        self, name: str, voltage_V: Optional[float] = None,
        include_tunneling: bool = True,
    ) -> float:
        """Evaluate a configured Schottky terminal current [A]."""
        if name not in self._schottky_contact_models:
            raise KeyError(f"No Schottky tunnelling model configured for '{name}'")
        if voltage_V is None:
            voltage_V = self._contact_voltages.get(name, 0.0)
        return self._schottky_contact_models[name].current(
            float(voltage_V), self.temperature, include_tunneling
        )

    def set_optical_generation(self, G_opt: np.ndarray):
        """Set optical generation rate [m^-3 s^-1] on the mesh.

        Parameters
        ----------
        G_opt : np.ndarray
            Optical generation rate at each mesh node.  Must match
            mesh.npts() in length.
        """
        if G_opt.size != self.mesh.npts():
            raise ValueError(f"G_opt size {G_opt.size} != mesh nodes {self.mesh.npts()}")
        self._sim.set_optical_generation(G_opt.astype(np.float64).ravel())

    def set_btbt_weight(self, weight: np.ndarray) -> None:
        """Set an optional per-node multiplier for solver BTBT generation.

        The default solver behavior is unchanged when this method is not used.
        Calibrated TFET/Hurkx replays can use it to restrict or weight the
        local generation volume without modifying optical generation or SRH.
        """
        weight = np.asarray(weight, dtype=np.float64).ravel()
        if weight.size != self.mesh.npts():
            raise ValueError(
                f"BTBT weight size {weight.size} != mesh nodes {self.mesh.npts()}"
            )
        if not np.all(np.isfinite(weight)):
            raise ValueError("BTBT weight values must be finite")
        if np.any(weight < 0.0):
            raise ValueError("BTBT weight values must be nonnegative")
        self._sim.set_btbt_weight(weight)

    def update_contact(self, name: str, voltage: float):
        """
        Update the voltage of an existing contact and re-apply BCs.
        The previous simulation results are kept as the initial guess
        for the next solve, enabling voltage ramping.
        """
        if self.results is None:
            raise RuntimeError("No previous results. Call set_contact() or run() first.")
        old_voltage = self._pending_contact_ramps.get(
            name, (self._accepted_contact_voltages.get(
                name, self._contact_voltages.get(name, float(voltage))), float(voltage)))[0]
        # Large bias jumps are deferred to run(), which inserts electronic
        # continuation points.  This is particularly important for FeFET,
        # GAA and tunnelling devices: a multi-volt jump can leave the previous
        # carrier state outside both the Gummel and Newton convergence basins.
        ramp_threshold = 0.1 if self._btbt_enabled else 1.0
        if abs(float(voltage) - old_voltage) > ramp_threshold:
            self._pending_contact_ramps[name] = (old_voltage, float(voltage))
        else:
            self._pending_contact_ramps.pop(name, None)
        # Re-apply contact BC with new voltage
        self.set_contact(name, voltage, self._contact_workfunctions.get(name))
        # Propagate previous solution as initial guess
        if self._accepted_initial_guess is not None:
            self._sim.set_initial_guess(*self._accepted_initial_guess)
        elif self.results.get("converged", False):
            self._sim.set_initial_guess(
                self.results["phi"].astype(np.float64),
                self.results["n"].astype(np.float64),
                self.results["p"].astype(np.float64))

    def set_solver_type(
        self,
        poisson_solver: SolverType = SolverType.DENSE_DIRECT,
        continuity_solver: SolverType = SolverType.DENSE_DIRECT,
    ):
        """Configure linear solver backend for Poisson and continuity equations.

        For large 3D problems (>5k nodes) use ``SolverType.PETSC`` to leverage
        PETSc + HYPRE BoomerAMG preconditioning.
        """
        poisson = int(poisson_solver)
        continuity = int(continuity_solver)
        # Validate both choices before changing either native or replay state.
        self._sim.validate_linear_solver_type(poisson)
        self._sim.validate_linear_solver_type(continuity)
        self._sim.set_poisson_solver_type(poisson)
        self._sim.set_continuity_solver_type(continuity)

    def set_nonlinear_history_enabled(self, enable: bool = True):
        """Record steady stages and transient trial outer-iteration diagnostics.

        Updates, equation residuals, solver stages and same-bias retries are
        separate. Transient groups survive rejection and rollback; retrieve with
        get_transient_attempt_history(). Does not trace Python continuation.
        """
        self._sim.set_nonlinear_history_enabled(enable)

    def get_transient_attempt_history(self):
        """Owned trace of the last native transient run, including rejected trials."""
        return self._sim.get_transient_attempt_history()

    def set_use_newton(self, enable: bool = True):
        """Use Newton-Raphson full-coupled solver instead of Gummel iteration.

        Default is Gummel (``enable=False``), which is robust for most cases.
        Newton uses a hybrid strategy: Gummel first for a robust initial guess,
        then Newton for rapid quadratic convergence. Useful for high-injection
        or strongly coupled problems.

        The Newton polish is attempted even when the Gummel warm-up stalls in
        a limit cycle (issues0719 P0-3 follow-up) — a limit cycle is exactly
        the failure mode a line-searched Newton finishes.  The reported
        ``converged`` flag reflects ONLY the true residual test of the final
        state, so a failed polish is honestly reported as non-converged.
        """
        self._sim.set_use_newton(enable)

    def set_newton_log_space(self, enable: bool = True) -> None:
        """Solve the Newton carrier blocks in log-space (u=ln n, v=ln p).

        Strongly recommended together with ``set_use_newton(True)`` for
        devices driven into strong inversion/accumulation: the linear-space
        carrier variables span >20 orders of magnitude and the Newton update
        stalls, while the log-space variables keep the update well-scaled.
        Verified on the AlScN/MoS2 FeFET template: bias points that
        limit-cycle in linear space (Vg >= 4 V) converge in ~200 iterations
        in log-space under the honest per-block residual test (issues0719
        P0-3).  Also enables log-space update damping.
        """
        self._sim.set_newton_use_log_space(enable)
        self._sim.set_newton_use_log_damping(enable)

    def set_newton_log_density_update(self, mode: str) -> None:
        """Select the per-instance log-space carrier update.

        ``exponential`` (default) applies u += alpha*du. ``additive`` applies
        u += log1p(alpha*du), equivalent to n *= (1+alpha*du); nonpositive
        trial factors are rejected before residual assembly. Both use the
        same log-Jacobian. This changes the nonlinear iteration path, not the
        physical equations or convergence gates. Only affects log-space
        Newton carriers; does not enable Newton/log-space or alter Gummel.
        The option is included in configuration replay and clone_on_mesh.
        """
        self._sim.set_newton_log_density_update(mode)

    def get_newton_log_density_update(self) -> str:
        """Return this instance's explicit log-density update policy."""
        return self._sim.get_newton_log_density_update()

    def set_freeze_phi(self, enable: bool = True):
        """Freeze the Poisson block (phi) during the Newton solve (C档).

        Pins phi to its current value so the Newton system reduces to a 2-block
        (n, p) continuity solve. With phi held flat (set via ``set_initial_guess``
        or a uniform Dirichlet bias) this kills the drift term, reducing the
        Scharfetter-Gummel scheme to pure central-difference diffusion — the
        basis for an isolated continuity-equation MMS (manufactured solution)
        grid-convergence test. Newton-only; the Gummel path is unaffected.
        Classical transient mode also honors this explicit approximation;
        its default solves Poisson and both carriers. FE transient mode
        rejects a frozen-potential request.
        """
        self._sim.set_newton_freeze_phi(enable)

    def set_freeze_n(self, enable: bool = True):
        """Freeze the electron block (n) during the Newton solve (C档)."""
        self._sim.set_newton_freeze_n(enable)

    def set_freeze_p(self, enable: bool = True):
        """Freeze the hole block (p) during the Newton solve (C档)."""
        self._sim.set_newton_freeze_p(enable)

    def set_newton_options(
        self,
        damping: float = 1.0,
        min_damping: float = 0.01,
        use_line_search: bool = True,
        line_search_max: int = 10,
        use_log_damping: bool = False,
        use_log_space: bool = False,
        jacobian_reuse_threshold: float = 0.0,
    ):
        """Configure Newton-Raphson solver behavior.

        Parameters
        ----------
        damping : float
            Initial step size factor (default 1.0 = full Newton step).
        min_damping : float
            Minimum accepted step size during line search.
        use_line_search : bool
            Enable backtracking line search to ensure residual reduction.
        line_search_max : int
            Maximum line search trials per iteration.
        use_log_damping : bool
            Use exponential update for carrier densities: ``n_new = n * exp(alpha*dn/n)``.
            Guarantees positivity without clamping.
        use_log_space : bool
            Solve the carrier blocks in log-space: the Newton state carries
            ``u = log(n)``, ``v = log(p)`` instead of ``n``, ``p``.  This keeps
            the Jacobian conditioning bounded across the ~1e47 carrier dynamic
            range (depletion -> inversion in cryo/FE devices).  The physics is
            identical — residuals are evaluated on the linearised densities
            ``n = exp(u)`` — but Newton updates are additive in log-space,
            giving automatic positivity and O(1) Jacobian diagonals.  When
            enabled, ``use_log_damping`` is ignored (log-space already does
            multiplicative updates).  See audit §18.
        jacobian_reuse_threshold : float
            Reuse Jacobian from previous iteration if residual dropped by more
            than this factor (0.0 = disabled). Typical value: 5.0–10.0.
        """
        self._sim.set_newton_damping(damping)
        self._sim.set_newton_min_damping(min_damping)
        self._sim.set_newton_use_line_search(use_line_search)
        self._sim.set_newton_line_search_max(line_search_max)
        self._sim.set_newton_use_log_damping(use_log_damping)
        self._sim.set_newton_use_log_space(use_log_space)
        self._sim.set_newton_jacobian_reuse_threshold(jacobian_reuse_threshold)

    def set_thermal_coupling(self, enable: bool = True,
                             thermal_conductivity: Optional[np.ndarray] = None,
                             ambient_temperature: float = 300.0):
        """Enable self-heating (thermal coupling) simulation.

        Parameters
        ----------
        enable : bool
            Turn thermal coupling on/off.
        thermal_conductivity : np.ndarray, optional
            Thermal conductivity [W/(m·K)] per grid point. Defaults to Silicon (~150).
        ambient_temperature : float
            Ambient temperature [K]. Used as initial guess and default boundary value.
        """
        self._sim.set_thermal_coupling_enabled(enable)
        self._sim.set_ambient_temperature(ambient_temperature)
        if thermal_conductivity is not None:
            self._sim.set_thermal_conductivity(thermal_conductivity.astype(float))

    def set_thermal_dirichlet(self, bc: Dict[int, float]):
        """Set explicit thermal Dirichlet boundary conditions.

        If not called, contact nodes are automatically anchored to
        ambient_temperature. Use this to override specific nodes.

        Parameters
        ----------
        bc : dict
            Mapping node_index -> temperature [K].
        """
        self._sim.set_thermal_dirichlet(bc)

    def set_lattice_mobility_feedback(self, enable: bool = True, *, max_iter: int = 100,
                                      temperature_tol_K: float = 1e-7, relaxation: float = 0.5):
        """Iterate native DD and lattice heat with local mobility feedback.

        Carrier thermal voltage, statistics, band parameters and contact
        densities stay at their reference values. This is a mobility-only
        feedback approximation. Requires thermal coupling; FE, quantum,
        traps, leakage, high-field and generation extensions are rejected.
        The default remains the existing one-way steady heat solve.
        """
        self._sim.set_lattice_mobility_feedback(enable, max_iter, temperature_tol_K, relaxation)

    def run_lattice_step(self, previous_temperature_K, heat_capacity_J_m3_K, dt_s: float):
        """Advance lattice heat by backward Euler at the configured fixed bias.

        The electrical subsystem is quasistatic DD, rather than a transient
        carrier continuity or carrier-energy solve. Pass the last accepted
        temperature explicitly; failed steps leave the native accepted seed
        and this object's results intact. Returns the raw native result.
        Resolve pending contact ramps with run() before taking heat steps.
        """
        if self._pending_contact_ramps:
            raise ValueError("resolve pending contact ramps with run() before a lattice step")
        self._configuration_depth += 1
        try:
            self._apply_cut_cell()
            result = self._sim.solve_lattice_step(previous_temperature_K, heat_capacity_J_m3_K, dt_s)
            if result['converged']:
                self.results = result
                self._accepted_initial_guess = tuple(result[k].copy() for k in ('phi', 'n', 'p'))
                self._accepted_contact_voltages = dict(self._contact_voltages)
            return result
        finally:
            self._configuration_depth -= 1

    def set_btbt(self, enabled: bool = True,
                 A_kane: float = 3.1e21,
                 B_kane: float = 2.0e9,
                 D: float = 2.0,
                 field_mode: str | int = "magnitude",
                 field_cap: float = 0.0,
                 field_alpha: float = 0.0,
                 field_ref: float = 1.0e8,
                 continuity_scale: float = 1.0,
                 use_nonlocal: bool = False,
                 tunnel_path_fraction: float = 0.5,
                 wkb_npts: int = 64) -> None:
        """Enable band-to-band tunneling.

        Parameters
        ----------
        enabled : bool
            Turn BTBT on/off.
        A_kane : float
            Kane A coefficient [cm^-3 s^-1 V^-D]. Default for Si: 3.1e21.
        B_kane : float
            Kane B coefficient [V/m]. Default for Si: 2.0e9.
            Phase 3.4 (audit §12.4): the field |E| passed to the model is in
            V/m (phi in volts, dx in metres), so B_kane must be in V/m to
            match.  The previous default 2.0e7 was the V/cm-convention value
            misused as V/m (gave exp(-B/E)~1, i.e. no barrier).  2.0e9 V/m is
            the SI-equivalent of the published 2.0e7 V/cm Si value.
        D : float
            Exponent: 2 for direct, 2.5 for indirect tunneling.  This is
            passed as a real-valued exponent; older builds truncated 2.5 to 2,
            which made Sentaurus-style indirect-BTBT calibration impossible.
        field_mode : {"magnitude", "x", "y", "z"} or int
            Local-field selector.  ``"magnitude"`` uses ``|grad(phi)|`` and is
            the backward-compatible default.  Component modes use ``|Ex|``,
            ``|Ey|`` or ``|Ez|`` and are useful for junction/path-field
            calibration against Sentaurus local-Hurkx TFET references.
        field_cap : float
            Optional local-field cap [V/m].  Values <=0 disable the cap.  This
            is a calibrated compatibility control for Sentaurus local-Hurkx
            TFET replay on sharp junction grids.
        field_alpha : float
            Optional local-field shape exponent.  ``E_eff =
            E*(E/field_ref)**field_alpha`` before evaluating Kane.  Zero
            preserves the original model.
        field_ref : float
            Reference field [V/m] for ``field_alpha``.  Must be positive.
        continuity_scale : float
            Multiplier for the BTBT source inserted into the carrier
            continuity equations.  The reported ``G_btbt`` array is not scaled.
            Default 1.0 preserves legacy behavior.
        use_nonlocal : bool
            Use non-local (path-integral WKB) tunneling model. Computes
            tunneling probability by integrating along the source-channel
            tunneling path, avoiding the overestimation of the local Kane
            model at sharp p+/n+ junctions. Recommended for TFET simulation.
        tunnel_path_fraction : float
            Non-local path cap as a fraction of the x-domain span. Set <=0 to
            disable this cap and use only the physical/barrier boundary caps.
        wkb_npts : int
            Number of WKB Simpson segments. Odd values are rounded up inside
            the C++ solver; values below 2 are rejected.
        """
        if not np.isfinite(tunnel_path_fraction):
            raise ValueError("tunnel_path_fraction must be finite")
        if int(wkb_npts) < 2:
            raise ValueError("wkb_npts must be >= 2")
        if isinstance(field_mode, str):
            field_mode_key = field_mode.strip().lower()
            field_mode_map = {
                "magnitude": 0,
                "mag": 0,
                "norm": 0,
                "x": 1,
                "ex": 1,
                "y": 2,
                "ey": 2,
                "z": 3,
                "ez": 3,
            }
            if field_mode_key not in field_mode_map:
                raise ValueError("field_mode must be one of magnitude, x, y, z")
            field_mode_value = field_mode_map[field_mode_key]
        else:
            field_mode_value = int(field_mode)
            if field_mode_value < 0 or field_mode_value > 3:
                raise ValueError("field_mode integer must be in [0, 3]")
        if not np.isfinite(field_cap):
            raise ValueError("field_cap must be finite")
        if not np.isfinite(field_alpha):
            raise ValueError("field_alpha must be finite")
        if not np.isfinite(field_ref) or field_ref <= 0.0:
            raise ValueError("field_ref must be finite and positive")
        if not np.isfinite(continuity_scale) or continuity_scale < 0.0:
            raise ValueError("continuity_scale must be finite and non-negative")
        self._sim.set_btbt_enabled(enabled)
        if not np.isfinite(D) or D <= 0.0:
            raise ValueError("D must be finite and positive")
        self._sim.set_btbt_params(A_kane, B_kane, float(D))
        if hasattr(self._sim, "set_btbt_field_shape"):
            self._sim.set_btbt_field_shape(
                field_mode_value, float(field_cap), float(field_alpha), float(field_ref),
            )
        elif hasattr(self._sim, "set_btbt_field_options"):
            self._sim.set_btbt_field_options(field_mode_value, float(field_cap))
        else:
            self._sim.set_btbt_field_mode(field_mode_value)
        if hasattr(self._sim, "set_btbt_continuity_scale"):
            self._sim.set_btbt_continuity_scale(float(continuity_scale))
        self._sim.set_btbt_use_nonlocal(use_nonlocal)
        self._sim.set_btbt_nonlocal_params(
            float(tunnel_path_fraction), int(wkb_npts),
        )
        self._btbt_enabled = bool(enabled)

    def set_impact_ionization(self, enabled: bool = True,
                              A_n: float = 7.03e7,
                              B_n: float = 1.231e8,
                              A_p: float = 1.58e8,
                              B_p: float = 2.036e8,
                              from_mesh: bool = False) -> None:
        """Enable avalanche impact ionization (Chynoweth model).

        Adds an electron-hole-pair generation source to both continuity
        equations:

            G_ii = (alpha_n(E)*|Jn| + alpha_p(E)*|Jp|) / q    [m^-3 s^-1]

        where the Chynoweth ionization coefficient is

            alpha(E) = A * exp(-B / |E|)            [1/m]

        and ``|E|`` is the edge-aligned electric field [V/m], and ``Jn``, ``Jp``
        are the Scharfetter-Gummel edge current densities [A/m^2]. This drives
        avalanche breakdown in reverse-biased junctions, MOSFET drain-substrate
        breakdown, BJT snapback, and ESD clamps.

        Parameters
        ----------
        enabled : bool
            Turn impact ionization on/off.
        A_n, B_n : float
            Electron ionization coefficients (alpha_n = A_n*exp(-B_n/|E|)).
            Units: ``A_n`` [1/m], ``B_n`` [V/m]. Defaults are silicon
            (Chynoweth 1959 / Overstraeten-De Man 1970), pre-converted from the
            literature 1/cm & V/cm values (A_n=7.03e5 /cm, B_n=1.231e6 V/cm).
        A_p, B_p : float
            Hole ionization coefficients. Defaults are silicon
            (A_p=1.58e6 /cm, B_p=2.036e6 V/cm) pre-converted to SI.
        from_mesh : bool
            If True, read the four coefficients from the per-node ``ii_*`` mesh
            fields (populated by ``Material.ii_A_n`` etc., e.g. ``silicon()``),
            taking the median over semiconductor (mu_n>0) nodes. This makes the
            material library the single source of truth. Defaults to False
            (explicit args override).

        Notes
        -----
        Coefficients must be finite and nonnegative, including mesh values
        at semiconductor nodes. Rejected configuration leaves the model and
        its enable flag unchanged. Coefficients use SI units. To use
        literature values quoted in ``1/cm`` and ``V/cm``, multiply ``A`` by
        ``1e2`` and ``B`` by ``1e2`` before passing. For materials other than
        Si, supply the appropriate Chynoweth coefficients — they are strongly
        material- and temperature-dependent.
        """
        enabled = bool(enabled)
        if from_mesh and "ii_A_n" in self.mesh.fields:
            ii_A_n = self.mesh.fields["ii_A_n"].ravel()
            ii_B_n = self.mesh.fields["ii_B_n"].ravel()
            ii_A_p = self.mesh.fields["ii_A_p"].ravel()
            ii_B_p = self.mesh.fields["ii_B_p"].ravel()
            # Semiconductor nodes: mu_n > 0 (where II is physically active).
            if "mu_n" in self.mesh.fields:
                mu_n = self.mesh.fields["mu_n"].ravel()
                semi = mu_n > 0
            else:
                semi = np.ones(ii_A_n.shape, dtype=bool)
            if semi.size != self.mesh.npts():
                raise ValueError("impact ionization mobility mask must match mesh nodes")
            for values in (ii_A_n, ii_B_n, ii_A_p, ii_B_p):
                if values.size != semi.size:
                    raise ValueError("impact ionization fields must match mesh nodes")
                selected = values[semi]
                if not np.all(np.isfinite(selected)) or np.any(selected < 0):
                    raise ValueError(
                        "impact ionization coefficients must be finite and nonnegative"
                    )
            # Use median over semiconductor nodes (a single global coefficient
            # set; median is robust to oxide zeros).
            if semi.any() and ii_A_n[semi].max() > 0:
                A_n = float(np.median(ii_A_n[semi]))
                B_n = float(np.median(ii_B_n[semi]))
                A_p = float(np.median(ii_A_p[semi]))
                B_p = float(np.median(ii_B_p[semi]))
        self._sim.set_ii_params(A_n, B_n, A_p, B_p)
        self._sim.set_ii_enabled(enabled)

    def set_ii_reference_density(self, n0: float, p0: float) -> None:
        """Set II quasi-Fermi reference densities [m^-3], default zero.

        These modify the II driving force only; SG carrier factors and
        HFS reference densities remain independent. ElectricField ignores them.
        """
        self._sim.set_ii_reference_density(n0,p0)

    def get_ii_reference_density(self):
        return self._sim.get_ii_reference_density()

    def set_ii_driving(self, driving: int) -> None:
        """Select 0 ElectricField (default) or 1 GradQuasiFermi for II alpha.

        GradQuasiFermi requires homogeneous 1D classical isothermal Boltzmann
        transport with constant mobility; it applies on all carrier edges.
        """
        self._sim.set_ii_driving(driving)

    def get_ii_driving(self) -> int:
        return self._sim.get_ii_driving()

    def set_ii_field_floor(self, floor: float) -> None:
        """Set the finite positive avalanche source cutoff in V/m.

        The default is 1e5. Fields below the cutoff generate no avalanche
        source; equality remains active. Applies to steady Gummel/Newton,
        returned generation and equation audits. This numerical cutoff does
        not calibrate material coefficients. Avalanche transient transport
        remains unsupported. Rejected requests preserve the configuration.
        """
        self._sim.set_ii_field_floor(floor)

    def get_ii_field_floor(self) -> float:
        """Return the configured avalanche source cutoff [V/m]."""
        return self._sim.get_ii_field_floor()

    def set_breakdown(self, enabled: bool = True,
                      sigma_bd: float = 1.0e-2) -> None:
        """Enable dielectric breakdown modelling (M7b, audit §22).

        After each converged solve, dielectric nodes whose field exceeds the
        material ``E_bd`` are flagged as broken. On subsequent solves, every
        dielectric edge touching a failed node carries the explicit current
        ``J_bd = sigma_bd * E`` in ``Jleak_x/y/z``. The breakdown is
        irreversible and does not introduce a fictitious Poisson connection
        to zero volts.

        The breakdown field ``E_bd`` is read per-node from the mesh's
        ``E_bd`` field, which ``Device.sample_on_grid`` populates from each
        ``Material.E_bd`` (e.g. ``sio2()`` -> 1.2e9 V/m, ``hfo2()`` -> 6e8
        V/m). Materials with ``E_bd == 0`` never break down.

        Parameters
        ----------
        enabled : bool
            Turn breakdown detection on/off.
        sigma_bd : float
            Post-breakdown filament conductivity [S/m]. Default 1e-2; increase
            it for a more conductive filament. The resulting current remains
            proportional to local field and participates in terminal-current
            integration and Joule heating.

        Notes
        -----
        Call ``set_material_from_mesh`` first so the ``E_bd`` mesh field is
        populated. After solving, inspect the breakdown state via
        ``sim._sim.breakdown_state()`` (an int8 array, 1 = broken down).
        """
        self._sim.set_breakdown_enabled(enabled)
        if enabled:
            import numpy as np
            if "E_bd" in self.mesh.fields:
                E_bd = self.mesh.fields["E_bd"].astype(np.float64).ravel()
                # Dielectric mask: nodes with E_bd > 0 (i.e. a dielectric
                # material that has a breakdown field defined).
                bd_mask = (E_bd > 0.0).astype(np.int8)
                self._sim.set_breakdown_params(bd_mask, E_bd, float(sigma_bd))
            else:
                # No E_bd field -> nothing to monitor; warn implicitly by no-op.
                import warnings
                warnings.warn(
                    "set_breakdown(enabled=True) but mesh has no 'E_bd' field; "
                    "call set_material_from_mesh() with materials that define E_bd.",
                    RuntimeWarning, stacklevel=2)

    _POLAR_AXIS_NAMES = {"x": 0, "y": 1, "z": 2}

    def _resolve_polar_axis(self, polar_axis, fe_mask: np.ndarray) -> int:
        """Resolve the ferroelectric polar axis (P0-1).

        ``polar_axis`` may be None (auto-detect), "x"/"y"/"z", or 0/1/2.
        Auto-detection uses a thin-film-normal heuristic: a ferroelectric
        film is polar along its normal, i.e. the axis along which the FE
        region is a SLAB bounded by other materials.  Concretely, among the
        axes with nonzero FE span we pick the one minimizing
        ``FE_span / mesh_span`` (a film fills the device in-plane but only
        a fraction through-thickness).  A degenerate quasi-2D axis (thin in
        y simply because the device is 2-D) fills the whole mesh along that
        axis and is therefore NOT mistaken for the film normal.  For a 1-D
        slab only one axis has nonzero span, so the heuristic reduces to
        that axis.  Pass an explicit axis for non-film geometries (pillars,
        multi-domain, etc.).
        """
        if polar_axis is None:
            if not np.any(fe_mask):
                return 0
            all_coords = getattr(self.mesh, "node_coords", None)
            if all_coords is None:
                return 0
            all_coords = np.asarray(all_coords, dtype=float)
            coords = all_coords[fe_mask.astype(bool)]
            if coords.ndim != 2 or coords.shape[1] < 3 or coords.shape[0] == 0:
                return 0
            spans = coords.max(axis=0) - coords.min(axis=0)
            nonzero = np.where(spans > 0.0)[0]
            if nonzero.size == 0:
                return 0
            if nonzero.size == 1:
                return int(nonzero[0])
            mesh_spans = all_coords.max(axis=0) - all_coords.min(axis=0)
            with np.errstate(divide="ignore", invalid="ignore"):
                fill = np.where(mesh_spans > 0.0,
                                spans / np.maximum(mesh_spans, 1e-300), 1.0)
            # Film normal = axis where the FE region fills the smallest
            # fraction of the device (strictly a slab).  If the FE fills the
            # device along every axis (uniform FE block) fall back to the
            # smallest absolute span.
            cand = fill[nonzero]
            if cand.min() < 1.0 - 1e-12:
                return int(nonzero[np.argmin(cand)])
            return int(nonzero[np.argmin(spans[nonzero])])
        if isinstance(polar_axis, str):
            key = polar_axis.lower()
            if key not in self._POLAR_AXIS_NAMES:
                raise ValueError(
                    f"Invalid polar_axis '{polar_axis}'; expected 'x'/'y'/'z' or 0/1/2")
            return self._POLAR_AXIS_NAMES[key]
        axis = int(polar_axis)
        if axis not in (0, 1, 2):
            raise ValueError(f"Invalid polar_axis {polar_axis}; expected 0, 1 or 2")
        return axis

    def set_ferroelectric_polar_axis(self, polar_axis="x") -> None:
        """Set the ferroelectric polar axis explicitly (P0-1).

        The scalar Preisach/NLS models drive ``E_parallel = E·axis`` and write
        ``P = P_scalar*axis``; the LK model applies the built-in field and
        depolarization drive along this axis.  A z-stacked MFIS gate stack
        therefore needs ``polar_axis="z"`` — the historical hard-coded x
        axis left the built-in FeFET template with zero polarization.
        """
        axis = self._resolve_polar_axis(polar_axis, np.zeros(0, dtype=np.int8))
        self._sim.set_ferroelectric_polar_axis(axis)
        self._fe_polar_axis = axis

    @staticmethod
    def _validate_nls_parameters(tau0, E0, dt):
        for name, value, allow_zero in (("tau0", tau0, False), ("E0", E0, True), ("dt", dt, False)):
            if (not np.isscalar(value) or isinstance(value, (bool, np.bool_))
                    or not np.isfinite(value) or value < 0 or (not allow_zero and value == 0)):
                raise ValueError(f"NLS {name} must be finite and {'>= 0' if allow_zero else '> 0'}")

    @staticmethod
    def _validate_fe_amplitudes(Ps, Ec, Escale):
        for name, value in (("Ps", Ps), ("Ec", Ec), ("Escale", Escale)):
            if (not np.isscalar(value) or isinstance(value, (bool, np.bool_))
                    or not np.isfinite(value) or value < 0):
                raise ValueError(f"FE {name} must be finite and >= 0")

    def set_ferroelectric_nls_dwell_time(self, dt: float) -> None:
        """Set the physical dwell time of one NLS bias/pulse step [s].

        The configured Merz-law ``tau0`` and ``E0`` are preserved.  This is
        used by retention and pulse-width drivers; calling the private Cython
        setter with hard-coded defaults previously changed the material model
        whenever the pulse width was swept.
        """
        self._validate_nls_parameters(self._fe_nls_tau0, self._fe_nls_E0, dt)
        self._sim.set_ferroelectric_nls(
            self._fe_nls_tau0, self._fe_nls_E0, float(dt),
        )
        self._fe_nls_dt = float(dt)

    def set_ferroelectric(self, enabled: bool = True,
                          alpha: float = -5.0e8,
                          beta: float = 1.5e10,
                          model: str = "landau_khalatnikov",
                          Ps: float = 0.2,
                          Ec: float = 1.0e9,
                          Escale: float = 0.0,
                          nls_tau0: float = 1.0e-6,
                          nls_E0: float = 2.0e9,
                          nls_dt: float = 1.0e-6,
                          polar_axis=None,
                          fe_mask_override: Optional[np.ndarray] = None,
                          extra_depolarization_eps_r: float = 0.0) -> None:
        """Enable ferroelectric polarization.

        Four models are supported (M7c + P3 + Sentaurus calibration):

        - ``"landau_khalatnikov"`` (default): the cubic L-K model
          ``alpha*P + beta*P^3 = E``. Hysteresis arises from per-component
          branch continuation. Parameters ``alpha``/``beta`` set the double-well
          shape (Ps = sqrt(-alpha/beta), Ec = (2|alpha|/3)*sqrt(-alpha/(3beta))).
        - ``"preisach"``: the classical scalar Preisach (play-operator) model,
          parameterised DIRECTLY by saturation polarization ``Ps`` [C/m^2] and
          coercive field ``Ec`` [V/m]. This sidesteps the L-K alpha/beta
          dimensional ambiguity and produces a natural memory loop.
        - ``"sentaurus_preisach"``: Sentaurus-compatible Ps/Pr/Fc branches,
          asymmetric initial loading, nested minor loops and memory wipeout.
          Set ``Escale=2*Ec/log((Ps+Pr)/(Ps-Pr))``. This compact model uses
          one domain ensemble per FE mask and retains its turning points.
        - ``"nls"``: compact Nucleation-Limited Switching relaxation with
          Merz law ``tau(E)=tau0·exp(E0/|E|)``. Volume-average effective field
          selects the sign and maximal local effective field sets the rate.
          One uniform ensemble advances per accepted clocked bias step;
          this does not resolve spatial domains or validate AlScN kinetics.

        Ferroelectric regions are identified from the mesh by the material's
        ``fe_alpha`` field (``fe_alpha != 0``), NOT by a dielectric-constant
        window. This lets low-permittivity ferroelectrics such as AlScN
        (epsilon_r ~ 15) be correctly detected — the old ``eps_r in [25,50]``
        window silently excluded them. Pass ``fe_mask_override`` to force a
        specific node mask regardless of materials. (P1.1.)

        Parameters
        ----------
        enabled : bool
            Turn ferroelectric on/off.
        alpha, beta : float
            L-K coefficients. Defaults now match the material library HfZrO
            (-5e8 / 1.5e10). When the mesh carries a ``fe_alpha`` field the
            per-node alpha/beta are read from it, overriding these scalars.
        model : str
            ``"landau_khalatnikov"``, ``"preisach"``, ``"nls"``, or
            ``"sentaurus_preisach"``.
        Ps : float
            Preisach saturation polarization [C/m^2]. When the mesh carries a
            ``fe_ps`` field with nonzero values, those are used instead.
        Ec : float
            Preisach coercive field [V/m]. Overridden by mesh ``fe_ec`` if set.
        Escale : float
            Preisach tanh output width [V/m]. Default 0 = ``Ec`` (keeps the
            play-operator loop correctly shaped with a nonzero remanence window).
            A smaller ``Escale`` (e.g. ``Ec/3``) lets |P| approach the named
            saturation Ps on a monotonic ramp, but too small collapses the loop.
        polar_axis : None, str or int
            Ferroelectric polar axis (P0-1): "x"/"y"/"z" or 0/1/2.
            Default None auto-detects the thin-film normal from the FE
            region geometry (smallest nonzero span), so a z-stacked MFIS
            template drives Pz rather than the historical hard-coded Px.
        fe_mask_override : np.ndarray, optional
            Explicit int8 node mask (1 = ferroelectric). Bypasses material
            auto-detection when provided.
        extra_depolarization_eps_r : float
            Optional additional unsimulated screening correction, using
            E_extra=-P/(eps_r*eps0). Zero disables it. Poisson already includes
            -div(P); material permittivity alone does not justify this term.
        """
        if fe_mask_override is not None:
            supplied_mask = np.asarray(fe_mask_override).ravel()
            if (supplied_mask.size != self.mesh.npts()
                    or not np.all(np.isfinite(supplied_mask))
                    or not np.all((supplied_mask == 0) | (supplied_mask == 1))):
                raise ValueError("fe_mask_override must contain one binary value per mesh node")
        model_map = {
            "landau_khalatnikov": 0,
            "preisach": 1,
            "nls": 2,
            "sentaurus_preisach": 3,
        }
        # issues0719 §5.4: fail fast on a misspelled model instead of
        # silently mapping it to Landau-Khalatnikov.
        if model.lower() not in model_map:
            raise ValueError(
                f"Unknown ferroelectric model '{model}'; "
                f"expected one of {sorted(model_map)}")
        model_int = model_map[model.lower()]
        if model_int in (1, 2, 3):
            self._validate_fe_amplitudes(Ps, Ec, Escale)
        if model_int == 2:
            self._validate_nls_parameters(nls_tau0, nls_E0, nls_dt)
        if (not np.isscalar(extra_depolarization_eps_r)
                or isinstance(extra_depolarization_eps_r, (bool, np.bool_))
                or not np.isfinite(extra_depolarization_eps_r) or extra_depolarization_eps_r < 0):
            raise ValueError("extra_depolarization_eps_r must be finite and >= 0")
        # --- Determine the FE node mask (P1.1: material-driven) ---
        npts = self.mesh.npts()
        if fe_mask_override is not None:
            fe_mask = np.asarray(fe_mask_override, dtype=np.int8).ravel()
        elif "fe_alpha" in self.mesh.fields:
            # Material-driven detection: a node is ferroelectric if its material
            # declares a nonzero Landau alpha. This supersedes the old
            # eps_r-in-[25,50] window which silently excluded AlScN (eps_r~15).
            fe_alpha_field = self.mesh.fields["fe_alpha"].ravel()
            fe_mask = (np.abs(fe_alpha_field) > 0.0).astype(np.int8)
        elif "material_id" in self.mesh.fields and "epsilon" in self.mesh.fields:
            # Legacy fallback (no fe_alpha field): eps_r window for HfZrO.
            eps = self.mesh.fields["epsilon"].ravel()
            eps0 = 8.854187817e-12
            fe_mask = ((eps > 25.0 * eps0) & (eps < 50.0 * eps0)).astype(np.int8)
        else:
            fe_mask = np.zeros(npts, dtype=np.int8)

        # --- Resolve alpha/beta (scalar default, or per-node from material) ---
        if "fe_alpha" in self.mesh.fields and np.any(fe_mask):
            alpha_field = np.asarray(self.mesh.fields["fe_alpha"]).ravel()
            beta_field = np.asarray(self.mesh.fields.get("fe_beta", ())).ravel()
            if alpha_field.size != npts or beta_field.size != npts:
                raise ValueError("fe_alpha and fe_beta must contain one value per mesh node")
            alpha_values = alpha_field[fe_mask.astype(bool)]
            beta_values = beta_field[fe_mask.astype(bool)]
            if (not np.all(np.isfinite(alpha_values))
                    or not np.all(np.isfinite(beta_values))
                    or not np.all(beta_values > 0)):
                raise ValueError("FE alpha/beta fields must be finite with beta > 0")
            alpha = float(alpha_values[0])
            beta = float(beta_values[0])
        if model_int in (1, 2, 3):
            # Resolve Preisach/NLS Ps/Ec from material field when available.
            for field_name in ("fe_ps", "fe_ec"):
                if field_name not in self.mesh.fields or not np.any(fe_mask):
                    continue
                values = np.asarray(self.mesh.fields[field_name]).ravel()
                if values.size != npts:
                    raise ValueError(f"{field_name} must contain one value per mesh node")
                values = values[fe_mask.astype(bool)]
                if not np.all(np.isfinite(values)) or np.any(values < 0):
                    raise ValueError(f"{field_name} must be finite and >= 0 in the FE region")
                if np.any(values > 0):
                    if field_name == "fe_ps":
                        Ps = float(values[values > 0][0])
                    else:
                        Ec = float(values[values > 0][0])
            self._validate_fe_amplitudes(Ps, Ec, Escale)
        axis = self._resolve_polar_axis(polar_axis, fe_mask)
        # Resolve material amplitudes and axis before changing the native model.
        self._sim.set_ferroelectric_enabled(enabled)
        self._sim.set_ferroelectric_model(model_int)
        self._fe_model_int = model_int
        if model_int in (1, 2, 3):
            self._sim.set_ferroelectric_preisach(Ps, Ec, Escale)
            self._fe_base_ps = float(Ps)
            self._fe_ec = float(Ec)
            self._fe_escale = float(Escale)
            if model_int == 2:
                # NLS Merz-law parameters (P3).
                self._sim.set_ferroelectric_nls(nls_tau0, nls_E0, nls_dt)
                self._fe_nls_tau0 = float(nls_tau0)
                self._fe_nls_E0 = float(nls_E0)
                self._fe_nls_dt = float(nls_dt)
        self._sim.set_ferroelectric_params(fe_mask, alpha, beta)
        # P0-1: wire the polar axis — scalar Preisach/NLS drive E·axis and
        # write P along axis; without this the z-stacked FeFET template was
        # driven by Ex~0 and stayed at P=0 (issues0719 P0-1).
        self._sim.set_ferroelectric_polar_axis(axis)
        self._fe_polar_axis = axis
        # Internal field / Imprint offset (P2.1): read from material field.
        if "fe_E_bi" in self.mesh.fields and np.any(fe_mask):
            ebi = self.mesh.fields["fe_E_bi"].ravel()[fe_mask.astype(bool)]
            if np.any(np.abs(ebi) > 0.0):
                self._sim.set_ferroelectric_builtin_field(float(ebi[np.abs(ebi) > 0.0][0]))
        # Poisson already includes bound polarization charge. An additional
        # screening correction is opt-in, rather than inferred from epsilon.
        self._sim.set_ferroelectric_depol(float(extra_depolarization_eps_r))
        # Readout uses the configured FE domain, including explicit overrides.
        self._fe_node_mask = (fe_mask.astype(bool).copy() if enabled
                              else np.zeros(npts, dtype=bool))

    def set_ferroelectric_model(self, model: str = "landau_khalatnikov",
                                Ps: float = 0.2, Ec: float = 1.0e9,
                                Escale: float = 0.0,
                                nls_tau0: float = 1.0e-6,
                                nls_E0: float = 2.0e9,
                                nls_dt: float = 1.0e-6) -> None:
        """Select the ferroelectric model (M7c + P3).

        Parameters
        ----------
        model : str
            ``"landau_khalatnikov"``, ``"preisach"``, ``"nls"``, or
            ``"sentaurus_preisach"``.
        Ps, Ec : float
            Saturation polarization [C/m^2] and coercive field [V/m] (used by
            the Preisach and NLS models).
        Escale : float
            Preisach tanh output width [V/m] (0 = ``Ec``; see
            ``set_ferroelectric`` for the saturation-Ps trade-off).
        nls_tau0, nls_E0 : float
            NLS Merz-law switching time ``tau(E) = tau0·exp(E0/|E|)`` [s], [V/m]
            (used only for the NLS model).
        nls_dt : float
            NLS effective dwell time per bias step [s] — controls the loop
            slope (larger => faster, more vertical switching).
        """
        model_map = {
            "landau_khalatnikov": 0,
            "preisach": 1,
            "nls": 2,
            "sentaurus_preisach": 3,
        }
        if model.lower() not in model_map:
            raise ValueError(
                f"Unknown ferroelectric model '{model}'; "
                f"expected one of {sorted(model_map)}")
        model_int = model_map[model.lower()]
        if model_int in (1, 2, 3):
            self._validate_fe_amplitudes(Ps, Ec, Escale)
        if model_int == 2:
            self._validate_nls_parameters(nls_tau0, nls_E0, nls_dt)
        self._sim.set_ferroelectric_model(model_int)
        self._fe_model_int = model_int
        if model_int in (1, 3):
            self._sim.set_ferroelectric_preisach(Ps, Ec, Escale)
        if model_int == 2:
            self._sim.set_ferroelectric_preisach(Ps, Ec, Escale)
            self._sim.set_ferroelectric_nls(nls_tau0, nls_E0, nls_dt)
            self._fe_nls_tau0 = float(nls_tau0)
            self._fe_nls_E0 = float(nls_E0)
            self._fe_nls_dt = float(nls_dt)
        if model_int in (1, 2, 3):
            self._fe_base_ps = float(Ps)
            self._fe_ec = float(Ec)
            self._fe_escale = float(Escale)

    def set_ferroelectric_active_fraction(self, fraction: float) -> None:
        """Apply wake-up/fatigue to the switchable Preisach/NLS population.

        This changes the active saturation polarization while preserving the
        solver's persistent play/NLS state. It is intentionally unavailable
        for the LK model, whose Landau coefficients require a separate
        calibrated degradation law.
        """
        if not np.isfinite(fraction) or fraction < 0.0:
            raise ValueError("active fraction must be finite and >= 0")
        if self._fe_model_int not in (1, 2, 3) or self._fe_base_ps <= 0.0:
            raise RuntimeError(
                "active-fraction degradation requires a configured Preisach/NLS model"
            )
        self._sim.set_ferroelectric_preisach(
            self._fe_base_ps * float(fraction), self._fe_ec, self._fe_escale,
        )

    def set_high_field_saturation(
        self,
        enabled: bool = True,
        vsat_n: float = 1.07e5,
        vsat_p: float = 8.37e4,
        beta_n: float = 2.0,
        beta_p: float = 1.0,
        driving: str = "grad_quasi_fermi",
    ) -> None:
        """Enable high-field velocity saturation (Caugy-Thomas).

        Per SG edge the mobility is reduced as
        ``mu(F) = mu_low / (1 + (mu_low*F/vsat)^beta)^(1/beta)`` with the
        driving force ``F`` taken from the lagged edge quasi-Fermi gradient
        (Sentaurus ``HighFieldSaturation(GradQuasiFermi)``) or the transport
        field.  Defaults are the Sentaurus Si MaterialDB saturation
        velocities.  Disabled by default (bit-preserving).

        Parameters
        ----------
        enabled : bool
            Turn the model on/off.
        vsat_n, vsat_p : float
            Saturation velocities [m/s].
        beta_n, beta_p : float
            Caugy-Thomas exponents.
        driving : {"grad_quasi_fermi", "electric_field"}
            Edge driving-force selector.
        """
        driving_map = {"grad_quasi_fermi": 0, "electric_field": 1}
        key = driving_map.get(str(driving).lower())
        if key is None:
            raise ValueError(
                "driving must be 'grad_quasi_fermi' or 'electric_field'"
            )
        self._sim.set_high_field_saturation(
            enabled, float(vsat_n), float(vsat_p),
            float(beta_n), float(beta_p), key,
        )

    def set_hfs_quasi_fermi_at_contacts(self, enabled: bool) -> None:
        """Select HFS driving on edges touching a carrier Dirichlet contact.

        True (default) preserves the configured driving everywhere. False
        uses the transport potential field on the corresponding electron or
        hole contact edges; interior edges retain the configured driving.
        """
        self._sim.set_hfs_quasi_fermi_at_contacts(enabled)

    def get_hfs_quasi_fermi_at_contacts(self) -> bool:
        """Return the HFS contact driving policy."""
        return self._sim.get_hfs_quasi_fermi_at_contacts()

    def set_high_field_reference_density(self, n0: float, p0: float) -> None:
        """Set HFS GQF reference densities in m^-3 (defaults: zero).

        Nonzero active references require a one-dimensional homogeneous,
        classical isothermal Boltzmann device with constant mobility.
        SG flux factors continue to use actual carrier densities.
        """
        self._sim.set_high_field_reference_density(n0,p0)

    def get_high_field_reference_density(self):
        """Return the electron and hole HFS reference densities [m^-3]."""
        return self._sim.get_high_field_reference_density()

    def set_hfs_low_field_cutoff(self, cutoff: float) -> None:
        """Set the numerical HFS driving-force cutoff [V/m].

        Default zero preserves continuous HFS. Below the finite nonnegative
        cutoff an edge uses low-field mobility; equality retains saturation.
        Both driving modes, assembly, returned currents and equation audits
        use the same branch. The threshold is discontinuous and has no
        Jacobian at equality. This does not fit material coefficients.
        """
        self._sim.set_hfs_low_field_cutoff(cutoff)

    def get_hfs_low_field_cutoff(self) -> float:
        """Return the configured HFS driving-force cutoff [V/m]."""
        return self._sim.get_hfs_low_field_cutoff()

    def set_ferroelectric_builtin_field(self, E_bi: float = 0.0) -> None:
        """Set the internal/imprint field offset (P2.1).

        For the Preisach ensemble (model 1) the play history tracks the
        applied field while ``E_bi`` offsets the output comparison
        (``P = Ps*tanh((E - E_bi - w)/Escale)``), so a nonzero ``E_bi``
        rigidly translates the saturated major-loop crossings by
        ``E_bi * t_FE`` (imprint/Vc audit, 2026-09-18).  Positive ``E_bi``
        biases the virgin state toward -P; an imprint stabilizing the
        polarity written by +V programming therefore uses negative
        ``E_bi``. ``E_bi = 0`` (default) restores a symmetric loop.

        Parameters
        ----------
        E_bi : float
            Internal field offset [V/m].
        """
        self._sim.set_ferroelectric_builtin_field(E_bi)

    def set_ferroelectric_depol(self, eps_fe: float = 0.0) -> None:
        """Set an explicit additional screening correction (zero disables).

        E_extra=-P/(eps_fe*eps0) is additional to the self-consistent Poisson
        field, which already includes -div(P). Use only when independently
        justified for screening absent from the simulated geometry. This
        parameter alone does not establish a thickness-dependent memory window.

        Parameters
        ----------
        eps_fe : float
            Ferroelectric layer relative permittivity.
        """
        if (not np.isscalar(eps_fe) or isinstance(eps_fe, (bool, np.bool_))
                or not np.isfinite(eps_fe) or eps_fe < 0):
            raise ValueError("extra depolarization permittivity must be finite and >= 0")
        self._sim.set_ferroelectric_depol(eps_fe)

    def set_leakage(self, enabled: bool = True,
                    pf_C: float = 0.02, pf_B: float = 5.0e5, pf_phi_t: float = 0.5,
                    fn_C: float = 0.0, fn_B: float = 0.0, fn_phi_b: float = 0.0,
                    fn_C_positive: Optional[float] = None,
                    fn_B_positive: Optional[float] = None,
                    fn_C_negative: Optional[float] = None,
                    fn_B_negative: Optional[float] = None,
                    E_floor: float = 1.0e6, sigma_cap: float = 0.05,
                    leak_mask_override: Optional[np.ndarray] = None) -> None:
        """Enable leakage current (Poole-Frenkel / Fowler-Nordheim) (P2.2).

        Leakage provides an explicit field-dependent conventional current
        across the ferroelectric/insulator stack. The returned result contains
        edge fluxes ``Jleak_x/y/z`` in A/m². Leakage is not inserted into the
        Poisson charge equation.

        The leaky nodes default to the ferroelectric nodes (auto-detected from
        the material's ``fe_alpha`` field); pass ``leak_mask_override`` to
        force a specific node mask.

        ``pf_C`` is a conductivity prefactor in S/m. ``fn_C`` is the FN
        current prefactor in A/V². ``sigma_cap`` limits the combined
        field-dependent conductivity in S/m.

        Parameters
        ----------
        enabled : bool
            Turn leakage on/off.
        pf_C, pf_B, pf_phi_t : float
            Poole-Frenkel conductivity prefactor [S/m], barrier
            coefficient, and trap ionization energy [eV].
            ``frac_pf = pf_C·exp(-pf_B·sqrt(pf_phi_t/|E|))``.
        fn_C, fn_B, fn_phi_b : float
            Symmetric Fowler-Nordheim prefactor [A/V²], exponent coefficient
            [V/m/eV^1.5], and barrier height [eV]. The current density is
            ``J_fn = fn_C·E²·exp(-fn_B·fn_phi_b^1.5/|E|)``.
        fn_C_positive, fn_B_positive, fn_C_negative, fn_B_negative : float, optional
            Signed-field FN coefficient pairs. If all four are supplied they
            override ``fn_C/fn_B`` according to the oriented edge field sign,
            matching Sentaurus Fowler write/erase parameters. Partial pairs
            are rejected.
        E_floor : float
            Field below which leakage is negligible [V/m].
        sigma_cap : float
            Cap on total dielectric conductivity [S/m].
        leak_mask_override : np.ndarray, optional
            Explicit int8 node mask (1 = leaky). Defaults to the FE mask.
        """
        if not enabled:
            self._sim.set_leakage_enabled(False)
            return
        directional = (
            fn_C_positive, fn_B_positive, fn_C_negative, fn_B_negative
        )
        if any(value is not None for value in directional) and not all(
            value is not None for value in directional
        ):
            raise ValueError(
                "all four signed-field FN coefficients must be provided"
            )
        if any(value is not None for value in directional):
            if any((not np.isfinite(value)) or value < 0.0 for value in directional):
                raise ValueError(
                    "signed-field FN coefficients must be finite and nonnegative"
                )
        npts = self.mesh.npts()
        if leak_mask_override is not None:
            mask = np.asarray(leak_mask_override, dtype=np.int8).ravel()
        elif "fe_alpha" in self.mesh.fields:
            mask = (np.abs(self.mesh.fields["fe_alpha"].ravel()) > 0.0).astype(np.int8)
        else:
            mask = np.zeros(npts, dtype=np.int8)
        self._sim.set_leakage(mask, pf_C, pf_B, pf_phi_t,
                              fn_C, fn_B, fn_phi_b, E_floor, sigma_cap)
        if any(value is not None for value in directional):
            self._sim.set_leakage_fn_polarity(*directional)

    def set_interface_traps(self, D_it: float = 0.0, E_t: float = 0.0,
                            trap_mask_override: Optional[np.ndarray] = None) -> None:
        """Enable interface traps (Dit) and bulk oxide traps (P6).

        Interface traps inject a charge ``Q_it = -q·D_it·dE·(f_t−0.5)`` into the
        Poisson RHS of interface nodes, where ``f_t`` is the trap occupancy
        determined by the local potential. This shifts the threshold voltage and
        affects memory window, retention, and endurance (comments.docx).

        The trap mask defaults to nodes where ``Dit > 0`` in the mesh fields;
        pass ``trap_mask_override`` to force a specific mask.

        Parameters
        ----------
        D_it : float
            Interface trap density [cm^-2 eV^-1]. Overridden by mesh field if
            nonzero values exist.
        E_t : float
            Trap energy level [eV] relative to intrinsic Fermi level. 0 = at
            midgap (maximally effective).
        trap_mask_override : np.ndarray, optional
            Explicit int8 node mask (1 = trap node).
        """
        npts = self.mesh.npts()
        if trap_mask_override is not None:
            mask = np.asarray(trap_mask_override, dtype=np.int8).ravel()
        elif "Dit" in self.mesh.fields:
            dit_field = self.mesh.fields["Dit"].ravel()
            mask = (np.abs(dit_field) > 0.0).astype(np.int8)
            if np.any(mask) and D_it == 0.0:
                D_it = float(dit_field[mask.astype(bool)][0])
        else:
            mask = np.zeros(npts, dtype=np.int8)
        self._sim.set_interface_traps(mask, D_it, E_t)
        # Also set bulk oxide traps if present in mesh.
        if "Q_ot" in self.mesh.fields:
            qot = self.mesh.fields["Q_ot"].ravel()
            if np.any(np.abs(qot) > 0.0):
                self._sim.set_oxide_traps(qot.astype(float))

    def set_oxide_traps(self, Q_ot) -> None:
        """Set bulk oxide/ferroelectric trap charge density [C/m^3].

        ``Q_ot`` may be a scalar (applied to dielectric nodes identified by
        ``Dit``/``fe_alpha``) or a node-sized array.  This public API lets
        endurance drivers feed accumulated fatigue charge back into Poisson
        instead of applying degradation only as a post-processing scale.
        """
        npts = self.mesh.npts()
        if np.isscalar(Q_ot):
            mask = np.zeros(npts, dtype=bool)
            if "Dit" in self.mesh.fields:
                mask |= np.abs(self.mesh.fields["Dit"].ravel()) > 0.0
            if "fe_alpha" in self.mesh.fields:
                mask |= np.abs(self.mesh.fields["fe_alpha"].ravel()) > 0.0
            # Generic dielectric fallback for new materials that do not yet
            # carry Dit/FE metadata: zero mobility plus a finite bandgap marks
            # an insulating region while excluding uncovered vacuum nodes.
            if all(k in self.mesh.fields for k in ("mu_n", "mu_p", "Eg")):
                mask |= (
                    (np.abs(self.mesh.fields["mu_n"].ravel()) < 1e-30)
                    & (np.abs(self.mesh.fields["mu_p"].ravel()) < 1e-30)
                    & (self.mesh.fields["Eg"].ravel() > 1.0)
                )
            if not np.any(mask):
                mask[:] = True
            values = np.zeros(npts, dtype=float)
            values[mask] = float(Q_ot)
        else:
            values = np.asarray(Q_ot, dtype=float).ravel()
            if values.size != npts:
                raise ValueError(
                    f"Q_ot size {values.size} does not match mesh npts={npts}"
                )
        if not np.all(np.isfinite(values)):
            raise ValueError("Q_ot must contain only finite values")
        self._sim.set_oxide_traps(values)

    def set_mobility_model(self, model: str = "constant") -> None:
        """Set mobility model for temperature/doping-dependent mobility.

        Parameters
        ----------
        model : str
            "constant" (user-provided, default), "arora" (Arora model),
            or "low_temp" (low-temperature phonon + impurity scattering).
        """
        type_map = {"constant": 0, "arora": 1, "low_temp": 2}
        if model not in type_map:
            raise ValueError(f"Unknown mobility model: {model}. Use {list(type_map.keys())}")
        self._sim.set_mobility_model(type_map[model])

    def set_statistics(self, stats: str = "boltzmann") -> None:
        """Set carrier statistics model.

        Parameters
        ----------
        stats : str
            "boltzmann" (default) or "fermi_dirac".
            Fermi-Dirac is needed at cryogenic temperatures where
            kT << (Ef - Ec) and Boltzmann approximation breaks down.
        """
        type_map = {"boltzmann": 0, "fermi_dirac": 1}
        if stats not in type_map:
            raise ValueError(f"Unknown statistics: {stats}. Use {list(type_map.keys())}")
        self._sim.set_statistics_type(type_map[stats])

    def set_transient(self, dt: float, t_final: float, fe_gamma: float = 0.0) -> None:
        """Configure transient (time-dependent) simulation.

        Parameters
        ----------
        dt : float
            Time step [s].
        t_final : float
            Total simulation time [s].
        fe_gamma : float
            Landau-Khalatnikov damping coefficient [V*m/C*s]. Positive LK
            values enable LK transient. Eligible 1-D dielectric, carrier and
            midpoint insulator/semiconductor chains use coupled material fields for monotone
            actual steps; other configurations retain operator splitting.
            Zero is used for
            classical transport, rate-independent Preisach, and rate-dependent
            NLS (whose dwell is the actual transient step).
        """
        if not np.isfinite(dt) or dt <= 0 or not np.isfinite(t_final) or t_final < 0:
            raise ValueError("dt must be finite and positive; t_final finite and nonnegative")
        gamma_array = np.asarray(fe_gamma)
        if (gamma_array.shape != () or gamma_array.dtype.kind not in "iuf"
                or not np.isfinite(gamma_array) or float(fe_gamma) < 0.0):
            raise ValueError("fe_gamma must be a finite nonnegative scalar")
        if not hasattr(self, "_sim") or not hasattr(self._sim, "set_ferroelectric_gamma"):
            if float(fe_gamma) != 0.0:
                raise ValueError("ferroelectric transient damping is unavailable")
        else:
            self._sim.set_ferroelectric_gamma(float(fe_gamma))
        self._sim.set_transient_enabled(True)
        self._sim.set_transient_dt(dt)
        self._sim.set_transient_t_final(t_final)

    def set_transient_lk_coupled(self, enable: bool = True) -> None:
        """Use simultaneous LK/Poisson/carrier BE solving by local elimination.

        Requires enabled LK, gamma > 0 and alpha+gamma/dt > 0 over the
        actual step range. Nonmonotone local roots are rejected; reduce dt or
        enable set_transient_lk_substepping().
        Without either LK mode override, eligible 1-D dielectric, carrier and
        midpoint insulator/semiconductor chains use coupled material fields if all actual steps
        satisfy this monotonicity condition. Other configurations keep the
        existing split solver. Explicit False retains splitting across runs.
        Automatic choices are recomputed and reported in snapshots as
        lk_coupled/lk_material_field; the configured dt is unchanged.
        This option does not validate
        a complete device energy balance or add other transient physics.
        """
        if not isinstance(enable, (bool, np.bool_)):
            raise ValueError("coupled LK enable must be a boolean")
        self._sim.set_transient_lk_coupled(bool(enable))

    def set_transient_lk_material_field(self, enable: bool = True) -> None:
        """Use material-side E in structured 1-D/2-D/3-D coupled LK devices.

        Requires set_transient_lk_coupled(True), potential contacts (two endpoints
        for a 1-D chain), zero contact doping, and no edge permittivity
        overrides, fractional volumes or frozen carrier blocks. Solves each
        node's polarization and edge displacement fields at native precision;
        nonuniform meshes/materials and polarization are allowed. Without an
        override, eligible 1-D coupled LK chains select this mode automatically on
        each run. True requires this mode and rejects unsupported combinations;
        False explicitly retains the legacy centered-field discretization.
        Snapshots report the actual mode as lk_material_field.
        With carriers, generation or recombination, retains the coupled
        Poisson/SG/backward-Euler equations and eliminates the nonlocal implicit
        polarization response with its exact Schur derivative. Automatic
        selection includes this transport path, subject to the same model and
        actual-step restrictions. Nodes require paired positive mobilities
        or paired zero mobilities with carriers at most 1e-20 m^-3, zero
        generation and SRH lifetimes >=1e90 s. Interfaces lie at node midpoints;
        full node volumes retain storage and sources at blocked SG faces.
        All transient carrier equations use these full volumes, independently
        of the selected LK field policy; fractional cut-cell transport is
        still unsupported.
        Mixed-grid total terminal current additionally requires complete
        equipotential electrodes, matching mobile reservoirs and empty blocked
        rows with no pair sources at both ends of each accepted interval.
        The compact derivative stores Cartesian line blocks, using
        O(N*(nx+ny+nz)) storage over active axes.
        Interior doping is signed ionized charge in m^-3. Multidimensional use
        requires explicit True and retains the componentwise local cubic model;
        gradient energy and inter-component Landau terms are not included.
        Nonmonotone LK steps remain unsupported in this mode.
        """
        if not isinstance(enable, (bool, np.bool_)):
            raise ValueError("material-field LK enable must be a boolean")
        self._sim.set_transient_lk_material_field(bool(enable))

    def set_transient_lk_zero_d_faces(self, faces: str = "") -> None:
        """Declare whole cell-centred insulating faces for material-field LK.

        xXyYzZ select lower/upper faces; each physical face lies half the
        adjacent mesh edge beyond its endpoint and has zero normal D. Use
        only when the supplied coordinates describe this domain. Contacts
        must have other face normals. Requires 2-D/3-D coupled material-field
        LK. Empty string restores endpoint-at-boundary LK support. The
        selected exterior halves also contribute to the local LK ledger.
        This does not construct cut cells or transfer polarization history.
        """
        self._sim.set_transient_lk_zero_d_faces(faces)

    def set_transient_lk_substepping(self, enable: bool = True, safety: float = 0.5) -> None:
        """Subdivide coupled LK time steps to preserve unique implicit roots.

        For alpha < 0 the actual dt is at most safety*gamma/abs(alpha), also
        clipped to the configured dt, voltage knots and final time. Requires
        set_transient_lk_coupled(True). Every accepted substep is returned with
        its actual clock and energy interval. This bound is not a temporal
        error estimate; accuracy still requires a step convergence study.
        """
        if not isinstance(enable, (bool, np.bool_)):
            raise ValueError("LK substepping enable must be a boolean")
        value = np.asarray(safety)
        if (value.shape != () or value.dtype.kind not in "iuf"
                or not np.isfinite(value) or not 0. < float(safety) < 1.):
            raise ValueError("LK substepping safety must be a finite real scalar in (0, 1)")
        self._sim.set_transient_lk_substepping(bool(enable), float(safety))

    def set_transient_lk_error_control(self, enable: bool = True, rtol: float = 1e-3,
                                     atol: float = 1e-6, min_dt: float = 1e-15,
                                     max_reject: int = 20) -> None:
        """Control local LK polarization error using BE step doubling.

        Requires coupled LK substepping. atol is in C/m². Rejected trials
        roll back; acceptance commits both half steps with their own ledgers.
        min_dt bounds retry proposals; final/knot intervals may be shorter.
        This estimator does not bound global error or directly control the
        potential/carriers. Perform a temporal convergence study as well.
        """
        self._sim.set_transient_lk_error_control(enable, rtol, atol, min_dt, max_reject)

    def set_transient_lk_electrical_error_control(self, enable: bool = True,
            phi_atol: float = 1e-6, carrier_rtol: float = 1e-3,
            carrier_atol: float = 1e10) -> None:
        """Add local phi/n/p budgets to coupled LK polarization error control.

        phi_atol is an absolute voltage tolerance; carrier_atol is in m^-3.
        Carrier estimates use carrier_atol + carrier_rtol*max(fine, coarse).
        All fields must pass before either half step is committed. Retry limits
        are configured by set_transient_lk_error_control. This does not bound
        global trajectory error or apply to classical-only/split FE dynamics.
        """
        self._sim.set_transient_lk_electrical_error_control(
            enable, phi_atol, carrier_rtol, carrier_atol)

    def set_transient_electrical_error_control(self, enable: bool = True,
            phi_atol: float = 1e-6, carrier_rtol: float = 1e-3,
            carrier_atol: float = 1e10, min_dt: float = 1e-15,
            max_reject: int = 20) -> None:
        """Control local phi/n/p error in classical coupled BE transients.

        Requires no FE/LK controls or frozen equations. Voltage uses an absolute
        budget in V; carrier_atol is in m^-3. Compare one coarse step with two
        half steps, roll back rejected groups and return only physical half
        steps. min_dt bounds retries; final/knot intervals may be shorter.
        This local estimate does not supply a global trajectory error bound.
        """
        self._sim.set_transient_electrical_error_control(enable, phi_atol,
            carrier_rtol, carrier_atol, min_dt, max_reject)

    def set_transient_nls_error_control(self, enable: bool = True, rtol: float = 1e-3,
            atol: float = 1e-8, phi_atol: float = 1e-6, carrier_rtol: float = 1e-3,
            carrier_atol: float = 1e10, min_dt: float = 1e-15, max_reject: int = 20) -> None:
        """Joint local P/phi/n/p error control for the split NLS ensemble.

        Polarization atol is in C/m^2, phi_atol in V and carrier_atol in m^-3.
        Requires enabled NLS FE, no other controllers and unfrozen equations.
        Compare one split step with two half steps; rejected groups roll back.
        This does not provide full NLS coupling or a global trajectory bound.
        """
        self._sim.set_transient_nls_error_control(enable, rtol, atol, phi_atol,
            carrier_rtol, carrier_atol, min_dt, max_reject)

    def set_transient_nls_event_control(self, enable: bool = True,
            half_width: float = 1e-18) -> None:
        """Opt in to NLS reversal sampling with a physical half width [s].

        Disabled initially. Requires float128 fixed split NLS, full FE support,
        complete polar end contacts, a voltage waveform, zero depolarization,
        unfrozen equations and no other time controllers. The width must be
        finite, positive, smaller than dt/8 and resolvable by the native clock.
        Existing waveform knots clip the event steps. Inputs and snapshots use
        float64 and do not preserve quad-precision restart states. This option
        does not provide a global trajectory error bound.
        """
        self._sim.set_transient_nls_event_control(enable, half_width)

    def _apply_transient_contact_waveforms(self, waveforms) -> None:
        times, profiles = waveforms
        offsets = {}
        for name, voltage in profiles.items():
            if name not in self._contact_voltages:
                raise ValueError(f"Waveform contact '{name}' must be configured first")
            keys = ([key for key in self.mesh.fields
                     if key == "contact_gate" or key.startswith("contact_gate_")]
                    if name == "gate" else [f"contact_{name}"])
            mask = np.zeros(self.mesh.npts(), dtype=bool)
            for key in keys:
                if key not in self.mesh.fields:
                    raise ValueError(f"Missing waveform contact field '{key}'")
                mask |= self.mesh.fields[key].astype(bool).ravel()
            nodes = np.flatnonzero(mask)
            if not nodes.size:
                raise ValueError(f"Waveform contact '{name}' matches zero mesh nodes")
            # Native offsets preserve each contact's built-in equilibrium
            # potential even if the configured applied DC voltage has changed.
            with np.errstate(over="ignore", invalid="ignore"):
                profile = voltage - self._contact_voltages[name]
            if not np.all(np.isfinite(profile)):
                raise ValueError("Waveform voltage offsets must be finite")
            for idx in nodes:
                node = int(idx)
                if node in offsets and not np.array_equal(offsets[node], profile):
                    raise ValueError("Overlapping waveform contacts prescribe conflicting voltages")
                offsets[node] = profile
        self._sim.set_transient_voltage_waveforms(times, offsets)

    def set_transient_contact_waveforms(self, times_s, voltages_V: Dict[str, np.ndarray]) -> None:
        """Set continuous piecewise-linear applied contact voltages, in V.

        Use a shared strictly increasing clock starting at zero and covering
        t_final. Every knot truncates the current time step. Profiles are copied;
        unspecified contacts retain their configured DC voltages. This does not
        change configured DC contacts. A run starts at transient_start_time
        (zero by default) and samples this absolute waveform clock. Existing FE
        physical memory follows the usual transient semantics.
        Frozen potential is incompatible with voltage waveforms.
        """
        clock = np.asarray(times_s)
        if clock.ndim != 1 or clock.dtype.kind not in "iuf":
            raise ValueError("Waveform times must be a real one-dimensional array")
        clock = np.array(clock, dtype=np.float64, copy=True)
        if (clock.size < 2 or not np.all(np.isfinite(clock)) or clock[0] != 0.
                or not np.all(clock[1:] > clock[:-1])):
            raise ValueError("Waveform times must be finite, increasing and start at zero")
        if not isinstance(voltages_V, dict) or not voltages_V:
            raise ValueError("Waveform voltages must be a nonempty contact mapping")
        profiles = {}
        for name, profile in voltages_V.items():
            values = np.asarray(profile)
            if values.ndim != 1 or values.dtype.kind not in "iuf" or values.shape != clock.shape:
                raise ValueError("Waveform voltages must be real arrays matching the clock")
            values = np.array(values, dtype=np.float64, copy=True)
            if not np.all(np.isfinite(values)):
                raise ValueError("Waveform voltages must be finite")
            profiles[name] = values
        waveforms = (clock, profiles)
        self._apply_transient_contact_waveforms(waveforms)
        self._transient_contact_waveforms = waveforms

    def clear_transient_contact_waveforms(self) -> None:
        """Remove transient drive profiles and return to configured DC contacts."""
        self._sim.clear_transient_voltage_waveforms()
        self._transient_contact_waveforms = None

    def create_nls_continuation(self, max_iter: int = 100, tol: float = 1e-16):
        """Prepare an opt-in persistent split-NLS transient without advancing it.

        Configure time, seed, NLS physics and optional error control first.
        The capsule holds the native simulator alive and retains its full
        precision accepted states/controller between ``advance(max_retries=1)``
        calls. Inspect ``status``, ``history``, ``trace`` and ``diagnostics``.
        Returned arrays are float64 copies, unsuitable as precision checkpoints.
        Subsequent physical/controller configuration changes are rejected.
        This restricted path supports the native split-NLS continuation scope;
        it does not enable unsupported thermal, quantum or other physics.
        It does not update ``Simulator.results``; read the capsule history.
        """
        self._sim.set_gummel_max_iter(max_iter)
        self._sim.set_tolerance(tol)
        self._apply_cut_cell()
        if getattr(self, "_transient_contact_waveforms", None) is not None:
            self._apply_transient_contact_waveforms(self._transient_contact_waveforms)
        # Native advancement happens through the capsule, outside RecordingBackend.
        # Conservatively prohibit seed-free replay once a capsule is handed out.
        self._configuration_state_advanced = True
        return self._sim.create_nls_continuation()

    def run_transient(self, max_iter: int = 50, tol: float = 1e-10) -> List[Dict[str, np.ndarray]]:
        """Execute transient simulation.

        Parameters
        ----------
        max_iter : int
            Maximum Newton iterations per attempted time step.
        tol : float
            Row-equilibrated Newton residual tolerance per time step.
            Linear carrier rows are normalized by their own local current
            and previous density; potential rows retain voltage units.

        Returns
        -------
        list of dict
            The initial state at the configured absolute start clock (default
            time_s=0), followed by accepted backward-Euler
            endpoints. The last step is truncated to t_final. A rejected
            attempt keeps the last accepted fields/time, valid=False and
            dt_s=0; attempted_time_s identifies its proposed endpoint.
            Classical transport solves Poisson and both carrier species by
            default. At t=0 potential is projected onto Gauss' law with the
            prescribed initial carriers, without advancing time or memory.
            Call set_freeze_phi(True) to request a fixed-potential classical
            benchmark; it preserves the supplied initial potential. Coupled
            mode requires a Dirichlet potential reference. Eligible 1-D
            dielectric, carrier and midpoint insulator/semiconductor LK chains
            automatically use coupled material fields
            for monotone actual steps when neither LK mode was overridden.
            Other FE configurations retain splitting (implicit LK or actual-step
            NLS), followed by electrical Newton with both species active.
            set_transient_lk_coupled(True) eliminates each unique local LK root
            into the simultaneous Poisson/carrier BE Newton equations, including
            the analytic polarization derivative. Traps/quantum/thermal
            and other unsupported enabled physics raise ValueError.
            Supported equipotential contact planes expose electrode charge and
            separate conduction, displacement (including FE), and total currents.
            These are accepted-interval BE currents; t=0 and rejected steps
            have no current interval. Use integrate_transient_terminal_history
            for their charge/source-work integral. The mobile-charge ledger's
            terminal_currents_A remains a conduction quantity.
            Dielectric and polarization currents are also exposed separately.
            For continuous linear contact voltage, the terminal-history helper
            accepts voltage_quadrature="linear" while holding each BE current
            constant. Pure lossless charge-free dielectrics additionally expose
            independent dielectric_energy_J and stable energy increments; use
            audit_transient_dielectric_energy for this limited energy balance.
            set_transient_contact_waveforms supplies continuous piecewise-linear
            applied voltages; steps stop at every knot. In FE mode, kinetics
            sees the endpoint applied field with previous accepted P/carriers.
            Configured DC contacts are restored after each run or exception.
            electrode_charge_increments_C is computed from accepted component
            increments; use it for small changes that absolute float64 electrode
            charges cannot resolve. No such increment exists at t=0 or failure.
        """
        self._sim.set_gummel_max_iter(max_iter)
        self._sim.set_tolerance(tol)
        self._apply_cut_cell()
        if getattr(self, "_transient_contact_waveforms", None) is not None:
            self._apply_transient_contact_waveforms(self._transient_contact_waveforms)
        history = self._sim.solve_transient()
        # Store last result for compatibility
        if history:
            last = history[-1]
            self.results = dict(last)
        return history

    def enable_cut_cell(self, enable: bool = True) -> None:
        """Enable cut-cell / immersed-boundary correction for Poisson solver.

        When enabled, the solver uses edge-effective permittivity that
        accounts for material interfaces cutting through grid edges,
        rather than the default node-based harmonic average.  This
        integrates all intersections of Box, Sphere, axis-aligned Cylinder,
        z-axis Cone and simple (possibly concave) z-extruded Prism
        regions, including layers with no mesh node. Other shapes retain a sampled first-crossing
        approximation. This does not construct cut-face transport or FE cells.

        The correction is applied automatically on the next ``run()``
        call based on the current mesh material fields.

        Parameters
        ----------
        enable : bool
            Turn cut-cell correction on/off.
        """
        if not isinstance(enable, (bool, np.bool_)):
            raise ValueError("enable must be boolean")
        if not enable and getattr(self, '_cut_cell_applied', False):
            empty = np.array([], dtype=np.float64)
            self._sim.set_edge_permittivity(*[empty] * 6)
            self._cut_cell_applied = False
        self._cut_cell_enabled = bool(enable)

    def _apply_cut_cell(self) -> None:
        """Internal: compute and push edge permittivity to C++ solver."""
        if not getattr(self, '_cut_cell_enabled', False):
            return
        mesh = self.mesh
        if "epsilon" not in mesh.fields or "material_id" not in mesh.fields:
            return
        eps = mesh.fields["epsilon"]
        mat_id = mesh.fields["material_id"]
        edge_eps = compute_edge_permittivity(
            mesh,
            eps,
            mat_id,
            shapes=getattr(mesh, "_material_shapes", None),
            material_permittivity=getattr(mesh, "_material_permittivity", None),
        )
        self._sim.set_edge_permittivity(
            edge_eps["x_plus"].astype(np.float64),
            edge_eps["x_minus"].astype(np.float64),
            edge_eps["y_plus"].astype(np.float64),
            edge_eps["y_minus"].astype(np.float64),
            edge_eps["z_plus"].astype(np.float64),
            edge_eps["z_minus"].astype(np.float64),
        )
        self._cut_cell_applied = True

    @contextmanager
    def reliability_transaction(self, *models, commit: bool = True):
        """Commit one retention/endurance segment, or restore it on exception.

        Covers native FE (including Preisach turning points), breakdown, oxide
        charge, active Ps/imprint/NLS parameters, contact BCs and electrical
        guesses with transport quantum continuation state; also Python
        results/contact caches and supplied slow models.
        Geometry, temperature, other physics configuration, time and RNG are
        outside this checkpoint. Do not reconfigure them inside the context.
        Callers must raise on invalid results. commit=False also restores on
        normal exit, allowing isolated experiments from the same initial state.
        """
        if not isinstance(commit, bool):
            raise ValueError("commit must be boolean")
        names = ("results", "_contact_voltages", "_contact_workfunctions",
                 "_pending_contact_ramps", "_accepted_contact_voltages",
                 "_accepted_initial_guess", "_fe_nls_dt",
                 "_configuration_calls", "_configuration_state_advanced")
        cache = {name: deepcopy(getattr(self, name)) for name in names
                 if hasattr(self, name)}
        states = [(model, deepcopy(model.__dict__)) for model in models
                  if model is not None]
        self._sim.begin_reliability_transaction()

        def restore():
            self._sim.rollback_reliability_transaction()
            for name in names:
                if name in cache:
                    setattr(self, name, cache[name])
                elif hasattr(self, name):
                    delattr(self, name)
            for model, state in states:
                model.__dict__.clear()
                model.__dict__.update(state)

        try:
            yield
        except BaseException:
            restore()
            raise
        else:
            if commit:
                self._sim.commit_reliability_transaction()
            else:
                restore()

    def run(self, max_iter: int = 50, tol: float = 1e-10,
            physical_step: bool = True, *, audit_newton: bool = False) -> Dict[str, np.ndarray]:
        """
        Execute block-Newton coupled Poisson-drift-diffusion solve.

        Parameters
        ----------
        max_iter : int
            Maximum outer iterations per solver invocation.
        tol : float
            Relative outer-update tolerance. The classical Gummel equation
            gate is min(max(100*tol, 1e-8), 1e-4); returned-state residuals
            and the actual gate are in steady_equation_audit. This numerical
            gate does not establish device energy or experimental validity.
        physical_step : bool
            Commit FE and irreversible breakdown history once at the requested
            bias if it converges. Numerical continuation keeps that memory fixed.
            False requests an electrical helper solve without advancing history.
            Separate programming pulses use separate run() calls; NLS dwell is
            set with set_ferroelectric_nls_dwell_time(). This is not a coupled
            FE transient or a complete device snapshot API.
        audit_newton : bool
            Reassemble the returned classical or basic DG Newton state with the SG row
            audit where supported. Its equation gate is separate from the
            Newton stopping metric; unavailable physics is reported explicitly.

        Returns
        -------
        dict
            Arrays: phi, n, p, Ex, Ey, Ez, Qn, Qp,
            temperature (if thermal coupling enabled),
            plus metadata converged, iterations.
        """
        if not isinstance(physical_step, bool):
            raise ValueError("physical_step must be boolean")
        if not isinstance(audit_newton, (bool, np.bool_)):
            raise ValueError("audit_newton must be a boolean")
        self._sim.set_gummel_max_iter(max_iter)
        self._sim.set_tolerance(tol)
        self._apply_cut_cell()
        if getattr(self, "_auto_newton_for_hetero_dos", False):
            self._sim.set_use_newton(True)
            self._sim.set_newton_use_log_space(True)
            self._sim.set_newton_use_log_damping(True)
        pending = dict(self._pending_contact_ramps)
        targets = dict(self._contact_voltages)
        self._pending_contact_ramps = {}
        continuation_steps = 1
        continuation_retries = 0
        continuation_steps_completed = 0
        helper_solves = 0
        total_iterations = 0
        applied_voltages = dict(targets)
        accepted_voltages = {name: start for name, (start, _) in pending.items()}
        target_reached = False

        def solve_at_bias(commit_history):
            nonlocal helper_solves, total_iterations, applied_voltages
            self._sim.set_history_updates_enabled(commit_history)
            applied_voltages = dict(self._contact_voltages)
            if not commit_history:
                helper_solves += 1
            result = self._sim.solve(audit_newton=True) if audit_newton else self._sim.solve()
            total_iterations += int(result.get("iterations", 0))
            if result.get("converged", False):
                self._accepted_contact_voltages = dict(applied_voltages)
                self._accepted_initial_guess = tuple(
                    result[key].astype(np.float64).copy() for key in ("phi", "n", "p"))
            return result

        try:
            # The zero-bias seed and intermediate voltages are numerical
            # helpers, not additional NLS dwell or irreversible stress steps.
            seed_failed = False
            if self.results is None and targets:
                if max(abs(v) for v in targets.values()) > 0.25:
                    for name in targets:
                        self.set_contact(name, 0.0, self._contact_workfunctions.get(name))
                    self.results = solve_at_bias(False)
                    pending = {name: (0.0, target) for name, target in targets.items()
                               if abs(target) > 0.0}
                    accepted_voltages = {name: 0.0 for name in pending}
                    seed_failed = not self.results.get("converged", False)
            if pending and not seed_failed:
                max_delta = max(abs(v1 - v0) for v0, v1 in pending.values())
                step_limit = 0.1 if self.results is not None else 0.25
                continuation_steps = max(2, int(np.ceil(max_delta / step_limit)))
                for step in range(1, continuation_steps + 1):
                    alpha = step / continuation_steps
                    for name, (v0, v1) in pending.items():
                        self.set_contact(name, v0 + alpha * (v1 - v0),
                                         self._contact_workfunctions.get(name))
                    if self._accepted_initial_guess is not None:
                        self._sim.set_initial_guess(*self._accepted_initial_guess)
                    commit = physical_step and step == continuation_steps
                    self.results = solve_at_bias(commit)
                    # Failed native attempts roll back FE/BD history. Reuse
                    # their electrical iterate only as a numerical seed.
                    for _ in range(2):
                        if self.results.get("converged", False):
                            break
                        continuation_retries += 1
                        self._sim.set_initial_guess(
                            self.results["phi"].astype(np.float64),
                            self.results["n"].astype(np.float64),
                            self.results["p"].astype(np.float64))
                        self.results = solve_at_bias(commit)
                    if not self.results.get("converged", False):
                        break
                    continuation_steps_completed = step
                    accepted_voltages.update({name: self._contact_voltages[name]
                                              for name in pending})
                target_reached = continuation_steps_completed == continuation_steps
            elif not seed_failed:
                self.results = solve_at_bias(physical_step)
                target_reached = bool(self.results.get("converged", False))
                continuation_steps_completed = int(target_reached)
            if not target_reached:
                # Keep the requested target for the next run() rather than
                # accidentally accepting the last helper voltage as its goal.
                self._pending_contact_ramps = {
                    name: (accepted_voltages.get(name, start), target)
                    for name, (start, target) in pending.items()}
        except BaseException:
            self._pending_contact_ramps = {
                name: (self._accepted_contact_voltages.get(name, start), target)
                for name, (start, target) in pending.items()}
            raise
        finally:
            self._sim.set_history_updates_enabled(True)
            if self._accepted_initial_guess is not None:
                self._sim.set_initial_guess(*self._accepted_initial_guess)
            for name, target in targets.items():
                self.set_contact(name, target, self._contact_workfunctions.get(name))
        self.results["continuation_steps"] = continuation_steps
        self.results["continuation_steps_completed"] = continuation_steps_completed
        self.results["continuation_retries"] = continuation_retries
        self.results["continuation_helper_solves"] = helper_solves
        self.results["continuation_iterations"] = total_iterations
        self.results["applied_contact_voltages"] = applied_voltages
        self.results["target_contact_voltages"] = targets
        self.results["target_reached"] = target_reached
        self.results["physical_step_accepted"] = bool(physical_step and target_reached)
        self.results["history_update_scope"] = "ferroelectric_and_irreversible_breakdown"
        # P0-3: every result carries an explicit validity flag; callers must
        # not silently consume a non-converged state as physical data.
        self.results["valid"] = bool(self.results.get("converged", False))
        if not self.results["valid"]:
            warnings.warn(
                "Solver did not converge; result marked valid=False. Do NOT "
                "use this point for physical conclusions (issues0719 P0-3).",
                RuntimeWarning, stacklevel=2)
        return self.results

    def to_mesh_fields(self) -> Dict[str, np.ndarray]:
        """Copy latest simulation results into mesh fields.

        C++ result vectors are in node order (i + nx*(j + ny*k), i fastest);
        to_3d() reshapes them to [i,j,k]-indexed 3-D arrays.  (Audit §19.)
        """
        if self.results is None:
            raise RuntimeError("No results. Call run() first.")
        fields = {}
        for key in ["phi", "n", "p", "Ex", "Ey", "Ez", "Qn", "Qp", "temperature"]:
            arr = self.results[key]
            if arr.size > 0:
                fields[key] = self.mesh.to_3d(arr)
        return fields

    def save(self, filename: str):
        """Export mesh with results to file (VTK, XDMF, etc. via meshio).

        to_mesh_fields() returns [i,j,k]-indexed 3-D arrays; from_3d() re-ravels
        them to node order to match node_coords.  (Audit §19.)
        """
        fields = self.to_mesh_fields()
        for name, data in fields.items():
            self.mesh.add_field(name, self.mesh.from_3d(data))
        self.mesh.save(filename)

    def run_adaptive(
        self,
        device: Device,
        max_rounds: int = 5,
        tol: float = 1e-3,
        initial_level: int = 1,
        refine_level: int = 1,
        error_fields: Optional[List[str]] = None,
        error_mode: str = "gradient",
        marker_combine: str = "union",
        verbose: bool = True,
        **sim_kwargs,
    ):
        """Run multi-round adaptive refinement loop.

        Cycles: solve -> estimate error -> refine -> prolongate -> re-solve.

        Parameters
        ----------
        device : Device
            Device definition (geometry, doping, contacts).
        max_rounds : int
            Maximum adaptive refinement cycles.
        tol : float
            Convergence tolerance on relative error reduction.
        initial_level : int
            Initial feature-based refinement level.
        refine_level : int
            Additional refinement per adaptive round.
        error_fields : list, optional
            Fields for error estimation. Default: ["phi", "n", "p"].
        error_mode : str
            "gradient" or "residual".
        marker_combine : str
            "union" or "intersection" for merging markers.
        verbose : bool
            Print progress per round.
        **sim_kwargs
            Passed to ``run()``.

        Returns
        -------
        grids : list of StructuredGrid
            Mesh at each round.
        results : list of dict
            Simulation results at each round.
        history : dict
            Per-round metrics: npts, max_error, delta_phi.
        """
        refiner = AdaptiveRefiner(device, base_resolution=(self.mesh.dx, self.mesh.dy, self.mesh.dz),
                                  base_shape=self.mesh.shape())
        return refiner.run_adaptive_solve(
            self, max_rounds=max_rounds, tol=tol,
            initial_level=initial_level, refine_level=refine_level,
            error_fields=error_fields, error_mode=error_mode,
            marker_combine=marker_combine, verbose=verbose,
            sim_kwargs=sim_kwargs if sim_kwargs else None,
        )


install_configuration_recording(Simulator)


def _ramp_voltages(target: float, steps: int) -> np.ndarray:
    """Generate monotonic voltage ramp from 0 to target."""
    if steps <= 1 or abs(target) < 1e-12:
        return np.array([target])
    return np.linspace(0.0, target, steps)


def simulate_device(
    device: Device,
    resolution: Optional[Tuple[float, float, float]] = None,
    temperature: float = 300.0,
    quantum: bool = True,
    optical_generation: Optional[np.ndarray] = None,
    adaptive_level: int = 0,
    poisson_solver: SolverType = SolverType.DENSE_DIRECT,
    continuity_solver: SolverType = SolverType.DENSE_DIRECT,
    ramp_steps: int = 1,
    **sim_kwargs,
) -> Tuple[Simulator, Dict[str, np.ndarray]]:
    """
    One-shot simulation from a Device definition.

    Parameters
    ----------
    device : Device
    resolution : tuple, optional
        Mesh resolution (dx, dy, dz) in meters.
    temperature : float
        Operating temperature [K].
    quantum : bool
        Enable density gradient correction.
    adaptive_level : int
        Number of adaptive refinement levels (0 = uniform mesh).
    ramp_steps : int
        Number of voltage ramp steps for non-equilibrium contacts.
        Values > 1 enable gradual ramping from 0 V to the target
        contact voltage, using the solution at each step as the
        initial guess for the next.  This dramatically improves
        convergence for MOSFETs at high gate/drain bias.
    **sim_kwargs
        Passed to ``Simulator.run()``.

    Returns
    -------
    (Simulator, results_dict)
    """
    if adaptive_level > 0:
        refiner = AdaptiveRefiner(device, base_resolution=resolution or (50e-9, 50e-9, 50e-9))
        mesh = refiner.generate_feature_refined_mesh(level=adaptive_level)
    else:
        mesh = structured_mesh_from_device(device, resolution=resolution)

    sim = Simulator(mesh, temperature=temperature)
    sim.set_material_from_mesh()
    if optical_generation is not None:
        sim.set_optical_generation(optical_generation)

    # Identify contacts that need ramping (non-zero voltage)
    contact_targets = {
        name: float(voltage)
        for name, (shape, voltage) in device.contacts.items()
    }
    contact_workfunctions = getattr(device, "contact_workfunctions", {})
    ramped_names = [n for n, v in contact_targets.items() if abs(v) > 1e-12]

    # If no ramping needed or only one step, do standard single solve
    if ramp_steps <= 1 or not ramped_names:
        for name, voltage in contact_targets.items():
            sim.set_contact(name, voltage, contact_workfunctions.get(name))
        sim.set_quantum(quantum)
        sim.set_solver_type(poisson_solver, continuity_solver)
        results = sim.run(**sim_kwargs)
        return sim, results

    # Voltage ramping: start with all contacts at 0 V
    for name in contact_targets:
        sim.set_contact(name, 0.0, contact_workfunctions.get(name))
    sim.set_quantum(quantum)
    sim.set_solver_type(poisson_solver, continuity_solver)

    # Run ramp steps in lock-step for all ramped contacts
    ramp_arrays = {
        name: _ramp_voltages(contact_targets[name], ramp_steps)
        for name in ramped_names
    }

    total_iters = 0
    for step in range(ramp_steps):
        for name in ramped_names:
            v = ramp_arrays[name][step]
            if step == 0:
                sim.set_contact(name, v, contact_workfunctions.get(name))
            else:
                sim.update_contact(name, v)
        results = sim.run(**{**sim_kwargs, "physical_step":
                            sim_kwargs.get("physical_step", True) and step == ramp_steps - 1})
        total_iters += int(results.get("continuation_iterations", results.get("iterations", 0)))
        if not results["converged"]:
            print(f"Warning: ramp step {step + 1}/{ramp_steps} did not converge")
            for name in ramped_names:
                sim.update_contact(name, contact_targets[name])
            results["target_contact_voltages"] = dict(contact_targets)
            results["target_reached"] = False
            break

    # Update metadata to reflect total work
    results["iterations"] = total_iters
    return sim, results


def simulate_sweep(
    base_device: Device,
    sweep_contacts: Dict[str, np.ndarray],
    resolution: Optional[Tuple[float, float, float]] = None,
    temperature: float = 300.0,
    quantum: bool = True,
    optical_generation: Optional[np.ndarray] = None,
    adaptive_level: int = 0,
    poisson_solver: SolverType = SolverType.DENSE_DIRECT,
    continuity_solver: SolverType = SolverType.DENSE_DIRECT,
    ramp_steps: int = 1,
    use_newton: bool = False,
    newton_log_space: bool = True,
    verbose: bool = True,
    **sim_kwargs,
) -> Tuple[Simulator, List[Dict[str, np.ndarray]]]:
    """
    Voltage sweep over one or more contacts with mesh reuse.

    The base device geometry is fixed; only contact voltages change
    between sweep points.  The mesh is generated once and reused,
    and the solution at each bias point is propagated as the initial
    guess for the next, giving fast sequential convergence.

    Parameters
    ----------
    base_device : Device
        Device template defining geometry, doping, and material.
        Contact voltages in this device are overwritten by sweep values.
    sweep_contacts : dict
        Mapping ``{contact_name: np.ndarray of voltages}``.
        All arrays must have the same length (number of sweep points).
        Example: ``{"gate": np.linspace(0, 1.0, 21)}``
    resolution : tuple, optional
        Mesh resolution (dx, dy, dz) in meters.
    temperature : float
        Operating temperature [K].
    quantum : bool
        Enable density gradient correction.
    adaptive_level : int
        Number of adaptive refinement levels (0 = uniform mesh).
    ramp_steps : int
        Number of voltage ramp steps per bias point.  Values > 1
        enable gradual ramping from the previous bias to the next,
        improving convergence for MOSFETs at high gate/drain bias.
    use_newton : bool
        Enable the Gummel-warm-up + line-searched Newton polish cascade
        (issues0719 P0-3): recommended for stiff sweeps (strong inversion,
        high injection).  Default False (plain Gummel).
    newton_log_space : bool
        Solve the Newton carrier blocks in log-space (default True when
        ``use_newton`` is set); strongly recommended in strong inversion.
    verbose : bool
        Print progress per sweep point.
    **sim_kwargs
        Passed to ``Simulator.run()`` (e.g. ``max_iter=120``, ``tol=1e-8``).

    Returns
    -------
    (Simulator, list of results)
        The Simulator object (holding the final mesh and results) and
        a list of result dictionaries, one per sweep point.

    Examples
    --------
    >>> import numpy as np
    >>> from tcad import Device, simulate_sweep
    >>> device = Device.mosfet(Lg=50e-9, tox=1.5e-9, tsi=15e-9, W=50e-9,
    ...                        Vg=0.0, Vd=0.1, Vs=0.0)
    >>> sim, results = simulate_sweep(
    ...     device,
    ...     sweep_contacts={"gate": np.linspace(0, 1.0, 21)},
    ...     resolution=(5e-9, 2.5e-9, 2.5e-9),
    ...     ramp_steps=3,
    ...     max_iter=120,
    ...     tol=1e-8,
    ... )
    >>> # Extract drain current proxy
    >>> for r in results:
    ...     n_max = r["n"].max()
    ...     print(f"Vg={r['V_gate']:.2f}V  n_max={n_max:.3e}")
    """
    if not sweep_contacts:
        raise ValueError("sweep_contacts must contain at least one contact to sweep")

    # Validate sweep arrays have consistent length
    sweep_lengths = {name: len(arr) for name, arr in sweep_contacts.items()}
    if len(set(sweep_lengths.values())) != 1:
        raise ValueError(
            f"All sweep arrays must have the same length, got: {sweep_lengths}"
        )
    n_points = next(iter(sweep_lengths.values()))
    if n_points == 0:
        raise ValueError("Sweep arrays must not be empty")

    # Build mesh once (geometry does not change during voltage sweep)
    if adaptive_level > 0:
        refiner = AdaptiveRefiner(base_device, base_resolution=resolution or (50e-9, 50e-9, 50e-9))
        mesh = refiner.generate_feature_refined_mesh(level=adaptive_level)
    else:
        mesh = structured_mesh_from_device(base_device, resolution=resolution)

    sim = Simulator(mesh, temperature=temperature)
    sim.set_material_from_mesh()
    if optical_generation is not None:
        sim.set_optical_generation(optical_generation)
    sim.set_quantum(quantum)
    sim.set_solver_type(poisson_solver, continuity_solver)
    if use_newton:
        # Gummel warm-up + line-searched Newton polish cascade
        # (issues0719 P0-3): far more robust on stiff sweeps; log-space
        # carrier variables keep the Newton update well-scaled in strong
        # inversion/accumulation.
        sim.set_use_newton(True)
        if newton_log_space:
            sim.set_newton_log_space(True)

    # Fixed contacts: those NOT being swept take their value from base_device
    all_contact_targets = {
        name: float(voltage)
        for name, (shape, voltage) in base_device.contacts.items()
    }
    fixed_contacts = {
        name: voltage
        for name, voltage in all_contact_targets.items()
        if name not in sweep_contacts
    }
    contact_workfunctions = getattr(base_device, "contact_workfunctions", {})
    for name, voltage in fixed_contacts.items():
        sim.set_contact(name, voltage, contact_workfunctions.get(name))

    # Pre-compute ramp arrays for each swept contact
    ramp_arrays = {}
    for name in sweep_contacts:
        ramp_arrays[name] = _ramp_voltages(
            float(all_contact_targets.get(name, 0.0)), ramp_steps
        )

    results: List[Dict[str, np.ndarray]] = []
    total_iters = 0

    for idx in range(n_points):
        # Determine target voltages for this sweep point
        target_voltages = {
            name: float(arr[idx])
            for name, arr in sweep_contacts.items()
        }

        if verbose:
            info = ", ".join(f"{n}={v:.3f}V" for n, v in target_voltages.items())
            print(f"[sweep {idx + 1}/{n_points}] {info}")

        # Apply ramping if requested (ramp from previous bias or from 0)
        if ramp_steps > 1:
            # Build ramp from previous voltages (or 0 for first step)
            prev_voltages = {
                name: (float(results[-1]["_voltages"][name]) if results else 0.0)
                for name in sweep_contacts
            }
            for step in range(ramp_steps):
                alpha = step / (ramp_steps - 1) if ramp_steps > 1 else 1.0
                for name in sweep_contacts:
                    v = prev_voltages[name] + alpha * (target_voltages[name] - prev_voltages[name])
                    if idx == 0 and step == 0:
                        sim.set_contact(name, v, contact_workfunctions.get(name))
                    else:
                        sim.update_contact(name, v)
                result = sim.run(**{**sim_kwargs, "physical_step":
                                   sim_kwargs.get("physical_step", True) and step == ramp_steps - 1})
                total_iters += int(result.get("continuation_iterations", result.get("iterations", 0)))
                if not result["converged"]:
                    print(f"  Warning: ramp sub-step {step + 1}/{ramp_steps} did not converge")
                    for name, voltage in target_voltages.items():
                        sim.update_contact(name, voltage)
                    result["target_contact_voltages"] = {**fixed_contacts, **target_voltages}
                    result["target_reached"] = False
                    break
        else:
            # Single-step: set or update contact
            for name, voltage in target_voltages.items():
                if idx == 0:
                    sim.set_contact(name, voltage, contact_workfunctions.get(name))
                else:
                    sim.update_contact(name, voltage)
            result = sim.run(**sim_kwargs)
            total_iters += int(result.get("continuation_iterations", result.get("iterations", 0)))

        # Annotate result with sweep metadata
        result["_requested_voltages"] = {**fixed_contacts, **target_voltages}
        result["_voltages"] = {**fixed_contacts, **target_voltages,
                               **result.get("applied_contact_voltages", {})}
        result["_sweep_index"] = idx
        result["iterations"] = total_iters  # cumulative for convenience
        results.append(result)

    if verbose:
        print(f"Sweep complete: {n_points} points, {total_iters} total iterations")

    return sim, results
