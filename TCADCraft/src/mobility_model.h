#pragma once

#include "math_types.h"
#include <vector>

namespace tcad {

enum class MobilityModelType {
    CONSTANT,   // User-provided constant mobility (default)
    ARORA,      // Arora model: temperature + doping dependent
    LOW_TEMP,   // Low-temperature model: phonon + impurity scattering
};

// Evaluate mobility for a given node.
// For CONSTANT: returns mu_const (user input).
// For ARORA: μ(T,N) = μ_min + (μ_max-μ_min)/(1+(N/N_ref)^α) · (T/300)^β
// For LOW_TEMP: 1/μ = 1/μ_ph + 1/μ_imp (Matthiessen's rule)
real_t evaluate_mobility(MobilityModelType type,
                         bool is_n_type,    // true = electron, false = hole
                         real_t T,          // temperature [K]
                         real_t Nd,         // donor concentration [m^-3]
                         real_t Na,         // acceptor concentration [m^-3]
                         real_t mu_const);  // base mobility for CONSTANT model

} // namespace tcad
