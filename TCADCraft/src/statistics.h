#pragma once

#include "math_types.h"
#include <stdexcept>

namespace tcad {

enum class StatisticsType {
    BOLTZMANN,    // n = Nc * exp((Ef-Ec)/kT), p = Nv * exp((Ev-Ef)/kT)
    FERMI_DIRAC,  // n = Nc * F_1/2((Ef-Ec)/kT), p = Nv * F_1/2((Ev-Ef)/kT)
};

// Normalized F_{1/2}(eta) = 2/sqrt(pi) integral sqrt(t)/(1+exp(t-eta)) dt.
// Bednarczyk & Bednarczyk, Phys. Lett. A 64 (1978), 409-410,
// doi:10.1016/0375-9601(78)90283-9. Relative approximation error < 0.4%.
// This is an approximation to the integral, not an exact FD device model.
static inline real_t fermi_dirac_half(real_t eta) {
    // Here the correction to exp(eta) is below real_t roundoff. Avoid both
    // exp(-eta) overflow and unnecessary powers for very negative arguments.
    if (eta < -TCAD_CONST(80.0)) return exp_q(eta);
    const real_t prefactor = TCAD_CONST(0.75) * sqrt_q(PI);
    const real_t gaussian = eta > TCAD_CONST(64.0) ? TCAD_CONST(0.0) :
        exp_q(-TCAD_CONST(0.17) * (eta + 1) * (eta + 1));
    const real_t linear = TCAD_CONST(33.6) * (1 - TCAD_CONST(0.68) * gaussian);
    real_t correction;
    if (eta >= TCAD_CONST(1.0)) {
        // Factor eta^4 out of nu before taking nu^(-3/8). This avoids
        // overflowing the quartic when F_{1/2} itself is representable.
        const real_t inverse = 1 / eta;
        const real_t scaled = 1 + inverse * inverse * inverse *
            (linear + TCAD_CONST(50.0) * inverse);
        correction = prefactor * inverse * sqrt_q(inverse) *
            pow_q(scaled, -TCAD_CONST(0.375));
    } else {
        const real_t eta2 = eta * eta;
        const real_t nu = eta2 * eta2 + TCAD_CONST(50.0) + eta * linear;
        correction = prefactor * pow_q(nu, -TCAD_CONST(0.375));
    }
    return 1 / (exp_q(-eta) + correction);
}

// Electron concentration given conduction band edge Ec, Fermi level Ef, T, Nc.
// Uses Boltzmann or Fermi-Dirac statistics.
static inline real_t carrier_density_n(real_t Ec, real_t Ef, real_t T,
                                       real_t Nc, StatisticsType st) {
    real_t VT = TCAD_CONST(8.617333262e-5) * T;  // kT/q [V]
    real_t eta = (Ef - Ec) / VT;

    if (st == StatisticsType::FERMI_DIRAC) {
        return Nc * fermi_dirac_half(eta);
    } else {
        // Boltzmann limit
        if (eta < -TCAD_CONST(100.0)) return TCAD_CONST(0.0);
        return Nc * exp_q(eta);
    }
}

// Hole concentration given valence band edge Ev, Fermi level Ef, T, Nv.
static inline real_t carrier_density_p(real_t Ev, real_t Ef, real_t T,
                                       real_t Nv, StatisticsType st) {
    real_t VT = TCAD_CONST(8.617333262e-5) * T;
    real_t eta = (Ev - Ef) / VT;

    if (st == StatisticsType::FERMI_DIRAC) {
        return Nv * fermi_dirac_half(eta);
    } else {
        if (eta < -TCAD_CONST(100.0)) return TCAD_CONST(0.0);
        return Nv * exp_q(eta);
    }
}

// Intrinsic carrier concentration.
// ni = sqrt(Nc * Nv) * exp(-Eg/(2kT))  [Boltzmann]
// For FD: find the common equilibrium Fermi level where n = p = ni.
static inline real_t intrinsic_density(real_t Eg, real_t T,
                                       real_t Nc, real_t Nv,
                                       StatisticsType st) {
    real_t VT = TCAD_CONST(8.617333262e-5) * T;

    if (st == StatisticsType::BOLTZMANN) {
        // ni = sqrt(Nc*Nv) * exp(-Eg/(2kT))
        real_t arg = -Eg / (TCAD_CONST(2.0) * VT);
        if (arg < -TCAD_CONST(500.0)) return TCAD_CONST(1.0e-20);  // effectively zero
        return sqrt_q(Nc * Nv) * exp_q(arg);
    } else {
        if (!isfinite_q(Eg) || !isfinite_q(T) || T <= 0 ||
            !isfinite_q(Nc) || !isfinite_q(Nv) || Nc <= 0 || Nv <= 0 ||
            !isfinite_q(VT) || VT <= 0)
            throw std::invalid_argument("FD intrinsic density requires finite energies, positive temperature and DOS");
        const real_t gap = Eg / VT;
        if (!isfinite_q(gap))
            throw std::invalid_argument("FD intrinsic normalized gap is not representable");
        const real_t ln_c = log_q(Nc), ln_v = log_q(Nv);
        const real_t middle = -gap / 2, ratio = ln_v - ln_c;
        // Work in logarithms so Nc*Nv and the individual occupation factors
        // need not be representable. Match the same F_{1/2} approximation.
        auto log_half = [](real_t eta) {
            if (eta < -TCAD_CONST(80.0)) return eta;
            if (eta > TCAD_CONST(128.0)) {
                const real_t inv = 1 / eta;
                const real_t scaled = 1 + inv * inv * inv *
                    (TCAD_CONST(33.6) + TCAD_CONST(50.0) * inv);
                return TCAD_CONST(1.5) * log_q(eta) -
                    log_q(TCAD_CONST(.75) * sqrt_q(PI)) +
                    TCAD_CONST(.375) * log_q(scaled);
            }
            return log_q(fermi_dirac_half(eta));
        };
        auto density = [](real_t log_n) {
            const real_t value = exp_q(log_n);
            if (!isfinite_q(value))
                throw std::overflow_error("FD intrinsic density is not representable");
            return value; // A genuine floating-point underflow may return zero.
        };
        // Both species are in the exact exp tail of our approximation here.
        // Do not apply the historical Boltzmann branch's arbitrary ni floor.
        if (middle + abs_q(ratio) / 2 < -TCAD_CONST(80.0))
            return density(ln_c / 2 + ln_v / 2 + middle);
        auto balance = [&](real_t shift) {
            return (ln_c + log_half(middle + shift)) -
                   (ln_v + log_half(middle - shift));
        };
        const real_t radius = abs_q(middle) + abs_q(ratio) + 2;
        real_t lo = -radius, hi = radius;
        real_t f_lo = balance(lo), f_hi = balance(hi);
        if (!isfinite_q(f_lo) || !isfinite_q(f_hi) || f_lo > 0 || f_hi < 0)
            throw std::runtime_error("FD intrinsic neutrality could not be bracketed");
        real_t shift = ratio / 2;
        for (int iter = 0; iter < 512; ++iter) {
            const real_t log_n = ln_c + log_half(middle + shift);
            const real_t log_p = ln_v + log_half(middle - shift);
            const real_t error = log_n - log_p;
            const real_t tolerance = 32 * epsilon_q() * (1 + abs_q(log_n) + abs_q(log_p));
            if (isfinite_q(error) && abs_q(error) <= tolerance)
                return density(log_n / 2 + log_p / 2);
            if (!isfinite_q(error))
                throw std::runtime_error("FD intrinsic neutrality produced a nonfinite balance");
            if (error < 0) { lo = shift; f_lo = error; }
            else { hi = shift; f_hi = error; }
            // Secant accelerates the nearly Boltzmann regime; interleaved
            // bisection guarantees progress for strongly asymmetric DOS.
            real_t next = iter % 2 ? lo / 2 + hi / 2 :
                lo + (hi - lo) * (-f_lo / (f_hi - f_lo));
            if (!isfinite_q(next) || next <= lo || next >= hi || next == shift)
                next = lo / 2 + hi / 2;
            if (next == shift) break;
            shift = next;
        }
        throw std::runtime_error("FD intrinsic neutrality did not converge at scalar precision");
    }
}

} // namespace tcad
