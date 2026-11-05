#pragma once
#include "boltzmann_scaled_transport.h"

namespace tcad { namespace mb_endpoint_collision_compact_detail {
using namespace mb_scaled_collision_trace_detail;
inline std::string kind(const std::string& label) {
    if(label.rfind("aggregate.",0)==0)return "aggregate_value";
    if(label=="qold" || label=="capacity0" || label=="capacity1" ||
       label=="source0" || label=="source1" || label=="source2")return "division_remainder";
    if(label.rfind("lineage",0)==0) {
        const auto suffix=label.substr(label.find('.')+1);
        if(suffix=="1" || suffix=="3" || suffix=="5" || suffix=="13")return "division_remainder";
    }
    return {};
}
struct Trace {
    size_t evidence=0,records=0,stored=0,expanded=0,requested=0;
    std::string blocked="-",last="start";
    std::vector<std::string> body;
    void save(const std::string& label,I q,I r={}) {
        const auto a=ar::write(q),b=ar::write(r);
        const auto type=kind(label);
        const auto& selected=type=="aggregate_value"?a:b;
        const size_t cost=type.empty()?0:ar::count(selected[2],4096);
        if(evidence+cost>4096) {blocked=label;requested=evidence+cost;throw Stop{};}
        last=label;++records;expanded+=ar::count(a[2],4096)+ar::count(b[2],4096);
        if(expanded>99999)throw std::invalid_argument("compact expanded diagnostic count budget exceeded");
        if(type.empty())return;
        ++stored;evidence+=cost;
        body.insert(body.end(),{label,type,std::to_string(selected.size())});
        body.insert(body.end(),selected.begin(),selected.end());
    }
};
} // namespace mb_endpoint_collision_compact_detail
// Residual checkpoints plus exact aggregate increments. All omitted values
// are determined by the pinned operation graph and independently recomputed.
// The expanded trace counter is diagnostic, not a claim to fit the old wire.
inline std::vector<std::string> native_mb_endpoint_collision_compact_raw(
    const std::vector<std::string>& endpoint,const std::vector<std::string>& command) {
    using namespace mb_scaled_collision_trace_detail;
    namespace old=mb_affine_detail;
    if(real_mantissa_bits()!=113)throw std::invalid_argument("collision trace requires binary113");
    auto p=mb_scaled_transport_detail::decode(endpoint);mb_scaled_transport_detail::valid(p);
    const auto f=fermi_local_detail::decimals(p.frame),c=fermi_local_detail::decimals(command);
    if(c.size()!=6 || !(c[0]>0 && c[1]>0 && c[2]>0))
        throw std::invalid_argument("positive fixed-tau trace command required");
    for(real_t x:c)old::bounded(x);
    mb_endpoint_collision_compact_detail::Trace trace;
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
        original_lattice=atoms(p.v[0]);
        I rest;
        const auto qold=divide_atoms(original_lattice,cv,rest);trace.save("qold",qold,rest);
        const auto t=ar::plus(scalar(f[2]),qold);trace.save("thermal",t);
        std::vector<I> n,K,C,delta,capacity;
        for(size_t k=0;k<2;++k) {
            const auto dn=p.v[3+k];
            const auto du=p.v[5+k];
            n.push_back(ar::plus(scalar(f[k]),dn));
            trace.save("n"+std::to_string(k),n.back());
            K.push_back(ar::plus(ar::plus(multiply(multiply(alpha,t),scalar(f[k])),
                         p.v[1+k]),ar::plus(du,multiply(scalar(f[5+k]),dn),-1)));
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
    catch(const std::exception& e) {throw std::invalid_argument(std::string("endpoint collision after ")+trace.last+": "+e.what());}
    std::vector<std::string> out={"mb_endpoint_collision_compact_v1","113",
        trace.blocked=="-"?"complete":"evidence_budget_exceeded",std::to_string(trace.records),
        std::to_string(trace.stored),std::to_string(trace.evidence),std::to_string(trace.expanded),
        trace.blocked,std::to_string(trace.requested)};
    out.insert(out.end(),trace.body.begin(),trace.body.end());return out;
}
} // namespace tcad
