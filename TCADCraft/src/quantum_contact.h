#pragma once
#include <map>
#include <vector>
#include "math_types.h"

namespace tcad { namespace detail {
// Match Gummel and returned currents: a carrier Dirichlet contact pins
// only that species' DG transport correction, including after Picard mixing.
inline void pin_quantum_contacts(
    const std::map<size_t, real_t>& electron_contacts,
    const std::map<size_t, real_t>& hole_contacts,
    std::vector<real_t>& Qn, std::vector<real_t>& Qp) {
    for (const auto& bc : electron_contacts) Qn[bc.first] = TCAD_CONST(0.0);
    for (const auto& bc : hole_contacts) Qp[bc.first] = TCAD_CONST(0.0);
}
}}
