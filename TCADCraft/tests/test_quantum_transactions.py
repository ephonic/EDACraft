"""Transport-Q must roll back with phi/n/p in reliability checkpoints."""
from contextlib import contextmanager
import json
import sys
import numpy as np
import pytest
from tcad.core import native_constants
from tcad.mesh.structured_grid import StructuredGrid
from tcad.simulator import Simulator
from test_native_steady_thermal import EXTRUSION
from test_quantum_thermal_retry import device, same_state

SCENARIOS = ('rollback', 'error', 'cancel', 'inner_commit_outer_rollback',
             'inner_rollback_outer_commit', 'commit')


class CancelProbe(BaseException):
    pass


def make(axis, high):
    core = device(axis, .02)
    if not high:
        return core
    axes = [np.array([0.])] * 3
    axes[axis] = np.linspace(0., 1e-7, 5)
    bbox = tuple((0., 1e-7 if i == axis else float(EXTRUSION[i])) for i in range(3))
    mesh = StructuredGrid(bbox, *map(len, axes), axes=axes)
    mesh.fields.update(doping=np.array([0., 1e13, 2e13, 1e13, 0.]),
        Nc=np.full(5, 1e15), Nv=np.full(5, 1e15), Eg=np.zeros(5),
        mu_n=np.full(5, .01), mu_p=np.full(5, .005),
        contact_left=np.arange(5) == 0, contact_right=np.arange(5) == 4)
    sim = Simulator(mesh)
    # The same complete native physical fixture is used at both API levels.
    sim._sim.backend = core
    sim.set_contact('left', 0.)
    sim.set_contact('right', .02)
    return sim


def solve(sim, high, voltage=None):
    if voltage is not None:
        if high:
            sim.set_contact('right', voltage)
        else:
            sim.set_dirichlet_potential({0: 0., 4: voltage})
    result = sim.run(max_iter=300, tol=1e-11) if high else sim.solve()
    assert result['converged']
    return result


@contextmanager
def transaction(sim, high, commit):
    if high:
        with sim.reliability_transaction(commit=commit):
            yield
        return
    sim.begin_reliability_transaction()
    try:
        yield
    except BaseException:
        sim.rollback_reliability_transaction()
        raise
    else:
        (sim.commit_reliability_transaction if commit else sim.rollback_reliability_transaction)()


def fields(result):
    return {k: result[k] for k in ('phi', 'n', 'p', 'Qn', 'Qp', 'temperature',
        'Jn_x', 'Jn_y', 'Jn_z', 'Jp_x', 'Jp_y', 'Jp_z', 'iterations', 'converged')}


def exercise(axis, warm, high, scenario):
    sim, reference = make(axis, high), make(axis, high)
    entered = None
    if warm:
        entered = fields(solve(sim, high))
        same_state(entered, fields(solve(reference, high)))
    trial = []
    commits_outer = scenario in ('commit', 'inner_rollback_outer_commit')
    try:
        with transaction(sim, high, commits_outer):
            trial.append(fields(solve(sim, high, .04)))
            if scenario == 'inner_commit_outer_rollback':
                with transaction(sim, high, True):
                    trial.append(fields(solve(sim, high, -.04)))
            elif scenario == 'inner_rollback_outer_commit':
                with transaction(sim, high, False):
                    trial.append(fields(solve(sim, high, -.04)))
            elif scenario == 'error':
                raise RuntimeError('trial rejected after native convergence')
            elif scenario == 'cancel':
                raise CancelProbe('trial cancelled after native convergence')
    except (RuntimeError, CancelProbe) as error:
        assert scenario in ('error', 'cancel')
        assert str(error) == ('trial rejected after native convergence' if scenario == 'error'
                              else 'trial cancelled after native convergence')
    if commits_outer:
        solve(reference, high, .04)
    # Commit controls preserve the trial; rollback cases restore the original
    # boundary and seed. Neither path reconfigures quantum/material physics.
    retry, expected = fields(solve(sim, high)), fields(solve(reference, high))
    return dict(axis=axis, warm=warm, high=high, scenario=scenario, entered=entered,
                trial=trial, retry=retry, reference=expected)


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('warm', [False, True])
@pytest.mark.parametrize('high', [False, True])
@pytest.mark.parametrize('scenario', SCENARIOS)
def test_quantum_checkpoint_pairs_cache_with_accepted_seed(axis, warm, high, scenario):
    row = exercise(axis, warm, high, scenario)
    same_state(row['retry'], row['reference'])


if __name__ == '__main__':
    rows = [exercise(axis, warm, high, scenario) for scenario in SCENARIOS
            for high in (False, True) for warm in (False, True) for axis in range(3)]
    with open(sys.argv[1], 'w') as f:
        json.dump(dict(constants=native_constants(), records=rows), f, sort_keys=True,
                  default=lambda v: v.tolist() if isinstance(v, np.ndarray) else v.item())
