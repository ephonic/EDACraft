#pragma once
#include "boltzmann_lattice_transport.h"
namespace tcad { namespace mb_recomputed_lattice_detail {
using namespace mb_lattice_detail;
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
    const size_t evidence=components(p.v),expanded=components(proof)+evidence;
    if(evidence>4096)throw std::invalid_argument("lattice cell combined component budget exceeded");
    if(expanded>8192)throw std::invalid_argument("recomputed lattice expanded component budget exceeded");
    std::vector<std::string> out={"mb_lattice_recomputed_cell_v1","113",std::to_string(evidence),std::to_string(expanded)};
    transport::packet(out,transport::emit(p));return out;
}
} }
