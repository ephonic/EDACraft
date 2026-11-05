#pragma once

// Conservative five-equation local assembly. FD thermodynamics, spectral
// transport, Poisson and Newton are separate native primitives. Python still
// orchestrates those calls; this header does not claim a monolithic driver.
#include "fermi_local.h"

namespace tcad {
// Cells (19): n0,p0,Tl0,n,p,Tl,u0n,un,ueqn,u0p,up,ueqp,V,Cv,
//             phi0,phi,kappa,tau_n,tau_p.
// Faces (13): owner,neighbor,Fn,Fp,En,Ep,phi0,phi,area,do,dn,bathT,bathMode.
// All face fluxes point out of the owner. E is material energy (band+kinetic).
// Output nc blocks: rn,rp,du_n,du_p,dl,exchange_n,exchange_p,work_n,work_p,
//                  energy_n,energy_p,energy_l, followed by nf Fourier fluxes.
inline std::vector<double> native_three_temperature_local_raw(
    const std::vector<std::string>& cells, const std::vector<std::string>& faces,
    double dt_s, const std::vector<std::string>& intercarrier = {},
    const std::vector<std::string>& generation = {},
    const std::vector<std::string>& traps = {},
    const std::vector<std::string>& radiation = {},
    const std::vector<std::string>& auger = {},
    const std::vector<std::string>& band_increments = {}) {
    using namespace fermi_local_detail;
    if (cells.empty() || cells.size()%19 || faces.empty() || faces.size()%13 ||
        !std::isfinite(dt_s) || dt_s<=0)
        throw std::invalid_argument("native three-temperature dimensions or timestep invalid");
    const auto c=decimals(cells),f=decimals(faces);
    const size_t nc=c.size()/19,nf=f.size()/13;
    const real_t dt=dt_s;
    std::vector<real_t> r(12*nc+nf,0);
    for (size_t i=0;i<nc;++i) {
        const size_t b=19*i;
        for (size_t k:{0,1,2,3,4,5,12,13,16,17,18}) if (c[b+k]<=0)
            throw std::invalid_argument("positive native three-temperature state and coefficients required");
        const real_t V=c[b+12];
        r[i]=V*(c[b+3]-c[b]);r[nc+i]=V*(c[b+4]-c[b+1]);
        r[2*nc+i]=V*(c[b+7]-c[b+6]);r[3*nc+i]=V*(c[b+10]-c[b+9]);
        r[4*nc+i]=V*c[b+13]*(c[b+5]-c[b+2]);
        r[5*nc+i]=dt*V*(c[b+7]-c[b+8])/c[b+17];
        r[6*nc+i]=dt*V*(c[b+10]-c[b+11])/c[b+18];
        r[9*nc+i]=r[2*nc+i]+r[5*nc+i];
        r[10*nc+i]=r[3*nc+i]+r[6*nc+i];
        r[11*nc+i]=r[4*nc+i]-r[5*nc+i]-r[6*nc+i];
    }
    for (size_t k=0;k<nf;++k) {
        const size_t b=13*k;
        if (f[b]<0 || f[b]>=nc || f[b+1]<-1 || f[b+1]>=nc ||
            f[b]!=(real_t)(size_t)f[b] || (f[b+1]!=-1 && f[b+1]!=(real_t)(size_t)f[b+1]) ||
            f[b]==f[b+1] || f[b+8]<=0 || f[b+9]<=0 ||
            (f[b+1]>=0 ? f[b+10]<=0 : f[b+10]!=0) ||
            (f[b+12]!=0 && f[b+12]!=1) ||
            (f[b+12]==1 && (f[b+1]>=0 || f[b+11]<=0)) ||
            (f[b+12]==0 && f[b+11]!=0))
            throw std::invalid_argument("native three-temperature face geometry, index or bath invalid");
        const size_t i=(size_t)f[b];const long j=(long)f[b+1];
        real_t heat=0;
        if (j>=0)
            heat=f[b+8]/(f[b+9]/c[19*i+16]+f[b+10]/c[19*j+16])*(c[19*i+5]-c[19*j+5]);
        else if (f[b+12]==1)
            heat=f[b+8]*c[19*i+16]/f[b+9]*(c[19*i+5]-f[b+11]);
        r[12*nc+k]=heat;
        const real_t facephi=(f[b+6]+f[b+7])/2;
        auto deposit=[&](size_t node,real_t sign) {
            const real_t phi=(c[19*node+14]+c[19*node+15])/2;
            const real_t wn=-si_transport::elementary_charge*dt*sign*f[b+2]*(phi-facephi);
            const real_t wp= si_transport::elementary_charge*dt*sign*f[b+3]*(phi-facephi);
            r[node]+=dt*sign*f[b+2];r[nc+node]+=dt*sign*f[b+3];
            r[7*nc+node]+=wn;r[8*nc+node]+=wp;
            r[9*nc+node]+=dt*sign*f[b+4]-wn;
            r[10*nc+node]+=dt*sign*f[b+5]-wp;
            r[11*nc+node]+=dt*sign*heat;
        };
        deposit(i,1);if (j>=0) deposit((size_t)j,-1);
    }
    if (!intercarrier.empty()) {
        if (intercarrier.size()!=3*nc)
            throw std::invalid_argument("native intercarrier exchange coverage mismatch");
        const auto e=decimals(intercarrier);
        for (size_t i=0;i<nc;++i) {
            if(e[3*i]<=0 || e[3*i+1]<=0 || e[3*i+2]<0)
                throw std::invalid_argument("positive temperatures and nonnegative intercarrier conductance required");
            // Signed energy from electrons to holes, implicit at the new state.
            // Deposit opposite entries before exporting any conservation row.
            const real_t energy=dt*c[19*i+12]*e[3*i+2]*(e[3*i]-e[3*i+1]);
            if(!isfinite_q(energy) || !std::isfinite(double(energy)))
                throw std::invalid_argument("native intercarrier exchange outside finite export range");
            r[9*nc+i]+=energy;r[10*nc+i]-=energy;r.push_back(energy);
        }
    }
    if (!generation.empty()) {
        if (generation.size()!=3*nc || intercarrier.size()!=3*nc)
            throw std::invalid_argument("native pair generation coverage mismatch");
        const auto g=decimals(generation);
        // Tail blocks: generated pair count, electron injection J, hole injection J.
        const size_t offset=r.size();r.resize(offset+3*nc,0);
        for(size_t i=0;i<nc;++i) {
            if(g[3*i]<0 || (g[3*i]>0 && g[3*i+1]+g[3*i+2]<=0))
                throw std::invalid_argument("nonnegative pair rate and positive absorbed pair energy required");
            const real_t pairs=dt*c[19*i+12]*g[3*i];
            const real_t en=pairs*g[3*i+1],ep=pairs*g[3*i+2];
            r[i]-=pairs;r[nc+i]-=pairs;
            r[9*nc+i]-=en;r[10*nc+i]-=ep;
            r[offset+i]=pairs;r[offset+nc+i]=en;r[offset+2*nc+i]=ep;
        }
    }
    if(!traps.empty()) {
        // rn,rp,Jn,Jp,sigma,Nt,Et,f0,f per cell, still in real_t.
        if(traps.size()!=9*nc) throw std::invalid_argument("native trap source coverage mismatch");
        const auto t=decimals(traps);const size_t offset=r.size();r.resize(offset+8*nc,0);
        for(size_t i=0;i<nc;++i) {
            const size_t b=9*i;const real_t V=c[19*i+12];
            if(t[b+5]<0 || t[b+7]<=0 || t[b+7]>=1 || t[b+8]<=0 || t[b+8]>=1)
                throw std::invalid_argument("native trap density or occupancy invalid");
            const real_t cn=dt*V*t[b],cp=dt*V*t[b+1],en=dt*V*t[b+2],ep=dt*V*t[b+3];
            const real_t occupied=V*t[b+5]*(t[b+8]-t[b+7]);
            const real_t stored=t[b+6]*occupied,heat=en+ep-t[b+6]*(cn-cp);
            r[i]+=cn;r[nc+i]+=cp;r[9*nc+i]+=en;r[10*nc+i]+=ep;r[11*nc+i]-=heat;
            const real_t values[]={occupied-cn+cp,stored,cn,cp,en,ep,heat,dt*V*t[b+4]};
            for(size_t k=0;k<8;++k) r[offset+k*nc+i]=values[k];
        }
    }
    if(!radiation.empty()) {
        // R,Jn,Jp,sigma per cell: net recombination, removed energies, entropy.
        if(radiation.size()!=4*nc) throw std::invalid_argument("native radiative coverage mismatch");
        const auto a=decimals(radiation);const size_t offset=r.size();r.resize(offset+5*nc,0);
        for(size_t i=0;i<nc;++i) {
            const real_t factor=dt*c[19*i+12];
            const real_t pairs=factor*a[4*i],en=factor*a[4*i+1],ep=factor*a[4*i+2];
            r[i]+=pairs;r[nc+i]+=pairs;r[9*nc+i]+=en;r[10*nc+i]+=ep;
            const real_t values[]={pairs,en,ep,en+ep,factor*a[4*i+3]};
            for(size_t k=0;k<5;++k) r[offset+k*nc+i]=values[k];
        }
    }
    if(!auger.empty()) {
        // R,Un,Up,sigma: signed recombination and ADDED carrier energies.
        if(auger.size()!=4*nc) throw std::invalid_argument("native Auger coverage mismatch");
        const auto a=decimals(auger);const size_t offset=r.size();r.resize(offset+4*nc,0);
        for(size_t i=0;i<nc;++i) {
            const real_t factor=dt*c[19*i+12];
            const real_t pairs=factor*a[4*i],en=factor*a[4*i+1],ep=factor*a[4*i+2];
            r[i]+=pairs;r[nc+i]+=pairs;r[9*nc+i]-=en;r[10*nc+i]-=ep;
            const real_t values[]={pairs,en,ep,factor*a[4*i+3]};
            for(size_t k=0;k<4;++k) r[offset+k*nc+i]=values[k];
        }
    }
    if(!band_increments.empty()) {
        if(band_increments.size()!=2*nc)
            throw std::invalid_argument("native band increment coverage mismatch");
        const auto shifts=decimals(band_increments);
        const size_t offset=r.size();r.resize(offset+2*nc,0);
        for(size_t i=0;i<nc;++i) for(size_t s=0;s<2;++s) {
            // Exact discrete product rule: d(nE)=E_mid*dn+n_mid*dE.
            // Internal work is deposited with opposite signs before export.
            const real_t w=c[19*i+12]*(c[19*i+s]+c[19*i+3+s])/2*shifts[2*i+s];
            r[(9+s)*nc+i]-=w;r[11*nc+i]+=w;r[offset+s*nc+i]=w;
        }
    }
    return exported(r);
}

// The original three-argument public primitive and its output layout remain
// available. This explicit extension appends nc signed exchange energies after
// the nf Fourier fluxes; lattice relaxation entries retain their old meaning.
inline std::vector<double> native_three_temperature_exchange_local_raw(
    const std::vector<std::string>& cells,const std::vector<std::string>& faces,
    double dt_s,const std::vector<std::string>& exchange) {
    if(exchange.empty()) throw std::invalid_argument("explicit intercarrier exchange inputs required");
    return native_three_temperature_local_raw(cells,faces,dt_s,exchange);
}

inline std::vector<double> native_three_temperature_generation_local_raw(
    const std::vector<std::string>& cells,const std::vector<std::string>& faces,
    double dt_s,const std::vector<std::string>& exchange,const std::vector<std::string>& generation) {
    if(generation.empty()) throw std::invalid_argument("explicit pair generation inputs required");
    return native_three_temperature_local_raw(cells,faces,dt_s,exchange,generation);
}
} // namespace tcad
