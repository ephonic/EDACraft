#pragma once
#include "spectral_auger.h"
#include <array>
#include <cstring>

// Five independent-temperature conservation equations and Newton in one native
// call. Only model/state inputs cross the boundary; no precomputed physics or
// Python residual callback is accepted. Final exported quantities are audited
// independently by the public driver before it returns a new immutable state.
#include "fermi_dispatch.h"
#include "three_temperature_local.h"
#include "three_temperature_reconstruction.h"
#include "spectral_trap_capture.h"
#include "spectral_radiative.h"

namespace tcad {
struct ThreeTemperatureDispatchResult {
    int density_mantissa_bits=std::numeric_limits<long double>::digits;
    std::vector<std::string> n,p;
    std::vector<double> temperature_n,temperature_p,temperature_l,local,fn,fp,energy_n,energy_p;
    std::vector<double> tau_n,tau_p;
    std::vector<double> trap_fraction;
    std::vector<std::vector<double>> trap_moments;
    std::vector<std::vector<double>> radiative_moments;
    std::vector<std::vector<std::vector<double>>> auger_moments;
    std::vector<std::vector<double>> old_poisson,new_poisson,moments,newton;
};

namespace three_temperature_dispatch_detail {
using fermi_dispatch_detail::pack;
using fermi_dispatch_detail::text;

inline bool auger_schema(const std::vector<double>& p) {
    return p.size()>17 && (p[17]==-6 || p[17]==-7 || p[17]==-8 || p[17]==-9);
}
inline std::vector<std::vector<real_t>> auger_tables(const std::vector<double>& p) {
    std::vector<std::vector<real_t>> tables;
    if(!auger_schema(p)) return tables;
    for(double v:p) if(!std::isfinite(v)) throw std::invalid_argument("finite native Auger parameters required");
    for(size_t b=18;b<p.size();) {
        if(p.size()-b<10 || p[b+9]<1 || p[b+9]>4096 || p[b+9]!=std::floor(p[b+9]))
            throw std::invalid_argument("native Auger cell record and event count invalid");
        const size_t count=size_t(p[b+9]),end=b+10+11*count;
        if(end>p.size()) throw std::invalid_argument("native Auger event coverage mismatch");
        tables.emplace_back(p.begin()+b+10,p.begin()+end);b=end;
    }
    if(tables.empty()) throw std::invalid_argument("native Auger cells required");
    return tables;
}
inline std::vector<double> source_parameters(const std::vector<double>& p) {
    if(!auger_schema(p)) return p;
    const auto tables=auger_tables(p);
    const bool trap=p[17]==-7 || p[17]==-9,rad=p[17]==-8 || p[17]==-9;
    std::vector<double> out(p.begin(),p.begin()+17);
    out.push_back(rad?(trap?-5.:-4.):(trap?-3.:-2.));
    size_t b=18;
    for(const auto& table:tables) {
        out.insert(out.end(),p.begin()+b,p.begin()+b+4);
        if(trap) out.insert(out.end(),p.begin()+b+4,p.begin()+b+7);
        else if(p[b+4]!=0 || p[b+5]!=0 || p[b+6]!=0)
            throw std::invalid_argument("unconfigured native Auger trap coefficients");
        if(rad) out.insert(out.end(),p.begin()+b+7,p.begin()+b+9);
        else if(p[b+7]!=0 || p[b+8]!=0)
            throw std::invalid_argument("unconfigured native Auger radiation coefficients");
        b+=10+table.size();
    }
    return out;
}

// Optional ten extra parameters: (Tref,nref,a_Tl,b_Tc,c_density) per carrier.
// Seven-parameter callers retain the exact constant-time path.
inline std::vector<double> base_parameters(const std::vector<double>& params) {
    const bool coupled=params.size()>=19 && params[17]==-1.;
    const bool generated=params.size()>=22 && params[17]==-2.;
    const bool trapped=params.size()>=25 && params[17]==-3.;
    const bool radiative=params.size()>=24 && (params[17]==-4. || params[17]==-5.);
    if(params.size()!=7 && params.size()!=17 && !coupled && !generated && !trapped && !radiative)
        throw std::invalid_argument("native three-temperature parameter schema invalid");
    if(params.size()>=17) {
        for(size_t k=7;k<17;++k) if(!std::isfinite(params[k]))
            throw std::invalid_argument("finite native relaxation law parameters required");
        for(size_t k:{7,8,12,13}) if(params[k]<=0)
            throw std::invalid_argument("positive native relaxation reference temperature and density required");
    }
    if(coupled) for(size_t k=18;k<params.size();++k)
        if(!std::isfinite(params[k]) || params[k]<0)
            throw std::invalid_argument("finite nonnegative native intercarrier conductance required");
    if(generated) {
        if((params.size()-18)%4) throw std::invalid_argument("native generation parameter width mismatch");
        for(size_t k=18;k<params.size();++k) if(!std::isfinite(params[k]))
            throw std::invalid_argument("finite native generation parameters required");
        for(size_t k=18;k<params.size();k+=4)
            if(params[k]<0 || params[k+1]<0 || params[k+2]<0 || params[k+3]<0)
                throw std::invalid_argument("nonnegative native pair rate, conductance and kinetic energy required");
    }
    if(trapped) {
        if((params.size()-18)%7) throw std::invalid_argument("native trap parameter width mismatch");
        for(size_t k=18;k<params.size();++k) if(!std::isfinite(params[k]))
            throw std::invalid_argument("finite native trap parameters required");
        for(size_t k=18;k<params.size();k+=7)
            for(size_t j:{0,1,2,3,5,6}) if(params[k+j]<0)
                throw std::invalid_argument("nonnegative native source and capture coefficients required");
    }
    if(radiative) {
        const size_t stride=params[17]==-5. ? 9 : 6;
        if((params.size()-18)%stride) throw std::invalid_argument("native radiative parameter width mismatch");
        for(size_t k=18;k<params.size();++k) if(!std::isfinite(params[k]))
            throw std::invalid_argument("finite native radiative parameters required");
        for(size_t k=18;k<params.size();k+=stride) {
            for(size_t j:{0,1,2,3}) if(params[k+j]<0)
                throw std::invalid_argument("nonnegative source coefficients required");
            if(params[k+stride-2]<=0 || params[k+stride-1]<0)
                throw std::invalid_argument("positive photon temperature and nonnegative transition rate required");
            if(stride==9 && (params[k+5]<0 || params[k+6]<0))
                throw std::invalid_argument("nonnegative radiative-mode trap capture coefficients required");
        }
    }
    return std::vector<double>(params.begin(),params.begin()+7);
}

// Cell width 21: the shared geometry/material schema (17 entries) followed by
// independent old Tn,Tp,tau_n,tau_p. Face width and seven parameters are the
// existing FD dispatch schema. Reuse its validated geometry, native Poisson,
// matched-valley reservoirs and fixed contact reservoirs without duplicating
// those operators. Its shared-temperature energy cache is never used here.
inline std::vector<std::string> base_cells(const std::vector<std::string>& raw) {
    if(raw.empty() || raw.size()%21 || 5*(raw.size()/21)>1024)
        throw std::invalid_argument("native three-temperature dimensions or dense Newton limit invalid");
    const auto c=fermi_local_detail::decimals(raw);
    std::vector<std::string> base;
    for(size_t i=0;i<c.size()/21;++i) {
        for(size_t k:{17,18}) if(c[21*i+k]<=1 || c[21*i+k]>=TCAD_CONST(1e5))
            throw std::invalid_argument("native independent carrier temperature bounds invalid");
        for(size_t k:{19,20}) if(c[21*i+k]<=0)
            throw std::invalid_argument("positive native carrier relaxation times required");
        base.insert(base.end(),raw.begin()+21*i,raw.begin()+21*i+17);
    }
    return base;
}

// Optional wrapper keeps dt/budgets at their legacy indices. Unwrapped source
// schemas remain byte-for-byte compatible with every existing caller.
inline bool contact_schema(const std::vector<double>& p) {return p.size()>7 && p[7]==-13.;}
inline std::vector<double> contact_inner(const std::vector<double>& p) {
    if(!contact_schema(p)) return p;
    if(p.size()<11 || !std::isfinite(p[8]) || p[8]<0 || p[8]!=std::floor(p[8]) ||
       p[8]>double(p.size()-11) || (p.size()-9-size_t(p[8]))%2)
        throw std::invalid_argument("native contact temperature wrapper coverage mismatch");
    std::vector<double> out(p.begin(),p.begin()+7);
    out.insert(out.end(),p.begin()+9,p.begin()+9+size_t(p[8]));
    if(contact_schema(out)) throw std::invalid_argument("nested native contact temperature wrapper");
    return out;
}
inline bool reconstruction_schema(const std::vector<double>& p) {
    const auto q=contact_inner(p);return q.size()>7 && q[7]==-12.;
}
inline bool band_schema(const std::vector<double>& p) {
    const auto q=contact_inner(p);return q.size()>7 && (q[7]==-10. || q[7]==-11.);
}
inline std::vector<double> band_parameters(const std::vector<double>& p,size_t nc) {
    if(contact_schema(p)) return band_parameters(contact_inner(p),nc);
    if(!band_schema(p)) return {};
    if(p.size()<10 || !std::isfinite(p[8]) || p[8]<0 || p[8]!=std::floor(p[8]) ||
       p[8]>double(p.size()-10) || p.size()-10-size_t(p[8])!=(p[7]==-11.?6:2)*nc)
        throw std::invalid_argument("native temperature band parameter coverage mismatch");
    const size_t b=9+size_t(p[8]);
    for(size_t k=b;k<p.size();++k) if(!std::isfinite(p[k]))
        throw std::invalid_argument("finite native affine band coefficients required");
    if(p[b]<=0) throw std::invalid_argument("positive native band reference temperature required");
    if(p[7]==-11.) for(size_t k=b+1+4*nc;k<p.size();++k)
        if(p[k]<0) throw std::invalid_argument("nonnegative native Varshni beta required");
    return std::vector<double>(p.begin()+b,p.end());
}
inline std::vector<double> unwrapped_parameters(const std::vector<double>& p,size_t nc) {
    if(contact_schema(p)) return unwrapped_parameters(contact_inner(p),nc);
    if(reconstruction_schema(p)) {
        if(p.size()<9 || (p[8]!=0 && p[8]!=10) || p.size()!=9+size_t(p[8]))
            throw std::invalid_argument("native quadratic parameter wrapper mismatch");
        std::vector<double> out(p.begin(),p.begin()+7);out.insert(out.end(),p.begin()+9,p.end());return out;
    }
    if(!band_schema(p)) return p;
    band_parameters(p,nc);
    std::vector<double> out(p.begin(),p.begin()+7);
    out.insert(out.end(),p.begin()+9,p.begin()+9+size_t(p[8]));return out;
}
inline real_t band_delta(const std::vector<double>& law,size_t nc,size_t i,size_t s,real_t t,real_t r) {
    real_t secant=real_t(law[1+s*nc+i]);
    if(law.size()==1+6*nc) {
        const real_t alpha=real_t(law[1+(2+s)*nc+i]),beta=real_t(law[1+(4+s)*nc+i]);
        secant-=alpha*(t*r+beta*(t+r))/((t+beta)*(r+beta));
    }
    return (t-r)*secant;
}
inline std::vector<std::string> band_cells(const std::vector<std::string>& raw,const std::vector<double>& law) {
    auto out=base_cells(raw);if(law.empty()) return out;
    const auto c=fermi_local_detail::decimals(raw);const size_t nc=c.size()/21;
    if(law.size()!=1+2*nc && law.size()!=1+6*nc) throw std::invalid_argument("native band cell coverage mismatch");
    for(size_t i=0;i<nc;++i) {
        real_t gap=0;
        for(size_t s=0;s<2;++s) {
            const real_t e=c[21*i+13+s]+band_delta(law,nc,i,s,c[21*i+10],real_t(law[0]));
            out[17*i+13+s]=text(e);gap+=e;
        }
        if(gap<=0) throw std::invalid_argument("positive native temperature-dependent gap required");
    }
    return out;
}

struct Context : fermi_dispatch_detail::Context {
    std::vector<real_t> c3;
    std::vector<double> relaxation,intercarrier;
    std::vector<real_t> generation;
    bool trapped=false;
    bool radiative=false;
    std::vector<std::vector<real_t>> collision_events;
    std::vector<real_t> radiation_parameters;
    std::vector<real_t> trap_parameters;
    std::vector<real_t> trap_valleys[2];
    std::vector<double> old_un,old_up;
    std::vector<double> band_law;
    std::vector<double> contact_temperature[2];
    ThreeTemperatureDispatchResult output;
    three_reconstruction_detail::Reconstruction reconstruction;
    real_t A(size_t i,size_t k) const {return c3[21*i+k];}

    // Context-local memoization of complete kernel input packets. Reservoir
    // decimal strings and face double bit patterns are matched exactly. There
    // is no tolerance, quantization or sharing between Newton contexts.

    // The complete cell packet sent to Poisson is the exact cache key. Faces
    // and charge budget are immutable within this context. Never share entries
    // across contexts or reuse a failed kernel result.
    struct PoissonCacheEntry {
        bool valid=false;
        std::vector<std::string> input;
        std::vector<std::vector<double>> output;
    };
    mutable PoissonCacheEntry poisson_cache;
    std::vector<std::vector<double>> poisson(const std::vector<real_t>& n,
            const std::vector<real_t>& p,const std::vector<double>& trap={}) const {
        if(!trap.empty() && trap.size()!=nc)
            throw std::invalid_argument("native trap charge coverage mismatch");
        std::vector<std::string> input;input.reserve(10*nc);
        for(size_t i=0;i<nc;++i) for(size_t k=0;k<10;++k)
            input.push_back(text(k==3 ? n[i] : k==4 ? p[i] :
                k==6 && !trap.empty() ? real_t(trap[i]) : C(i,k)));
        if(poisson_cache.valid && poisson_cache.input==input)return poisson_cache.output;
        auto value=fermi_dispatch_detail::Context::poisson(n,p,trap);
        PoissonCacheEntry updated;updated.input=std::move(input);updated.output=value;updated.valid=true;
        poisson_cache=std::move(updated);return value;
    }

    struct ReservoirCacheEntry {
        bool valid=false;
        std::vector<std::string> input;
        std::vector<double> output;
    };
    mutable std::vector<std::array<ReservoirCacheEntry,4>> reservoir_cache[2];
    mutable std::vector<size_t> reservoir_next[2];
    struct FaceCacheEntry {
        bool valid=false;
        std::vector<double> input,output;
    };
    std::vector<FaceCacheEntry> face_cache[4];

    std::vector<std::vector<double>> reservoir(size_t label,const std::vector<real_t>& density,
                                               const std::vector<double>& T) const {
        auto& cache=reservoir_cache[label];auto& next=reservoir_next[label];
        if(cache.empty()) {cache.resize(nc);next.assign(nc,0);}
        std::vector<std::vector<double>> rows(nc);
        for(size_t i=0;i<nc;++i) {
            std::vector<std::string> input;
            pack(input,{density[i],real_t(T[i]),C(i,13+label)});
            bool hit=false;
            for(const auto& entry:cache[i]) if(entry.valid && entry.input==input) {
                rows[i]=entry.output;hit=true;break;
            }
            if(hit) continue;
            auto value=native_fermi_reservoir_raw(input,valleys[label]);
            ReservoirCacheEntry entry;entry.input=std::move(input);entry.output=value;entry.valid=true;
            cache[i][next[i]]=std::move(entry);next[i]=(next[i]+1)%cache[i].size();
            rows[i]=std::move(value);
        }
        return rows;
    }

    std::vector<double> face_moments(size_t label,size_t f,const std::vector<double>& input) {
        auto& cache=face_cache[label];if(cache.empty()) cache.resize(nf);
        auto& entry=cache[f];
        if(entry.valid && entry.input.size()==input.size() &&
                std::memcmp(entry.input.data(),input.data(),input.size()*sizeof(double))==0)
            return entry.output;
        auto value=native_spectral_face_raw(input,valleys[label%2]);
        FaceCacheEntry updated;updated.input=input;updated.output=value;updated.valid=true;
        entry=std::move(updated);return value;
    }


    Context(const std::vector<std::string>& c,const std::vector<std::string>& f,
            const std::vector<double>& vn,const std::vector<double>& vp,const std::vector<double>& params)
        :Context(c,f,vn,vp,source_parameters(unwrapped_parameters(params,c.size()/21)),
            auger_tables(unwrapped_parameters(params,c.size()/21)),band_parameters(params,c.size()/21)) {
        for(size_t s=0;s<2;++s) {
            contact_temperature[s].resize(nf);
            for(size_t k=0;k<nf;++k) contact_temperature[s][k]=double(F(k,18));
        }
        if(contact_schema(params)) {
            const size_t b=9+size_t(params[8]);
            if(params.size()-b!=2*nf)
                throw std::invalid_argument("native contact temperature face coverage mismatch");
            for(size_t k=0;k<nf;++k) for(size_t s=0;s<2;++s) {
                const double t=params[b+2*k+s];
                if(!std::isfinite(t) || (mode(k,15) ? (t<=1 || t>=1e5) : t!=0))
                    throw std::invalid_argument("native contact temperature bounds or face mode invalid");
                if(mode(k,15)) {
                    contact_temperature[s][k]=t;
                    std::vector<std::string> state;
                    pack(state,{F(k,16+s),real_t(t),band_at(size_t(F(k,0)),s,F(k,18))});
                    contact[s][k]=native_fermi_reservoir_raw(state,valleys[s]);
                }
            }
        }
        if(reconstruction_schema(params)) reconstruction.initialize(*this);
    }

    Context(const std::vector<std::string>& c,const std::vector<std::string>& f,
            const std::vector<double>& vn,const std::vector<double>& vp,const std::vector<double>& params,
            const std::vector<std::vector<real_t>>& events,const std::vector<double>& band={})
        :fermi_dispatch_detail::Context(band_cells(c,band),f,vn,vp,base_parameters(params),params.size()>17 && (params[17]==-3. || params[17]==-5.),!band.empty()),
         c3(fermi_local_detail::decimals(c)),relaxation(params.size()>=17 ?
             std::vector<double>(params.begin()+7,params.begin()+17) : std::vector<double>{}) {
        band_law=band;
        if(!band_law.empty()) for(size_t f=0;f<nf;++f) {
            if(F(f,1)>=0 && !mode(f,19)) {
                const size_t i=size_t(F(f,0)),j=size_t(F(f,1));
                for(size_t s=0;s<2;++s) {
                    bool jump=A(i,13+s)!=A(j,13+s);
                    for(size_t block=s;block<(band_law.size()-1)/nc;block+=2)
                        jump=jump || band_law[1+block*nc+i]!=band_law[1+block*nc+j];
                    if(jump)
                        throw std::invalid_argument("native material band discontinuities require explicit thermionic faces");
                }
            }
            if(mode(f,15)) for(size_t s=0;s<2;++s) {
                std::vector<std::string> state;
                pack(state,{F(f,16+s),F(f,18),band_at(size_t(F(f,0)),s,F(f,18))});
                contact[s][f]=native_fermi_reservoir_raw(state,valleys[s]);
            }
        }
        collision_events=events;
        if(!events.empty()) {
            if(events.size()!=nc) throw std::invalid_argument("native Auger cell coverage mismatch");
            for(size_t s=0;s<2;++s)
                if(valleys[s].size()!=4 || std::abs(valleys[s][1]/valleys[s][0]-1)>1e-12 ||
                   valleys[s][3]!=0 || !radiative_detail::integer(real_t(valleys[s][2])))
                    throw std::invalid_argument("Auger requires one isotropic zero-offset integer-degeneracy valley");
            for(size_t i=0;i<nc;++i)
                spectral_auger_values({A(i,17),A(i,18),C(i,13),C(i,14),C(i,13),C(i,14),
                    real_t(valleys[0][0]),real_t(valleys[1][0])},events[i]);
        }
        trapped=params.size()>17 && (params[17]==-3. || params[17]==-5.);
        radiative=params.size()>17 && (params[17]==-4. || params[17]==-5.);
        if(trapped && 6*nc>1024) throw std::invalid_argument("six-field native Newton dense limit exceeded");
        if(params.size()>17) {
            const bool generated=params[17]==-2. || trapped || radiative;
            const size_t stride=radiative ? (trapped?9:6) : (trapped?7:4);
            if(params.size()!=18+(generated ? stride : 1)*nc)
                throw std::invalid_argument("native source coefficient coverage mismatch");
            if(!generated) intercarrier.assign(params.begin()+18,params.end());
            else for(size_t i=0;i<nc;++i) {
                intercarrier.push_back(params[18+stride*i]);
                generation.push_back(real_t(params[19+stride*i]));
                real_t total=0;
                for(size_t s=0;s<2;++s) {
                    double offset=valleys[s][3];
                    for(size_t v=7;v<valleys[s].size();v+=4) offset=std::min(offset,valleys[s][v]);
                    const real_t energy=C(i,13+s)+real_t(offset)+real_t(params[20+stride*i+s]);
                    generation.push_back(energy);total+=energy;
                }
                if(params[19+stride*i]>0 && (total<=0 || !isfinite_q(total) || !std::isfinite(double(total))))
                    throw std::invalid_argument("positive finite absorbed energy per generated pair required");
                if(trapped) {
                    for(size_t k=4;k<7;++k) trap_parameters.push_back(real_t(params[18+stride*i+k]));
                    if(C(i,6)<=0 || C(i,6)>=1) throw std::invalid_argument("open native trap occupancy required");
                }
                if(radiative) {
                    radiation_parameters.push_back(real_t(params[18+stride*i+stride-2]));
                    radiation_parameters.push_back(real_t(params[18+stride*i+stride-1]));
                }
            }
        }
        if(radiative) {
            // Raw schema declares isotropic masses through matching normal/DOS
            // entries. The public API also validates both tangential masses.
            for(size_t s=0;s<2;++s)
                if(valleys[s].size()!=4 || std::abs(valleys[s][1]/valleys[s][0]-1)>1e-12 ||
                   valleys[s][3]!=0 || !radiative_detail::integer(real_t(valleys[s][2])))
                    throw std::invalid_argument("radiative mode requires one isotropic zero-offset integer-degeneracy valley");
            if(valleys[0][2]!=valleys[1][2]) throw std::invalid_argument("matched radiative valley degeneracies required");
            for(size_t i=0;i<nc;++i) if(C(i,13)+C(i,14)<=0)
                throw std::invalid_argument("positive direct gap required for radiative mode");
        }
        if(trapped) {
            for(size_t s=0;s<2;++s) trap_valleys[s].assign(valleys[s].begin(),valleys[s].end());
            for(size_t i=0;i<nc;++i) {
                const real_t et=trap_parameters[3*i];real_t edge[2];
                for(size_t s=0;s<2;++s) {
                    edge[s]=C(i,13+s)+real_t(valleys[s][3]);
                    for(size_t v=7;v<valleys[s].size();v+=4) edge[s]=std::min(edge[s],C(i,13+s)+real_t(valleys[s][v]));
                }
                if(edge[0]+edge[1]<=0 || et>edge[0] || et<-edge[1])
                    throw std::invalid_argument("positive gap and in-gap native trap level required");
                output.trap_fraction.push_back(double(C(i,6)));
            }
        }
        output.old_poisson=result.old_poisson;
        std::vector<real_t> n(nc),p(nc);std::vector<double> Tn(nc),Tp(nc);
        for(size_t i=0;i<nc;++i) {n[i]=C(i,3);p[i]=C(i,4);Tn[i]=double(A(i,17));Tp[i]=double(A(i,18));}
        const auto rn=reservoir(0,n,Tn),rp=reservoir(1,p,Tp);
        old_un.resize(nc);old_up.resize(nc);
        for(size_t i=0;i<nc;++i) {old_un[i]=rn[i][1];old_up[i]=rp[i][1];}
        for(size_t i=0;i<nc;++i) {
            output.tau_n.push_back(double(tau(i,0,n[i],Tn[i],double(C(i,10)))));
            output.tau_p.push_back(double(tau(i,1,p[i],Tp[i],double(C(i,10)))));
        }
    }

    real_t tau(size_t i,size_t label,real_t density,double Tc,double Tl) const {
        const real_t reference=A(i,19+label);
        if(relaxation.empty()) return reference;
        const size_t b=5*label;
        if(relaxation[b+2]==0 && relaxation[b+3]==0 && relaxation[b+4]==0) return reference;
        const real_t value=exp_q(log_q(reference)+
            real_t(relaxation[b+2])*log_q(real_t(Tl)/real_t(relaxation[b]))+
            real_t(relaxation[b+3])*log_q(real_t(Tc)/real_t(relaxation[b]))+
            real_t(relaxation[b+4])*log_q(density/real_t(relaxation[b+1])));
        if(!isfinite_q(value) || !std::isfinite(double(value)) || double(value)<=0)
            throw FermiStateDomainError("effective native relaxation time outside positive float64 range");
        return value;
    }

    real_t band_at(size_t i,size_t s,real_t Tl) const {
        return band_law.empty() ? A(i,13+s) :
            A(i,13+s)+band_delta(band_law,nc,i,s,Tl,real_t(band_law[0]));
    }
    real_t band_derivative(size_t i,size_t s,real_t Tl) const {
        real_t derivative=real_t(band_law[1+s*nc+i]);
        if(band_law.size()==1+6*nc) {
            const real_t alpha=real_t(band_law[1+(2+s)*nc+i]),beta=real_t(band_law[1+(4+s)*nc+i]);
            derivative-=alpha*Tl*(Tl+2*beta)/((Tl+beta)*(Tl+beta));
        }
        return derivative;
    }

    void evaluate(const std::vector<double>& x,std::vector<double>& residual,double& merit) {
        std::vector<real_t> n(nc),p(nc);std::vector<double> Tn(nc),Tp(nc),Tl(nc),fraction;
        if(trapped) fraction.resize(nc);
        output.n.clear();output.p.clear();
        for(size_t i=0;i<nc;++i) {
            // Snap all kernels to the precision of the returned immutable state.
            n[i]=real_t((long double)C(i,3)*std::exp((long double)x[i]));
            p[i]=real_t((long double)C(i,4)*std::exp((long double)x[nc+i]));
            Tn[i]=double(A(i,17))*std::exp(x[2*nc+i]);
            Tp[i]=double(A(i,18))*std::exp(x[3*nc+i]);
            Tl[i]=double(C(i,10))*std::exp(x[4*nc+i]);
            if(trapped) {
                fraction[i]=x[5*nc+i];
                if(!(fraction[i]>0 && fraction[i]<1)) throw std::invalid_argument("open candidate trap occupancy required");
            }
            output.n.push_back(text(n[i]));output.p.push_back(text(p[i]));
            if(!band_law.empty()) {
                for(size_t s=0;s<2;++s) cells[17*i+13+s]=band_at(i,s,real_t(Tl[i]));
                if(C(i,13)+C(i,14)<=0)
                    throw FermiStateDomainError("positive candidate temperature-dependent gap required");
                if(C(i,11)+(C(i,3)+n[i])/2*band_derivative(i,0,real_t(Tl[i]))+
                        (C(i,4)+p[i])/2*band_derivative(i,1,real_t(Tl[i]))<=0)
                    throw FermiStateDomainError("positive native coupled lattice band capacity required");
            }
        }
        output.temperature_n=Tn;output.temperature_p=Tp;output.temperature_l=Tl;
        output.trap_fraction=fraction;output.new_poisson=poisson(n,p,fraction);
        const auto rn=reservoir(0,n,Tn),rp=reservoir(1,p,Tp);
        const auto eqn=reservoir(0,n,Tl),eqp=reservoir(1,p,Tl);
        output.fn.assign(nf,0);output.fp.assign(nf,0);
        output.energy_n.assign(nf,0);output.energy_p.assign(nf,0);output.moments.assign(2*nf,{});
        const auto& phi=output.new_poisson[0];
        for(size_t label=0;label<2;++label) {
            const auto& r=label==0 ? rn : rp;const auto& T=label==0 ? Tn : Tp;
            std::vector<std::vector<double>> reconstructed_rows;
            std::vector<double> reconstructed_T,reconstructed_Tl;
            if(reconstruction.enabled)reconstruction.states(*this,label,label==0?n:p,r,T,Tl,reconstructed_rows,reconstructed_T,reconstructed_Tl);
            std::vector<double> mobility(nc);
            for(size_t i=0;i<nc;++i)
                mobility[i]=double(C(i,15+label))*std::pow(parameters[4]/Tl[i],parameters[5+label]);
            for(size_t f=0;f<nf;++f) if(F(f,1)>=0 || mode(f,15)) {
                const size_t i=size_t(F(f,0));const long j=long(F(f,1));
                const auto& two=j>=0 ? r[size_t(j)] : contact[label][f];
                const double Ttwo=j>=0 ? T[size_t(j)] : contact_temperature[label][f];
                const double mtwo=j>=0 ? mobility[size_t(j)] :
                    double(C(i,15+label))*std::pow(parameters[4]/double(F(f,18)),parameters[5+label]);
                const std::vector<double> input={T[i],Ttwo,r[i][0],two[0],double(C(i,13+label)),
                    j>=0 ? double(C(size_t(j),13+label)) : double(band_at(i,label,F(f,18))),phi[i],j>=0 ? phi[size_t(j)] : double(F(f,9)),
                    phi[nc+f],label==0 ? -1. : 1.,mobility[i],mtwo,double(F(f,10)),double(F(f,11)),
                    double(F(f,12)),double(F(f,19)),double(F(f,20+label))};
                auto moments=face_moments(label,f,input);
                if(reconstruction.enabled) {
                    auto high_input=input;
                    high_input[0]=reconstructed_T[i];high_input[1]=j>=0?reconstructed_T[size_t(j)]:Ttwo;
                    high_input[2]=reconstructed_rows[i][0];high_input[3]=j>=0?reconstructed_rows[size_t(j)][0]:two[0];
                    high_input[10]=double(C(i,15+label))*std::pow(parameters[4]/reconstructed_Tl[i],parameters[5+label]);
                    if(j>=0)high_input[11]=double(C(size_t(j),15+label))*std::pow(parameters[4]/reconstructed_Tl[size_t(j)],parameters[5+label]);
                    const auto high=face_moments(label+2,f,high_input);
                    const auto& oldphi=output.old_poisson[0];
                    const real_t po=(real_t(oldphi[i])+real_t(phi[i]))/2;
                    const real_t pn=j>=0?(real_t(oldphi[size_t(j)])+real_t(phi[size_t(j)]))/2:F(f,9);
                    const real_t pf=(real_t(oldphi[nc+f])+real_t(phi[nc+f]))/2;
                    moments=three_reconstruction_detail::blend(moments,high,T[i],Ttwo,r[i][0],two[0],po,pn,pf,label==0?-si_transport::elementary_charge:si_transport::elementary_charge);
                }
                (label==0 ? output.fn : output.fp)[f]=moments[0];
                (label==0 ? output.energy_n : output.energy_p)[f]=moments[2];
                output.moments[label*nf+f]=moments;
            }
        }
        std::vector<std::string> lc,lf,exchange,source,trap_source,radiation_source,auger_source,band_shifts;
        output.trap_moments.clear();
        output.radiative_moments.clear();
        output.auger_moments.clear();
        output.tau_n.resize(nc);output.tau_p.resize(nc);
        for(size_t i=0;i<nc;++i) {
            const real_t tn=tau(i,0,n[i],Tn[i],Tl[i]),tp=tau(i,1,p[i],Tp[i],Tl[i]);
            output.tau_n[i]=double(tn);output.tau_p[i]=double(tp);
            pack(lc,{C(i,3),C(i,4),C(i,10),n[i],p[i],real_t(Tl[i]),real_t(old_un[i]),real_t(rn[i][1]),
                real_t(eqn[i][1]),real_t(old_up[i]),real_t(rp[i][1]),real_t(eqp[i][1]),C(i,0),C(i,11),
                real_t(output.old_poisson[0][i]),real_t(phi[i]),C(i,12),tn,tp});
            if(!intercarrier.empty()) pack(exchange,{real_t(Tn[i]),real_t(Tp[i]),real_t(intercarrier[i])});
            if(!generation.empty()) pack(source,{generation[3*i],
                generation[3*i+1]+(band_law.empty()?real_t(0):C(i,13)-band_at(i,0,C(i,10))),
                generation[3*i+2]+(band_law.empty()?real_t(0):C(i,14)-band_at(i,1,C(i,10)))});
            if(!band_law.empty()) pack(band_shifts,{
                band_delta(band_law,nc,i,0,real_t(Tl[i]),C(i,10)),
                band_delta(band_law,nc,i,1,real_t(Tl[i]),C(i,10))});
            if(trapped) {
                const auto moments=spectral_trap_capture_values({real_t(Tn[i]),real_t(Tp[i]),real_t(Tl[i]),
                    real_t(rn[i][0]),real_t(rp[i][0]),C(i,13),C(i,14),C(i,5),trap_parameters[3*i],
                    trap_parameters[3*i+1],trap_parameters[3*i+2],real_t(fraction[i])},trap_valleys[0],trap_valleys[1]);
                output.trap_moments.push_back(fermi_local_detail::exported(moments));
                pack(trap_source,{moments[8],moments[9],-moments[13],-moments[14],moments[20],
                    C(i,5),trap_parameters[3*i],C(i,6),real_t(fraction[i])});
            }
            if(!collision_events.empty()) {
                const auto rows=spectral_auger_values({real_t(Tn[i]),real_t(Tp[i]),real_t(rn[i][0]),real_t(rp[i][0]),
                    C(i,13),C(i,14),real_t(valleys[0][0]),real_t(valleys[1][0])},collision_events[i]);
                std::vector<std::vector<double>> exported;
                for(const auto& row:rows) exported.push_back(fermi_local_detail::exported(row));
                output.auger_moments.push_back(exported);
                pack(auger_source,{rows[0][2],rows[0][7],rows[0][8],rows[0][12]});
            }
            if(radiative) {
                const auto moments=spectral_radiative_values({real_t(Tn[i]),real_t(Tp[i]),radiation_parameters[2*i],
                    real_t(rn[i][0]),real_t(rp[i][0]),C(i,13),C(i,14),real_t(valleys[0][0]),
                    real_t(valleys[1][0]),real_t(valleys[0][2]),radiation_parameters[2*i+1]});
                output.radiative_moments.push_back(fermi_local_detail::exported(moments));
                pack(radiation_source,{moments[4],-moments[12],-moments[13],moments[18]});
            }
        }
        for(size_t f=0;f<nf;++f)
            pack(lf,{F(f,0),F(f,1),real_t(output.fn[f]),real_t(output.fp[f]),real_t(output.energy_n[f]),
                real_t(output.energy_p[f]),real_t(output.old_poisson[0][nc+f]),real_t(phi[nc+f]),
                F(f,10),F(f,11),F(f,12),F(f,14),F(f,13)});
        output.local=native_three_temperature_local_raw(lc,lf,parameters[0],exchange,source,trap_source,radiation_source,auger_source,band_shifts);
        residual.resize((trapped?6:5)*nc);merit=0;real_t charge=0;
        const size_t trap_offset=16*nc+nf;
        for(size_t i=0;i<nc;++i) {
            const real_t sn=C(i,0)*std::max(abs_q(real_t(old_un[i])),C(i,11)*A(i,17));
            const real_t sp=C(i,0)*std::max(abs_q(real_t(old_up[i])),C(i,11)*A(i,18));
            const real_t sl=C(i,0)*C(i,11)*C(i,10);
            residual[i]=double(real_t(output.local[i])/(C(i,0)*C(i,3)));
            residual[nc+i]=double(real_t(output.local[nc+i])/(C(i,0)*C(i,4)));
            residual[2*nc+i]=double(real_t(output.local[9*nc+i])/sn);
            residual[3*nc+i]=double(real_t(output.local[10*nc+i])/sp);
            residual[4*nc+i]=double(real_t(output.local[11*nc+i])/sl);
            merit=std::max({merit,std::abs(output.local[i])/parameters[2],
                std::abs(output.local[nc+i])/parameters[2],std::abs(output.local[9*nc+i])/parameters[3],
                std::abs(output.local[10*nc+i])/parameters[3],std::abs(output.local[11*nc+i])/parameters[3]});
            charge+=real_t(output.local[nc+i])-real_t(output.local[i]);
            if(trapped) {
                const double row=output.local[trap_offset+i];
                residual[5*nc+i]=C(i,5)>0 ? double(real_t(row)/(C(i,0)*C(i,5))) : fraction[i]-double(C(i,6));
                merit=std::max(merit,std::abs(row)/parameters[2]);charge-=real_t(row);
            }
        }
        merit=std::max(merit,double(abs_q(si_transport::elementary_charge*charge)/parameters[1]));
        // Local energy rows can have the same sign: their maximum alone is
        // not a whole-device first-law budget. Use the actual exported ledger,
        // including electrostatic storage, terminal work and source/port tails.
        // Keep the public driver's independent pre-commit checks unchanged.
        const real_t dt=parameters[0];
        real_t stored=real_t(output.new_poisson[6][0])-real_t(output.old_poisson[6][0]);
        real_t absorbed=0,outward=0,terminal_work=0,global_charge=0,terminal_charge=0;
        const size_t generation_offset=12*nc+nf+(!intercarrier.empty()?nc:0);
        const size_t radiation_offset=trap_offset+(trapped?8*nc:0);
        for(size_t i=0;i<nc;++i) {
            stored+=real_t(output.local[2*nc+i])+real_t(output.local[3*nc+i])+real_t(output.local[4*nc+i]);
            if(!generation.empty())
                absorbed+=real_t(output.local[generation_offset+nc+i])+real_t(output.local[generation_offset+2*nc+i]);
            if(trapped) stored+=real_t(output.local[trap_offset+nc+i]);
            if(radiative) outward+=real_t(output.local[radiation_offset+3*nc+i]);
            global_charge+=C(i,0)*(p[i]-C(i,4)-n[i]+C(i,3)-
                (trapped?C(i,5)*(real_t(fraction[i])-C(i,6)):real_t(0)));
        }
        global_charge*=si_transport::elementary_charge;
        for(size_t f=0;f<nf;++f) if(F(f,1)<0) {
            const real_t qflux=si_transport::elementary_charge*(real_t(output.fp[f])-real_t(output.fn[f]));
            outward+=dt*(real_t(output.energy_n[f])+real_t(output.energy_p[f])+real_t(output.local[12*nc+f]));
            global_charge+=dt*qflux;
            if(mode(f,8)) {
                const real_t dq=real_t(output.new_poisson[2][f])-real_t(output.old_poisson[2][f]);
                terminal_work-=F(f,9)*(dq+dt*qflux);
                terminal_charge-=dq+dt*qflux;
            }
        }
        merit=std::max({merit,double(abs_q(terminal_work+absorbed-stored-outward)/parameters[3]),
            double(abs_q(global_charge)/parameters[1]),double(abs_q(terminal_charge)/parameters[1])});
    }
    static int callback(void* pointer,const std::vector<double>& x,std::vector<double>& r,double* merit) {
        static_cast<Context*>(pointer)->evaluate(x,r,*merit);return 0;
    }
};
} // namespace three_temperature_dispatch_detail

inline ThreeTemperatureDispatchResult native_three_temperature_dispatch_raw(
        const std::vector<std::string>& c,const std::vector<std::string>& f,
        const std::vector<double>& vn,const std::vector<double>& vp,const std::vector<double>& params,int max_nfev) {
    using namespace three_temperature_dispatch_detail;
    if(max_nfev<1) throw std::invalid_argument("positive native three-temperature evaluation budget required");
    Context context(c,f,vn,vp,params);const size_t nc=context.nc;
    const size_t unknowns=(context.trapped?6:5)*nc;
    std::vector<double> x(unknowns,0),lower(unknowns),upper(unknowns);
    for(size_t k=0;k<unknowns;++k) {
        const size_t i=k%nc,block=k/nc;
        if(block==5) {x[k]=double(context.C(i,6));lower[k]=0;upper[k]=1;continue;}
        const real_t initial=block<2 ? context.C(i,3+block) : block<4 ? context.A(i,15+block) : context.C(i,10);
        const long double origin=std::log((long double)initial);
        lower[k]=double((block<2 ? -600.L : 0.L)-origin);
        upper[k]=double((block<2 ? 600.L : std::log(1e5L))-origin);
    }
    context.output.newton=native_fermi_newton_raw(x,lower,upper,max_nfev,Context::callback,&context);
    return context.output;
}
} // namespace tcad
