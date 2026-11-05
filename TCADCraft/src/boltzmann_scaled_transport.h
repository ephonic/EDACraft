#pragma once
#include "boltzmann_scaled_powerlaw.h"

namespace tcad { namespace mb_scaled_transport_detail {
using namespace mb_scaled_powerlaw_detail;
namespace old=mb_affine_detail;
struct Point {std::vector<std::string> frame;std::vector<I> v;};
inline void packet(std::vector<std::string>& out,const std::vector<std::string>& p) {
    out.push_back(std::to_string(p.size()));out.insert(out.end(),p.begin(),p.end());
}
inline std::vector<std::string> take(const std::vector<std::string>& wire,size_t& j,size_t maximum=8195) {
    if(j>=wire.size())throw std::invalid_argument("scaled transport packet missing");
    const size_t n=ar::count(wire[j++],maximum);
    if(j+n>wire.size())throw std::invalid_argument("scaled transport packet truncated");
    std::vector<std::string> r(wire.begin()+j,wire.begin()+j+n);j+=n;return r;
}
inline std::vector<std::string> emit(const Point& p) {
    std::vector<std::string> out={"mb_scaled_endpoint_v1","113","9"};
    out.insert(out.end(),p.frame.begin(),p.frame.end());
    size_t evidence=0;
    for(const auto& v:p.v) {const auto w=ar::write(v);evidence+=ar::count(w[2],4096);packet(out,w);}
    if(evidence>4096)throw std::invalid_argument("scaled endpoint component budget exceeded");
    return out;
}
inline Point decode(const std::vector<std::string>& wire) {
    if(wire.size()<12 || wire.size()>60000 || wire[0]!="mb_scaled_endpoint_v1" || wire[1]!="113" || wire[2]!="9")
        throw std::invalid_argument("scaled endpoint version/frame coverage");
    Point p;p.frame.assign(wire.begin()+3,wire.begin()+12);size_t j=12;
    for(size_t k=0;k<7;++k)p.v.push_back(ar::read(take(wire,j)));
    if(j!=wire.size() || emit(p)!=wire)throw std::invalid_argument("scaled endpoint noncanonical or trailing value");
    const auto f=fermi_local_detail::decimals(p.frame);
    for(real_t x:f)old::bounded(x);
    for(size_t k:{size_t(0),size_t(1),size_t(3),size_t(4)})
        if(!(f[k]>=TCAD_CONST(1e-1000) && f[k]<=TCAD_CONST(1e1000)))throw std::invalid_argument("scaled endpoint reference range");
    if(!(f[2]>1 && f[2]<100000 && f[7]>1 && f[7]<f[8] && f[8]<100000))throw std::invalid_argument("scaled endpoint temperature domain");
    if(abs_q(f[5])>TCAD_CONST(1e1000) || abs_q(f[6])>TCAD_CONST(1e1000))throw std::invalid_argument("scaled endpoint band range");
    return p;
}
inline std::vector<I> coordinates(const Point& p,I& remainder) {
    const auto f=fermi_local_detail::decimals(p.frame);const auto cv=scalar(f[3]),alpha=scalar(TCAD_CONST(1.5)*KB);
    const I q=divide_atoms(atoms(p.v[0]),cv,remainder),t=ar::plus(scalar(f[2]),q);
    std::vector<I> result={t};
    for(size_t k=0;k<2;++k) {
        result.push_back(ar::plus(scalar(f[k]),p.v[3+k]));
        result.push_back(ar::plus(ar::plus(multiply(multiply(alpha,t),scalar(f[k])),p.v[1+k]),
            ar::plus(p.v[5+k],multiply(scalar(f[5+k]),p.v[3+k]),-1)));
    }
    const real_t Tl=real113(ar::rounded_ratio(ar::plus(multiply(scalar(f[2]),cv),p.v[0]),cv));
    const real_t env=128*epsilon_q()*std::max(real_t(1),f[8]);
    if(Tl<f[7]-env || Tl>f[8]+env)throw std::invalid_argument("scaled actual lattice temperature outside bounds");
    for(size_t k=0;k<2;++k) {
        const real_t n=real113(ar::rounded_ratio(result[1+2*k],scalar(1)));
        if(!(n>=TCAD_CONST(1e-1000) && n<=TCAD_CONST(1e1000)))throw std::invalid_argument("scaled actual density outside bounds");
        const real_t T=real113(ar::rounded_ratio(result[2+2*k],multiply(alpha,result[1+2*k])));
        if(T<f[7]-env || T>f[8]+env)throw std::invalid_argument("scaled actual carrier temperature outside bounds");
    }
    return result;
}
inline void valid(const Point& p) {I r;coordinates(p,r);}
inline std::vector<std::string> values(const std::vector<I>& v,const std::string& name) {
    std::vector<std::string> out={name,"113",std::to_string(v.size())};
    size_t evidence=0;for(auto x:v){const auto w=ar::write(x);evidence+=ar::count(w[2],4096);packet(out,w);}
    if(evidence>4096)throw std::invalid_argument("scaled transport saved component budget exceeded");
    return out;
}
inline std::vector<I> read_values(const std::vector<std::string>& raw,const std::string& name,size_t expected) {
    if(raw.size()<3 || raw[0]!=name || raw[1]!="113" || ar::count(raw[2],16)!=expected)
        throw std::invalid_argument("scaled transport value coverage");
    std::vector<I> v;size_t j=3;
    for(size_t k=0;k<expected;++k)v.push_back(ar::read(take(raw,j)));
    if(j!=raw.size() || values(v,name)!=raw)throw std::invalid_argument("noncanonical scaled transport values");
    return v;
}
} // namespace mb_scaled_transport_detail

inline std::vector<std::string> native_mb_scaled_endpoint_raw(const std::vector<std::string>& endpoint,
    const std::vector<std::string>& L,const std::vector<std::string>& un,const std::vector<std::string>& up) {
    using namespace mb_scaled_transport_detail;
    const auto a=old::decode(endpoint);old::temperatures(a);
    Point p;p.frame.assign(a.frame.begin(),a.frame.begin()+9);
    p.v={ar::plus(imported(std::vector<std::string>(a.frame.begin()+9,a.frame.end())),ar::read(L)),
         imported(a.en),imported(a.ep),imported(boltzmann_detail::exported(a.change[0])),
         imported(boltzmann_detail::exported(a.change[1])),
         ar::plus(imported(boltzmann_detail::exported(a.change[2])),ar::read(un)),
         ar::plus(imported(boltzmann_detail::exported(a.change[3])),ar::read(up))};
    valid(p);return emit(p);
}

// Full-density rational moment difference; this is a separate, versioned
// flux model. Remainders retain all division tails as computational evidence.
inline std::vector<std::string> native_mb_scaled_face_raw(const std::vector<std::string>& owner,
    const std::vector<std::string>& neighbor,const std::vector<std::string>& geometry) {
    using namespace mb_scaled_transport_detail;
    const auto a=decode(owner),b=decode(neighbor);
    const auto f=fermi_local_detail::decimals(a.frame),h=fermi_local_detail::decimals(b.frame),g=fermi_local_detail::decimals(geometry);
    if(g.size()!=5)throw std::invalid_argument("scaled face geometry coverage");
    for(real_t x:g)old::bounded(x);
    if(!(g[0]>0 && g[1]>0 && g[2]>=0 && g[3]>0 && g[4]>0) || f[5]!=h[5] || f[6]!=h[6])
        throw std::invalid_argument("scaled face geometry or flat bands invalid");
    I r;const auto o=coordinates(a,r);std::vector<I> proof={r};const auto n=coordinates(b,r);proof.push_back(r);
    const real_t G=g[0]/(g[1]/g[3]+g[2]/g[4])/si_transport::elementary_charge;
    const std::vector<real_t> coeff={TCAD_CONST(1.5)*KB,G*2/3,G*TCAD_CONST(10.)/9,f[5],f[6]};
    if(!(G>0))throw std::invalid_argument("positive scaled face conductance required");
    for(real_t x:coeff)old::bounded(x);
    std::vector<I> N,U;
    for(size_t k=0;k<2;++k) {
        const auto no=o[1+2*k],nn=n[1+2*k],Ko=o[2+2*k],Kn=n[2+2*k];
        const auto A=ar::plus(Ko,Kn,-1),B=ar::plus(Ko,Kn),D=ar::plus(no,nn,-1);
        const auto P=multiply(A,B),H=multiply(Kn,Kn);
        const auto first=divide_atoms(atoms(P),no,r);proof.push_back(r);
        const auto second=divide_atoms(atoms(multiply(H,D)),multiply(no,nn),r);proof.push_back(r);
        N.push_back(multiply(A,scalar(coeff[1])));
        U.push_back(ar::plus(multiply(N.back(),scalar(coeff[3+k])),multiply(ar::plus(first,second,-1),scalar(coeff[2]))));
    }
    proof.insert(proof.end(),{N[0],N[1],U[0],U[1]});
    size_t evidence=5;for(auto x:proof)evidence+=ar::count(ar::write(x)[2],4096);
    if(evidence>4096)throw std::invalid_argument("scaled face combined saved evidence budget exceeded");
    auto out=values(proof,"mb_scaled_face_v1");
    const auto raw=boltzmann_detail::exported(coeff);out.insert(out.begin()+3,raw.begin(),raw.end());return out;
}

inline std::vector<std::string> native_mb_scaled_cell_raw(const std::vector<std::string>& endpoint,
    const std::vector<std::string>& transfers,const std::vector<std::string>& command,
    const std::vector<std::string>& clock) {
    using namespace mb_scaled_transport_detail;
    auto p=decode(endpoint);valid(p);const auto f=fermi_local_detail::decimals(p.frame),c=fermi_local_detail::decimals(command);
    if(c.size()!=1 || !(c[0]>0))throw std::invalid_argument("positive scaled transport dt required");
    old::bounded(c[0]);const I dt=scalar(c[0]),start=ar::read(clock);
    if(start.sign<0)throw std::invalid_argument("nonnegative scaled transport clock required");
    if(transfers.size()<3 || transfers.size()>262144 || transfers[0]!="mb_scaled_transfers_v1" || transfers[1]!="113")
        throw std::invalid_argument("scaled transfer framing");
    const size_t count=ar::count(transfers[2],512);size_t j=3;std::vector<I> integrated(4);
    for(size_t i=0;i<count;++i) {
        if(j>=transfers.size() || (transfers[j]!="1" && transfers[j]!="-1"))throw std::invalid_argument("scaled transfer orientation");
        const int sign=transfers[j++]=="1"?1:-1;
        auto moments=read_values(take(transfers,j,65535),"mb_scaled_moments_v1",4);
        for(size_t k=0;k<4;++k)integrated[k]=ar::plus(integrated[k],multiply(moments[k],dt),sign);
    }
    if(j!=transfers.size())throw std::invalid_argument("scaled transfer trailing token");
    std::vector<I> remainders;
    for(size_t k=0;k<4;++k) {
        I r;const auto q=divide_atoms(atoms(integrated[k]),scalar(f[4]),r);
        remainders.push_back(r);p.v[3+k]=ar::plus(p.v[3+k],q);
    }
    valid(p);const auto state=emit(p),end=ar::write(ar::plus(start,dt));
    integrated.insert(integrated.end(),remainders.begin(),remainders.end());
    auto proof=values(integrated,"mb_scaled_cell_v1");
    size_t evidence=0;for(auto x:p.v)evidence+=ar::count(ar::write(x)[2],4096);
    for(auto x:integrated)evidence+=ar::count(ar::write(x)[2],4096);
    evidence+=ar::count(end[2],4096);
    if(evidence>4096)throw std::invalid_argument("scaled cell combined saved evidence budget exceeded");
    proof.insert(proof.begin()+3,std::to_string(evidence));packet(proof,state);packet(proof,end);return proof;
}
} // namespace tcad
