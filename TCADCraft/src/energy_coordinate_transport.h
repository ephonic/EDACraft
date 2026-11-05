#pragma once
#include "fermi_energy_coordinates.h"
#include "three_temperature_excess_local.h"
#include "three_temperature_dispatch.h"

namespace tcad {
struct EnergyCoordinateTransportResult {
    ThreeTemperatureDispatchResult transport;
    std::vector<std::string> excess,ledger,local_cells,local_faces,temperature_cells;
    int seed_evaluations=0;
};
namespace energy_coordinate_transport_detail {
using isolated_relaxation_detail::text;
using fermi_dispatch_detail::pack;
struct Context : fermi_dispatch_detail::Context {
    std::vector<real_t> law,old_excess,old_eq,scale,generation,intercarrier,radiation;
    EnergyCoordinateTransportResult output;
    Context(const std::vector<std::string>& c,const std::vector<std::string>& f,
            const std::vector<double>& vn,const std::vector<double>& vp,const std::vector<double>& p,
            const std::vector<std::string>& laws,const std::vector<std::string>& excess)
        :fermi_dispatch_detail::Context(c,f,vn,vp,p),law(fermi_local_detail::decimals(laws)),
         old_excess(fermi_local_detail::decimals(excess)) {
        if(nc>64 || old_excess.size()!=2*nc)
            throw std::invalid_argument("energy-coordinate transport cell/law/state coverage invalid");
        // The historical 10*nc law packet stays exact when generation is off.
        // A -1 marker introduces nc triples (pair rate, material En, material Ep).
        // -2 uses quadruples (rate, En, Ep, Gnp), including source-free coupling.
        generation.assign(3*nc,0);intercarrier.assign(nc,0);
        if(law.size()!=10*nc) {
            const bool optical=law.size()==13*nc+1 && law[10*nc]==-1;
            const bool coupled=law.size()==14*nc+1 && law[10*nc]==-2;
            const bool radiative=law.size()==16*nc+1 && law[10*nc]==-3;
            if(!optical && !coupled && !radiative)
                throw std::invalid_argument("energy-coordinate pair-source schema invalid");
            if(radiative) {
                radiation.resize(2*nc);
                for(size_t s=0;s<2;++s)
                    if(valleys[s].size()!=4 || valleys[s][3]!=0 ||
                       !radiative_detail::integer(real_t(valleys[s][2])))
                        throw std::invalid_argument("matched isotropic zero-offset radiative valleys required");
                if(valleys[0][2]!=valleys[1][2])
                    throw std::invalid_argument("matched radiative degeneracies required");
            }
            for(size_t i=0;i<nc;++i) {
                const size_t b=10*nc+1+(radiative?6:coupled?4:3)*i;
                for(size_t k=0;k<3;++k)generation[3*i+k]=law[b+k];
                if(coupled || radiative)intercarrier[i]=law[b+3];
                if(radiative) {
                    radiation[2*i]=law[b+4];radiation[2*i+1]=law[b+5];
                    if(radiation[2*i]<=0 || radiation[2*i+1]<0 ||
                       !std::isfinite(double(radiation[2*i])) || !std::isfinite(double(radiation[2*i+1])) ||
                       C(i,13)+C(i,14)<=0)
                        throw std::invalid_argument("positive photon temperature and gap, nonnegative finite radiative rate required");
                }
                const real_t rate=generation[3*i],en=generation[3*i+1],ep=generation[3*i+2];
                if(rate<0 || !std::isfinite(double(rate)) || !std::isfinite(double(en)) || !std::isfinite(double(ep)) ||
                   (rate>0 && (en+ep<=0 || !std::isfinite(double(en+ep)))) ||
                   intercarrier[i]<0 || !std::isfinite(double(intercarrier[i])))
                    throw std::invalid_argument("finite nonnegative pair rate and positive absorbed pair energy required");
            }
            law.resize(10*nc);
        }
        output.transport.old_poisson=result.old_poisson;
        for(size_t i=0;i<nc;++i)for(size_t s=0;s<2;++s) {
            const size_t b=10*i+5*s;
            for(size_t k:{0,1,2})if(law[b+k]<=0)throw std::invalid_argument("positive energy relaxation coefficients required");
            const auto eq=fermi_energy_detail::reservoir(C(i,3+s),C(i,10),C(i,13+s),valleys[s]);
            old_eq.push_back(eq.u);
            scale.push_back(std::max(C(i,11)*C(i,10),std::max(abs_q(eq.u),abs_q(old_excess[2*i+s]))));
            // Validate the actual old energy coordinate before any recoverable
            // Newton callback, even if the caller bypassed Python validation.
            fermi_energy_detail::temperature(C(i,3+s),double(C(i,10)),old_excess[2*i+s],C(i,13+s),valleys[s]);
        }
    }
    real_t logtau(size_t i,size_t s,real_t n,double Tl)const {
        const size_t b=10*i+5*s;
        return log_q(law[b])+law[b+3]*log_q(real_t(Tl)/law[b+1])+law[b+4]*log_q(n/law[b+2]);
    }
    void evaluate(const std::vector<double>& x,std::vector<double>& residual,double& merit) {
        auto& o=output.transport;std::vector<real_t> n(nc),p(nc),eq(2*nc),e(2*nc),weighted(2*nc),lost(2*nc);
        std::vector<double> T[2],Tl(nc);T[0].resize(nc);T[1].resize(nc);
        o.n.clear();o.p.clear();output.excess.clear();output.temperature_cells.clear();o.radiative_moments.clear();
        for(size_t i=0;i<nc;++i) {
            n[i]=real_t((long double)C(i,3)*std::exp((long double)x[i]));
            p[i]=real_t((long double)C(i,4)*std::exp((long double)x[nc+i]));
            Tl[i]=double(C(i,10))*std::exp(x[4*nc+i]);o.n.push_back(text(n[i]));o.p.push_back(text(p[i]));
            for(size_t s=0;s<2;++s) {
                const size_t k=2*i+s;const real_t lt=logtau(i,s,s==0?n[i]:p[i],Tl[i]);
                const real_t tau=exp_q(lt);
                if(!isfinite_q(tau) || !std::isfinite(double(tau)) || double(tau)<=0)
                    throw FermiStateDomainError("energy-coordinate effective relaxation outside positive float64 range");
                const real_t ratio=lt-log_q(real_t(parameters[0]));
                const real_t retained=isolated_relaxation_detail::logistic(ratio);
                lost[k]=isolated_relaxation_detail::logistic(-ratio);
                weighted[k]=scale[k]*real_t(x[(2+s)*nc+i]);e[k]=retained*weighted[k];
                const auto decoded=fermi_energy_detail::temperature(s==0?n[i]:p[i],Tl[i],e[k],C(i,13+s),valleys[s]);
                T[s][i]=decoded.T;eq[k]=decoded.eq;output.excess.push_back(text(e[k]));
                for(real_t value:{real_t(decoded.T),decoded.eq,e[k],decoded.error,decoded.lower,decoded.upper})
                    output.temperature_cells.push_back(text(value));
            }
        }
        o.temperature_n=T[0];o.temperature_p=T[1];o.temperature_l=Tl;o.new_poisson=poisson(n,p);
        const auto rn=reservoir(0,n,T[0]),rp=reservoir(1,p,T[1]);
        o.fn.assign(nf,0);o.fp.assign(nf,0);o.energy_n.assign(nf,0);o.energy_p.assign(nf,0);o.moments.assign(2*nf,{});
        const auto& phi=o.new_poisson[0];
        for(size_t s=0;s<2;++s) {
            const auto& r=s==0?rn:rp;std::vector<double> mobility(nc);
            for(size_t i=0;i<nc;++i)mobility[i]=double(C(i,15+s))*std::pow(parameters[4]/Tl[i],parameters[5+s]);
            for(size_t f=0;f<nf;++f)if(F(f,1)>=0 || mode(f,15)) {
                const size_t i=size_t(F(f,0));const long j=long(F(f,1));
                const auto& two=j>=0?r[size_t(j)]:contact[s][f];
                const double Ttwo=j>=0?T[s][size_t(j)]:double(F(f,18));
                const double mtwo=j>=0?mobility[size_t(j)]:double(C(i,15+s))*std::pow(parameters[4]/Ttwo,parameters[5+s]);
                const auto moments=native_spectral_face_raw({T[s][i],Ttwo,r[i][0],two[0],double(C(i,13+s)),
                    j>=0?double(C(size_t(j),13+s)):double(C(i,13+s)),phi[i],j>=0?phi[size_t(j)]:double(F(f,9)),
                    phi[nc+f],s==0?-1.:1.,mobility[i],mtwo,double(F(f,10)),double(F(f,11)),double(F(f,12)),
                    double(F(f,19)),double(F(f,20+s))},valleys[s]);
                (s==0?o.fn:o.fp)[f]=moments[0];(s==0?o.energy_n:o.energy_p)[f]=moments[2];o.moments[s*nf+f]=moments;
            }
        }
        std::vector<std::string> c,f;std::vector<real_t> rounding(nc,0);
        for(size_t i=0;i<nc;++i) {
            pack(c,{C(i,3),C(i,4),C(i,10),n[i],p[i],real_t(Tl[i]),old_eq[2*i],eq[2*i],old_excess[2*i],
                old_eq[2*i+1],eq[2*i+1],old_excess[2*i+1],C(i,0),C(i,11),real_t(o.old_poisson[0][i]),real_t(phi[i]),C(i,12)});
            for(size_t k=0;k<10;++k)c.push_back(text(law[10*i+k]));
            if(generation[3*i]!=0 || intercarrier[i]!=0 || !radiation.empty()) {
                const real_t count=real_t(parameters[0])*C(i,0)*generation[3*i];
                const real_t factor=real_t(parameters[0])*C(i,0)*intercarrier[i];
                const real_t exchange=factor*(real_t(T[0][i])-real_t(T[1][i]));
                for(size_t s=0;s<2;++s) {
                    const double value=T[s][i];
                    const real_t left=real_t(value)-real_t(std::nextafter(value,-std::numeric_limits<double>::infinity()));
                    const real_t right=real_t(std::nextafter(value,std::numeric_limits<double>::infinity()))-real_t(value);
                    rounding[i]+=factor*std::max(left,right)/2;
                }
                if(!isfinite_q(rounding[i]) || rounding[i]>=real_t(parameters[3]))
                    throw FermiStateDomainError("intercarrier temperature rounding exhausts energy budget");
                real_t pairs=0,un=0,up=0;
                if(!radiation.empty()) {
                    const auto moments=spectral_radiative_values({real_t(T[0][i]),real_t(T[1][i]),radiation[2*i],
                        real_t(rn[i][0]),real_t(rp[i][0]),C(i,13),C(i,14),real_t(valleys[0][0]),
                        real_t(valleys[1][0]),real_t(valleys[0][2]),radiation[2*i+1]});
                    o.radiative_moments.push_back(fermi_local_detail::exported(moments));
                    const real_t factor=real_t(parameters[0])*C(i,0);
                    pairs=factor*moments[4];un=factor*moments[12];up=factor*moments[13];
                }
                pack(c,{count-pairs,count-pairs,count*generation[3*i+1]-exchange+un,
                    count*generation[3*i+2]+exchange+up,0,0,0});
            } else for(size_t k=0;k<7;++k)c.push_back("0");
        }
        for(size_t face=0;face<nf;++face)pack(f,{F(face,0),F(face,1),real_t(o.fn[face]),real_t(o.fp[face]),
            real_t(o.energy_n[face]),real_t(o.energy_p[face]),real_t(o.old_poisson[0][nc+face]),real_t(phi[nc+face]),
            F(face,10),F(face,11),F(face,12),F(face,14),F(face,13)});
        const auto raw=native_three_temperature_excess_local_raw(c,f,text(real_t(parameters[0])));
        auto ledger=fermi_local_detail::decimals(raw);residual.assign(5*nc,0);merit=0;real_t charge=0;
        o.tau_n.resize(nc);o.tau_p.resize(nc);
        for(size_t i=0;i<nc;++i) {
            for(size_t s=0;s<2;++s) {
                const size_t k=2*i+s;const real_t change=weighted[k]-ledger[20*i+18+s];
                ledger[20*i+2+s]=e[k];
                ledger[20*i+4+s]=C(i,0)*((eq[k]-old_eq[k])+(e[k]-old_excess[k]));
                ledger[20*i+7+s]=C(i,0)*lost[k]*weighted[k];
                ledger[20*i+11+s]=C(i,0)*change;
                ledger[20*i+13]-=C(i,0)*lost[k]*change;
                (s==0?o.tau_n:o.tau_p)[i]=double(ledger[20*i+14+s]);
                residual[s*nc+i]=double(ledger[20*i+s]/(C(i,0)*C(i,3+s)));
                residual[(2+s)*nc+i]=double(change/scale[k]);
                merit=std::max({merit,double(abs_q(ledger[20*i+s])/parameters[2]),
                    double((abs_q(ledger[20*i+11+s])+rounding[i])/parameters[3])});
            }
            residual[4*nc+i]=double(ledger[20*i+13]/(C(i,0)*C(i,11)*C(i,10)));
            merit=std::max(merit,double(abs_q(ledger[20*i+13])/parameters[3]));
            charge+=ledger[20*i+1]-ledger[20*i];
        }
        merit=std::max(merit,double(abs_q(si_transport::elementary_charge*charge)/parameters[1]));
        output.ledger.clear();for(real_t value:ledger)output.ledger.push_back(text(value));
        output.local_cells.swap(c);output.local_faces.swap(f);
    }
    static int callback(void* p,const std::vector<double>& x,std::vector<double>& r,double* merit) {
        static_cast<Context*>(p)->evaluate(x,r,*merit);return 0;
    }
};
} // namespace energy_coordinate_transport_detail

inline EnergyCoordinateTransportResult native_energy_coordinate_transport_raw(
        const std::vector<std::string>& c,const std::vector<std::string>& f,const std::vector<double>& vn,
        const std::vector<double>& vp,const std::vector<double>& parameters,const std::vector<std::string>& law,
        const std::vector<std::string>& excess,int max_nfev) {
    using namespace energy_coordinate_transport_detail;
    if(max_nfev<1)throw std::invalid_argument("positive shared energy-coordinate evaluation budget required");
    Context context(c,f,vn,vp,parameters,law,excess);const size_t nc=context.nc;
    std::vector<double> x(5*nc,0),lower(5*nc),upper(5*nc);
    int seeds=0;
    for(size_t i=0;i<nc;++i) {
        if(seeds>=max_nfev)throw std::runtime_error("energy-coordinate seed evaluation budget exhausted");
        std::vector<std::string> state,args;
        pack(state,{context.C(i,3),context.C(i,4),context.C(i,10),context.old_excess[2*i],context.old_excess[2*i+1]});
        const auto& L=context.law;
        pack(args,{context.C(i,11),context.C(i,0),context.C(i,13),context.C(i,14),L[10*i],L[10*i+5],
            L[10*i+1],L[10*i+2],L[10*i+3],L[10*i+4],L[10*i+6],L[10*i+7],L[10*i+8],L[10*i+9],
            TCAD_CONST(1.000001),TCAD_CONST(99999.999),real_t(parameters[0]),real_t(parameters[3])});
        const auto seed=native_isolated_relaxation_raw(state,args,vn,vp,false,max_nfev-seeds);
        seeds+=int(fermi_local_detail::decimal(seed[13]));const double Tl=double(fermi_local_detail::decimal(seed[0]));
        x[4*nc+i]=std::log(Tl/double(context.C(i,10)));
        for(size_t s=0;s<2;++s) {
            const size_t k=2*i+s;
            const auto eq=fermi_energy_detail::reservoir(context.C(i,3+s),real_t(Tl),context.C(i,13+s),s==0?vn:vp);
            const real_t driven=(context.old_eq[k]-eq.u)+context.old_excess[k];
            x[(2+s)*nc+i]=double(driven/context.scale[k]);
        }
    }
    for(size_t k=0;k<5*nc;++k) {
        const size_t block=k/nc,i=k%nc;
        if(block==2 || block==3){lower[k]=-1e6;upper[k]=1e6;continue;}
        const real_t initial=block<2?context.C(i,3+block):context.C(i,10);
        const long double origin=std::log((long double)initial);
        lower[k]=double((block<2?-600.L:0.L)-origin);
        upper[k]=double((block<2?600.L:std::log(1e5L))-origin);
    }
    if(seeds>=max_nfev)throw std::runtime_error("energy-coordinate shared evaluation budget exhausted");
    context.output.transport.newton=native_fermi_newton_raw(x,lower,upper,max_nfev-seeds,Context::callback,&context);
    context.output.seed_evaluations=seeds;return context.output;
}
} // namespace tcad
