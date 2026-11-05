"""Native-backed continuation resumption after Python boundary interruptions."""
import itertools
import json
import math
from pathlib import Path
import sys

import numpy as np
import pytest
from tcad.core import native_constants
from test_physical_step_commit import high_level,PS

class AbortSolve(BaseException):
    pass

ERRORS={'runtime':RuntimeError,'keyboard':KeyboardInterrupt,'exit':SystemExit,'abort':AbortSolve}
CASES=list(itertools.product([False,True],['first','middle','final'],ERRORS))
FIELDS=['phi','n','p','P','Ex','Ey','Ez','Jn_x','Jp_x']

def fields(result):
    return {k:result[k].tolist() for k in FIELDS if k in result}

def record(warm,stage,error):
    tested=high_level(initial_voltage=0. if warm else 4.)
    reference=high_level(initial_voltage=0. if warm else 4.)
    for sim in (tested,reference):
        if warm:
            assert sim.run(max_iter=300,tol=1e-8)['converged']
            sim.update_contact('right',4.)
    core=tested._sim;call_at={'first':1,'middle':3,'final':40}[stage]+int(not warm)
    trace=[]
    class InterruptOnce:
        calls=0
        def __getattr__(self,name):return getattr(core,name)
        def solve(self):
            self.calls+=1
            if self.calls==call_at:raise ERRORS[error]('boundary interruption')
            result=core.solve()
            trace.append(dict(call=self.calls,fields=fields(result)))
            return result
    proxy=InterruptOnce();tested._sim=proxy
    try:
        tested.run(max_iter=300,tol=1e-8)
    except BaseException as exc:
        assert type(exc) is ERRORS[error] and str(exc)=='boundary interruption'
    else:raise AssertionError('interruption did not propagate')
    finally:tested._sim=core
    accepted=float(tested._accepted_contact_voltages['right'])
    pending={name:list(pair) for name,pair in tested._pending_contact_ramps.items()}
    before=dict(accepted_V=accepted,pending=pending,targets=dict(tested._contact_voltages),
                guess=[v.tolist() for v in tested._accepted_initial_guess],
                depth=tested._configuration_depth,trace=trace)
    actual=tested.run(max_iter=300,tol=1e-8)
    expected=reference.run(max_iter=300,tol=1e-8)
    assert actual['valid'] and expected['valid']
    return dict(warm=warm,stage=stage,error=error,before=before,
                actual=fields(actual),reference=fields(expected),
                retry_steps=actual['continuation_steps'],retry_helpers=actual['continuation_helper_solves'],
                target_reached=actual['target_reached'],physical_step_accepted=actual['physical_step_accepted'])

@pytest.mark.parametrize('warm,stage,error',CASES)
def test_interruption_retains_resume_path_and_single_physical_dwell(warm,stage,error):
    row=record(warm,stage,error);before=row['before']
    expected_start={'first':0.,'middle':.2,'final':3.9}[stage]
    assert before['accepted_V']==pytest.approx(expected_start,rel=1e-14,abs=0.)
    assert before['targets']=={'left':0.,'right':4.} and before['depth']==0
    assert before['pending']=={'right':[before['accepted_V'],4.]}
    assert row['retry_steps']>=2 and row['retry_helpers']==row['retry_steps']-1
    assert row['target_reached'] and row['physical_step_accepted']
    for state in before['trace']:
        np.testing.assert_array_equal(state['fields']['P'],np.zeros((9,3)))
    for k in FIELDS:
        if k in row['actual']:
            np.testing.assert_allclose(row['actual'][k],row['reference'][k],rtol=1e-10,atol=1e-12)
    np.testing.assert_allclose(np.asarray(row['actual']['P'])[:,0],-PS*(1-math.exp(-.1)),rtol=1e-12,atol=1e-12)
    np.testing.assert_allclose(row['actual']['phi'],np.linspace(0.,4.,9),rtol=1e-12,atol=1e-12)

if __name__=='__main__':
    Path(sys.argv[1]).write_text(json.dumps(dict(constants=native_constants(),records=[record(*case) for case in CASES]),indent=2,allow_nan=False))
