#pragma once
#include "boltzmann_affine_transport.h"
namespace tcad {
// Constant tau only. Full affine density is retained in every capacity and
// denominator. One residual-correction quotient is an explicit approximation;
// independent, unapproximated per-lineage BE gates must also pass.
inline std::vector<std::string> native_mb_affine_collision_raw(
    const std::vector<std::string>& endpoint,const std::vector<std::string>& command) {
    using namespace mb_affine_detail;
    auto p=decode(endpoint);temperatures(p);
    const auto f=fermi_local_detail::decimals(p.frame),c=fermi_local_detail::decimals(command);
    if(c.size()!=6)throw std::invalid_argument("affine collision command coverage invalid");
    for(real_t x:c)bounded(x);
    if(!(c[0]>0 && c[1]>0 && c[2]>0))throw std::invalid_argument("positive affine collision dt/tau required");
    const real_t alpha=TCAD_CONST(1.5)*KB;
    Vec lattice(f.begin()+9,f.end()),qold=divide(lattice,f[3]),t=add({f[2]},qold);
    std::vector<Vec> n,K,C,delta,capacity;
    for(size_t k=0;k<2;++k) {
        const auto v=coordinates(p,t,k);n.push_back(v[0]);K.push_back(v[1]);C.push_back(scale(v[0],alpha));
        delta.push_back(add(v[1],mul(C.back(),t),-1));capacity.push_back(pack(divide(C.back(),f[3])));
    }
    const Vec R={c[0]/(c[0]+c[1]),c[0]/(c[0]+c[2])};
    for(real_t r:R){bounded(r);if(!(r>0 && r<=1))throw std::invalid_argument("affine collision exchange coefficient range");}
    const auto D=add(add({1},scale(capacity[0],R[0])),scale(capacity[1],R[1]));
    if(D.empty() || D.back()<=0)throw std::invalid_argument("positive affine collision denominator required");
    std::vector<std::string> out=boltzmann_detail::exported({alpha});
    size_t payload=0;
    auto save=[&](const Vec& v){payload+=v.size();if(payload>4096)throw std::invalid_argument("affine collision evidence budget exceeded");emit(out,v);};
    save(R);save(qold);save(t);
    for(const auto& v:n)save(v);for(const auto& v:K)save(v);for(const auto& v:C)save(v);
    for(const auto& v:delta)save(v);for(const auto& v:capacity)save(v);save(D);
    struct Input{Vec v;size_t kind;bool source;};std::vector<Input> inputs;
    for(size_t k=0;k<2;++k)if(!delta[k].empty())inputs.push_back({delta[k],k,false});
    std::vector<Vec> sources;
    for(size_t k=0;k<3;++k){sources.push_back(divide({c[k+3]},f[4]));save(sources.back());
        if(!sources.back().empty())inputs.push_back({pack(sources.back()),k,true});}
    if(inputs.size()>4096)throw std::invalid_argument("affine collision lineage budget exceeded");
    out.push_back(boltzmann_detail::exported({real_t(inputs.size())})[0]);
    Vec L,un,up;
    for(const auto& input:inputs) {
        const Vec v0=input.v,ownn=input.kind==0?v0:Vec{},ownp=input.kind==1?v0:Vec{};
        const Vec qn=input.source?ownn:Vec{},qp=input.source?ownp:Vec{},ql=input.kind==2?v0:Vec{};
        const auto head=boltzmann_detail::exported({real_t(input.kind),real_t(input.source)});out.insert(out.end(),head.begin(),head.end());save(v0);
        std::vector<Vec> v;
        auto op=[&](Vec x){save(x);v.push_back(std::move(x));};
        op(scale(v0,input.kind==2?real_t(1):R[input.kind])); // 0 numerator
        op(pack(divide(v[0],D.back())));                    // 1 leading quotient
        op(add(v[0],mul(D,v[1]),-1));                       // 2 exact residual
        op(pack(divide(v[2],D.back())));                    // 3 correction quotient
        op(add(v[1],v[3]));                                // 4 trial lattice
        op(pack(divide(v[4],f[3])));                        // 5 trial dTl
        op(mul(C[0],v[5]));op(mul(C[1],v[5]));              // 6,7 actual capacity products
        op(add(ownn,v[6],-1));op(add(ownp,v[7],-1));         // 8,9 pre-exchange excess
        op(scale(v[8],R[0]));op(scale(v[9],R[1]));           // 10,11 exchanges
        op(add(add(v[10],v[11]),ql));                       // 12 conservative lattice
        op(pack(divide(v[12],f[3])));                       // 13 committed dTl
        op(scale(scale(v[13],alpha),-f[0]));op(scale(scale(v[13],alpha),-f[1])); // 14,15 rebase
        op(add(qn,v[10],-1));op(add(qp,v[11],-1));           // 16,17 physical carrier changes
        op(add(v[14],v[16]));op(add(v[15],v[17]));           // 18,19 stored changes
        L=add(L,v[12]);un=add(un,v[18]);up=add(up,v[19]);
    }
    if(p.frame.size()+L.size()>256 || p.change[2].size()+un.size()>4096 || p.change[3].size()+up.size()>4096)
        throw std::invalid_argument("affine collision state budget exceeded");
    save(L);save(un);save(up);
    const auto rawL=boltzmann_detail::exported(L);p.frame.insert(p.frame.end(),rawL.begin(),rawL.end());
    p.change[2].insert(p.change[2].end(),un.begin(),un.end());p.change[3].insert(p.change[3].end(),up.begin(),up.end());
    mb_affine_coordinate_detail::validate_anchor(p.frame,p.en,p.ep);
    const auto temps=boltzmann_detail::exported(temperatures(p));out.insert(out.end(),temps.begin(),temps.end());
    return out;
}
} // namespace tcad
