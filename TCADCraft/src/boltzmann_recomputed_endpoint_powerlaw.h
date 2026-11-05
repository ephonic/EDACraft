#pragma once
#include "boltzmann_recomputed_endpoint_collision.h"
namespace tcad {
// Bounded nonlinear collision and exact clock candidate. Original endpoint is
// immutable; output contains a final compact proof, not a production commit.
inline std::vector<std::string> native_mb_recomputed_endpoint_powerlaw_raw(
    const std::vector<std::string>& endpoint,const std::vector<std::string>& command,
    const std::vector<std::string>& clock) {
    using namespace mb_scaled_powerlaw_detail;
    namespace old=mb_affine_detail;
    auto p=mb_scaled_transport_detail::decode(endpoint);mb_scaled_transport_detail::valid(p);
    const auto f=fermi_local_detail::decimals(p.frame),c=fermi_local_detail::decimals(command);
    if(c.size()!=18)throw std::invalid_argument("scaled powerlaw command/clock coverage");
    for(real_t x:c)old::bounded(x);
    if(!(c[14]>0 && c[2]>0 && c[3]>0 && c[4]>0 && c[5]>0 && c[8]>0 && c[9]>0))
        throw std::invalid_argument("positive scaled powerlaw references required");
    if(c[0]!=f[3] || c[1]!=f[4] || c[12]!=f[7] || c[13]!=f[8])
        throw std::invalid_argument("scaled powerlaw frame configuration mismatch");
    for(size_t j:{size_t(6),size_t(7),size_t(10),size_t(11)})
        if(abs_q(c[j])>8)throw std::invalid_argument("scaled powerlaw requires abs(a,c)<=8; extreme stiffness unsupported");
    const auto start=ar::read(clock),dt=scalar(c[14]),end=ar::plus(start,dt);
    if(start.sign<0 || ar::plus(end,start,-1).sign<=0)
        throw std::invalid_argument("nonnegative advancing scaled clock required");
    if(ar::write(start)!=clock)throw std::invalid_argument("canonical exact endpoint root clock required");
    const auto cv=scalar(f[3]),one=scalar(1);
    const auto old_lattice=p.v[0];
    const auto baseline=multiply(scalar(f[2]),cv);
    auto temperature=[&](I increment) {
        return real113(ar::rounded_ratio(ar::plus(ar::plus(baseline,old_lattice),increment),cv));
    };
    std::vector<I> density;
    for(size_t k=0;k<2;++k)density.push_back(ar::plus(scalar(f[k]),p.v[3+k]));
    std::vector<real_t> trace,chosenTau;
    std::vector<std::string> chosenProof;real_t chosenT=0;size_t evaluations=0;
    auto evaluate=[&](real_t T) {
        if(!(T>=f[7] && T<=f[8]) || ++evaluations>256)
            throw std::invalid_argument("scaled powerlaw bounded temperature root exhausted");
        std::vector<real_t> tau;
        for(size_t k=0;k<2;++k) {
            const size_t j=k?8:4;
            const auto head=ar::rounded_ratio(density[k],one),low=ar::plus(density[k],head,-1);
            const real_t h=real113(head),correction=real113(ar::rounded_ratio(low,head));
            const real_t ratio=h/c[j+1],tr=T/c[j];
            old::bounded(correction);old::bounded(ratio);old::bounded(tr);
            if(!(ratio>0 && tr>0))throw std::invalid_argument("scaled powerlaw logarithm ratio range");
            #ifdef TCAD_USE_FLOAT128
            const real_t logn=log_q(ratio)+log1pq(correction);
            #else
            const real_t logn=log_q(ratio)+std::log1p(correction);
            #endif
            const real_t value=exp_q(log_q(c[k+2])+c[j+2]*log_q(tr)+c[j+3]*logn);
            old::bounded(value);
            if(!(value/c[14]>=TCAD_CONST(1e-3) && value/c[14]<=TCAD_CONST(1e3)))
                throw std::invalid_argument("scaled powerlaw requires 1e-3<=tau/dt<=1e3; extreme stiffness unsupported");
            tau.push_back(value);
        }
        const auto args=boltzmann_detail::exported({c[14],tau[0],tau[1],c[15],c[16],c[17]});
        auto proof=native_mb_recomputed_endpoint_collision_compact_raw(endpoint,args);
        if(proof[2]!="complete")throw std::invalid_argument("endpoint collision evidence budget exceeded at "+proof[7]+" requested "+proof[8]);
        auto legacy=proof;legacy[0]="mb_scaled_collision_compact_v1";const auto values=aggregates(legacy);
        const real_t actualT=temperature(values[0]);
        if(!(actualT>=f[7] && actualT<=f[8]))throw std::invalid_argument("scaled root candidate lattice outside bounds");
        trace.insert(trace.end(),{T,tau[0],tau[1],actualT});chosenT=T;chosenTau=tau;chosenProof=std::move(proof);
        return actualT-T;
    };
    const real_t tolerance=8*epsilon_q()*std::max(real_t(1),std::max(abs_q(f[7]),abs_q(f[8])));
    real_t x=temperature({}),res=evaluate(x);bool done=abs_q(res)<=tolerance;
    for(size_t i=0;i<48 && !done;++i){x+=res;res=evaluate(x);done=abs_q(res)<=tolerance;}
    if(!done) {
        real_t lo=f[7],hi=f[8],fl=evaluate(lo),fh=evaluate(hi);
        if(fl==0){evaluate(lo);done=true;}
        else if(fh==0)done=true;
        else {
            if((fl>0)==(fh>0))throw std::invalid_argument("scaled powerlaw root not bracketed");
            while(!done && evaluations<256) {
                x=lo+(hi-lo)/2;res=evaluate(x);done=abs_q(res)<=tolerance;
                if((res>0)==(fl>0)){lo=x;fl=res;}else {hi=x;fh=res;}
            }
        }
    }
    if(!done)throw std::invalid_argument("scaled powerlaw root did not converge");
    const auto beginWire=ar::write(start),endWire=ar::write(end);
    const size_t evidence=trace.size()+ar::count(chosenProof[5],4096)+
        ar::count(beginWire[2],4096)+ar::count(endWire[2],4096);
    if(evidence>4096)throw std::invalid_argument("scaled powerlaw combined saved evidence budget exceeded");
    auto scalarHeader=boltzmann_detail::exported({chosenT,chosenTau[0],chosenTau[1]});
    std::vector<std::string> out={"mb_recomputed_endpoint_powerlaw_v1","113",std::to_string(evaluations)};
    out.insert(out.end(),scalarHeader.begin(),scalarHeader.end());out.push_back(std::to_string(evidence));
    const auto history=boltzmann_detail::exported(trace);out.insert(out.end(),history.begin(),history.end());
    const std::vector<const std::vector<std::string>*> packets={&beginWire,&endWire,&chosenProof};
    for(const auto* wire:packets) {
        out.push_back(std::to_string(wire->size()));out.insert(out.end(),wire->begin(),wire->end());
    }
    return out;
}
} // namespace tcad

namespace tcad {
inline std::vector<std::string> native_mb_recomputed_endpoint_apply_raw(const std::vector<std::string>& endpoint,
    const std::vector<std::string>& L,const std::vector<std::string>& un,const std::vector<std::string>& up) {
    using namespace mb_scaled_transport_detail;
    auto p=decode(endpoint);const std::vector<I> increments={ar::read(L),ar::read(un),ar::read(up)};
    for(size_t k=0;k<3;++k)if(ar::write(increments[k])!=std::vector<std::vector<std::string>>{L,un,up}[k])
        throw std::invalid_argument("canonical endpoint collision increment required");
    p.v[0]=ar::plus(p.v[0],increments[0]);p.v[5]=ar::plus(p.v[5],increments[1]);p.v[6]=ar::plus(p.v[6],increments[2]);
    valid(p);return emit(p);
}
}
