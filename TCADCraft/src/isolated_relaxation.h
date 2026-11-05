#pragma once
// Explicit closed single-cell FD mode. Primary carrier state is the signed
// energy density ABOVE the same-density equilibrium at Tl, never U-Ueq formed
// from two rounded absolute temperatures. Optional prescribed energy impulses
// drive each reservoir. Densities and band edges remain fixed; no transport.
#include "fermi_local.h"
#include <cstdio>

namespace tcad {
namespace isolated_relaxation_detail {
inline std::string text(real_t value) {
    if(!isfinite_q(value)) throw std::invalid_argument("nonfinite isolated relaxation output");
    char buffer[128];
#ifdef TCAD_USE_FLOAT128
    quadmath_snprintf(buffer,sizeof(buffer),"%.36Qg",value);
#else
    std::snprintf(buffer,sizeof(buffer),"%.24Lg",value);
#endif
    return buffer;
}
inline real_t logistic(real_t x) {
    if(x>=0) return 1/(1+exp_q(-x));
    const real_t e=exp_q(x);return e/(1+e);
}
}

// State: n,p,Tl,excess_n,excess_p (decimal strings). initialize=true interprets
// the final two inputs as ordinary Tn,Tp and returns Tl,excess_n,excess_p.
// Parameters: Cv,V,Ec,Eh,tau0n,tau0p,Trefn,nrefn,a_n,c_n,
//             Trefp,nrefp,a_p,c_p,Tmin,Tmax,dt,energy_atol_J.
// Optional final three parameters: signed external impulses Qn,Qp,Ql in J.
// Only carrier-temperature exponent b=0 is supported, explicitly at the API.
// Step output: Tl,excess_n,excess_p,exchange_n_J,exchange_p_J,du_n_J,du_p_J,
//             du_l_J,rn_J,rp_J,rl_J,tau_n_s,tau_p_s,evaluations.
inline std::vector<std::string> native_isolated_relaxation_raw(
        const std::vector<std::string>& state,const std::vector<std::string>& parameters,
        const std::vector<double>& vn,const std::vector<double>& vp,
        bool initialize,int max_nfev) {
    using namespace fermi_local_detail;
    using isolated_relaxation_detail::text;
    if(state.size()!=5 || (parameters.size()!=18 && parameters.size()!=21) || max_nfev<1)
        throw std::invalid_argument("isolated relaxation dimensions or evaluation budget invalid");
    const auto s=decimals(state),p=decimals(parameters);
    const real_t source[]={p.size()==21?p[18]:real_t(0),p.size()==21?p[19]:real_t(0),p.size()==21?p[20]:real_t(0)};
    for(size_t k:{0,1,4,5,6,7,10,11,14,15,16,17})
        if(p[k]<=0) throw std::invalid_argument("positive isolated relaxation coefficients required");
    if(s[0]<=0 || s[1]<=0 || s[2]<=0 || p[14]>=p[15] || s[2]<p[14] || s[2]>p[15])
        throw std::invalid_argument("positive isolated density/temperature and enclosing bracket required");
    auto energy=[&](size_t carrier,real_t temperature) {
        const auto result=native_fermi_reservoir_raw({text(s[carrier]),text(temperature),text(p[2+carrier])},carrier==0?vn:vp);
        return real_t(result[1]); // established native FD quadrature/export accuracy
    };
    const real_t old_eq[]={energy(0,s[2]),energy(1,s[2])};
    if(initialize) {
        if(s[3]<=0 || s[4]<=0 || s[3]<p[14] || s[3]>p[15] || s[4]<p[14] || s[4]>p[15])
            throw std::invalid_argument("positive initial carrier temperatures inside bracket required");
        return {text(s[2]),text(energy(0,s[3])-old_eq[0]),text(energy(1,s[4])-old_eq[1])};
    }
    for(size_t k=0;k<2;++k) {
        const auto& valleys=k==0?vn:vp;real_t edge=p[2+k]+valleys[3];
        for(size_t v=3;v<valleys.size();v+=4)edge=std::min(edge,p[2+k]+real_t(valleys[v]));
        if(old_eq[k]+s[3+k]<=s[k]*edge)
            throw std::invalid_argument("isolated carrier energy below band minimum");
    }
    struct Trial {real_t T=0,excess[2]{},impulse[2]{},du[2]{},logtau[2]{},lattice=0,residual=0;};
    int evaluations=0;
    auto evaluate=[&](real_t T) {
        if(evaluations>=max_nfev)throw std::runtime_error("isolated relaxation evaluation budget exhausted");
        ++evaluations;Trial result;result.T=T;
        for(size_t k=0;k<2;++k) {
            const size_t base=6+4*k;
            const real_t logtau=log_q(p[4+k])+p[base+2]*log_q(T/p[base])+p[base+3]*log_q(s[k]/p[base+1]);
            const real_t logratio=logtau-log_q(p[16]);
            // Compute both weights separately. Neither tau nor 1-weight is
            // formed for bracketing, avoiding overflow and cancellation.
            const real_t retained=isolated_relaxation_detail::logistic(logratio);
            const real_t lost=isolated_relaxation_detail::logistic(-logratio);
            const real_t difference=(old_eq[k]-energy(k,T))+s[3+k];
            // Solve dU + dt*V*excess/tau = Q without subtracting two
            // rounded temperatures, including when retained is ~1e-100.
            const real_t driven=difference+source[k]/p[1];
            result.logtau[k]=logtau;result.excess[k]=retained*driven;
            result.impulse[k]=p[1]*lost*driven;
            result.du[k]=p[1]*(-difference+result.excess[k]);
        }
        result.lattice=p[1]*p[0]*(T-s[2]);
        result.residual=result.lattice-result.impulse[0]-result.impulse[1]-source[2];
        return result;
    };
    Trial accepted=evaluate(s[2]);
    if(abs_q(accepted.residual)>p[17]/8) {
        real_t lo=p[14],hi=p[15];const auto left=evaluate(lo),right=evaluate(hi);
        if(left.residual>0 || right.residual<0)
            throw std::runtime_error("isolated relaxation energy root not bracketed");
        if(abs_q(left.residual)<=p[17]/8)accepted=left;
        else if(abs_q(right.residual)<=p[17]/8)accepted=right;
        else for(;;) {
            const real_t mid=(lo+hi)/2;
            if(mid==lo || mid==hi)throw std::runtime_error("isolated relaxation root precision exhausted");
            accepted=evaluate(mid);
            if(abs_q(accepted.residual)<=p[17]/8)break;
            if(accepted.residual<0)lo=mid;else hi=mid;
        }
    }
    real_t tau[2];
    for(size_t k=0;k<2;++k) {
        tau[k]=exp_q(accepted.logtau[k]);
        if(!isfinite_q(tau[k]) || !std::isfinite(double(tau[k])) || double(tau[k])<=0)
            throw std::invalid_argument("isolated effective relaxation time outside positive float64 range");
        const auto& valleys=k==0?vn:vp;real_t edge=p[2+k]+valleys[3];
        for(size_t v=3;v<valleys.size();v+=4)edge=std::min(edge,p[2+k]+real_t(valleys[v]));
        if(energy(k,accepted.T)+accepted.excess[k]<=s[k]*edge)
            throw std::invalid_argument("driven isolated carrier energy below band minimum");
        if(abs_q(accepted.du[k]+accepted.impulse[k]-source[k])>p[17])
            throw std::runtime_error("isolated carrier physical energy budget failed");
    }
    std::vector<std::string> output;
    for(real_t v:{accepted.T,accepted.excess[0],accepted.excess[1],accepted.impulse[0],accepted.impulse[1],
            accepted.du[0],accepted.du[1],accepted.lattice,accepted.du[0]+accepted.impulse[0]-source[0],
            accepted.du[1]+accepted.impulse[1]-source[1],accepted.residual,tau[0],tau[1],real_t(evaluations)})output.push_back(text(v));
    return output;
}
} // namespace tcad
