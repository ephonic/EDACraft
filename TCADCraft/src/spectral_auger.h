#pragma once
// Discrete on-shell collision events, not a material continuum Auger kernel.
#include "spectral_radiative.h"
namespace tcad {
inline std::vector<std::vector<real_t>> spectral_auger_values(
    const std::vector<real_t>& s,const std::vector<real_t>& ev) {
    using namespace fermi_local_detail;
    if(s.size()!=8 || ev.empty() || ev.size()%11 || ev.size()/11>4096)
        throw std::invalid_argument("Auger state width8, event width11, count1..4096 required");
    for(real_t x:s) if(!isfinite_q(x)) throw std::invalid_argument("finite Auger state required");
    for(real_t x:ev) if(!isfinite_q(x)) throw std::invalid_argument("finite Auger events required");
    if(s[0]<=0 || s[1]<=0 || s[6]<=0 || s[7]<=0 || s[4]+s[5]<=0)
        throw std::invalid_argument("positive temperatures, masses and gap required");
    const real_t gap=s[4]+s[5],hbar=TCAD_CONST(6.62607015e-34)/(2*PI),m0=TCAD_CONST(9.1093837015e-31);
    std::vector<real_t> total(14,0);std::vector<std::vector<real_t>> rows;
    std::vector<std::vector<real_t>> seen;
    auto checked=[](const std::vector<real_t>& x) {
        auto out=fermi_local_detail::exported(x);
        for(double v:out) if(!std::isfinite(v)) throw std::invalid_argument("Auger output exceeds float64 report range");
        return x;
    };
    for(size_t b=0;b<ev.size();b+=11) {
        if((ev[b]!=0 && ev[b]!=1) || ev[b+1]<0)
            throw std::invalid_argument("Auger channel0/1 and nonnegative weight required");
        const bool hole=ev[b]==1;const real_t weight=ev[b+1];
        real_t scale=0;for(size_t j=0;j<9;++j) scale=std::max(scale,abs_q(ev[b+2+j]));
        if(scale==0) throw std::invalid_argument("nonzero Auger momentum shape required");
        real_t q[4][3]={};for(size_t i=0;i<3;++i) for(size_t j=0;j<3;++j) q[i][j]=ev[b+2+3*i+j]/scale;
        bool equal=true;for(size_t j=0;j<3;++j) equal=equal && q[0][j]==q[1][j];
        if(equal) throw std::invalid_argument("two initial majority states must have distinct momenta");
        // Canonicalize the exchange of the two indistinguishable initial legs.
        bool swap=false;for(size_t j=0;j<3;++j) if(q[0][j]!=q[1][j]) {swap=q[0][j]>q[1][j];break;}
        if(swap) for(size_t j=0;j<3;++j) std::swap(q[0][j],q[1][j]);
        std::vector<real_t> key={ev[b]};for(size_t i=0;i<3;++i) for(size_t j=0;j<3;++j) key.push_back(q[i][j]);
        if(std::find(seen.begin(),seen.end(),key)!=seen.end()) throw std::invalid_argument("duplicate normalized Auger event");
        seen.push_back(key);
        for(size_t j=0;j<3;++j) q[3][j]=q[0][j]+q[1][j]+q[2][j];
        const real_t mass=hole?s[7]:s[6],other=hole?s[6]:s[7];
        real_t a[4]={};for(size_t i=0;i<4;++i) for(size_t j=0;j<3;++j) a[i]+=q[i][j]*q[i][j]/(i==2?other:mass);
        const real_t D=a[3]-a[0]-a[1]-a[2];
        if(D<=0) throw std::invalid_argument("momentum shape has no positive-gap on-shell scale");
        real_t kinetic[4];for(size_t i=0;i<3;++i) kinetic[i]=gap*a[i]/D;
        kinetic[3]=gap+kinetic[0]+kinetic[1]+kinetic[2];
        const real_t edge=hole?s[5]:s[4],minor=hole?s[4]:s[5];
        const real_t T=hole?s[1]:s[0],To=hole?s[0]:s[1],mu=hole?s[3]:s[2],muo=hole?s[2]:s[3];
        real_t z[4];for(size_t i=0;i<4;++i) z[i]=((i==2?muo:mu)-(i==2?minor:edge)-kinetic[i])/(KB*(i==2?To:T));
        real_t la=0,lb=0;for(size_t i=0;i<4;++i) {
            la+=radiative_detail::log_f(i==3?-z[i]:z[i]);
            lb+=radiative_detail::log_f(i==3?z[i]:-z[i]);
        }
        const real_t forward=weight*exp_q(la),reverse=weight*exp_q(lb);
        const real_t net=weight*radiative_detail::difference(la,lb),energy=minor+kinetic[2];
        const real_t un=(hole?-1:1)*energy*net,up=-un,sigma=KB*net*(la-lb);
        const real_t kscale=sqrt_q(2*m0*gap/D)/hbar;
        const real_t defect=gap*a[3]/D-kinetic[3];
        rows.push_back(checked({forward,reverse,net,un,up,sigma,kinetic[0],kinetic[1],kinetic[2],kinetic[3],kscale,la-lb,defect}));
        total[0]+=forward;total[1]+=reverse;total[2]+=net;total[hole?4:3]+=net;
        total[5]-=net;total[6]-=net;total[7]+=un;total[8]+=up;total[12]+=sigma;
        total[13]=std::max(total[13],abs_q(defect)/std::max(gap,kinetic[3]));
    }
    // lattice heat, charge and total energy are zero: this is an internal collision.
    rows.insert(rows.begin(),checked(total));return rows;
}
inline std::vector<std::vector<double>> native_spectral_auger_raw(
    const std::vector<std::string>& state,const std::vector<std::string>& events) {
    const auto values=spectral_auger_values(fermi_local_detail::decimals(state),fermi_local_detail::decimals(events));
    std::vector<std::vector<double>> out;
    for(const auto& row:values) out.push_back(fermi_local_detail::exported(row));
    return out;
}
} // namespace tcad
