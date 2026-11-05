#pragma once
#include "boltzmann_affine_collision.h"
namespace tcad {
// Bounded constitutive temperature root. Only the scalar transcendental
// coefficients are rounded: the inner capacity, state and energy ledger retain
// complete affine expansions. A separate actual-state nonlinear BE audit is
// mandatory. This is deliberately not the original extreme-stiffness branch.
inline std::vector<std::string> native_mb_affine_powerlaw_root_raw(
    const std::vector<std::string>& endpoint,const std::vector<std::string>& command) {
    using namespace mb_affine_detail;
    const auto p=decode(endpoint);temperatures(p);
    const auto f=fermi_local_detail::decimals(p.frame),c=fermi_local_detail::decimals(command);
    if(c.size()!=18)throw std::invalid_argument("affine powerlaw command coverage");
    for(real_t x:c)bounded(x);
    if(!(c[14]>0 && c[2]>0 && c[3]>0 && c[4]>0 && c[5]>0 && c[8]>0 && c[9]>0))
        throw std::invalid_argument("positive affine powerlaw references required");
    if(c[0]!=f[3] || c[1]!=f[4] || c[12]!=f[7] || c[13]!=f[8])
        throw std::invalid_argument("affine powerlaw frame configuration mismatch");
    for(size_t j:{size_t(6),size_t(7),size_t(10),size_t(11)})
        if(abs_q(c[j])>8)throw std::invalid_argument("bounded affine powerlaw requires abs_q(a,c)<=8; extreme stiffness unsupported");
    const auto t=add({f[2]},divide(Vec(f.begin()+9,f.end()),f[3]));
    std::vector<Vec> n;for(size_t k=0;k<2;++k)n.push_back(coordinates(p,t,k)[0]);
    Vec trace;size_t evaluations=0;real_t chosenT=0;Vec chosenTau;
    auto evaluate=[&](real_t T) {
        if(!(T>=f[7] && T<=f[8]) || ++evaluations>256)
            throw std::invalid_argument("affine powerlaw bounded temperature root exhausted");
        Vec tau;
        for(size_t k=0;k<2;++k) {
            const size_t j=k?8:4;const auto& nk=n[k];
            Vec low(nk.begin(),nk.end()-1);const real_t lo=view(low),h=nk.back();
            const real_t correction=lo/h,ratio=h/c[j+1],tr=T/c[j];
            bounded(correction);bounded(ratio);bounded(tr);
            if((lo!=0 && correction==0) || ratio<=0 || tr<=0)
                throw std::invalid_argument("affine powerlaw logarithm ratio range");
            #ifdef TCAD_USE_FLOAT128
            const real_t logn=log_q(ratio)+log1pq(correction);
#else
            const real_t logn=log_q(ratio)+std::log1p(correction);
#endif
            const real_t lt=log_q(c[k+2])+c[j+2]*log_q(tr)+c[j+3]*logn;
            const real_t tk=exp_q(lt);bounded(tk);const real_t relative=tk/c[14];
            if(!(relative>=TCAD_CONST(1e-3) && relative<=TCAD_CONST(1e3)))
                throw std::invalid_argument("affine powerlaw requires 1e-3<=tau/dt<=1e3; extreme stiffness unsupported");
            tau.push_back(tk);
        }
        const auto args=boltzmann_detail::exported({c[14],tau[0],tau[1],c[15],c[16],c[17]});
        const auto raw=native_mb_affine_collision_raw(endpoint,args);
        const auto temps=fermi_local_detail::decimals(std::vector<std::string>(raw.end()-3,raw.end()));
        trace.insert(trace.end(),{T,tau[0],tau[1],temps[0]});chosenT=T;chosenTau=tau;
        return temps[0]-T;
    };
    const real_t tol=8*epsilon_q()*std::max(real_t(1),std::max(abs_q(f[7]),abs_q(f[8])));
    real_t x=view(t),res=evaluate(x);bool done=abs_q(res)<=tol;
    for(size_t k=0;k<48 && !done;++k) {x+=res;res=evaluate(x);done=abs_q(res)<=tol;}
    if(!done) {
        real_t lo=f[7],hi=f[8],fl=evaluate(lo),fh=evaluate(hi);
        if(fl==0){x=lo;res=fl;evaluate(x);done=true;}
        else if(fh==0){x=hi;res=fh;done=true;}
        else {
            if((fl>0)==(fh>0))throw std::invalid_argument("affine powerlaw root not bracketed");
            while(!done && evaluations<256) {
                x=lo+(hi-lo)/2;res=evaluate(x);done=abs_q(res)<=tol;
                if((res>0)==(fl>0)){lo=x;fl=res;}else {hi=x;fh=res;}
                if(!done && (x==lo && x==hi))break;
            }
        }
    }
    if(!done)throw std::invalid_argument("affine powerlaw root did not converge");
    auto out=boltzmann_detail::exported({chosenT,chosenTau[0],chosenTau[1],real_t(evaluations)});
    const auto history=boltzmann_detail::exported(trace);out.insert(out.end(),history.begin(),history.end());return out;
}
} // namespace tcad
