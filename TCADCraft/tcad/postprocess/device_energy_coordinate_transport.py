"""Independent physical replay for the explicit device transaction envelope."""
from .energy_coordinate_transport import audit_energy_coordinate_step
from tcad.solver.energy_coordinate_transport import SCOPE

DEVICE_SCOPE='fixed_band_b0_native_FD_energy_coordinate_device'
METADATA=dict(device_state_owner='C++ DeviceSimulator',device_mesh_mode='explicit_cells',
    device_transaction='independently_audited_prepare_commit',legacy_StructuredGrid_integrated=False)


def audit_device_energy_coordinate_step(model,old,new,report,**budgets):
    extras=set(METADATA)
    expected={'scope','dt_s','raw','shared_max_nfev','complete_device_energy','physical_validated',
              'native_device_session_integrated'}|extras
    if set(report)-{'independent_audit'}!=expected:raise ValueError('exact device report coverage required')
    if (report['scope']!=DEVICE_SCOPE or report['native_device_session_integrated'] is not True or
        any(report[k]!=v or type(report[k]) is not type(v) for k,v in METADATA.items())):
        raise ValueError('invalid energy-coordinate device transaction scope')
    # Reuse the mathematical step schema without weakening its existing rule
    # that a standalone functional step cannot claim native device ownership.
    mathematical={k:v for k,v in report.items() if k not in extras}
    mathematical['scope']=SCOPE;mathematical['native_device_session_integrated']=False
    checked=audit_energy_coordinate_step(model,old,new,mathematical,**budgets)
    return dict(checked,native_device_session_integrated=True)
