#pragma once
#include "boltzmann_particle_energy.h"
#include "boltzmann_relaxation.h"

namespace tcad {
namespace mb_expanded_detail {
inline std::vector<real_t> pack(const std::vector<real_t>& input) {
    std::vector<real_t> expansion;
    for(real_t x:input) {
        real_t carry=x;std::vector<real_t> next;
        for(real_t y:expansion) {
            const real_t high=carry+y,v=high-carry,low=(carry-(high-v))+(y-v);
            mb_particle_detail::bounded(high);mb_particle_detail::bounded(low);
            if(low!=0)next.push_back(low);carry=high;
        }
        if(carry!=0)next.push_back(carry);expansion=std::move(next);
    }
    return expansion;
}
}
// Frame and carrier components follow native_boltzmann_particle_energy_raw.
// Laws: tau0n,tau0p,Tlaw_n,nlaw_n,a_n,c_n,Tlaw_p,nlaw_p,a_p,c_p,dt.
// Fixed n/bands, constant Cv, equal offsets, b=0. Each old carrier component
// and each of Qn/Qp/Ql has its own five-component response (L,dn,dp,xn,xp).
// These lineages are never summed into a scalar carrier state. A scalar root
// selects a common final temperature; energy closes separately per lineage.
inline std::vector<std::string> native_boltzmann_expanded_collision_raw(
    const std::vector<std::string>& frame,const std::vector<std::string>& dn,
    const std::vector<std::string>& dp,const std::vector<std::string>& laws,
    const std::vector<std::string>& impulses,int max_nfev=256) {
    using namespace mb_particle_detail;
    using boltzmann_relaxation_detail::softplus;
    using boltzmann_relaxation_detail::weighted;
    using boltzmann_detail::exported;
    if(laws.size()!=11 || impulses.size()!=3 || max_nfev<2 || max_nfev>4096)
        throw std::invalid_argument("MB expanded collision law/source/evaluation coverage invalid");
    // Reuse the identity transaction's full old-frame/range validation.
    if(frame.size()<10)throw std::invalid_argument("MB expanded collision frame coverage invalid");
    const auto check=native_boltzmann_particle_energy_raw(frame,dn,dp,
        {frame[0],frame[1],frame[5],frame[6],"0","0"});
    const auto f=fermi_local_detail::decimals(frame),p=fermi_local_detail::decimals(laws),q=fermi_local_detail::decimals(impulses);
    for(real_t x:p)bounded(x);for(real_t x:q)bounded(x);
    for(size_t k:{0,1,2,3,6,7,10})if(!(p[k]>0))
        throw std::invalid_argument("MB expanded collision requires positive relaxation scales");
    const size_t groups=dn.size()+dp.size()+3;
    if(groups>4096)
        throw std::invalid_argument("MB expanded collision lineage/frame budget exceeded");
    const real_t alpha=TCAD_CONST(1.5)*KB,C[]={alpha*f[0],alpha*f[1]};
    const real_t lc[]={log_q(C[0])-log_q(f[3]),log_q(C[1])-log_q(f[3])};
    const std::vector<real_t> old_lattice(f.begin()+9,f.end());
    const real_t oldT=f[2]+view(old_lattice)/f[3];
    struct Input {real_t value;int kind;std::string raw;};std::vector<Input> inputs;
    for(const auto& x:dn)inputs.push_back({fermi_local_detail::decimals({x})[0],0,x});
    for(const auto& x:dp)inputs.push_back({fermi_local_detail::decimals({x})[0],1,x});
    for(size_t k=0;k<3;++k) {
        const real_t x=q[k]/f[4];bounded(x);
        if(q[k]!=0 && x==0)throw std::invalid_argument("MB expanded source density underflow");
        inputs.push_back({x,int(k),exported({x})[0]});
    }
    struct Trial {real_t T,physicalT,residual,logtau[2],lr[2];std::vector<std::vector<real_t>> rows;};
    int evaluations=0;
    auto evaluate=[&](real_t T,bool commit=false) {
        if(evaluations++>=max_nfev)throw std::runtime_error("MB expanded collision evaluation budget exhausted");
        Trial r{};r.T=T;real_t lr[2],ll[2];
        for(size_t k=0;k<2;++k) {
            const size_t b=2+4*k;
            r.logtau[k]=log_q(p[k])+p[b+2]*log_q(T/p[b])+p[b+3]*log_q(f[k]/p[b+1]);
            bounded(r.logtau[k]);const real_t z=r.logtau[k]-log_q(p[10]);
            lr[k]=-softplus(-z);ll[k]=-softplus(z);r.lr[k]=lr[k];
        }
        const real_t an=ll[0]+lc[0],ap=ll[1]+lc[1];
        const real_t base=std::max({real_t(0),an,ap});
        const real_t logD=base+log_q(exp_q(-base)+exp_q(an-base)+exp_q(ap-base));
        std::vector<real_t> lattice=old_lattice;
        for(const auto& input:inputs) {
            const real_t v=input.value;real_t logs[5];int signs[5]={1,1,1,1,1};
            if(input.kind==0) {
                const real_t own=softplus(ap)-logD;
                logs[0]=ll[0]-logD;logs[1]=lr[0]+own;logs[2]=lr[1]+lc[1]+ll[0]-logD;
                logs[3]=ll[0]+own;logs[4]=ll[1]+lc[1]+ll[0]-logD;signs[2]=signs[4]=-1;
            } else if(input.kind==1) {
                const real_t own=softplus(an)-logD;
                logs[0]=ll[1]-logD;logs[1]=lr[0]+lc[0]+ll[1]-logD;logs[2]=lr[1]+own;
                logs[3]=ll[0]+lc[0]+ll[1]-logD;logs[4]=ll[1]+own;signs[1]=signs[3]=-1;
            } else {
                logs[0]=-logD;logs[1]=lr[0]+lc[0]-logD;logs[2]=lr[1]+lc[1]-logD;
                logs[3]=ll[0]+lc[0]-logD;logs[4]=ll[1]+lc[1]-logD;
                signs[1]=signs[2]=signs[3]=signs[4]=-1;
            }
            std::vector<real_t> row;
            for(size_t j=0;j<5;++j) {
                real_t value=(!commit && j>0)?0:signs[j]*weighted(logs[j],v);
                if(commit) {
                    bounded(value);
                    if(v!=0 && value==0)throw std::invalid_argument("nonzero MB expanded response underflows");
                } else if(j==0 && abs_q(value)<TCAD_CONST(1e-4000))value=0;
                row.push_back(value);
            }
            lattice.push_back(row[0]);r.rows.push_back(std::move(row));
        }
        r.physicalT=f[2]+view(lattice)/f[3];r.residual=T-r.physicalT;
        bounded(r.residual);return r;
    };
    auto inside=[&](real_t t){return isfinite_q(t) && t>=f[7] && t<=f[8];};
    Trial accepted=evaluate(oldT);
    const real_t gate=16*epsilon_q()*std::max({real_t(1),abs_q(f[2]),abs_q(f[7]),abs_q(f[8])});
    if(inside(accepted.physicalT))accepted=evaluate(accepted.physicalT);
    if(abs_q(accepted.residual)>gate) {
        real_t lo=f[7],hi=f[8];const auto left=evaluate(lo),right=evaluate(hi);
        if(left.residual>0 || right.residual<0)throw std::runtime_error("MB expanded temperature root not bracketed");
        if(abs_q(left.residual)<=gate)accepted=left;
        else if(abs_q(right.residual)<=gate)accepted=right;
        else for(;;) {
            const real_t mid=lo+(hi-lo)/2;
            if(mid==lo || mid==hi)throw std::runtime_error("MB expanded temperature root precision exhausted");
            accepted=evaluate(mid);if(abs_q(accepted.residual)<=gate)break;
            if(accepted.residual<0)lo=mid;else hi=mid;
        }
    }
    // Trial-only underflow is confined to root views; every committed
    // nonzero response is recomputed and range-checked, never clipped.
    accepted=evaluate(accepted.T,true);
    // Near-unity retention needs the old input AND its microscopic losses.
    // A single rounded retained value would invent energy when the exchange
    // is below that value's ulp. Stiff tails use the direct log-domain response.
    std::vector<std::vector<std::vector<std::string>>> components;
    std::vector<real_t> nd,pd,lattice_increments;
    for(size_t i=0;i<groups;++i) {
        const auto& row=accepted.rows[i];std::vector<std::vector<std::string>> pair;
        lattice_increments.push_back(row[0]);
        for(size_t k=0;k<2;++k) {
            std::vector<std::string> raw;
            if(accepted.lr[k]>-1) {
                raw.push_back(inputs[i].kind==int(k)?inputs[i].raw:"0");
                const real_t ratio=C[k]/f[3];bounded(ratio);
                const auto product_parts=product(-ratio,row[0]);
                const auto correction=exported(product_parts.empty()?std::vector<real_t>{0,0}:product_parts);
                raw.insert(raw.end(),correction.begin(),correction.end());
                raw.push_back(exported({-row[3+k]})[0]);
            } else raw=exported({row[1+k]});
            auto& values=k==0?nd:pd;
            for(real_t x:fermi_local_detail::decimals(raw))if(x!=0)values.push_back(x);
            pair.push_back(std::move(raw));
        }
        components.push_back(std::move(pair));
    }
    const auto packed_lattice=mb_expanded_detail::pack(lattice_increments);
    if(nd.size()>4096 || pd.size()>4096 || frame.size()+packed_lattice.size()>256)
        throw std::invalid_argument("MB expanded output component/frame budget exceeded");
    const real_t Tn=accepted.physicalT+view(nd)/C[0],Tp=accepted.physicalT+view(pd)/C[1];
    if(!inside(accepted.physicalT) || !inside(Tn) || !inside(Tp))
        throw std::invalid_argument("MB expanded final temperature outside configured bounds");
    auto result=exported({real_t(groups),real_t(evaluations),accepted.logtau[0],accepted.logtau[1]});
    result.insert(result.end(),check.end()-3,check.end());
    const auto temps=exported({accepted.physicalT,Tn,Tp});result.insert(result.end(),temps.begin(),temps.end());
    const auto lattice_raw=exported(packed_lattice);
    const auto lattice_count=exported({real_t(lattice_raw.size())});result.push_back(lattice_count[0]);
    result.insert(result.end(),lattice_raw.begin(),lattice_raw.end());
    for(size_t i=0;i<groups;++i) {
        const auto& row=accepted.rows[i];const auto& pair=components[i];
        const auto raw=exported({row[0],row[3],row[4],real_t(pair[0].size()),real_t(pair[1].size())});
        result.insert(result.end(),raw.begin(),raw.end());
        for(const auto& part:pair)result.insert(result.end(),part.begin(),part.end());
    }
    return result;
}
} // namespace tcad
