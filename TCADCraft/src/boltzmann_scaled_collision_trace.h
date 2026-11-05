#pragma once
#include "boltzmann_scaled_arithmetic.h"
#include "boltzmann_affine_transport.h"

namespace tcad { namespace mb_scaled_collision_trace_detail {
namespace ar=mb_scaled_arithmetic_detail;
using I=ar::Integer;
struct Stop {};
struct Trace {
    size_t evidence=0,records=0,requested=0;
    std::string blocked="-";
    std::vector<std::string> body;
    void save(const std::string& label,I q,I r={}) {
        const auto a=ar::write(q),b=ar::write(r);
        const size_t cost=ar::count(a[2],4096)+ar::count(b[2],4096);
        if(evidence+cost>4096) {blocked=label;requested=evidence+cost;throw Stop{};}
        evidence+=cost;++records;body.push_back(label);
        for(const auto* wire:{&a,&b}) {
            body.push_back(std::to_string(wire->size()));
            body.insert(body.end(),wire->begin(),wire->end());
        }
    }
};
inline I imported(const std::vector<std::string>& raw) {return ar::normalized(ar::sum(raw));}
inline I scalar(real_t x) {return imported(boltzmann_detail::exported({x}));}
inline I multiply(I a,I b) {
    if(ar::count(ar::write(a)[2],4096)*ar::count(ar::write(b)[2],4096)>65536)
        throw std::invalid_argument("original trace product pair budget exceeded");
    return ar::times(a,b);
}
inline I divide_atoms(const std::vector<I>& atoms,I b,I& remainder) {
    I q;remainder={};
    for(const auto& a:atoms) {
        const auto h=ar::rounded_ratio(a,b);
        const auto l=ar::rounded_ratio(ar::plus(a,multiply(b,h),-1),b);
        const auto part=ar::plus(h,l);
        q=ar::plus(q,part);
        remainder=ar::plus(remainder,ar::plus(a,multiply(b,part),-1));
    }
    return q;
}
inline std::vector<I> atoms(I a) {
    const auto wire=ar::write(a);std::vector<I> result;
    for(size_t j=3;j<wire.size();j+=2)
        result.push_back(ar::coefficient(wire[j],ar::bounded_decimal_integer(wire[j+1])));
    return result;
}
} // namespace mb_scaled_collision_trace_detail

// Complete fixed-tau arithmetic attempt. Budget exhaustion returns an audited
// prefix and the first omitted record, never an accepted state or new clock.
inline std::vector<std::string> native_mb_scaled_collision_trace_raw(
    const std::vector<std::string>& endpoint,const std::vector<std::string>& command) {
    using namespace mb_scaled_collision_trace_detail;
    namespace old=mb_affine_detail;
    if(real_mantissa_bits()!=113)throw std::invalid_argument("collision trace requires binary113");
    auto p=old::decode(endpoint);old::temperatures(p);
    const auto f=fermi_local_detail::decimals(p.frame),c=fermi_local_detail::decimals(command);
    if(c.size()!=6 || !(c[0]>0 && c[1]>0 && c[2]>0))
        throw std::invalid_argument("positive fixed-tau trace command required");
    for(real_t x:c)old::bounded(x);
    Trace trace;
    try {
        const I alpha=scalar(TCAD_CONST(1.5)*KB),cv=scalar(f[3]),volume=scalar(f[4]),one=scalar(1);
        trace.save("alpha",alpha);
        std::vector<I> R;
        for(size_t k=0;k<2;++k) {
            const real_t r=c[0]/(c[0]+c[k+1]);
            old::bounded(r);
            if(!(r>0 && r<=1))throw std::invalid_argument("trace exchange coefficient outside range");
            R.push_back(scalar(r));trace.save("R"+std::to_string(k),R.back());
        }
        std::vector<I> original_lattice;
        for(size_t j=9;j<f.size();++j)original_lattice.push_back(scalar(f[j]));
        I rest;
        const auto qold=divide_atoms(original_lattice,cv,rest);trace.save("qold",qold,rest);
        const auto t=ar::plus(scalar(f[2]),qold);trace.save("thermal",t);
        std::vector<I> n,K,C,delta,capacity;
        for(size_t k=0;k<2;++k) {
            const auto dn=imported(boltzmann_detail::exported(p.change[k]));
            const auto du=imported(boltzmann_detail::exported(p.change[2+k]));
            n.push_back(ar::plus(scalar(f[k]),dn));
            trace.save("n"+std::to_string(k),n.back());
            K.push_back(ar::plus(ar::plus(multiply(multiply(alpha,t),scalar(f[k])),
                         imported(k==0?p.en:p.ep)),ar::plus(du,multiply(scalar(f[5+k]),dn),-1)));
            trace.save("K"+std::to_string(k),K.back());
            C.push_back(multiply(alpha,n.back()));trace.save("C"+std::to_string(k),C.back());
            delta.push_back(ar::plus(K.back(),multiply(C.back(),t),-1));
            trace.save("delta"+std::to_string(k),delta.back());
            capacity.push_back(divide_atoms(atoms(C.back()),cv,rest));
            trace.save("capacity"+std::to_string(k),capacity.back(),rest);
        }
        const auto D=ar::plus(ar::plus(one,multiply(R[0],capacity[0])),multiply(R[1],capacity[1]));
        if(D.sign<=0)throw std::invalid_argument("positive scaled denominator required");
        trace.save("D",D);
        const auto head=ar::rounded_ratio(D,one);trace.save("Dhead",head);
        struct Input {I value;size_t kind;bool source;};
        std::vector<Input> inputs;
        for(size_t k=0;k<2;++k)if(delta[k].sign)inputs.push_back({delta[k],k,false});
        for(size_t k=0;k<3;++k) {
            const auto source=divide_atoms({scalar(c[k+3])},volume,rest);
            trace.save("source"+std::to_string(k),source,rest);
            if(source.sign)inputs.push_back({source,k,true});
        }
        I L,un,up;
        for(size_t j=0;j<inputs.size();++j) {
            const auto input=inputs[j];
            const std::string prefix="lineage"+std::to_string(j)+".";
            trace.save(prefix+"input",input.value);
            const I ownn=input.kind==0?input.value:I{},ownp=input.kind==1?input.value:I{};
            const I qn=input.source?ownn:I{},qp=input.source?ownp:I{},ql=input.kind==2?input.value:I{};
            std::vector<I> v;
            auto op=[&](I q,I r=I{}) {trace.save(prefix+std::to_string(v.size()),q,r);v.push_back(q);};
            auto div=[&](I a,I b) {I r;const auto q=divide_atoms(atoms(a),b,r);op(q,r);};
            op(multiply(input.value,input.kind==2?one:R[input.kind]));
            div(v[0],head);
            op(ar::plus(v[0],multiply(D,v[1]),-1));
            div(v[2],head);
            op(ar::plus(v[1],v[3]));
            div(v[4],cv);
            op(multiply(C[0],v[5]));op(multiply(C[1],v[5]));
            op(ar::plus(ownn,v[6],-1));op(ar::plus(ownp,v[7],-1));
            op(multiply(R[0],v[8]));op(multiply(R[1],v[9]));
            op(ar::plus(ar::plus(v[10],v[11]),ql));
            div(v[12],cv);
            op(multiply(multiply(alpha,scalar(-f[0])),v[13]));
            op(multiply(multiply(alpha,scalar(-f[1])),v[13]));
            op(ar::plus(qn,v[10],-1));op(ar::plus(qp,v[11],-1));
            op(ar::plus(v[14],v[16]));op(ar::plus(v[15],v[17]));
            L=ar::plus(L,v[12]);un=ar::plus(un,v[18]);up=ar::plus(up,v[19]);
        }
        trace.save("aggregate.L",L);trace.save("aggregate.un",un);trace.save("aggregate.up",up);
    } catch(const Stop&) {}
    std::vector<std::string> out={"mb_scaled_collision_trace_v1","113",
        trace.blocked=="-"?"complete":"evidence_budget_exceeded",std::to_string(trace.records),
        std::to_string(trace.evidence),trace.blocked,std::to_string(trace.requested)};
    out.insert(out.end(),trace.body.begin(),trace.body.end());return out;
}
} // namespace tcad
