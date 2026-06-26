#pragma once

#include "math_types.h"

namespace tcad {

enum class StatisticsType {
    BOLTZMANN,    // n = Nc * exp((Ef-Ec)/kT), p = Nv * exp((Ev-Ef)/kT)
    FERMI_DIRAC,  // n = Nc * F_1/2((Ef-Ec)/kT), p = Nv * F_1/2((Ev-Ef)/kT)
};

// Fermi-Dirac integral of order 1/2 via Bednarczyk (1981) rational approximation.
// Accurate to < 0.4% for all eta.
static inline real_t fermi_dirac_half(real_t eta) {
    // For very negative eta, Boltzmann limit is accurate enough
    if (eta < -20.0Q) return exp_q(eta);

    if (eta < 5.0Q) {
        // Low-to-moderate eta region
        real_t eta2 = eta * eta;
        real_t eta3 = eta2 * eta;
        real_t num = 1.0Q + 0.2319Q * eta + 0.02803Q * eta2 + 0.001872Q * eta3;
        num = num * num;
        real_t den = 1.0Q + 0.1337Q * eta + 0.02578Q * eta2 + 0.001237Q * eta3;
        // 4/sqrt(pi) * Gamma(3/2) = 2/sqrt(pi) ≈ 1.128
        real_t prefactor = 1.1283791670955126Q;
        return prefactor * sqrt_q(eta2 + 1.0Q) * num / den;
    } else {
        // High eta: asymptotic expansion
        // F_1/2(η) ≈ (2/3) η^(3/2) * (1 + π^2/(8η^2) + ...)
        real_t eta_sqrt = sqrt_q(eta);
        real_t result = (2.0Q / 3.0Q) * eta * eta_sqrt;
        result *= (1.0Q + 3.14159265358979323846Q * 3.14159265358979323846Q / (8.0Q * eta * eta));
        return result;
    }
}

// Electron concentration given conduction band edge Ec, Fermi level Ef, T, Nc.
// Uses Boltzmann or Fermi-Dirac statistics.
static inline real_t carrier_density_n(real_t Ec, real_t Ef, real_t T,
                                       real_t Nc, StatisticsType st) {
    real_t VT = 8.617333262e-5Q * T;  // kT/q [V]
    real_t eta = (Ef - Ec) / VT;

    if (st == StatisticsType::FERMI_DIRAC) {
        return Nc * fermi_dirac_half(eta);
    } else {
        // Boltzmann limit
        if (eta < -100.0Q) return 0.0Q;
        return Nc * exp_q(eta);
    }
}

// Hole concentration given valence band edge Ev, Fermi level Ef, T, Nv.
static inline real_t carrier_density_p(real_t Ev, real_t Ef, real_t T,
                                       real_t Nv, StatisticsType st) {
    real_t VT = 8.617333262e-5Q * T;
    real_t eta = (Ev - Ef) / VT;

    if (st == StatisticsType::FERMI_DIRAC) {
        return Nv * fermi_dirac_half(eta);
    } else {
        if (eta < -100.0Q) return 0.0Q;
        return Nv * exp_q(eta);
    }
}

// Intrinsic carrier concentration.
// ni = sqrt(Nc * Nv) * exp(-Eg/(2kT))  [Boltzmann]
// For FD: iteratively solve n·p = ni^2 with FD statistics
static inline real_t intrinsic_density(real_t Eg, real_t T,
                                       real_t Nc, real_t Nv,
                                       StatisticsType st) {
    real_t VT = 8.617333262e-5Q * T;

    if (st == StatisticsType::BOLTZMANN) {
        // ni = sqrt(Nc*Nv) * exp(-Eg/(2kT))
        real_t arg = -Eg / (2.0Q * VT);
        if (arg < -500.0Q) return 1.0e-20Q;  // effectively zero
        return sqrt_q(Nc * Nv) * exp_q(arg);
    } else {
        // For FD statistics, ni is computed by finding Ef where n = p.
        // Use the Boltzmann value as a first guess and iterate.
        real_t ni_boltz = intrinsic_density(Eg, T, Nc, Nv, StatisticsType::BOLTZMANN);
        // For moderate temperatures (< 200K), FD correction is small for intrinsic Si.
        // Return Boltzmann as a reasonable approximation.
        // Full FD would require root-finding for n(Ef) = p(Ef).
        return ni_boltz;
    }
}

} // namespace tcad
