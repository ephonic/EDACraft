#pragma once
#include "boltzmann_particle_energy.h"

namespace tcad { namespace mb_flat_detail {
inline std::vector<real_t> pack(const std::vector<real_t>& input) {
    std::vector<real_t> e;
    for(real_t x:input) {
        real_t q=x;std::vector<real_t> next;
        for(real_t y:e) {
            const real_t h=q+y,v=h-q,l=(q-(h-v))+(y-v);
            mb_particle_detail::bounded(h);mb_particle_detail::bounded(l);
            if(l!=0)next.push_back(l);
            q=h;
        }
        if(q!=0)next.push_back(q);
        e=std::move(next);
    }
    // Compress a weakly nonoverlapping Grow result into a strongly
    // nonoverlapping expansion. Both sweeps use exact FastTwoSum residuals.
    if(e.empty())return e;
    std::vector<real_t> h(e.size());size_t bottom=e.size()-1;real_t Q=e.back();
    for(size_t i=e.size()-1;i>0;--i) {
        const real_t high=Q+e[i-1],low=e[i-1]-(high-Q);
        mb_particle_detail::bounded(high);mb_particle_detail::bounded(low);
        if(low!=0){h[bottom--]=high;Q=low;}else Q=high;
    }
    h[bottom]=Q;std::vector<real_t> result;Q=h[bottom];
    for(size_t i=bottom+1;i<h.size();++i) {
        const real_t high=h[i]+Q,low=Q-(high-h[i]);
        mb_particle_detail::bounded(high);mb_particle_detail::bounded(low);
        if(low!=0)result.push_back(low);
        Q=high;
    }
    if(Q!=0)result.push_back(Q);
    return result;
}
} // namespace mb_flat_detail

// Uniform parabolic DOS, identical band and lattice coordinate on both sides.
// Geometry: area, owner distance, neighbor distance, owner/neighbor mobility.
// Outward number = G*kB*(no*To-nn*Tn).
// Outward material energy = E*number+G*(5/2)*kB^2*(no*To^2-nn*Tn^2).
// G=area/(do/muo+dn/mun)/q. No field, heat flux, state update or time step.
inline std::vector<std::string> native_boltzmann_expanded_flat_face_raw(
    const std::vector<std::string>& owner,const std::vector<std::string>& on,const std::vector<std::string>& op,
    const std::vector<std::string>& neighbor,const std::vector<std::string>& nn,const std::vector<std::string>& np,
    const std::vector<std::string>& geometry) {
    using namespace mb_particle_detail;
    using boltzmann_detail::exported;
    using mb_flat_detail::pack;
    for(const auto& triple:{std::vector<std::vector<std::string>>{owner,on,op},std::vector<std::vector<std::string>>{neighbor,nn,np}}) {
        if(triple[0].size()<10)throw std::invalid_argument("MB flat face frame coverage invalid");
        native_boltzmann_particle_energy_raw(triple[0],triple[1],triple[2],
            {triple[0][0],triple[0][1],triple[0][5],triple[0][6],"0","0"});
    }
    if(geometry.size()!=5 || owner.size()!=neighbor.size())throw std::invalid_argument("MB flat face coverage invalid");
    const auto a=fermi_local_detail::decimals(owner),b=fermi_local_detail::decimals(neighbor),g=fermi_local_detail::decimals(geometry);
    for(real_t x:g)bounded(x);
    if(!(g[0]>0 && g[1]>0 && g[2]>=0 && g[3]>0 && g[4]>0))throw std::invalid_argument("MB flat face geometry invalid");
    for(size_t j:{2,3,5,6})if(a[j]!=b[j])throw std::invalid_argument("MB flat face requires common lattice and bands");
    for(size_t j=9;j<a.size();++j)if(a[j]!=b[j])throw std::invalid_argument("MB flat face requires identical lattice history");
    const real_t inverse=1/a[3],resistance=g[1]/g[3]+g[2]/g[4],G=g[0]/resistance/si_transport::elementary_charge;
    for(real_t x:{inverse,resistance,G})if(!(x>0))throw std::invalid_argument("MB flat face positive scale underflow");
    bounded(inverse);bounded(resistance);bounded(G);
    std::vector<real_t> thermal={a[2]};
    for(size_t j=9;j<a.size();++j){const auto v=product(a[j],inverse);thermal.insert(thermal.end(),v.begin(),v.end());}
    thermal=pack(thermal);
    std::vector<std::string> result=exported({inverse});
    auto emit=[&](const std::vector<real_t>& v){const auto count=exported({real_t(v.size())});result.push_back(count[0]);const auto raw=exported(v);result.insert(result.end(),raw.begin(),raw.end());};
    emit(thermal);
    size_t terms=0,parts=0;
    for(size_t k=0;k<2;++k) {
        const auto x=fermi_local_detail::decimals(k==0?on:op),y=fermi_local_detail::decimals(k==0?nn:np);
        std::vector<real_t> diff=x,sum=x;
        for(real_t z:y){diff.push_back(-z);sum.push_back(z);}
        const auto D=pack(difference(a[k],b[k])),d=pack(diff),s=pack(sum),h=pack(y);
        const std::vector<real_t> coefficients={G*KB,G*2/3,a[5+k],G*TCAD_CONST(2.5)*KB*KB,
            G*TCAD_CONST(10.)/3*KB,G*TCAD_CONST(10.)/9/a[k],-G*TCAD_CONST(10.)/9/a[k]/b[k]};
        for(size_t j=0;j<coefficients.size();++j){bounded(coefficients[j]);if(j!=2 && coefficients[j]==0)throw std::invalid_argument("MB flat face coefficient underflow");}
        emit(coefficients);emit(D);emit(d);emit(s);emit(h);
        struct Row {int kind;std::vector<real_t> factors,value;};std::vector<Row> rows;std::vector<real_t> number;
        auto add=[&](int kind,std::vector<real_t> factors) {
            if(++terms>4096)throw std::invalid_argument("MB flat face term budget exceeded");
            std::vector<real_t> v=coefficients[kind]==0?std::vector<real_t>{}:std::vector<real_t>{coefficients[kind]};
            for(real_t z:factors)v=multiply(v,z);
            v=pack(v);parts+=v.size();
            if(parts>4096)throw std::invalid_argument("MB flat face component budget exceeded");
            if(kind<2)number.insert(number.end(),v.begin(),v.end());
            rows.push_back({kind,std::move(factors),std::move(v)});
        };
        for(real_t z:D)for(real_t t:thermal)add(0,{z,t});
        for(real_t z:d)add(1,{z});
        for(real_t z:number)add(2,{z});
        for(real_t z:D)for(real_t t:thermal)for(real_t u:thermal)add(3,{z,t,u});
        for(real_t z:d)for(real_t t:thermal)add(4,{z,t});
        for(real_t z:d)for(real_t u:s)add(5,{z,u});
        for(real_t z:h)for(real_t u:h)for(real_t v:D)add(6,{z,u,v});
        const auto count=exported({real_t(rows.size())});result.push_back(count[0]);
        for(const auto& row:rows){const auto kind=exported({real_t(row.kind)});result.push_back(kind[0]);emit(row.factors);emit(row.value);}
    }
    return result;
}
} // namespace tcad
