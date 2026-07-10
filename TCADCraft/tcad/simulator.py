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

    def set_freeze_phi(self, enable: bool = True):
        """Freeze the Poisson block (phi) during the Newton solve (C档).

        Pins phi to its current value so the Newton system reduces to a 2-block
        (n, p) continuity solve. With phi held flat (set via ``set_initial_guess``
        or a uniform Dirichlet bias) this kills the drift term, reducing the
        Scharfetter-Gummel scheme to pure central-difference diffusion — the
        basis for an isolated continuity-equation MMS (manufactured solution)
        grid-convergence test. Newton-only; the Gummel path is unaffected.
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
        Coefficients are passed in SI units (no runtime scaling). To use
        literature values quoted in ``1/cm`` and ``V/cm``, multiply ``A`` by
        ``1e2`` and ``B`` by ``1e2`` before passing. For materials other than
        Si, supply the appropriate Chynoweth coefficients — they are strongly
        material- and temperature-dependent.
        """
        self._sim.set_ii_enabled(enabled)
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
            # Use median over semiconductor nodes (a single global coefficient
            # set; median is robust to oxide zeros).
            if semi.any() and ii_A_n[semi].max() > 0:
                A_n = float(np.median(ii_A_n[semi]))
                B_n = float(np.median(ii_B_n[semi]))
                A_p = float(np.median(ii_A_p[semi]))
                B_p = float(np.median(ii_B_p[semi]))
        self._sim.set_ii_params(A_n, B_n, A_p, B_p)

    def set_breakdown(self, enabled: bool = True,
                      sigma_bd: float = 1.0e-2) -> None:
        """Enable dielectric breakdown modelling (M7b, audit §22).

        After each converged solve, dielectric-region nodes whose electric
        field magnitude ``|E|`` exceeds the material breakdown field ``E_bd``
        are flagged as *soft-broken*. On subsequent solves a leakage term
        ``sigma_bd`` is added to the Poisson diagonal at those nodes (same
        units as the Laplacian diagonal ``eps/dx^2``), locally relaxing
        ``phi`` toward 0 (a soft short) so a gate leak develops. The breakdown
        is **irreversible** — once a node breaks down it stays broken down,
        modelling the conductive filament.

        The breakdown field ``E_bd`` is read per-node from the mesh's
        ``E_bd`` field, which ``Device.sample_on_grid`` populates from each
        ``Material.E_bd`` (e.g. ``sio2()`` -> 1.2e9 V/m, ``hfo2()`` -> 6e8
        V/m). Materials with ``E_bd == 0`` never break down.

        Parameters
        ----------
        enabled : bool
            Turn breakdown detection on/off.
        sigma_bd : float
            Soft-breakdown leakage term [F/m^3] — an effective added
            permittivity-density added to the Poisson diagonal at broken nodes
            (same units as ``eps/dx^2``, so dimensionally consistent with the
            Laplacian). Default 1e-2 (~10% of a typical oxide diagonal
            ``eps_SiO2/dx^2`` for a 2 nm oxide; raise for a harder short,
            e.g. 1e0 dominates the diagonal and pins phi≈0).
            (A档: was documented [S/m], which was dimensionally wrong.)

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
                          fe_mask_override: Optional[np.ndarray] = None) -> None:
        """Enable ferroelectric polarization.

        Three models are supported (M7c + P3):

        - ``"landau_khalatnikov"`` (default): the cubic L-K model
          ``alpha*P + beta*P^3 = E``. Hysteresis arises from per-component
          branch continuation. Parameters ``alpha``/``beta`` set the double-well
          shape (Ps = sqrt(-alpha/beta), Ec = (2|alpha|/3)*sqrt(-alpha/(3beta))).
        - ``"preisach"``: the classical scalar Preisach (play-operator) model,
          parameterised DIRECTLY by saturation polarization ``Ps`` [C/m^2] and
          coercive field ``Ec`` [V/m]. This sidesteps the L-K alpha/beta
          dimensional ambiguity and produces a natural memory loop.
        - ``"nls"``: Nucleation-Limited Switching (Merz law
          ``tau(E)=tau0·exp(E0/|E|)``), suited to wurtzite ferroelectrics like
          AlScN whose switching is domain-nucleation-limited. Produces a finite-
          slope (S-shaped) loop instead of a vertical jump. (P3.)

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
            ``"landau_khalatnikov"`` or ``"preisach"``.
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
        fe_mask_override : np.ndarray, optional
            Explicit int8 node mask (1 = ferroelectric). Bypasses material
            auto-detection when provided.
        """
        self._sim.set_ferroelectric_enabled(enabled)
        model_map = {"landau_khalatnikov": 0, "preisach": 1, "nls": 2}
        model_int = model_map.get(model.lower(), 0)
        self._sim.set_ferroelectric_model(model_int)

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
            alpha = float(self.mesh.fields["fe_alpha"].ravel()[fe_mask.astype(bool)][0])
            beta = float(self.mesh.fields["fe_beta"].ravel()[fe_mask.astype(bool)][0])
        if model_int == 1 or model_int == 2:
            # Resolve Preisach/NLS Ps/Ec from material field when available.
            if "fe_ps" in self.mesh.fields and np.any(fe_mask):
                ps_field = self.mesh.fields["fe_ps"].ravel()[fe_mask.astype(bool)]
                ec_field = self.mesh.fields["fe_ec"].ravel()[fe_mask.astype(bool)]
                if np.any(np.abs(ps_field) > 0.0):
                    Ps = float(ps_field[np.abs(ps_field) > 0.0][0])
                if np.any(np.abs(ec_field) > 0.0):
                    Ec = float(ec_field[np.abs(ec_field) > 0.0][0])
            self._sim.set_ferroelectric_preisach(Ps, Ec, Escale)
            if model_int == 2:
                # NLS Merz-law parameters (P3).
                self._sim.set_ferroelectric_nls(nls_tau0, nls_E0, nls_dt)
        self._sim.set_ferroelectric_params(fe_mask, alpha, beta)
        # Internal field / Imprint offset (P2.1): read from material field.
        if "fe_E_bi" in self.mesh.fields and np.any(fe_mask):
            ebi = self.mesh.fields["fe_E_bi"].ravel()[fe_mask.astype(bool)]
            if np.any(np.abs(ebi) > 0.0):
                self._sim.set_ferroelectric_builtin_field(float(ebi[np.abs(ebi) > 0.0][0]))

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
            ``"landau_khalatnikov"``, ``"preisach"``, or ``"nls"``.
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
        model_map = {"landau_khalatnikov": 0, "preisach": 1, "nls": 2}
        model_int = model_map.get(model.lower(), 0)
        self._sim.set_ferroelectric_model(model_int)
        if model_int == 1:
            self._sim.set_ferroelectric_preisach(Ps, Ec, Escale)
        if model_int == 2:
            self._sim.set_ferroelectric_preisach(Ps, Ec, Escale)
            self._sim.set_ferroelectric_nls(nls_tau0, nls_E0, nls_dt)

    def set_ferroelectric_builtin_field(self, E_bi: float = 0.0) -> None:
        """Set the internal/imprint field offset (P2.1).

        The effective ferroelectric switching drive becomes ``E_eff = E - E_bi``.
        This models a built-in bias or wake-up imprint that breaks the +/- loop
        symmetry. ``E_bi = 0`` (default) restores a symmetric loop.

        Parameters
        ----------
        E_bi : float
            Internal field offset [V/m].
        """
        self._sim.set_ferroelectric_builtin_field(E_bi)

    def set_leakage(self, enabled: bool = True,
                    pf_C: float = 0.02, pf_B: float = 5.0e5, pf_phi_t: float = 0.5,
                    fn_C: float = 0.0, fn_B: float = 0.0, fn_phi_b: float = 0.0,
                    E_floor: float = 1.0e6, sigma_cap: float = 0.05,
                    leak_mask_override: Optional[np.ndarray] = None) -> None:
        """Enable leakage current (Poole-Frenkel / Fowler-Nordheim) (P2.2).

        Leakage provides a field-dependent conductive path across the
        ferroelectric/insulator stack. This relaxes the internal potential
        slightly at the leaky layer so the P-V loop does NOT close at V=0
        — reproducing the experimentally observed "0V non-closure" and the
        off-state gate leakage in FeFETs.

        The leaky nodes default to the ferroelectric nodes (auto-detected from
        the material's ``fe_alpha`` field); pass ``leak_mask_override`` to
        force a specific node mask.

        The PF/FN conductance is added to the Poisson diagonal **normalised to
        the local Laplacian diagonal** ``eps/dx²``, so ``pf_C``/``fn_C`` are
        dimensionless fractions (e.g. 0.02 ≈ 2% of the dielectric conductance at
        high field). This makes the model grid-independent.

        Parameters
        ----------
        enabled : bool
            Turn leakage on/off.
        pf_C, pf_B, pf_phi_t : float
            Poole-Frenkel prefactor (fraction of ``eps/dx²``), barrier
            coefficient, and trap ionization energy [eV].
            ``frac_pf = pf_C·exp(-pf_B·sqrt(pf_phi_t/|E|))``.
        fn_C, fn_B, fn_phi_b : float
            Fowler-Nordheim prefactor, exponent coefficient, and barrier height
            [eV]. ``frac_fn = fn_C·|E|·exp(-fn_B·fn_phi_b^1.5/|E|)``.
        E_floor : float
            Field below which leakage is negligible [V/m].
        sigma_cap : float
            Cap on added conductance as a fraction of ``eps/dx²``.
        leak_mask_override : np.ndarray, optional
            Explicit int8 node mask (1 = leaky). Defaults to the FE mask.
        """
        if not enabled:
            self._sim.set_leakage_enabled(False)
            return
        npts = self.mesh.npts()
        if leak_mask_override is not None:
            mask = np.asarray(leak_mask_override, dtype=np.int8).ravel()
        elif "fe_alpha" in self.mesh.fields:
            mask = (np.abs(self.mesh.fields["fe_alpha"].ravel()) > 0.0).astype(np.int8)
        else:
            mask = np.zeros(npts, dtype=np.int8)
        self._sim.set_leakage(mask, pf_C, pf_B, pf_phi_t,
                              fn_C, fn_B, fn_phi_b, E_floor, sigma_cap)

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
