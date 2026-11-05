#pragma once
#include "boltzmann_scaled_transport.h"
#include "boltzmann_capacity_collision_helpers.h"

namespace tcad { namespace mb_lattice_detail {
using namespace mb_capacity_collision_detail;
namespace transport=mb_scaled_transport_detail;
inline size_t components(const std::vector<I>& values) {
    size_t n=0;for(const auto& x:values)n+=ar::count(ar::write(x)[2],4096);return n;
}
inline std::vector<std::string> pack(const std::string& name,const std::vector<I>& values) {
    if(components(values)>4096)throw std::invalid_argument("lattice saved component budget exceeded");
    std::vector<std::string> out={name,"113"};
    for(const auto& x:values)transport::packet(out,ar::write(x));return out;
}
inline I temperature(const transport::Point& p,I& remainder) {
    const auto f=fermi_local_detail::decimals(p.frame);
    return ar::plus(scalar(f[2]),divide_atoms(atoms(p.v[0]),scalar(f[3]),remainder));
}
inline std::vector<std::string> face(const std::vector<std::string>& owner,
    const std::vector<std::string>& neighbor,const std::vector<std::string>& command,bool bath) {
    if(real_mantissa_bits()!=113)throw std::invalid_argument("lattice transport requires binary113");
    const auto a=transport::decode(owner);transport::valid(a);
    const auto g=fermi_local_detail::decimals(command);
    if(g.size()!=(bath?6:5))throw std::invalid_argument("lattice geometry coverage");
    for(real_t x:g)mb_affine_detail::bounded(x);
    if(!(g[0]>0 && g[1]>0 && g[3]>0 && g[4]>0 && (bath?g[2]==0:g[2]>0)))
        throw std::invalid_argument("positive lattice geometry and explicit boundary kind required");
    I ra,rb;const auto Ta=temperature(a,ra);I Tb;
    if(bath) {
        if(!(g[5]>1 && g[5]<100000))throw std::invalid_argument("lattice bath temperature domain");
        Tb=scalar(g[5]);
    } else {
        const auto b=transport::decode(neighbor);transport::valid(b);Tb=temperature(b,rb);
    }
    const real_t G=g[0]/(g[1]/g[3]+g[2]/g[4]);mb_affine_detail::bounded(G);
    if(!(G>0))throw std::invalid_argument("positive lattice conductance required");
    const auto flux=multiply(scalar(G),ar::plus(Ta,Tb,-1));
    auto out=pack("mb_lattice_face_v1",{Ta,ra,Tb,rb,flux});
    if(components({Ta,ra,Tb,rb,flux})+1>4096)throw std::invalid_argument("lattice face component budget exceeded");
    out.insert(out.begin()+2,boltzmann_detail::exported({G})[0]);return out;
}
inline std::vector<std::string> cell(const std::vector<std::string>& endpoint,
    const std::vector<std::string>& transfers,const std::vector<std::string>& command) {
    if(real_mantissa_bits()!=113)throw std::invalid_argument("lattice transport requires binary113");
    auto p=transport::decode(endpoint);transport::valid(p);
    const auto f=fermi_local_detail::decimals(p.frame),c=fermi_local_detail::decimals(command);
    if(c.size()!=1 || !(c[0]>0))throw std::invalid_argument("positive lattice exposure dt required");
    mb_affine_detail::bounded(c[0]);
    if(transfers.size()<3 || transfers.size()>262144 || transfers[0]!="mb_lattice_transfers_v1" || transfers[1]!="113")
        throw std::invalid_argument("lattice transfer framing");
    const size_t n=ar::count(transfers[2],512);size_t j=3;I integrated;
    for(size_t k=0;k<n;++k) {
        if(j>=transfers.size() || (transfers[j]!="1" && transfers[j]!="-1"))throw std::invalid_argument("lattice transfer orientation");
        const int sign=transfers[j++]=="1"?1:-1;const auto raw=transport::take(transfers,j);
        const auto flux=ar::read(raw);if(ar::write(flux)!=raw)throw std::invalid_argument("canonical lattice flux required");
        integrated=ar::plus(integrated,multiply(flux,scalar(c[0])),sign);
    }
    if(j!=transfers.size())throw std::invalid_argument("lattice transfer trailing token");
    I rV,rn,rp;
    const auto L=divide_atoms(atoms(integrated),scalar(f[4]),rV);
    const auto alpha=scalar(TCAD_CONST(1.5)*KB),cv=scalar(f[3]);
    const auto cn=ar::plus(I{},divide_atoms(atoms(multiply(multiply(alpha,scalar(f[0])),L)),cv,rn),-1);
    const auto cp=ar::plus(I{},divide_atoms(atoms(multiply(multiply(alpha,scalar(f[1])),L)),cv,rp),-1);
    p.v[0]=ar::plus(p.v[0],L);p.v[5]=ar::plus(p.v[5],cn);p.v[6]=ar::plus(p.v[6],cp);
    transport::valid(p);
    const std::vector<I> proof={integrated,L,rV,cn,rn,cp,rp};
    const size_t evidence=components(proof)+components(p.v);
    if(evidence>4096)throw std::invalid_argument("lattice cell combined component budget exceeded");
    auto out=pack("mb_lattice_cell_v1",proof);out.insert(out.begin()+2,std::to_string(evidence));
    transport::packet(out,transport::emit(p));return out;
}
} }
