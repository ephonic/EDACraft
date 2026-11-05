#pragma once
#include "boltzmann_scaled_arithmetic.h"
#include "boltzmann_affine_transport.h"

namespace tcad {
// Continue ONLY the first electron-excess lineage at the saved operation6.
// Old normalization is replayed natively. No new state or clock is emitted.
inline std::vector<std::string> native_mb_scaled_collision_tail_raw(
    const std::vector<std::string>& endpoint,const std::vector<std::string>& command,
    const std::vector<std::string>& saved_capacity,const std::vector<std::string>& saved_dTl) {
    namespace ar=mb_scaled_arithmetic_detail;
    namespace old=mb_affine_detail;
    auto p=old::decode(endpoint);old::temperatures(p);
    const auto f=fermi_local_detail::decimals(p.frame),c=fermi_local_detail::decimals(command);
    if(c.size()!=6 || !(c[0]>0 && c[1]>0 && c[2]>0))
        throw std::invalid_argument("positive saved collision commands required");
    for(real_t x:c)old::bounded(x);
    const real_t alpha=TCAD_CONST(1.5)*KB;
    const old::Vec lattice(f.begin()+9,f.end());
    const auto t=old::add({f[2]},old::divide(lattice,f[3]));
    const auto e=old::coordinates(p,t,0),h=old::coordinates(p,t,1);
    const auto Cn=old::scale(e[0],alpha),Cp=old::scale(h[0],alpha);
    const auto own=old::add(e[1],old::mul(Cn,t),-1);
    auto imported=[](const old::Vec& v) {
        return ar::normalized(ar::sum(boltzmann_detail::exported(v)));
    };
    if(saved_capacity.size()>4096 || saved_dTl.size()>4096 || saved_capacity.size()*saved_dTl.size()>65536)
        throw std::invalid_argument("original saved product budgets exceeded");
    if(ar::plus(imported(Cn),ar::sum(saved_capacity),-1).sign)
        throw std::invalid_argument("saved original electron capacity mismatch");
    const auto alpha_int=imported({alpha});
    auto bn=ar::times(alpha_int,imported({f[0]}));bn.sign=-bn.sign;
    auto bp=ar::times(alpha_int,imported({f[1]}));bp.sign=-bp.sign;
    const real_t rn=c[0]/(c[0]+c[1]),rp=c[0]/(c[0]+c[2]);
    if(!(rn>0 && rn<=1 && rp>0 && rp<=1))throw std::invalid_argument("saved collision fraction range");
    const std::vector<ar::Integer> context={imported(Cn),imported(Cp),imported({rn}),imported({rp}),
        imported({f[3]}),bn,bp,imported(own),ar::normalized(ar::sum(saved_dTl))};
    std::vector<std::vector<std::string>> ctx;
    std::vector<std::string> out={"mb_scaled_collision_tail_v1","113","9","14"};
    size_t payload=0;
    auto save=[&](const std::vector<std::string>& wire,size_t components) {
        payload+=components;
        if(payload>4096)throw std::invalid_argument("original collision evidence budget exceeded");
        out.push_back(std::to_string(wire.size()));out.insert(out.end(),wire.begin(),wire.end());
    };
    for(const auto& x:context) {
        ctx.push_back(ar::write(x));save(ctx.back(),ar::count(ctx.back()[2],4096));
    }
    const auto zero=ar::write({});
    std::vector<std::vector<std::string>> v;
    auto step=[&](const std::string& op,const std::vector<std::string>& a,const std::vector<std::string>& b) {
        const auto packet=native_mb_scaled_arithmetic_raw(op,a,b);
        const size_t size=ar::count(packet[3],8195);
        std::vector<std::string> value(packet.begin()+4,packet.begin()+4+size);
        const size_t remainder_start=5+size;
        const size_t components=ar::count(value[2],4096)+ar::count(packet[remainder_start+2],4096);
        save(packet,components);v.push_back(value);
    };
    step("multiply",ctx[0],ctx[8]); // 6
    step("multiply",ctx[1],ctx[8]); // 7
    step("subtract",ctx[7],v[0]);   // 8
    step("subtract",zero,v[1]);     // 9
    step("multiply",ctx[2],v[2]);   // 10
    step("multiply",ctx[3],v[3]);   // 11
    step("add",v[4],v[5]);         // 12
    step("divide",v[6],ctx[4]);    // 13; exact remainder is also retained
    step("multiply",ctx[5],v[7]);  // 14
    step("multiply",ctx[6],v[7]);  // 15
    step("subtract",zero,v[4]);    // 16
    step("subtract",zero,v[5]);    // 17
    step("add",v[8],v[10]);        // 18
    step("add",v[9],v[11]);        // 19
    return out;
}
} // namespace tcad
