#pragma once
#include "sparse_matrix.h"
#include <algorithm>
#include <map>

namespace tcad {
// Steady, one-dimensional SG chain with one reservoir per active component.
// Keep the two face coefficients separate: summing them into a diagonal before
// elimination can erase the weak reservoir coupling in a strongly inverted MOS.
// Row i is weight[i]*(flux[i]-flux[i-1])=rhs[i], with
// flux[i]=from[i]*density[i]-to[i]*density[i+1]. Reflecting endpoints have flux=0.
// Sources and their implicit reaction sinks are retained, including SRH and
// optical/BTBT contributions. The sink vector includes the source-cell width.
inline bool solve_single_reservoir_chain(
        const SparseMatrix& matrix, const Vector& rhs, const Vector& mobility,
        const std::map<size_t,real_t>& reservoirs, const Vector& from,
        const Vector& to, const Vector& weight, const Vector& sink,
        real_t residual_gate, Vector& output) {
    const size_t N=matrix.rows();
    if (N<2 || rhs.size()!=N || mobility.size()!=N || from.size()!=N ||
        to.size()!=N || weight.size()!=N || sink.size()!=N) return false;
    Vector candidate(N,EPSILON);
    for(real_t value:mobility) if(!isfinite_q(value) || value<0) return false;
    for (const auto& bc:reservoirs) {
        if (bc.first>=N || !isfinite_q(bc.second) || bc.second<0) return false;
        candidate[bc.first]=bc.second;
    }
    for (size_t begin=0;begin<N;) {
        if (mobility[begin]<EPSILON) { ++begin;continue; }
        size_t end=begin;
        while(end+1<N && mobility[end+1]>=EPSILON) ++end;
        size_t contact=N,contacts=0;
        for(size_t i=begin;i<=end;++i) if(reservoirs.count(i)) {contact=i;++contacts;}
        if(contacts!=1) return false;
        for(size_t i=begin;i<end;++i)
            if(!isfinite_q(from[i]) || !isfinite_q(to[i]) || from[i]<=0 || to[i]<=0)
                return false;
        for(size_t i=begin;i<=end;++i)
            if(i!=contact && (!isfinite_q(weight[i]) || weight[i]<=0 || !isfinite_q(rhs[i]) || !isfinite_q(sink[i]) || sink[i]<0))
                return false;
        // Eliminate each reflecting half-chain toward the fixed reservoir.
        // W*(flux[i]-flux[i-1]) + sink[i]*density[i] = rhs[i].
        // Preserve the sink separately; subtracting face coefficients from
        // an assembled diagonal can erase a small but resolved SRH term.
        Vector ratio(end-begin+1,0), offset(end-begin+1,0);
        real_t incoming_constant=0, incoming_sink=0;
        for(size_t i=begin;i<contact;++i) {
            const real_t reaction=incoming_sink+sink[i]/weight[i];
            const real_t source=incoming_constant+rhs[i]/weight[i];
            const real_t diagonal=from[i]+reaction;
            ratio[i-begin]=to[i]/diagonal;
            offset[i-begin]=source/diagonal;
            incoming_constant=from[i]*offset[i-begin];
            incoming_sink=to[i]*(reaction/diagonal);
        }
        for(size_t i=contact;i>begin;--i)
            candidate[i-1]=ratio[i-1-begin]*candidate[i]+offset[i-1-begin];
        incoming_constant=0;incoming_sink=0;
        for(size_t i=end;i>contact;--i) {
            const size_t edge=i-1;
            const real_t reaction=incoming_sink+sink[i]/weight[i];
            const real_t source=incoming_constant+rhs[i]/weight[i];
            const real_t diagonal=to[edge]+reaction;
            ratio[i-begin]=from[edge]/diagonal;
            offset[i-begin]=source/diagonal;
            incoming_constant=to[edge]*offset[i-begin];
            incoming_sink=from[edge]*(reaction/diagonal);
        }
        for(size_t i=contact;i<end;++i)
            candidate[i+1]=ratio[i+1-begin]*candidate[i]+offset[i+1-begin];
        begin=end+1;
    }
    for(real_t value:candidate) if(!isfinite_q(value) || value<0) return false;
    // Audit the actual assembled equations too; unsupported or inconsistent
    // input is transactional and falls back to the general linear solver.
    const Vector applied=matrix.apply(candidate);
    const auto& rows=matrix.row_offsets();const auto& cols=matrix.col_indices();
    const auto& values=matrix.vals();
    for(size_t i=0;i<N;++i) {
        real_t scale=abs_q(rhs[i]);
        for(size_t k=rows[i];k<rows[i+1];++k) scale+=abs_q(values[k]*candidate[cols[k]]);
        const real_t error=abs_q(applied[i]-rhs[i])/std::max(scale,TCAD_CONST(1.0));
        if(!isfinite_q(error) || error>residual_gate) return false;
    }
    output=std::move(candidate);return true;
}
} // namespace tcad
