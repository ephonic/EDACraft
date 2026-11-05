#pragma once
#include "boltzmann_frozen_finite_volume.h"
#include "boltzmann_affine_coordinates.h"

namespace tcad { namespace mb_affine_detail {
using Vec=std::vector<real_t>;
using namespace mb_particle_detail;
using mb_flat_detail::pack;
struct Point {std::vector<std::string> frame,en,ep;std::vector<Vec> change;};
inline Point decode(const std::vector<std::string>& raw) {
    size_t j=0;
    auto take=[&]() {
        if(j>=raw.size())throw std::invalid_argument("MB affine endpoint truncated");
        const real_t n=fermi_local_detail::decimals({raw[j++]})[0];
        if(n<0 || n>4096 || n!=real_t(size_t(n)) || j+size_t(n)>raw.size())
            throw std::invalid_argument("MB affine endpoint coverage invalid");
        std::vector<std::string> v(raw.begin()+j,raw.begin()+j+size_t(n));j+=size_t(n);return v;
    };
    Point p;p.frame=take();p.en=take();p.ep=take();
    for(int k=0;k<4;++k){const auto v=fermi_local_detail::decimals(take());for(real_t x:v)bounded(x);p.change.push_back(v);}
    if(j!=raw.size() || p.frame.size()<10)throw std::invalid_argument("MB affine endpoint coverage invalid");
    mb_affine_coordinate_detail::validate_anchor(p.frame,p.en,p.ep);
    return p;
}
inline Vec add(Vec a,const Vec& b,real_t sign=1) {
    for(real_t x:b)a.push_back(sign*x);return pack(a);
}
inline Vec mul(const Vec& a,const Vec& b) {
    if(a.size()*b.size()>65536)throw std::invalid_argument("MB affine multiplication work budget exceeded");
    Vec r;for(real_t x:a)for(real_t y:b)for(real_t z:product(x,y))if(z!=0)r.push_back(z);
    return pack(r);
}
inline Vec scale(const Vec& a,real_t b) {return pack(multiply(a,b));}
inline Vec thermal(const Point& p) {
    const auto f=fermi_local_detail::decimals(p.frame);Vec t={f[2]};
    const real_t inverse=1/f[3];bounded(inverse);
    for(size_t j=9;j<f.size();++j){const auto v=product(f[j],inverse);t.insert(t.end(),v.begin(),v.end());}
    return pack(t);
}
inline std::vector<Vec> coordinates(const Point& p,const Vec& t,size_t k) {
    const auto f=fermi_local_detail::decimals(p.frame);const real_t alpha=TCAD_CONST(1.5)*KB;
    auto n=add({f[k]},p.change[k]);
    auto K=scale(scale(t,alpha),f[k]);
    K=add(K,fermi_local_detail::decimals(k==0?p.en:p.ep));K=add(K,p.change[2+k]);
    K=add(K,scale(p.change[k],f[5+k]),-1);
    if(n.empty() || n.back()<=0 || view(n)<TCAD_CONST(1e-1000) || view(n)>TCAD_CONST(1e1000))
        throw std::invalid_argument("MB affine updated density outside range");
    return {n,K};
}
inline Vec temperatures(const Point& p) {
    const auto f=fermi_local_detail::decimals(p.frame);const auto t=thermal(p);Vec ts={view(t)};
    for(size_t k=0;k<2;++k){const auto c=coordinates(p,t,k);ts.push_back(view(c[1])/(TCAD_CONST(1.5)*KB*view(c[0])));}
    for(real_t x:ts)if(!isfinite_q(x) || x<f[7] || x>f[8])throw std::invalid_argument("MB affine temperature outside bounds");
    return ts;
}
inline void emit(std::vector<std::string>& out,const Vec& v) {
    if(v.size()>4096)throw std::invalid_argument("MB affine output vector budget exceeded");
    out.push_back(boltzmann_detail::exported({real_t(v.size())})[0]);
    const auto raw=boltzmann_detail::exported(v);out.insert(out.end(),raw.begin(),raw.end());
}
} // namespace mb_affine_detail

inline std::vector<std::string> native_mb_affine_face_raw(const std::vector<std::string>& owner,
    const std::vector<std::string>& neighbor,const std::vector<std::string>& geometry) {
    using namespace mb_affine_detail;
    const auto a=decode(owner),b=decode(neighbor);temperatures(a);temperatures(b);
    const auto f=fermi_local_detail::decimals(a.frame),h=fermi_local_detail::decimals(b.frame),g=fermi_local_detail::decimals(geometry);
    if(g.size()!=5 || f.size()!=h.size())throw std::invalid_argument("MB affine face coverage invalid");
    for(real_t x:g)bounded(x);
    if(!(g[0]>0 && g[1]>0 && g[2]>=0 && g[3]>0 && g[4]>0))throw std::invalid_argument("MB affine face geometry invalid");
    for(size_t j:{2,3,5,6})if(f[j]!=h[j])throw std::invalid_argument("MB affine face common lattice/band required");
    for(size_t j=9;j<f.size();++j)if(f[j]!=h[j])throw std::invalid_argument("MB affine face identical lattice required");
    const real_t G=g[0]/(g[1]/g[3]+g[2]/g[4])/si_transport::elementary_charge,alpha=TCAD_CONST(1.5)*KB,inverse=1/f[3];
    if(!(G>0 && inverse>0))throw std::invalid_argument("MB affine face positive scales required");
    bounded(G);bounded(alpha);bounded(inverse);const auto t=thermal(a);
    std::vector<std::string> out=boltzmann_detail::exported({alpha,inverse});emit(out,t);size_t components=t.size();
    for(size_t k=0;k<2;++k) {
        const auto o=coordinates(a,t,k),n=coordinates(b,t,k);
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

inline std::vector<std::string> native_mb_affine_cell_raw(const std::vector<std::string>& endpoint,
    const std::vector<std::string>& nn,const std::vector<std::string>& np,
    const std::vector<std::string>& un,const std::vector<std::string>& up) {
    using namespace mb_affine_detail;
    auto p=decode(endpoint);temperatures(p);const auto f=fermi_local_detail::decimals(p.frame);
    std::vector<std::string> out;size_t k=0;
    for(const auto& raw:{nn,np,un,up}) {
        if(raw.size()>4096)throw std::invalid_argument("MB affine transfer budget exceeded");
        const auto v=fermi_local_detail::decimals(raw);for(real_t x:v)bounded(x);
        const auto q=divide(v,f[4]);if(q.size()+p.change[k].size()>4096)throw std::invalid_argument("MB affine cumulative component budget exceeded");
        emit(out,q);p.change[k].insert(p.change[k].end(),q.begin(),q.end());++k;
    }
    const auto ts=boltzmann_detail::exported(temperatures(p));out.insert(out.end(),ts.begin(),ts.end());return out;
}
} // namespace tcad
