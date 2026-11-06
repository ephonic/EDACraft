"""Opt-in observational profiling; arguments and numeric returns are unchanged."""
from pathlib import Path
import atexit,json,resource,time

_stream=None
_origin=None
_phase=None
_sequence=0

def emit(event,**values):
    global _sequence
    _sequence+=1
    usage=resource.getrusage(resource.RUSAGE_SELF)
    memory={}
    for line in Path('/proc/self/status').read_text().splitlines():
        if line.startswith(('VmRSS:','VmHWM:')):
            k,v=line.split(':',1);memory[k+'_kB']=int(v.split()[0])
    row=dict(sequence=_sequence,event=event,phase=_phase,elapsed_s=time.monotonic()-_origin,
             process_cpu_s=time.process_time(),peak_rss_MiB=usage.ru_maxrss/1024,**memory,**values)
    _stream.write(json.dumps(row,allow_nan=False)+'\n');_stream.flush()

def timed(name,function):
    def call(*args,**kwargs):
        start=time.monotonic();cpu=time.process_time()
        emit(name+'_begin')
        try:result=function(*args,**kwargs)
        except BaseException as error:
            emit(name+'_error',error_type=type(error).__name__);raise
        emit(name+'_end',wall_s=time.monotonic()-start,cpu_s=time.process_time()-cpu)
        return result
    return call

class _ProfiledFactor:
    def __init__(self,factor):
        self._factor=factor
        self.solve=timed('triangular_solve',factor.solve)

def install(stem):
    global _stream,_origin
    if _stream is not None:raise RuntimeError('profiling already installed')
    import tcad.solver._sheet_linear as linear
    import tcad.solver.sheet_dielectric as dielectric
    _stream=Path(str(stem)+'.profile.jsonl').open('x')
    atexit.register(_stream.close);_origin=time.monotonic()
    original_factor=linear.splu
    def factor(*args,**kwargs):
        return _ProfiledFactor(timed('newton_factorization',original_factor)(*args,**kwargs))
    original_solve=linear._ReusedGMRES.solve
    def solve(self,A,b):
        global _phase
        previous=_phase;_phase=self.operator_key
        emit('linear_solve_begin',dimension=A.shape[0],nnz=A.nnz)
        start=time.monotonic();cpu=time.process_time()
        try:return original_solve(self,A,b)
        except BaseException as error:
            emit('linear_solve_error',error_type=type(error).__name__);raise
        finally:
            emit('linear_solve_end',wall_s=time.monotonic()-start,cpu_s=time.process_time()-cpu)
            _phase=previous
    linear.splu=factor
    linear.gmres=timed('gmres',linear.gmres)
    linear._ReusedGMRES.solve=solve
    dielectric.spsolve=timed('initial_bulk_solve',dielectric.spsolve)
    emit('profile_installed')
