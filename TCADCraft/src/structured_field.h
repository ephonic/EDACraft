#pragma once

#include <cstddef>
#include <vector>
#include "math_types.h"

namespace tcad {

// Minus the derivative of the quadratic interpolant at an interior node.
// Boundary nodes retain the first-order, one-sided field convention. The
// implicit uniform-grid branch preserves the original arithmetic exactly.
template<class Potential>
inline real_t structured_node_field(const Potential& phi,
    size_t idx, size_t node, size_t stride, size_t count,
    const std::vector<real_t>& positions, real_t uniform_h) {
    if (count <= 1) return TCAD_CONST(0.0);
    if (positions.empty()) {
        if (node > 0 && node + 1 < count)
            return -(phi[idx+stride]-phi[idx-stride]) / (TCAD_CONST(2.0)*uniform_h);
        if (node + 1 < count)
            return -(phi[idx+stride]-phi[idx]) / uniform_h;
        return -(phi[idx]-phi[idx-stride]) / uniform_h;
    }
    if (node == 0)
        return -(phi[idx+stride]-phi[idx]) / (positions[1]-positions[0]);
    if (node + 1 == count)
        return -(phi[idx]-phi[idx-stride]) / (positions[node]-positions[node-1]);
    const real_t hm = positions[node]-positions[node-1];
    const real_t hp = positions[node+1]-positions[node];
    if (hm == hp)
        return -(phi[idx+stride]-phi[idx-stride]) / (TCAD_CONST(2.0)*hm);
    const real_t left = (phi[idx]-phi[idx-stride])/hm;
    const real_t right = (phi[idx+stride]-phi[idx])/hp;
    return -(hp*left + hm*right)/(hm+hp);
}

// Visit the nonzero potential coefficients of the same linear field stencil.
// Keeping indices in the callback avoids allocating per-node sparse vectors.
template<class Visitor>
inline void structured_node_field_weights(size_t idx, size_t node,
    size_t stride, size_t count, const std::vector<real_t>& positions,
    real_t uniform_h, Visitor visit) {
    if (count <= 1) return;
    if (node == 0) {
        const real_t h = positions.empty() ? uniform_h : positions[1]-positions[0];
        visit(idx, TCAD_CONST(1.0)/h);
        visit(idx+stride, -TCAD_CONST(1.0)/h);
    } else if (node+1 == count) {
        const real_t h = positions.empty() ? uniform_h : positions[node]-positions[node-1];
        visit(idx-stride, TCAD_CONST(1.0)/h);
        visit(idx, -TCAD_CONST(1.0)/h);
    } else {
        const real_t hm = positions.empty() ? uniform_h : positions[node]-positions[node-1];
        const real_t hp = positions.empty() ? uniform_h : positions[node+1]-positions[node];
        const real_t left = hp/(hm*(hm+hp));
        const real_t right = -hm/(hp*(hm+hp));
        visit(idx-stride, left);
        visit(idx, -(left+right));
        visit(idx+stride, right);
    }
}

} // namespace tcad
