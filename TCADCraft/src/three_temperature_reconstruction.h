#pragma once
#include "fermi_energy_coordinates.h"
#include <array>

namespace tcad { namespace three_reconstruction_detail {
// Explicitly scoped, cell-average preserving reconstruction. No stored-state
// values are replaced by the derived reservoirs used for candidate transport.
struct Reconstruction {
    bool enabled=false;
    std::vector<real_t> edges,xi;
    struct Entry {bool valid=false;real_t n=0,k=0;double T=0;std::vector<double> r;};
    std::vector<std::array<Entry,4>> cache[2];
    std::vector<size_t> next[2];

    template<class Context> void initialize(const Context& c) {
        const size_t nc=c.nc;
        if(nc<3 || !c.band_law.empty() || c.trapped || c.radiative ||
           !c.intercarrier.empty() || !c.generation.empty() || !c.collision_events.empty())
            throw std::invalid_argument("quadratic reconstruction requires >=3 fixed-band source-free cells");
        for(size_t s=0;s<2;++s) {
            if(c.valleys[s].size()!=4 || c.valleys[s][3]!=0)
                throw std::invalid_argument("quadratic reconstruction requires one zero-offset valley per carrier");
            cache[s].resize(nc);next[s].assign(nc,0);
        }
        real_t area=0;size_t contacts=0,axial=0;
        for(size_t f=0;f<c.nf;++f) {
            const bool active=c.F(f,1)>=0 || c.mode(f,15);
            if(c.F(f,2)!=0) {
                if(c.F(f,3)!=0 || c.F(f,4)!=0 || !active || c.F(f,19)!=2)
                    throw std::invalid_argument("quadratic reconstruction requires axial linear-series faces");
                if(area==0) area=c.F(f,10);
                if(abs_q(c.F(f,10)/area-1)>TCAD_CONST(1e-12))
                    throw std::invalid_argument("quadratic reconstruction requires constant cross section");
                const long i=long(c.F(f,0)),j=long(c.F(f,1));
                if(j>=0 && std::abs(j-i)!=1)
                    throw std::invalid_argument("quadratic reconstruction requires ordered adjacent cells");
                edges.push_back(c.F(f,5));++axial;
                if(j<0) {if(!c.mode(f,15))throw std::invalid_argument("quadratic endpoint contacts required");++contacts;}
            } else if(active || c.mode(f,13) || c.mode(f,8))
                throw std::invalid_argument("quadratic reconstruction requires insulating lateral faces");
        }
        std::sort(edges.begin(),edges.end());
        if(axial!=nc+1 || contacts!=2 || edges.size()!=nc+1)
            throw std::invalid_argument("quadratic axial face coverage mismatch");
        for(size_t i=0;i<nc;++i) {
            const real_t width=edges[i+1]-edges[i];
            if(width<=0 || c.C(i,5)!=0 || c.C(i,11)!=c.C(0,11) ||
               abs_q(c.C(i,8)-c.C(0,8))>TCAD_CONST(1e-12)*width || abs_q(c.C(i,9)-c.C(0,9))>TCAD_CONST(1e-12)*width ||
               c.C(i,13)!=c.C(0,13) || c.C(i,14)!=c.C(0,14) ||
               abs_q(width*area/c.C(i,0)-1)>TCAD_CONST(1e-12))
                throw std::invalid_argument("quadratic reconstruction material or Cartesian volume mismatch");
            const real_t x=(c.C(i,7)-edges[i])/width-TCAD_CONST(.5);
            if(abs_q(x)>TCAD_CONST(1e-12))
                throw std::invalid_argument("quadratic reconstruction requires midpoint centers");
            xi.push_back(x);
        }
        enabled=true;
    }

    std::vector<real_t> centers(const std::vector<real_t>& mean,real_t floor) const {
        const size_t nc=mean.size();std::vector<real_t> result(nc);
        for(size_t i=0;i<nc;++i) {
            if(!(mean[i]>=floor))throw FermiStateDomainError("quadratic mean below required floor");
            const size_t start=i==0?0:(i==nc-1?nc-3:i-1);
            const real_t h=edges[i+1]-edges[i],mid=(edges[i+1]+edges[i])/2;
            real_t m1[3],m2[3];
            for(size_t j=0;j<3;++j) {
                const real_t l=(edges[start+j]-mid)/h,r=(edges[start+j+1]-mid)/h;
                m1[j]=(l+r)/2;m2[j]=(l*l+l*r+r*r)/3-TCAD_CONST(1.0)/12;
            }
            const size_t row=i-start;size_t one=(row+1)%3,two=(row+2)%3;
            const real_t a=m1[one]-m1[row],b=m2[one]-m2[row],d=m1[two]-m1[row],e=m2[two]-m2[row];
            const real_t det=a*e-b*d;
            if(!isfinite_q(det) || abs_q(det)<128*epsilon_q()*std::max(real_t(1),abs_q(a*e)+abs_q(b*d)))
                throw FermiStateDomainError("quadratic stencil is ill-conditioned");
            const real_t y=mean[start+one]-mean[i],z=mean[start+two]-mean[i];
            real_t slope=(y*e-b*z)/det,curve=(a*z-y*d)/det;
            auto value=[&](real_t x){return mean[i]+slope*x+curve*(x*x-TCAD_CONST(1.0)/12);};
            real_t low=std::min(value(TCAD_CONST(-.5)),value(TCAD_CONST(.5)));
            if(curve>0) {const real_t vertex=-slope/(2*curve);if(vertex>TCAD_CONST(-.5) && vertex<TCAD_CONST(.5))low=std::min(low,value(vertex));}
            if(low<floor) {
                real_t theta=(mean[i]-floor)/(mean[i]-low)*(1-16*epsilon_q());
                slope*=theta;curve*=theta;
                real_t checked=std::min(value(TCAD_CONST(-.5)),value(TCAD_CONST(.5)));
                if(curve>0) {const real_t v=-slope/(2*curve);if(v>TCAD_CONST(-.5) && v<TCAD_CONST(.5))checked=std::min(checked,value(v));}
                if(checked<floor){slope=0;curve=0;}
            }
            result[i]=value(xi[i]);
            if(!isfinite_q(result[i]) || result[i]<floor)
                throw FermiStateDomainError("quadratic center outside scalar bounds");
        }
        return result;
    }

    template<class Context> void states(const Context& c,size_t s,const std::vector<real_t>& density,
            const std::vector<std::vector<double>>& mean,const std::vector<double>& T,
            const std::vector<double>& Tl,std::vector<std::vector<double>>& rows,
            std::vector<double>& temperatures,std::vector<double>& lattice) {
        std::vector<real_t> kinetic(c.nc),heat(c.nc);
        for(size_t i=0;i<c.nc;++i) {kinetic[i]=real_t(mean[i][1])-c.C(i,13+s)*density[i];heat[i]=c.C(i,11)*real_t(Tl[i]);}
        const auto n=centers(density,0),k=centers(kinetic,0),h=centers(heat,c.C(0,11));
        rows.resize(c.nc);temperatures.resize(c.nc);lattice.resize(c.nc);
        for(size_t i=0;i<c.nc;++i) {
            lattice[i]=double(h[i]/c.C(i,11));
            // Lattice energy is independent of the cached carrier n/kinetic
            // key. Validate every derived lattice state before cache reuse.
            if(n[i]<=0 || k[i]<=0 || !(lattice[i]>1 && lattice[i]<1e5))
                throw FermiStateDomainError("quadratic candidate requires positive FD state");
            bool hit=false;
            for(const auto& entry:cache[s][i])if(entry.valid && entry.n==n[i] && entry.k==k[i]) {
                rows[i]=entry.r;temperatures[i]=entry.T;hit=true;break;
            }
            if(hit)continue;
            real_t lo=1,hi=TCAD_CONST(1e5),t=T[i];bool converged=false;
            for(int iteration=0;iteration<48;++iteration) {
                const auto r=fermi_energy_detail::reservoir(n[i],t,0,c.valleys[s]);
                const real_t error=r.u-k[i];
                if(abs_q(error)<=TCAD_CONST(1e-24)*k[i]){converged=true;break;}
                if(error>0)hi=t;else lo=t;
                real_t trial=t-error/r.capacity;
                if(!isfinite_q(trial) || !(trial>lo && trial<hi))trial=(lo+hi)/2;
                t=trial;
            }
            if(!converged || !(double(t)>1 && double(t)<1e5))
                throw FermiStateDomainError("quadratic FD center decoding outside supported bounds");
            temperatures[i]=double(t);std::vector<std::string> input;
            for(real_t v:{n[i],real_t(temperatures[i]),c.C(i,13+s)})input.push_back(fermi_dispatch_detail::text(v));
            rows[i]=native_fermi_reservoir_raw(input,c.valleys[s]);
            auto& entry=cache[s][i][next[s][i]];entry={true,n[i],k[i],temperatures[i],rows[i]};next[s][i]=(next[s][i]+1)%4;
        }
    }
};

inline std::vector<double> blend(const std::vector<double>& low,const std::vector<double>& high,
        double To,double Tn,double muo,double mun,real_t po,real_t pn,real_t pf,real_t charge) {
    const real_t af=(real_t(muo)+charge*(po-pf))/real_t(To)-(real_t(mun)+charge*(pn-pf))/real_t(Tn);
    const real_t ag=1/real_t(Tn)-1/real_t(To);
    auto sigma=[&](const std::vector<double>& v){return af*real_t(v[0])+ag*real_t(v[2]);};
    const real_t a=sigma(low),b=sigma(high);
    if(a<0)throw FermiStateDomainError("midpoint-work baseline has negative stored-state entropy pairing");
    double theta=b>=0?1.:double(a/(a-b))*(1-16*std::numeric_limits<double>::epsilon());
    auto mix=[&](double fraction) {
        if(fraction==1)return high;
        if(fraction==0)return low;
        std::vector<double> out(low.size());
        for(size_t j=0;j<out.size();++j)out[j]=double((1-real_t(fraction))*real_t(low[j])+real_t(fraction)*real_t(high[j]));
        return out;
    };
    auto out=mix(theta);
    if(sigma(out)<0){theta=0;out=low;}
    out[3]=double(sigma(out));out[4]=std::min(low[4],high[4]);out[5]=std::max(low[5],high[5]);
    out.insert(out.end(),low.begin(),low.end());out.insert(out.end(),high.begin(),high.end());
    out.push_back(theta);out.push_back(double(sigma(out)));return out;
}
} } // namespaces
