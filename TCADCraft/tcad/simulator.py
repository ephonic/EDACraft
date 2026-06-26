"""High-level Python API for 3D quantum-corrected device simulation."""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import numpy as np

from tcad.geometry.device_builder import Device
from tcad.mesh.structured_grid import StructuredGrid
from tcad.solver.unstructured_simulator import UnstructuredSimulator
from tcad.mesh.cut_cell import compute_edge_permittivity
from tcad.mesh.generator import structured_mesh_from_device
from tcad.mesh.adaptive_refiner import AdaptiveRefiner
from tcad.core import PyDeviceSimulator, SolverType


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

        g = mesh.to_cxx_grid()
        self._sim = PyDeviceSimulator(g["nx"], g["ny"], g["nz"],
                                      g["dx"], g["dy"], g["dz"])
        self.results: Optional[Dict[str, np.ndarray]] = None

        # Default arrays
        npts = mesh.npts()
        self._sim.set_permittivity(np.ones(npts, dtype=float) * 8.854187817e-12 * 11.7)
        self._sim.set_mobility(np.ones(npts, dtype=float) * 1400e-4,
                               np.ones(npts, dtype=float) * 450e-4)
        self._sim.set_doping(np.zeros(npts, dtype=float))
        self._sim.set_thermal_voltage(self.VT)

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
            self._sim.set_effective_dos(
                self.mesh.fields["Nc"].astype(float) * 1e6,
                self.mesh.fields["Nv"].astype(float) * 1e6,
            )
        if "Eg" in self.mesh.fields:
            self._sim.set_bandgap(self.mesh.fields["Eg"].astype(float))

    def set_contact(self, name: str, voltage: float, workfunction: Optional[float] = None):
        """
        Apply Dirichlet BC to a named contact.
        The mesh must contain a field ``contact_<name>``.
        """
        field_name = f"contact_{name}"
        if field_name not in self.mesh.fields:
            raise KeyError(f"Contact '{name}' not found in mesh fields. Available: {list(self.mesh.fields.keys())}")
        mask = self.mesh.fields[field_name].astype(bool)
        indices = np.nonzero(mask.ravel())[0].astype(np.int64)

        # Equilibrium carrier densities at contacts (Boltzmann approx)
        if "doping" not in self.mesh.fields:
            raise RuntimeError("Doping field required to set carrier BCs")
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
        mu_n_contact = self.mesh.fields.get("mu_n", np.ones_like(doping))
        is_metal = mu_n_contact[mask].astype(float).mean() < 1e-12
        for idx in indices:
            idx_i = int(idx)
            C = doping[idx_i]
            # Intrinsic concentration at this node
            ni = float(np.sqrt(Nc[idx_i] * Nv[idx_i]) * np.exp(-Eg[idx_i] / (2 * VT)))
            if C > 0:  # n-type
                n_bc[idx_i] = float(C)
                p_bc[idx_i] = float(ni * ni / max(C, 1.0))
                # Equilibrium potential: phi_eq = VT * ln(n/ni)
                phi_eq = float(VT * np.log(max(C, ni) / ni))
            elif C < 0:  # p-type
                p_bc[idx_i] = float(abs(C))
                n_bc[idx_i] = float(ni * ni / max(abs(C), 1.0))
                # Equilibrium potential: phi_eq = -VT * ln(p/ni)
                phi_eq = float(-VT * np.log(max(abs(C), ni) / ni))
            else:  # intrinsic / undoped
                phi_eq = 0.0
            # Applied voltage shifts equilibrium potential
            phi_bc[idx_i] = float(voltage + phi_eq)
        self._sim.set_dirichlet_potential(phi_bc)
        if not is_metal:
            self._sim.set_electron_bc(n_bc)
            self._sim.set_hole_bc(p_bc)

    def set_quantum(self, enabled: bool = True):
        """Enable/disable density-gradient quantum correction."""
        self._sim.set_quantum_enabled(enabled)

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

    def update_contact(self, name: str, voltage: float):
        """
        Update the voltage of an existing contact and re-apply BCs.
        The previous simulation results are kept as the initial guess
        for the next solve, enabling voltage ramping.
        """
        if self.results is None:
            raise RuntimeError("No previous results. Call set_contact() or run() first.")
        # Re-apply contact BC with new voltage
        self.set_contact(name, voltage)
        # Propagate previous solution as initial guess
        self._sim.set_initial_guess(
            self.results["phi"].astype(np.float64),
            self.results["n"].astype(np.float64),
            self.results["p"].astype(np.float64),
        )

    def set_solver_type(
        self,
        poisson_solver: SolverType = SolverType.DENSE_DIRECT,
        continuity_solver: SolverType = SolverType.DENSE_DIRECT,
    ):
        """Configure linear solver backend for Poisson and continuity equations.

        For large 3D problems (>5k nodes) use ``SolverType.PETSC`` to leverage
        PETSc + HYPRE BoomerAMG preconditioning.
        """
        self._sim.set_poisson_solver_type(int(poisson_solver))
        self._sim.set_continuity_solver_type(int(continuity_solver))

    def set_use_newton(self, enable: bool = True):
        """Use Newton-Raphson full-coupled solver instead of Gummel iteration.

        Default is Gummel (``enable=False``), which is robust for most cases.
        Newton uses a hybrid strategy: Gummel first for a robust initial guess,
        then Newton for rapid quadratic convergence. Useful for high-injection
        or strongly coupled problems.
        """
        self._sim.set_use_newton(enable)

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

    def set_btbt(self, enabled: bool = True,
                 A_kane: float = 3.1e21,
                 B_kane: float = 2.0e9,
                 D: int = 2,
                 use_nonlocal: bool = False) -> None:
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
        D : int
            Exponent: 2 for direct, 2.5 (truncated to 2) for indirect tunneling.
        use_nonlocal : bool
            Use non-local (path-integral WKB) tunneling model. Computes
            tunneling probability by integrating along the source-channel
            tunneling path, avoiding the overestimation of the local Kane
            model at sharp p+/n+ junctions. Recommended for TFET simulation.
        """
        self._sim.set_btbt_enabled(enabled)
        self._sim.set_btbt_params(A_kane, B_kane, int(D))
        self._sim.set_btbt_use_nonlocal(use_nonlocal)

    def set_ferroelectric(self, enabled: bool = True,
                          alpha: float = -1.0e8,
                          beta: float = 1.0e18) -> None:
        """Enable ferroelectric polarization (Landau-Khalatnikov model).

        Ferroelectric regions are identified from the mesh ``material_id`` field.
        The ferroelectric model adds a self-consistent polarization charge to the
        Poisson equation, producing the negative capacitance amplification effect.

        Parameters
        ----------
        enabled : bool
            Turn ferroelectric on/off.
        alpha : float
            Landau coefficient alpha [m/F]. Must be negative for double-well
            potential. Typical for HfZrO: ~-1e8.
        beta : float
            Landau coefficient beta [m^5/(F*C^2)]. Must be positive.
            Typical for HfZrO: ~1e18.
        """
        self._sim.set_ferroelectric_enabled(enabled)
        # Identify ferroelectric nodes from material_id field
        if "material_id" in self.mesh.fields:
            mat_id = self.mesh.fields["material_id"].astype(np.int8).ravel()
            # HfZrO materials have material_id >= 4 (based on device region order)
            # Use a simple heuristic: nodes in the gate oxide region of FeFET devices
            fe_mask = np.zeros(self.mesh.npts(), dtype=np.int8)
            # Mark nodes with epsilon corresponding to ferroelectric material
            if "epsilon" in self.mesh.fields:
                eps = self.mesh.fields["epsilon"].ravel()
                # HfZrO epsilon_r ~30-40, eps = eps_r * eps0
                eps0 = 8.854187817e-12
                fe_mask = ((eps > 25.0 * eps0) & (eps < 50.0 * eps0)).astype(np.int8)
            self._sim.set_ferroelectric_params(fe_mask, alpha, beta)

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
            Landau-Khalatnikov damping coefficient for ferroelectric
            transient dynamics [V·m/C·s]. Default 0 (quasi-static FE).
        """
        self._sim.set_transient_enabled(True)
        self._sim.set_transient_dt(dt)
        self._sim.set_transient_t_final(t_final)
        if fe_gamma > 0.0:
            self._sim.set_ferroelectric_gamma(fe_gamma)

    def run_transient(self, max_iter: int = 50, tol: float = 1e-10) -> List[Dict[str, np.ndarray]]:
        """Execute transient simulation.

        Parameters
        ----------
        max_iter : int
            Maximum Gummel iterations per time step.
        tol : float
            Relative convergence tolerance per time step.

        Returns
        -------
        list of dict
            One result dict per time step, each containing phi, n, p,
            Ex, Ey, Ez, converged, iterations.
        """
        self._sim.set_gummel_max_iter(max_iter)
        self._sim.set_tolerance(tol)
        self._apply_cut_cell()
        history = self._sim.solve_transient()
        # Store last result for compatibility
        if history:
            last = history[-1]
            self.results = {
                "phi": last["phi"], "n": last["n"], "p": last["p"],
                "Ex": last.get("Ex", np.array([])),
                "Ey": last.get("Ey", np.array([])),
                "Ez": last.get("Ez", np.array([])),
                "converged": last["converged"],
                "iterations": last.get("iterations", 0),
            }
        return history

    def enable_cut_cell(self, enable: bool = True) -> None:
        """Enable cut-cell / immersed-boundary correction for Poisson solver.

        When enabled, the solver uses edge-effective permittivity that
        accounts for material interfaces cutting through grid edges,
        rather than the default node-based harmonic average.  This
        improves accuracy for curved or angled material boundaries on
        structured Cartesian grids.

        The correction is applied automatically on the next ``run()``
        call based on the current mesh material fields.

        Parameters
        ----------
        enable : bool
            Turn cut-cell correction on/off.
        """
        self._cut_cell_enabled = enable

    def _apply_cut_cell(self) -> None:
        """Internal: compute and push edge permittivity to C++ solver."""
        if not getattr(self, '_cut_cell_enabled', False):
            return
        mesh = self.mesh
        if "epsilon" not in mesh.fields or "material_id" not in mesh.fields:
            return
        eps = mesh.fields["epsilon"]
        mat_id = mesh.fields["material_id"]
        edge_eps = compute_edge_permittivity(mesh, eps, mat_id)
        self._sim.set_edge_permittivity(
            edge_eps["x_plus"].astype(np.float64),
            edge_eps["x_minus"].astype(np.float64),
            edge_eps["y_plus"].astype(np.float64),
            edge_eps["y_minus"].astype(np.float64),
            edge_eps["z_plus"].astype(np.float64),
            edge_eps["z_minus"].astype(np.float64),
        )

    def run(self, max_iter: int = 50, tol: float = 1e-10) -> Dict[str, np.ndarray]:
        """
        Execute block-Newton coupled Poisson-drift-diffusion solve.

        Parameters
        ----------
        max_iter : int
            Maximum Newton iterations.
        tol : float
            Relative convergence tolerance for all fields.

        Returns
        -------
        dict
            Arrays: phi, n, p, Ex, Ey, Ez, temperature (if thermal coupling enabled),
            plus metadata converged, iterations.
        """
        self._sim.set_gummel_max_iter(max_iter)
        self._sim.set_tolerance(tol)
        self._apply_cut_cell()
        self.results = self._sim.solve()
        return self.results

    def to_mesh_fields(self) -> Dict[str, np.ndarray]:
        """Copy latest simulation results into mesh fields.

        C++ result vectors are in node order (i + nx*(j + ny*k), i fastest);
        to_3d() reshapes them to [i,j,k]-indexed 3-D arrays.  (Audit §19.)
        """
        if self.results is None:
            raise RuntimeError("No results. Call run() first.")
        fields = {}
        for key in ["phi", "n", "p", "Ex", "Ey", "Ez", "temperature"]:
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
        refiner = AdaptiveRefiner(device, base_resolution=(self.mesh.dx, self.mesh.dy, self.mesh.dz))
        return refiner.run_adaptive_solve(
            self, max_rounds=max_rounds, tol=tol,
            initial_level=initial_level, refine_level=refine_level,
            error_fields=error_fields, error_mode=error_mode,
            marker_combine=marker_combine, verbose=verbose,
            sim_kwargs=sim_kwargs if sim_kwargs else None,
        )


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
    ramped_names = [n for n, v in contact_targets.items() if abs(v) > 1e-12]

    # If no ramping needed or only one step, do standard single solve
    if ramp_steps <= 1 or not ramped_names:
        for name, voltage in contact_targets.items():
            sim.set_contact(name, voltage)
        sim.set_quantum(quantum)
        sim.set_solver_type(poisson_solver, continuity_solver)
        results = sim.run(**sim_kwargs)
        return sim, results

    # Voltage ramping: start with all contacts at 0 V
    for name in contact_targets:
        sim.set_contact(name, 0.0)
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
                sim.set_contact(name, v)
            else:
                sim.update_contact(name, v)
        results = sim.run(**sim_kwargs)
        total_iters += int(results.get("iterations", 0))
        if not results["converged"]:
            print(f"Warning: ramp step {step + 1}/{ramp_steps} did not converge")

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
    for name, voltage in fixed_contacts.items():
        sim.set_contact(name, voltage)

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
                        sim.set_contact(name, v)
                    else:
                        sim.update_contact(name, v)
                result = sim.run(**sim_kwargs)
                total_iters += int(result.get("iterations", 0))
                if not result["converged"]:
                    print(f"  Warning: ramp sub-step {step + 1}/{ramp_steps} did not converge")
        else:
            # Single-step: set or update contact
            for name, voltage in target_voltages.items():
                if idx == 0:
                    sim.set_contact(name, voltage)
                else:
                    sim.update_contact(name, voltage)
            result = sim.run(**sim_kwargs)
            total_iters += int(result.get("iterations", 0))

        # Annotate result with sweep metadata
        result["_voltages"] = {**fixed_contacts, **target_voltages}
        result["_sweep_index"] = idx
        result["iterations"] = total_iters  # cumulative for convenience
        results.append(result)

    if verbose:
        print(f"Sweep complete: {n_points} points, {total_iters} total iterations")

    return sim, results
