"""Cumulative charge from freshly reconstructed general-three-temperature ledgers."""
from math import fsum
import numpy as np
from tcad.solver.cut_cell_transport import Q


def audit_charge_path(model, initial, final, ledgers, cell_ledgers, *, charge_budget_C):
    """Reconstruct mobile/trap storage, transport and integrated terminal KCL.

    No production operator or attached audit summary supplies these balances.
    Sources create neutral pairs or transfer charge into the explicit trap
    reservoir. They cancel in total charge, including with nonlinear band work.
    This is a conservation check, not a constitutive or experimental validation.
    """
    ld=np.longdouble;volume=model.vol.astype(ld);nc=model.nc
    def total(key, species=None):
        arrays=[]
        for ledger in cell_ledgers:
            raw=ledger[key] if species is None else ledger[key][species]
            value=np.asarray(raw,ld)
            if value.shape!=(nc,) or not np.all(np.isfinite(value)):
                raise ValueError('finite independently reconstructed cell charge ledger required')
            arrays.append(value)
        return np.sum(arrays,axis=0,dtype=ld) if arrays else np.zeros(nc,ld)
    trapped=model.trap_capture_law is not None
    trap_endpoint=volume*model.Nt*(final.trap_fraction.astype(ld)-initial.trap_fraction)
    trap_increment=total('occupied_trap_increment') if trapped else np.zeros(nc,ld)
    endpoint=ld(Q)*(volume*((final.p_m3-initial.p_m3)-(final.n_m3-initial.n_m3))-trap_endpoint)
    increments=ld(Q)*(total('particle_increments','holes')-total('particle_increments','electrons')-trap_increment)
    outward=ld(Q)*(total('particle_transport','holes')-total('particle_transport','electrons'))
    balance=endpoint+outward;telescoping=increments-endpoint
    terminals={face:fsum(ledger['terminal_charge_C'][face] for ledger in ledgers) for face in model.bc}
    kcl=fsum(terminals.values())
    global_balance=float(np.sum(balance,dtype=ld))
    global_telescoping=float(np.sum(telescoping,dtype=ld))
    worst=max(float(np.max(abs(balance),initial=0)),float(np.max(abs(telescoping),initial=0)),
        abs(global_balance),abs(global_telescoping),abs(kcl))
    finite=bool(all(np.all(np.isfinite(v)) for v in (endpoint,increments,outward,balance,telescoping)) and
        all(np.isfinite(v) for v in (*terminals.values(),kcl,global_balance,global_telescoping)))
    valid=bool(finite and np.isfinite(charge_budget_C) and charge_budget_C>0 and worst<=charge_budget_C)
    vector=lambda value:list(map(float,value))
    return dict(charge_path_valid=valid,independently_reconstructed_cumulative_charge=True,
        cell_endpoint_charge_increments_C=vector(endpoint),cell_charge_increments_C=vector(increments),
        cell_outward_charge_C=vector(outward),cell_charge_balance_residuals_C=vector(balance),
        cell_charge_storage_telescoping_errors_C=vector(telescoping),
        cumulative_charge_balance_residual_C=global_balance,
        cumulative_charge_storage_telescoping_error_C=global_telescoping,
        cumulative_terminal_charge_C=terminals,cumulative_terminal_KCL_residual_C=kcl,
        maximum_cumulative_charge_error_C=worst,cumulative_charge_atol_C=charge_budget_C)
