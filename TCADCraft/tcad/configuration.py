"""Owned configuration recipes, distinct from accepted physical history.

High-level setters are replayed against freshly sampled material/contact
geometry. Explicit nodal overrides are interpolated in physical coordinates;
binary masks use nearest neighbours. This is not conservative state transfer.
"""
from copy import deepcopy
from functools import wraps
import inspect
import hashlib

import numpy as np


_NODAL_ARGUMENTS = {
    'set_charge_volume_fraction': ('fraction',),
    'set_optical_generation': ('G_opt',),
    'set_btbt_weight': ('weight',),
    'set_thermal_coupling': ('thermal_conductivity',),
    'set_ferroelectric': ('fe_mask_override',),
    'set_leakage': ('leak_mask_override',),
    'set_interface_traps': ('trap_mask_override',),
    'set_oxide_traps': ('Q_ot',),
}
_NODE_MAPS = {'set_dirichlet_potential', 'set_electron_bc', 'set_hole_bc',
              'set_thermal_dirichlet'}
_NATIVE_NODAL = {
    'set_permittivity', 'set_mobility', 'set_doping',
    'set_charge_volume_fraction', 'set_optical_generation', 'set_btbt_weight',
    'set_recombination', 'set_effective_dos', 'set_bandgap',
    'set_thermal_conductivity', 'set_ferroelectric_params', 'set_leakage',
    'set_interface_traps', 'set_oxide_traps', 'set_initial_guess',
}
_FIELD_DERIVED = {'set_material_from_mesh', 'set_disordered_transport', 'set_contact',
    'update_contact', 'set_impact_ionization', 'set_breakdown', 'set_ferroelectric',
    'set_ferroelectric_model', 'set_leakage', 'set_interface_traps', 'set_oxide_traps'}


def _field_digest(values):
    a = np.ascontiguousarray(values)
    return (a.dtype.str, a.shape, hashlib.sha256(a.tobytes()).hexdigest())


def remember_device_fields(mesh):
    """Retain small provenance digests so explicit edits can be distinguished
    from material fields that should be freshly sampled after refinement.
    """
    mesh._device_field_digests = {k: _field_digest(v) for k, v in mesh.fields.items()}


class RecordingBackend:
    """Forward the native API while recording explicit user configuration.

    Simulator-internal calls are suppressed by the enclosing operation. Direct
    ``sim._sim.set_*`` calls are recorded too; unsupported mesh-dependent calls
    fail on replay instead of being silently omitted.
    """
    def __init__(self, owner, backend):
        self.owner = owner
        self.backend = backend

    def __getattr__(self, name):
        method = getattr(self.backend, name)
        if not callable(method):
            return method
        if name in {'set_ferroelectric_history','set_ferroelectric_ensemble_history'}:
            @wraps(method)
            def install_history(*args, **kwargs):
                result = method(*args, **kwargs)
                self.owner._configuration_state_advanced = True
                return result
            return install_history
        if name.startswith('solve'):
            @wraps(method)
            def solve(*args, **kwargs):
                self.owner._configuration_state_advanced = True
                return method(*args, **kwargs)
            return solve
        if not name.startswith(('set_', 'clear_')):
            return method

        @wraps(method)
        def configure(*args, **kwargs):
            record = self.owner._configuration_depth == 0
            saved = deepcopy((args, kwargs)) if record else None
            result = method(*args, **kwargs)
            if record:
                self.owner._configuration_calls.append(('native', name, *saved))
            return result
        return configure


def _record_method(method):
    signature = inspect.signature(method)

    @wraps(method)
    def configured(self, *args, **kwargs):
        # Some existing validation adapters call unbound Simulator setters on
        # a lightweight host exposing only _sim. Preserve that public behavior.
        if not hasattr(self, '_configuration_calls'):
            return method(self, *args, **kwargs)
        record = self._configuration_depth == 0
        bound = signature.bind(self, *args, **kwargs)
        saved = deepcopy({k: v for k, v in bound.arguments.items() if k != 'self'}) if record else None
        if record and method.__name__ in _FIELD_DERIVED:
            baseline = getattr(self.mesh, '_device_field_digests', {})
            saved['_mesh_overrides'] = {k: v.copy() for k, v in self.mesh.fields.items()
                if _field_digest(v) != baseline.get(k)}
            saved['_mesh_removed'] = sorted(set(baseline) - self.mesh.fields.keys())
        self._configuration_depth += 1
        try:
            result = method(self, *args, **kwargs)
        finally:
            self._configuration_depth -= 1
        if record:
            name = method.__name__
            if name == 'update_contact':
                # Replay the requested boundary, not the source solve/continuation.
                name = 'set_contact'
                saved['workfunction'] = self._contact_workfunctions.get(saved['name'])
            self._configuration_calls.append(('python', name, saved))
        return result
    return configured


def _numerical_operation(method):
    @wraps(method)
    def operation(self, *args, **kwargs):
        if not hasattr(self, '_configuration_calls'):
            return method(self, *args, **kwargs)
        self._configuration_depth += 1
        try:
            result = method(self, *args, **kwargs)
            if (method.__name__ in ('run','run_transient') and self.results
                    and self.results.get('converged',False)):
                self._accepted_fe_checkpoint = self._sim.get_ferroelectric_ensemble_history()
            return result
        finally:
            self._configuration_depth -= 1
    return operation


def install_configuration_recording(cls):
    """Cover all public configuration setters, including nested convenience APIs."""
    for name, method in list(vars(cls).items()):
        if callable(method) and (name.startswith('set_') or name in {
                'enable_cut_cell', 'update_contact', 'clear_transient_contact_waveforms'}):
            setattr(cls, name, _record_method(method))
    for name in ('run', 'run_transient', 'create_nls_continuation', '_apply_cut_cell'):
        setattr(cls, name, _numerical_operation(getattr(cls, name)))


class MeshTransfer:
    def __init__(self, source, target):
        self.source, self.target = source, target
        self.axes = source.axis_coordinates()
        target_axes = target.axis_coordinates()
        self.same = all(np.array_equal(a, b) for a, b in zip(self.axes, target_axes))
        for axis in 'xyz':
            for end in ('min', 'max'):
                if getattr(source, axis + end) != getattr(target, axis + end):
                    raise ValueError('configuration transfer requires identical bounding boxes')
        for a, b in zip(self.axes, target_axes):
            if (a.size == 1) != (b.size == 1) or (a.size == 1 and a[0] != b[0]):
                raise ValueError('configuration transfer cannot change active axes or singleton planes')

    def nodal(self, values, *, nearest=False):
        a = np.asarray(values)
        if a.size != self.source.npts():
            raise ValueError('configuration override requires one value per source mesh node')
        if self.same:
            return np.ascontiguousarray(a.ravel()).copy()
        if np.all(a == a.flat[0]):
            # A multilinear interpolator can put a constant carrier floor one
            # ULP above its bound in 3-D, changing the admissible physics mode.
            return np.full(self.target.npts(),a.flat[0],dtype=a.dtype)
        from scipy.interpolate import RegularGridInterpolator
        interpolate = RegularGridInterpolator(self.axes, self.source.to_3d(a.ravel()),
            method='nearest' if nearest or a.dtype.kind in 'biu' else 'linear', bounds_error=True)
        result = interpolate(np.column_stack(self.target.flat_coords()))
        if a.dtype.kind == 'f' and np.all(np.isfinite(a)):
            result = np.clip(result,np.min(a),np.max(a))
        return np.ascontiguousarray(result, dtype=a.dtype)

    def node_map(self, values):
        if self.same:
            return deepcopy(values)
        # Explicit node maps pin physical points, not inferred electrode faces.
        # All specified source nodes must exist exactly on the new grid.
        lookup = {tuple(p): i for i, p in enumerate(np.column_stack(self.target.flat_coords()))}
        coords = np.column_stack(self.source.flat_coords())
        result = {}
        for index, value in values.items():
            if not isinstance(index, (int, np.integer)) or not 0 <= index < len(coords):
                raise ValueError('invalid source node in configuration boundary map')
            point = tuple(coords[index])
            if point not in lookup:
                raise ValueError('configuration boundary node is absent on target mesh; use named contacts')
            result[lookup[point]] = value
        return result

    def python_arguments(self, name, values):
        values = deepcopy(values)
        if name == 'set_thermal_dirichlet':
            values['bc'] = self.node_map(values['bc'])
        for key in _NODAL_ARGUMENTS.get(name, ()):
            value = values.get(key)
            if value is not None and not np.isscalar(value):
                values[key] = self.nodal(value, nearest=key.endswith('_override'))
        return values

    def native_arguments(self, name, args, kwargs):
        args, kwargs = deepcopy((args, kwargs))
        if self.same:
            return args, kwargs
        if name in _NODE_MAPS:
            return tuple(self.node_map(v) for v in args), {k: self.node_map(v) for k, v in kwargs.items()}
        if name == 'set_ohmic_contacts':
            raise ValueError('native ohmic-contact node sets require explicit redefinition after remeshing')
        if name in {'set_edge_permittivity', 'set_x_positions', 'set_y_positions', 'set_z_positions'}:
            raise ValueError(f'{name} cannot be interpolated; configure mesh coordinates or enable_cut_cell instead')
        if name == 'set_transient_voltage_waveforms':
            # Offset maps are indexed by boundary node and cannot be treated
            # as nodal spatial arrays (time samples may have the same length).
            signature_keys = ('times_s', 'offsets_V')
            values = dict(zip(signature_keys, args)); values.update(kwargs)
            values['offsets_V'] = self.node_map(values['offsets_V'])
            return (), values
        def remap(v):
            if isinstance(v, np.ndarray):
                if name not in _NATIVE_NODAL:
                    raise ValueError(f'no spatial remapping rule for {name}')
                return self.nodal(v)
            if isinstance(v, (dict, list, tuple, set)):
                raise ValueError(f'no spatial remapping rule for {name}')
            return v
        return tuple(remap(v) for v in args), {k: remap(v) for k, v in kwargs.items()}


def clone_on_mesh(source, mesh, *, include_initial_guess=True,
                  fe_history=None, max_landau_energy_change_J=None):
    """Replay owned configuration into an independent, fresh native simulator.

    Default rejects accepted FE/domain/breakdown history. ``conservative`` LK
    projection requires an energy budget; ``conservative_ensemble`` replicates
    one accepted non-LK ensemble including its branch/turning-point memory.
    ``include_initial_guess=False`` requests a fresh physical restart instead.
    Arbitrary private-attribute writes and replacement backends are unsupported.
    """
    from tcad.simulator import Simulator
    if not isinstance(source._sim, RecordingBackend):
        raise ValueError('configuration inheritance requires the original recording backend')
    if mesh is source.mesh or fe_history:
        mesh = deepcopy(mesh)
    transfer = MeshTransfer(source.mesh, mesh)
    if fe_history not in (None, 'conservative','conservative_ensemble'):
        raise ValueError("fe_history must be None, 'conservative' or 'conservative_ensemble'")
    if fe_history=='conservative' and (not include_initial_guess or max_landau_energy_change_J is None):
        raise ValueError('conservative history requires initial state and explicit Landau energy budget')
    if fe_history and not include_initial_guess:
        raise ValueError('history transfer requires an accepted initial state')
    breakdown = False
    faces = ''
    stateful = bool(source._fe_node_mask is not None and np.any(source._fe_node_mask))
    for kind, name, *payload in source._configuration_calls:
        if name in {'set_ferroelectric_enabled', 'set_breakdown_enabled'} and kind == 'native':
            a, k = payload
            stateful |= bool(a[0] if a else k.get('enable', False))
        if name == 'set_breakdown' and kind == 'python':
            stateful |= bool(payload[0].get('enabled', True))
            breakdown |= bool(payload[0].get('enabled', True))
        if name == 'set_breakdown_enabled' and kind == 'native':
            a,k = payload; breakdown = bool(a[0] if a else k.get('enable',False))
        if name == 'set_transient_lk_zero_d_faces':
            if kind == 'python': faces = payload[0].get('faces','')
            else:
                a,k = payload; faces = a[0] if a else k.get('faces','')
    if include_initial_guess and stateful and source._configuration_state_advanced and not fe_history:
        raise ValueError('accepted FE/breakdown history cannot be remeshed; explicitly request a fresh physical restart')
    if fe_history=='conservative':
        state = source.results
        if (breakdown or not state or not state.get('valid',False) or not state.get('converged',False)
                or not state.get('lk_energy_available',False) or 'time_s' not in state
                or not np.array_equal(source._sim.get_ferroelectric_history().ravel(),state.get('P'))):
            raise ValueError('conservative history requires current accepted cubic-LK transient state without breakdown')
    elif fe_history=='conservative_ensemble':
        state=source.results
        checkpoint=getattr(source,'_accepted_fe_checkpoint',None)
        current=source._sim.get_ferroelectric_ensemble_history()
        if (breakdown or not state or not state.get('converged',False) or checkpoint is None
                or any(not np.array_equal(current[k],checkpoint[k]) for k in ('parameters','mask','polarization','play'))
                or not np.array_equal(current['polarization'].ravel(),np.asarray(state.get('P')).ravel())):
            raise ValueError('ensemble transfer requires unchanged accepted non-LK state without breakdown')
    clone = Simulator(mesh, temperature=source.temperature)
    # Copy only fields missing from a freshly sampled target; geometry-derived
    # fields already present on that target retain their exact material masks.
    for name, values in source.mesh.fields.items():
        if name not in mesh.fields:
            mesh.add_field(name, transfer.nodal(values, nearest=(name.startswith('contact_') or name == 'material_id')))
    for kind, name, *payload in source._configuration_calls:
        if kind == 'python':
            arguments = dict(payload[0])
            for field in arguments.pop('_mesh_removed', []):
                mesh.fields.pop(field, None)
            for field, values in arguments.pop('_mesh_overrides', {}).items():
                mesh.add_field(field, transfer.nodal(values,
                    nearest=(field.startswith('contact_') or field == 'material_id')))
            getattr(clone, name)(**transfer.python_arguments(name, arguments))
        else:
            if name in {'set_ferroelectric_history','set_ferroelectric_ensemble_history'} or (name == 'set_transient_start_time' and not include_initial_guess):
                # Installed history is an accepted state, never configuration.
                continue
            if not include_initial_guess and name in {'set_initial_guess', 'clear_initial_guess'}:
                continue
            args, kwargs = transfer.native_arguments(name, *payload)
            getattr(clone._sim, name)(*args, **kwargs)
    if include_initial_guess:
        guess = tuple(state[k] for k in ('phi','n','p')) if fe_history else source._accepted_initial_guess
        if guess is None and source.results is not None and source.results.get('converged', False):
            guess = tuple(source.results[k] for k in ('phi', 'n', 'p'))
        if guess is not None:
            mapped = tuple(transfer.nodal(v) for v in guess)
            clone._sim.set_initial_guess(*mapped)
            clone._accepted_initial_guess = tuple(v.copy() for v in mapped)
            clone._accepted_contact_voltages = deepcopy(source._accepted_contact_voltages)
        clone._pending_contact_ramps = deepcopy(source._pending_contact_ramps)
    if fe_history=='conservative_ensemble':
        from tcad.mesh.conservative_transfer import dual_faces
        from tcad.mesh.ensemble_transfer import conservative_ensemble_transfer
        def supports(grid):return dual_faces(grid.axis_coordinates(),(grid.dx,grid.dy,grid.dz),faces)
        mapped,report=conservative_ensemble_transfer(checkpoint,supports(source.mesh),supports(mesh),
            target_mask=clone._sim.get_ferroelectric_mask())
        clone._sim.set_ferroelectric_ensemble_history(mapped)
        if 'time_s' in state:
            clone._sim.set_transient_start_time(float(state['time_s']))
            report['absolute_start_time_s']=float(state['time_s'])
        clone._accepted_fe_checkpoint=deepcopy(mapped)
        clone._fe_history_transfer_report=deepcopy(report)
        clone._configuration_state_advanced=True
    elif fe_history:
        from tcad.mesh.conservative_transfer import dual_faces, conservative_lk_transfer
        def supports(grid):
            return dual_faces(grid.axis_coordinates(), (grid.dx,grid.dy,grid.dz), faces)
        params = np.asarray(state['lk_parameters'])
        # Extra imprint/depolarization also change remesh energy; not budgeted
        # by the quartic-only projection and therefore require a later model.
        if params.shape != (6,) or params[3] != 0 or params[4] != 0:
            raise ValueError('conservative projection currently requires zero imprint/extra depolarization')
        if (not np.array_equal(params,source._sim.get_ferroelectric_lk_parameters())
                or not np.array_equal(params,clone._sim.get_ferroelectric_lk_parameters())):
            raise ValueError('LK coefficients changed after the accepted history')
        sf=supports(source.mesh)
        x,y,z=(np.diff(f) for f in sf)
        native_volume=np.asarray(state['lk_node_volumes_m3'])
        expected_volume=(z[:,None,None]*y[None,:,None]*x[None,None,:]).ravel()
        if not np.allclose(native_volume,np.where(source._sim.get_ferroelectric_mask(),expected_volume,0),rtol=1e-12,atol=0):
            raise ValueError('LK geometry changed after the accepted history')
        p,report = conservative_lk_transfer(np.asarray(state['P']).reshape(-1,3),
            sf,supports(mesh),source_mask=source._sim.get_ferroelectric_mask(),
            target_mask=clone._sim.get_ferroelectric_mask(),alpha=params[0],beta=params[1],
            max_landau_energy_change_J=max_landau_energy_change_J)
        clone._configuration_depth += 1
        try:
            clone._sim.set_ferroelectric_history(p)
            clone._sim.set_transient_start_time(float(state['time_s']))
        finally: clone._configuration_depth -= 1
        report['absolute_start_time_s'] = float(state['time_s'])
        clone._fe_history_transfer_report = deepcopy(report)
        clone._configuration_state_advanced = True
    return clone
