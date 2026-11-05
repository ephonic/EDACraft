#pragma once
#include "boltzmann_spectral.h"

namespace tcad { namespace boltzmann_relaxation_detail {
inline real_t logistic(real_t x) {
    if(x>=0)return 1/(1+exp_q(-x));
    const real_t e=exp_q(x);return e/(1+e);
}
inline real_t softplus(real_t x) {
#ifdef TCAD_USE_FLOAT128
    return x>0?x+log1pq(exp_q(-x)):log1pq(exp_q(x));
#else
    return x>0?x+std::log1p(exp_q(-x)):std::log1p(exp_q(x));
#endif
}
inline real_t weighted(real_t logweight,real_t value) {
    if(value==0)return 0;
    // Near unity, a log/exp round trip of a microscopic value amplifies
    // rounding by |log(value)|. Multiply directly; retain the log product for
    // small weights whose standalone exponential can underflow.
    if(logweight>-1)return value*exp_q(logweight);
    const real_t magnitude=exp_q(log_q(abs_q(value))+logweight);
    return value>0?magnitude:-magnitude;
}
inline void equal_offsets(const std::vector<std::string>& raw) {
    const auto v=boltzmann_detail::valleys(raw);
    for(size_t j=3;j<v.size();j+=4)if(v[j]!=v[3])
        throw std::invalid_argument("MB relaxation requires equal valley offsets; split valleys are unsupported");
}
} // namespace boltzmann_relaxation_detail

// State: [n,p,Treference,lattice_base_density,delta_n,delta_p,L1,L2,...].
// Each accepted lattice increment is retained as an expansion component;
// adding a microscopic increment to the rounded temperature view loses no ledger energy. Carrier
// deltas are relative to the CURRENT lattice equilibrium, preserving stiff
// tails. initialize=true interprets the final three values as Tl,Tn,Tp.
// Parameters: Cv,V,tau0n,tau0p,Trefn,nrefn,a_n,c_n,Trefp,nrefp,a_p,c_p,
//             Tmin,Tmax,dt,energy_atol_J,Qn,Qp,Ql. b=0 only; fixed n/bands;
// all valleys within each carrier must have the same offset.
// Output: new state(old width+1), then 15 diagnostic decimals:
// Tl,Tn,Tp,exchange_n/p_J,du_n/p/l_J,r_n/p/l/global_J,log_tau_n/p,evaluations.
inline std::vector<std::string> native_boltzmann_relaxation_raw(
    const std::vector<std::string>& raw_state,const std::vector<std::string>& raw_parameters,
    const std::vector<std::string>& vn,const std::vector<std::string>& vp,
    bool initialize=false,int max_nfev=256) {
    using boltzmann_detail::exported;
    if(raw_state.size()<6 || raw_state.size()>4096 || (initialize && raw_state.size()!=6) || raw_parameters.size()!=19 || max_nfev<1 || max_nfev>4096)
        throw std::invalid_argument("MB relaxation state/parameter width or evaluation budget invalid");
    boltzmann_relaxation_detail::equal_offsets(vn);boltzmann_relaxation_detail::equal_offsets(vp);
    const auto s=fermi_local_detail::decimals(raw_state),p=fermi_local_detail::decimals(raw_parameters);
    for(size_t k:{0,1,2,3,4,5,8,9,14,15})if(!(p[k]>0))
        throw std::invalid_argument("positive MB relaxation scales required");
    if(!(s[0]>0 && s[1]>0 && s[2]>1 && s[2]<TCAD_CONST(1e5) && p[12]>1 && p[13]<TCAD_CONST(1e5) && p[12]<p[13]))
        throw std::invalid_argument("MB relaxation positive densities and open temperature bounds required");
    const real_t C[]={TCAD_CONST(1.5)*KB*s[0],TCAD_CONST(1.5)*KB*s[1]};
    if(!(C[0]>0 && C[1]>0) || !isfinite_q(C[0]) || !isfinite_q(C[1]))
        throw std::invalid_argument("representable MB carrier capacities required");
    auto inside=[&](real_t T){return isfinite_q(T) && T>=p[12] && T<=p[13];};
    if(initialize) {
        if(!inside(s[3]) || !inside(s[4]) || !inside(s[5]))throw std::invalid_argument("initial MB temperatures outside configured bounds");
        const real_t lattice=p[0]*(s[3]-s[2]),dn=C[0]*(s[4]-s[3]),dp=C[1]*(s[5]-s[3]);
        if((s[3]!=s[2] && lattice==0) || (s[4]!=s[3] && dn==0) || (s[5]!=s[3] && dp==0))
            throw std::invalid_argument("nonzero initial MB energy underflows");
        return exported({s[0],s[1],s[2],lattice,dn,dp});
    }
    real_t lattice=s[3];
    for(size_t k=6;k<s.size();++k)lattice+=s[k];
    if(!isfinite_q(lattice))throw std::invalid_argument("MB lattice expansion view range exceeded");
    const real_t oldTl=s[2]+lattice/p[0];
    if(!inside(oldTl) || !inside(oldTl+s[4]/C[0]) || !inside(oldTl+s[5]/C[1]))
        throw std::invalid_argument("MB relaxation initial energy state outside bounds");
    const real_t source[]={p[16]/p[1],p[17]/p[1],p[18]/p[1]},ratioC[]={C[0]/p[0],C[1]/p[0]};
    for(size_t k=0;k<3;++k)if(!isfinite_q(source[k]) || (p[16+k]!=0 && source[k]==0))
        throw std::invalid_argument("MB source density range exceeded");
    for(real_t x:ratioC)if(!(x>0) || !isfinite_q(x))throw std::invalid_argument("MB capacity ratio range exceeded");
    struct Trial {real_t increment,T,delta[2],exchange[2],logtau[2],residual,feedback;};
    int evaluations=0;
    auto evaluate=[&](real_t increment) {
        if(evaluations>=max_nfev)throw std::runtime_error("MB relaxation evaluation budget exhausted");
        ++evaluations;Trial r{};r.increment=increment;r.T=s[2]+(lattice+increment)/p[0];
        if(!inside(r.T))throw std::invalid_argument("MB lattice trial outside configured bounds");
        for(size_t k=0;k<2;++k) {
            const size_t b=4+4*k;
            r.logtau[k]=log_q(p[2+k])+p[b+2]*log_q(r.T/p[b])+p[b+3]*log_q(s[k]/p[b+1]);
            if(!isfinite_q(r.logtau[k]))throw std::invalid_argument("finite MB relaxation logarithm required");
            const real_t ratio=r.logtau[k]-log_q(p[14]);
            const real_t lr=-boltzmann_relaxation_detail::softplus(-ratio),ll=-boltzmann_relaxation_detail::softplus(ratio);
            const real_t drive=(s[4+k]+source[k])-ratioC[k]*increment;
            r.delta[k]=boltzmann_relaxation_detail::weighted(lr,drive);
            r.exchange[k]=boltzmann_relaxation_detail::weighted(ll,drive);
            r.feedback+=boltzmann_relaxation_detail::weighted(ll,ratioC[k]);
        }
        r.residual=p[1]*(increment-r.exchange[0]-r.exchange[1]-source[2]);
        if(!isfinite_q(r.residual))throw std::invalid_argument("finite MB relaxation residual required");
        return r;
    };
    Trial accepted=evaluate(0);
    const real_t scale=std::max({abs_q(p[1]*s[4]),abs_q(p[1]*s[5]),abs_q(p[16]),abs_q(p[17]),abs_q(p[18])});
    const real_t gate=scale>0?std::min(p[15]/8,128*epsilon_q()*scale):p[15]/8;
    // This proposal solves constant-tau exchange directly and preserves tiny
    // lattice increments rather than accepting the zero-increment seed just
    // because the configured absolute energy gate is larger than the signal.
    const real_t proposal=(accepted.exchange[0]+accepted.exchange[1]+source[2])/(1+accepted.feedback);
    const real_t proposalT=s[2]+(lattice+proposal)/p[0];
    if(inside(proposalT))accepted=evaluate(proposal);
    if(abs_q(accepted.residual)>gate) {
        real_t lo=p[0]*(p[12]-s[2])-lattice,hi=p[0]*(p[13]-s[2])-lattice;
        const auto left=evaluate(lo),right=evaluate(hi);
        if(left.residual>0 || right.residual<0)throw std::runtime_error("MB relaxation energy root not bracketed");
        if(abs_q(left.residual)<=gate)accepted=left;
        else if(abs_q(right.residual)<=gate)accepted=right;
        else for(;;) {
            const real_t mid=lo+(hi-lo)/2;
            if(mid==lo || mid==hi)throw std::runtime_error("MB relaxation root precision exhausted");
            accepted=evaluate(mid);
            if(abs_q(accepted.residual)<=gate)break;
            if(accepted.residual<0)lo=mid;else hi=mid;
        }
    }
    const real_t increment=accepted.increment;
    for(size_t k=0;k<2;++k) {
        const real_t drive=(s[4+k]+source[k])-ratioC[k]*increment;
        if(drive!=0 && (accepted.delta[k]==0 || accepted.exchange[k]==0))
            throw std::invalid_argument("nonzero MB exchange/tail outside native representable range");
    }
    if(abs_q(accepted.residual)>gate)throw std::runtime_error("MB relaxation committed coordinate exceeds root budget");
    const real_t Tn=accepted.T+accepted.delta[0]/C[0],Tp=accepted.T+accepted.delta[1]/C[1];
    if(!inside(Tn) || !inside(Tp))throw std::invalid_argument("driven MB carrier energy outside configured bounds");
    const real_t qn=p[1]*accepted.exchange[0],qp=p[1]*accepted.exchange[1];
    if((qn==0 && accepted.exchange[0]!=0) || (qp==0 && accepted.exchange[1]!=0))
        throw std::invalid_argument("nonzero MB exchange in joules underflows");
    const real_t dun=p[1]*((C[0]/p[0])*increment+(accepted.delta[0]-s[4]));
    const real_t dup=p[1]*((C[1]/p[0])*increment+(accepted.delta[1]-s[5]));
    const real_t dul=p[1]*increment;
    const real_t rn=dun+qn-p[16],rp=dup+qp-p[17],rl=dul-qn-qp-p[18],global=dun+dup+dul-p[16]-p[17]-p[18];
    for(real_t x:{rn,rp,rl,global})if(!isfinite_q(x) || abs_q(x)>p[15])
        throw std::runtime_error("MB relaxation physical energy budget failed");
    auto result=raw_state;
    result[4]=exported({accepted.delta[0]})[0];result[5]=exported({accepted.delta[1]})[0];
    const auto tail=exported({increment,accepted.T,Tn,Tp,qn,qp,dun,dup,dul,rn,rp,rl,global,
        accepted.logtau[0],accepted.logtau[1],real_t(evaluations)});
    result.insert(result.end(),tail.begin(),tail.end());return result;
}
} // namespace tcad
