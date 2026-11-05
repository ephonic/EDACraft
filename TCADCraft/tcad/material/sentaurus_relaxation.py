"""Export explicit constitutive controls to the installed Sentaurus standard PMI.

ReadScalar dependencies on lattice T and density have no complete PMI Jacobian.
Successful commercial solves and independent observations are still required;
generating a source file does not calibrate or qualify any physical material.
"""
import numpy as np
from .energy_relaxation import EnergyRelaxationPowerLaw


def sentaurus_relaxation_pmi_source(*, electron_tau0_s, hole_tau0_s,
                                   electron_law, hole_law):
    """Return C++ source for both EnergyRelaxationTime constructors.

    Inputs use SI, including density in m^-3. ReadScalar eDensity/hDensity
    values use cm^-3 and are converted explicitly. Compile with vendor cmi,
    select EnergyRelaxationTimes(model_name), and set File PMIPath explicitly.
    The ct derivative is supplied; added ReadScalar dependencies have the
    vendor's experimental-interface derivative/convergence limitations.
    Nonpositive/nonfinite runtime states fail; there is no density floor.
    """
    rows=[]
    for carrier,tau,law,field in (
            ('e',electron_tau0_s,electron_law,'eDensity'),
            ('h',hole_tau0_s,hole_law,'hDensity')):
        a=np.asarray(tau)
        if (a.ndim or a.dtype.kind not in 'fiu' or not np.isfinite(a)
                or not 0<float(a)<np.inf):
            raise ValueError('positive finite reference relaxation time required')
        if type(law) is not EnergyRelaxationPowerLaw:
            raise ValueError('explicit immutable EnergyRelaxationPowerLaw required')
        Tref,nref,alpha,beta,gamma=law.parameters()
        rows.append(f'''
class Relaxation_{carrier} : public PMI_EnergyRelaxationTime {{
public:
  explicit Relaxation_{carrier}(const PMI_Environment& env) : PMI_EnergyRelaxationTime(env) {{}}
  void Compute_tau(const double ct, double& tau) override {{
    const double Tl = ReadScalar("LatticeTemperature");
    const double density_cm3 = ReadScalar("{field}");
    if (!std::isfinite(ct) || !std::isfinite(Tl) || !std::isfinite(density_cm3) ||
        ct <= 0 || Tl <= 0 || density_cm3 <= 0)
      throw std::domain_error("positive finite local relaxation state required");
    // Difference of logs avoids overflow in the SI density conversion/ratios.
    const double exponent = std::log({float(a):.17g}) +
      ({alpha:.17g})*(std::log(Tl)-std::log({Tref:.17g})) +
      ({beta:.17g})*(std::log(ct)-std::log({Tref:.17g})) +
      ({gamma:.17g})*(std::log(density_cm3)+std::log(1e6)-std::log({nref:.17g}));
    tau = std::exp(exponent);
    if (!std::isfinite(tau) || tau <= 0)
      throw std::domain_error("effective relaxation time outside positive double range");
  }}
  void Compute_dtaudct(const double ct, double& derivative) override {{
    double tau; Compute_tau(ct,tau);
    derivative = ({beta:.17g})*(tau/ct);
    if (!std::isfinite(derivative))
      throw std::domain_error("relaxation derivative outside finite double range");
  }}
}};
extern "C" PMI_EnergyRelaxationTime* new_PMI_{carrier}_EnergyRelaxationTime(const PMI_Environment& env) {{
  return new Relaxation_{carrier}(env);
}}
''')
    return '#include "PMIModels.h"\n#include <cmath>\n#include <stdexcept>\n'+''.join(rows)
