#include "mobility_model.h"
#include "math_types.h"

namespace tcad {

// Arora model parameters (Si, from Arora et al. 1982)
// Electrons
static constexpr real_t ARORA_N_UN = TCAD_CONST(9.68e16);   // N_ref [cm^-3]
static constexpr real_t ARORA_ALPHA_N = TCAD_CONST(0.68);
static constexpr real_t ARORA_BETA_N = -TCAD_CONST(0.66);    // T exponent
static constexpr real_t ARORA_MIN_N = TCAD_CONST(52.2);      // μ_min [cm^2/Vs]
static constexpr real_t ARORA_MAX_N = TCAD_CONST(1417.0);    // μ_max [cm^2/Vs] at 300K
// Holes
static constexpr real_t ARORA_N_UP = TCAD_CONST(2.23e17);
static constexpr real_t ARORA_ALPHA_P = TCAD_CONST(0.72);
static constexpr real_t ARORA_BETA_P = -TCAD_CONST(2.05);
static constexpr real_t ARORA_MIN_P = TCAD_CONST(49.9);
static constexpr real_t ARORA_MAX_P = TCAD_CONST(470.5);

// Low-temperature model parameters
static constexpr real_t LT_PH_N_0 = TCAD_CONST(1400.0);      // μ_ph0 electrons [cm^2/Vs]
static constexpr real_t LT_PH_P_0 = TCAD_CONST(450.0);       // μ_ph0 holes [cm^2/Vs]
static constexpr real_t LT_IMP_N_0 = TCAD_CONST(1.0e17);     // μ_imp0 electrons [cm^2/Vs·cm^3]
static constexpr real_t LT_IMP_P_0 = TCAD_CONST(1.0e17);     // μ_imp0 holes [cm^2/Vs·cm^3]

static real_t power_q(real_t base, real_t exp) {
    return pow_q(base, exp);
}

real_t evaluate_mobility(MobilityModelType type,
                         bool is_n_type,
                         real_t T,
                         real_t Nd,
                         real_t Na,
                         real_t mu_const) {
    if (type == MobilityModelType::CONSTANT) {
        return mu_const;
    }

    // Total doping concentration for scattering
    real_t N_total = Nd + Na;
    // Convert from m^-3 to cm^-3 for model parameters
    real_t N_cm3 = N_total * TCAD_CONST(1.0e-6);

    if (type == MobilityModelType::ARORA) {
        // μ(T,N) = μ_min + (μ_max-μ_min)/(1+(N/N_ref)^α) · (T/300)^β
        real_t mu_min, mu_max, n_ref, alpha, beta;
        if (is_n_type) {
            mu_min = ARORA_MIN_N;
            mu_max = ARORA_MAX_N;
            n_ref = ARORA_N_UN;
            alpha = ARORA_ALPHA_N;
            beta = ARORA_BETA_N;
        } else {
            mu_min = ARORA_MIN_P;
            mu_max = ARORA_MAX_P;
            n_ref = ARORA_N_UP;
            alpha = ARORA_ALPHA_P;
            beta = ARORA_BETA_P;
        }

        real_t dop_factor = (mu_max - mu_min) / (TCAD_CONST(1.0) + power_q(N_cm3 / n_ref, alpha));
        real_t temp_factor = power_q(T / TCAD_CONST(300.0), beta);
        // Result in cm^2/Vs, convert to m^2/Vs
        return (mu_min + dop_factor * temp_factor) * TCAD_CONST(1.0e-4);
    }

    // LOW_TEMP: Matthiessen's rule
    // 1/μ = 1/μ_ph + 1/μ_imp
    // μ_ph = μ_ph0 · (T/300)^(-1.5)  (phonon scattering decreases at low T)
    // μ_imp = μ_imp0 · T^(1.5) / N_d  (impurity scattering increases at low T)
    real_t mu_ph0 = is_n_type ? LT_PH_N_0 : LT_PH_P_0;
    real_t mu_imp0 = is_n_type ? LT_IMP_N_0 : LT_IMP_P_0;

    real_t mu_ph = mu_ph0 * power_q(T / TCAD_CONST(300.0), -TCAD_CONST(1.5));

    real_t n_doping = is_n_type ? Nd : Na;
    real_t n_doping_cm3 = n_doping * TCAD_CONST(1.0e-6);
    real_t mu_imp = (n_doping_cm3 > 1.0)
        ? mu_imp0 * power_q(T, TCAD_CONST(1.5)) / n_doping_cm3
        : mu_ph * TCAD_CONST(1.0e6);  // avoid division by zero

    real_t mu_inv = TCAD_CONST(1.0) / mu_ph + TCAD_CONST(1.0) / mu_imp;
    // Result in cm^2/Vs, convert to m^2/Vs
    return (TCAD_CONST(1.0) / mu_inv) * TCAD_CONST(1.0e-4);
}

} // namespace tcad
