#pragma once
#include "boltzmann_affine_transport.h"

namespace tcad {
inline std::vector<std::string> native_mb_nonisothermal_face_raw(const std::vector<std::string>& owner,
    const std::vector<std::string>& neighbor,const std::vector<std::string>& geometry) {
    using namespace mb_affine_detail;
    const auto a=decode(owner),b=decode(neighbor);temperatures(a);temperatures(b);
    const auto f=fermi_local_detail::decimals(a.frame),h=fermi_local_detail::decimals(b.frame),g=fermi_local_detail::decimals(geometry);
    if(g.size()!=5)throw std::invalid_argument("MB affine face coverage invalid");
    for(real_t x:g)bounded(x);
    if(!(g[0]>0 && g[1]>0 && g[2]>=0 && g[3]>0 && g[4]>0))throw std::invalid_argument("MB affine face geometry invalid");
    for(size_t j:{5,6})if(f[j]!=h[j])throw std::invalid_argument("MB nonisothermal face flat bands required");
    const real_t G=g[0]/(g[1]/g[3]+g[2]/g[4])/si_transport::elementary_charge,alpha=TCAD_CONST(1.5)*KB;
    if(!(G>0))throw std::invalid_argument("MB nonisothermal positive scale required");
    bounded(G);bounded(alpha);
    const Vec la(f.begin()+9,f.end()),lb(h.begin()+9,h.end());
    const auto qa=divide(la,f[3]),qb=divide(lb,h[3]);
    const auto t=add({f[2]},qa),tn=add({h[2]},qb);
    std::vector<std::string> out=boltzmann_detail::exported({alpha});
    emit(out,qa);emit(out,qb);emit(out,t);emit(out,tn);size_t components=qa.size()+qb.size()+t.size()+tn.size();
    for(size_t k=0;k<2;++k) {
        const auto o=coordinates(a,t,k),n=coordinates(b,tn,k);
        const real_t ro=1/o[0].back(),rn=1/n[0].back();
        const Vec c={G*2/3,f[5+k],G*TCAD_CONST(10.)/9,ro,-ro*ro,-ro*rn,-ro*ro,rn*rn};
        for(size_t j=0;j<c.size();++j){bounded(c[j]);if(j!=1 && c[j]==0)throw std::invalid_argument("MB affine coefficient underflow");}
        emit(out,c);for(const auto& v:{o[0],n[0],o[1],n[1]}){emit(out,v);components+=v.size();}
        const Vec Lo(o[0].begin(),o[0].end()-1),Ln(n[0].begin(),n[0].end()-1);
        std::vector<Vec> v;
        auto save=[&](Vec x){components+=x.size();if(components>4096)throw std::invalid_argument("MB affine face component budget exceeded");emit(out,x);v.push_back(std::move(x));};
        save(add(o[1],n[1],-1));                 // 0 A = Ko-Kn
        save(add(o[1],n[1]));                    // 1 B = Ko+Kn
        save(add(o[0],n[0],-1));                 // 2 D = no-nn
        save(mul(v[0],v[1]));                    // 3 P = A*B
        save(mul(n[1],n[1]));                    // 4 H = Kn^2
        save(mul(v[4],add({o[0].back()},{n[0].back()},-1))); // 5 H*(Ho-Hn)
        save(scale(v[3],c[3]));                  // 6 P/Ho
        save(mul(v[3],Lo));                      // 7 P*Lo
        save(scale(v[7],c[4]));                  // 8 -P*Lo/Ho^2
        save(scale(v[5],c[5]));                  // 9 -H*(Ho-Hn)/(Ho*Hn)
        save(mul(v[4],Lo));                      // 10 H*Lo
        save(scale(v[10],c[6]));                 // 11 -H*Lo/Ho^2
        save(mul(v[4],Ln));                      // 12 H*Ln
        save(scale(v[12],c[7]));                 // 13 H*Ln/Hn^2
        save(add(add(add(add(v[6],v[8]),v[9]),v[11]),v[13])); // 14 kinetic rational difference
        save(scale(v[0],c[0]));                  // 15 number
        save(scale(v[15],c[1]));                 // 16 band energy
        save(scale(v[14],c[2]));                 // 17 kinetic energy
        save(add(v[16],v[17]));                  // 18 total material energy
    }
    return out;
}

} // namespace tcad
