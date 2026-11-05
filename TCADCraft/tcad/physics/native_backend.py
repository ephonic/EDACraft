"""Small, explicit bridge for native statistics and silicon multi-valley setup."""


def configure_native_multivalley(simulator, *, statistics="fermi_dirac", enable=True,
                                 longitudinal_mass=0.916, transverse_mass=0.190,
                                 subbands=4):
    """Configure the existing C++/Cython backend and return an audit record.

    This only configures native state; it does not claim that a thermionic
    interface or a complete device energy ledger has been solved.
    """
    if statistics not in ("boltzmann", "fermi_dirac"):
        raise ValueError("statistics must be boltzmann or fermi_dirac")
    required = ("set_statistics_type", "set_density_gradient_silicon_multivalley")
    if any(not hasattr(simulator, name) for name in required):
        raise TypeError("simulator does not expose the native statistics/multivalley API")
    if not isinstance(enable, bool):
        raise ValueError("enable must be boolean")
    simulator.set_statistics_type(1 if statistics == "fermi_dirac" else 0)
    simulator.set_density_gradient_silicon_multivalley(
        enable, longitudinal_mass, transverse_mass, subbands)
    return dict(native_backend_configured=True, statistics=statistics,
                silicon_multivalley=enable,
                longitudinal_mass=float(longitudinal_mass),
                transverse_mass=float(transverse_mass), subbands=int(subbands),
                thermionic_interface_coupled=False,
                complete_device_energy=False, physical_validated=False)
