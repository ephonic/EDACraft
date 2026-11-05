#pragma once
#include "isolated_relaxation.h"

namespace tcad {
// Local Schur complement only: prescribed candidate n,p,Tl and matched FD
// equilibrium energies / face moments. It does not solve Poisson, recover Tc,
// iterate the face moments or commit a device state. Relaxation b_Tc=0 only.
// Cells (34), row-major decimal strings:
// n0,p0,Tl0,n,p,Tl,ueq0n,ueqn,e0n,ueq0p,ueqp,e0p,V,Cv,phi0,phi,kappa,
// tau0n,Trefn,nrefn,a_n,c_n,tau0p,Trefp,nrefp,a_p,c_p,
// added_count_n,added_count_p,Qn,Qp,Ql,band_work_n,band_work_p.
// Q and band work are signed integrated J, counts are integrated particles.
// Band work is internal transfer from lattice to a carrier; Q is external to
// these three reservoirs (other reservoirs must be accounted for by callers).
// Faces (13) exactly match three_temperature_local.h. Empty faces are allowed.
// Output: 20 row-major values per cell, then nf Fourier fluxes in W:
// rn,rp,e_n,e_p,du_n,du_p,du_l,exchange_n,exchange_p,work_n,work_p,
// residual_n,residual_p,residual_l,tau_n,tau_p,retained_n,retained_p,drive_n,drive_p.
inline std::vector<std::string> native_three_temperature_excess_local_raw(
        const std::vector<std::string>& cells,const std::vector<std::string>& faces,
        const std::string& timestep) {
    using fermi_local_detail::decimals;
    using isolated_relaxation_detail::text;
    if(cells.empty() || cells.size()%34 || faces.size()%13)
        throw std::invalid_argument("excess local cell or face coverage invalid");
    const auto c=decimals(cells),f=decimals(faces),d=decimals({timestep});
    const size_t nc=c.size()/34,nf=f.size()/13;
    const real_t dt=d[0];
    if(dt<=0)throw std::invalid_argument("positive excess local timestep required");
    auto C=[&](size_t i,size_t k){return c[34*i+k];};
    std::vector<real_t> result(20*nc+nf,0),div_n(nc,0),div_p(nc,0),heat(nc,0);
    for(size_t i=0;i<nc;++i) {
        for(size_t k:{0,1,2,3,4,5,12,13,16,17,18,19,22,23,24})
            if(C(i,k)<=0)throw std::invalid_argument("positive excess local state and coefficients required");
        result[20*i]=C(i,12)*(C(i,3)-C(i,0))-C(i,27);
        result[20*i+1]=C(i,12)*(C(i,4)-C(i,1))-C(i,28);
        result[20*i+6]=C(i,12)*C(i,13)*(C(i,5)-C(i,2));
    }
    for(size_t face=0;face<nf;++face) {
        const size_t b=13*face;
        if(f[b]<0 || f[b]>=nc || f[b]!=(real_t)(size_t)f[b] ||
           f[b+1]<-1 || f[b+1]>=nc || (f[b+1]!=-1 && f[b+1]!=(real_t)(size_t)f[b+1]) || f[b]==f[b+1] ||
           f[b+8]<=0 || f[b+9]<=0 || (f[b+1]>=0?f[b+10]<=0:f[b+10]!=0) ||
           (f[b+12]!=0 && f[b+12]!=1) ||
           (f[b+12]==1 && (f[b+1]>=0 || f[b+11]<=0)) || (f[b+12]==0 && f[b+11]!=0))
            throw std::invalid_argument("excess local face geometry, index or bath invalid");
        const size_t i=size_t(f[b]);const long j=long(f[b+1]);
        real_t conduction=0;
        if(j>=0)conduction=f[b+8]/(f[b+9]/C(i,16)+f[b+10]/C(size_t(j),16))*(C(i,5)-C(size_t(j),5));
        else if(f[b+12]==1)conduction=f[b+8]*C(i,16)/f[b+9]*(C(i,5)-f[b+11]);
        result[20*nc+face]=conduction;
        const real_t facephi=(f[b+6]+f[b+7])/2;
        auto deposit=[&](size_t node,real_t sign) {
            const real_t phi=(C(node,14)+C(node,15))/2;
            result[20*node]+=dt*sign*f[b+2];result[20*node+1]+=dt*sign*f[b+3];
            result[20*node+9]+=-si_transport::elementary_charge*dt*sign*f[b+2]*(phi-facephi);
            result[20*node+10]+=si_transport::elementary_charge*dt*sign*f[b+3]*(phi-facephi);
            div_n[node]+=dt*sign*f[b+4];div_p[node]+=dt*sign*f[b+5];
            heat[node]+=dt*sign*conduction;
        };
        deposit(i,1);if(j>=0)deposit(size_t(j),-1);
    }
    for(size_t i=0;i<nc;++i) {
        real_t exchanged[2]{};
        for(size_t s=0;s<2;++s) {
            const size_t eq=6+3*s,law=17+5*s;
            const real_t logtau=log_q(C(i,law))+C(i,law+3)*log_q(C(i,5)/C(i,law+1))+
                C(i,law+4)*log_q(C(i,3+s)/C(i,law+2));
            const real_t tau=exp_q(logtau);
            if(!isfinite_q(tau) || !std::isfinite(double(tau)) || double(tau)<=0)
                throw std::invalid_argument("excess local relaxation outside positive float64 range");
            const real_t ratio=logtau-log_q(dt);
            const real_t retained=isolated_relaxation_detail::logistic(ratio);
            const real_t lost=isolated_relaxation_detail::logistic(-ratio);
            const real_t difference=(C(i,eq)-C(i,eq+1))+C(i,eq+2);
            const real_t net=C(i,29+s)+C(i,32+s)+result[20*i+9+s]-(s==0?div_n[i]:div_p[i]);
            const real_t driven=difference+net/C(i,12);
            const real_t excess=retained*driven;
            const real_t exchange=C(i,12)*lost*driven;
            const real_t storage=C(i,12)*(-difference+excess);
            result[20*i+2+s]=excess;result[20*i+4+s]=storage;
            result[20*i+7+s]=exchange;result[20*i+11+s]=storage+exchange-net;
            result[20*i+14+s]=tau;result[20*i+16+s]=retained;
            result[20*i+18+s]=driven;exchanged[s]=exchange;
        }
        result[20*i+13]=result[20*i+6]-exchanged[0]-exchanged[1]+heat[i]-C(i,31)+C(i,32)+C(i,33);
    }
    std::vector<std::string> output;output.reserve(result.size());
    for(real_t value:result)output.push_back(text(value));
    return output;
}
} // namespace tcad
