#pragma once
// Coupled lattice-only spatial transport. Carrier faces are explicitly blocked
// in the frozen model. This is not a general carrier-transport fallback.
#include "isolated_relaxation.h"
#include "fermi_newton.h"
#include <set>

namespace tcad {
namespace lattice_excess_detail {
struct Context {
    size_t nc,nf,nb;
    int evaluations=0;
    std::vector<real_t> s,p,f,q,old_eq,output,bath,band;
    const std::vector<double>& vn;
    const std::vector<double>& vp;
    real_t dt,gate;
    Context(const std::vector<std::string>& state,const std::vector<std::string>& parameters,
            const std::vector<std::string>& faces,const std::vector<std::string>& source,
            const std::vector<double>& n,const std::vector<double>& h,double step,double tolerance,
            const std::vector<std::string>& boundaries={},const std::vector<std::string>& varshni={}):
            nc(state.size()/5),nf(faces.size()/3),nb(boundaries.size()/3),s(fermi_local_detail::decimals(state)),
            p(fermi_local_detail::decimals(parameters)),f(fermi_local_detail::decimals(faces)),
            bath(fermi_local_detail::decimals(boundaries)),band(fermi_local_detail::decimals(varshni)),vn(n),vp(h),dt(step),gate(tolerance) {
        if(nc<2 || nc>64 || state.size()!=5*nc || parameters.size()!=16*nc ||
                faces.empty() || faces.size()%3 || !std::isfinite(step) || step<=0 ||
                !std::isfinite(tolerance) || tolerance<=0 || (!source.empty() && source.size()!=3*nc) || boundaries.size()%3 ||
                (!band.empty() && band.size()!=4*nc))
            throw std::invalid_argument("lattice excess dimensions, timestep or budgets invalid");
        q=source.empty()?std::vector<real_t>(3*nc,0):fermi_local_detail::decimals(source);
        old_eq.resize(2*nc);output.resize(13*nc+nf+nb);
        for(real_t v:band)if(v<0)throw std::invalid_argument("nonnegative Varshni alpha and beta required");
        for(size_t i=0;i<nc;++i) {
            for(size_t k:{0,1,4,5,6,7,10,11,14,15})
                if(P(i,k)<=0)throw std::invalid_argument("positive lattice excess coefficients required");
            if(S(i,0)<=0 || S(i,1)<=0 || !(P(i,14)<S(i,2) && S(i,2)<P(i,15)))
                throw std::invalid_argument("lattice excess requires positive densities and strict lattice bounds");
            // For alpha>=0, capacity is nonincreasing in T. This certifies
            // monotone storage over the entire frozen bracket, not only a trial.
            if(!band.empty() && storage_capacity(i,P(i,15))<=0)
                throw std::invalid_argument("positive Varshni storage capacity over frozen bounds required");
            for(size_t k=0;k<2;++k) {
                old_eq[2*i+k]=energy(i,k,S(i,2));
                admissible(i,k,S(i,2),S(i,3+k));
            }
        }
        std::set<std::pair<size_t,size_t>> seen;
        for(size_t j=0;j<nf;++j) {
            if(f[3*j]<0 || f[3*j+1]<0 || f[3*j]>=nc || f[3*j+1]>=nc ||
                    real_t(size_t(f[3*j]))!=f[3*j] || real_t(size_t(f[3*j+1]))!=f[3*j+1] ||
                    f[3*j]==f[3*j+1] || f[3*j+2]<=0)
                throw std::invalid_argument("valid lattice excess internal face required");
            size_t a=size_t(f[3*j]),b=size_t(f[3*j+1]);if(a>b)std::swap(a,b);
            if(!seen.insert({a,b}).second)throw std::invalid_argument("duplicate lattice excess face");
        }
        for(size_t j=0;j<nb;++j) {
            const real_t owner=bath[3*j];
            if(owner<0 || owner>=nc || real_t(size_t(owner))!=owner || bath[3*j+1]<=0 || bath[3*j+2]<=0)
                throw std::invalid_argument("valid owner, conductance and bath temperature required");
        }
    }
    real_t S(size_t i,size_t k)const{return s[5*i+k];}
    real_t P(size_t i,size_t k)const{return p[16*i+k];}
    static std::pair<real_t,real_t> ratios(real_t T,real_t beta) {
        const real_t scale=std::max(T,beta),u=T/scale,v=beta/scale;
        return {u/(u+v),v/(u+v)};
    }
    static real_t secant(real_t T,real_t old,real_t beta) {
        const auto a=ratios(T,beta),b=ratios(old,beta);
        return a.first+a.second*b.first; // exact divided difference of T^2/(T+beta)
    }
    real_t storage_capacity(size_t i,real_t T)const {
        real_t result=P(i,0);
        if(!band.empty())for(size_t k=0;k<2;++k) {
            const auto r=ratios(T,band[4*i+2*k+1]);
            result-=S(i,k)*band[4*i+2*k]*r.first*(r.first+2*r.second);
        }
        return result;
    }
    real_t energy(size_t i,size_t k,real_t T)const {
        using isolated_relaxation_detail::text;
        return real_t(native_fermi_reservoir_raw({text(S(i,k)),text(T),text(P(i,2+k))},k==0?vn:vp)[1]);
    }
    void admissible(size_t i,size_t k,real_t T,real_t excess)const {
        const auto& valleys=k==0?vn:vp;real_t edge=P(i,2+k)+valleys.at(3);
        for(size_t j=3;j<valleys.size();j+=4)edge=std::min(edge,P(i,2+k)+real_t(valleys[j]));
        if(energy(i,k,T)+excess<=S(i,k)*edge)
            throw std::invalid_argument("lattice excess carrier energy below band minimum");
    }
    int evaluate_quad(const std::vector<real_t>& x,std::vector<real_t>& residual,real_t* merit) {
        ++evaluations;
        if(x.size()!=nc)throw std::invalid_argument("lattice excess trial coverage mismatch");
        real_t worst=0,endpoint=0;
        for(size_t i=0;i<nc;++i) {
            const real_t T=x[i];if(!(P(i,14)<T && T<P(i,15)))
                throw std::invalid_argument("lattice excess trial outside frozen bounds");
            auto* o=output.data()+13*i;o[0]=T;
            for(size_t k=0;k<2;++k) {
                const size_t b=6+4*k;
                const real_t logtau=log_q(P(i,4+k))+P(i,b+2)*log_q(T/P(i,b))+
                    P(i,b+3)*log_q(S(i,k)/P(i,b+1));
                const real_t ratio=logtau-log_q(dt);
                const real_t retained=isolated_relaxation_detail::logistic(ratio);
                const real_t lost=isolated_relaxation_detail::logistic(-ratio);
                const real_t difference=old_eq[2*i+k]-energy(i,k,T)+S(i,3+k);
                const real_t driven=difference+q[3*i+k]/P(i,1);
                o[1+k]=retained*driven;o[3+k]=P(i,1)*lost*driven;
                o[5+k]=P(i,1)*(-difference+o[1+k]);
                o[8+k]=o[5+k]+o[3+k]-q[3*i+k];o[11+k]=logtau;
            }
            o[7]=P(i,1)*P(i,0)*(T-S(i,2));
            if(!band.empty())for(size_t k=0;k<2;++k)
                o[7]-=P(i,1)*S(i,k)*band[4*i+2*k]*(T-S(i,2))*secant(T,S(i,2),band[4*i+2*k+1]);
            o[10]=o[7]-o[3]-o[4]-q[3*i+2];
            endpoint+=o[5]+o[6]+o[7]-q[3*i]-q[3*i+1]-q[3*i+2];
        }
        for(size_t j=0;j<nf;++j) {
            const size_t a=size_t(f[3*j]),b=size_t(f[3*j+1]);
            const real_t impulse=dt*f[3*j+2]*(real_t(x[a])-real_t(x[b]));
            output[13*nc+j]=impulse;output[13*a+10]+=impulse;output[13*b+10]-=impulse;
        }
        for(size_t j=0;j<nb;++j) {
            const size_t owner=size_t(bath[3*j]);
            const real_t impulse=dt*bath[3*j+1]*(real_t(x[owner])-bath[3*j+2]);
            output[13*nc+nf+j]=impulse;output[13*owner+10]+=impulse;endpoint+=impulse;
        }
        residual.resize(nc);
        for(size_t i=0;i<nc;++i) {
            for(size_t k=8;k<=10;++k)worst=std::max(worst,abs_q(output[13*i+k])*real_t(4*nc)/gate);
            residual[i]=output[13*i+10]/(P(i,1)*P(i,0));
        }
        *merit=std::max(worst,abs_q(endpoint)/gate);return 0;
    }
    int evaluate(const std::vector<double>& x,std::vector<double>& residual,double* merit) {
        std::vector<real_t> qx(x.begin(),x.end()),qr;real_t qm=0;
        const int result=evaluate_quad(qx,qr,&qm);
        residual.assign(qr.begin(),qr.end());*merit=double(qm);return result;
    }
    static int callback(void* data,const std::vector<double>& x,std::vector<double>& r,double* merit) {
        return static_cast<Context*>(data)->evaluate(x,r,merit);
    }
};

// Same rows and constitutive kernels as the float64 route. All temperature
// coordinates, Jacobian entries and linear algebra remain real_t here. The
// shared counter includes every earlier float64 probe, including failed ones.
inline std::vector<int> quad_newton(Context& context,const std::vector<real_t>& initial,int total_budget) {
    const size_t n=context.nc;int iterations=0,backtracks=0;
    auto evaluate=[&](const std::vector<real_t>& x,std::vector<real_t>& r,real_t& merit) {
        if(context.evaluations>=total_budget)throw std::runtime_error("lattice quad Newton evaluation budget exhausted");
        context.evaluate_quad(x,r,&merit);
        if(r.size()!=n || !isfinite_q(merit) || merit<0)throw std::invalid_argument("invalid lattice quad merit");
        for(real_t v:r)if(!isfinite_q(v))throw std::invalid_argument("nonfinite lattice quad residual");
    };
    auto norm=[](const std::vector<real_t>& r) {real_t v=0;for(real_t x:r)v+=x*x;return v;};
    std::vector<real_t> x=initial,r;real_t merit=0;evaluate(x,r,merit);
    while(merit>TCAD_CONST(0.25)) {
        const real_t old_norm=norm(r),old_merit=merit;
        std::vector<real_t> a(n*n),b(n),scale(n),plus=x,minus=x,rp,rm;
        for(size_t j=0;j<n;++j) {
            const real_t h=std::min(TCAD_CONST(1e-7),TCAD_CONST(0.25)*std::min(x[j]-context.P(j,14),context.P(j,15)-x[j]));
            if(!(h>0) || x[j]+h==x[j] || x[j]-h==x[j])throw std::runtime_error("lattice quad derivative stagnation");
            plus[j]=x[j]+h;minus[j]=x[j]-h;real_t unused;
            evaluate(plus,rp,unused);evaluate(minus,rm,unused);
            for(size_t i=0;i<n;++i)a[i*n+j]=(rp[i]-rm[i])/(2*h);
            plus[j]=minus[j]=x[j];
        }
        for(size_t i=0;i<n;++i) {
            b[i]=-r[i];for(size_t j=0;j<n;++j)scale[i]=std::max(scale[i],abs_q(a[i*n+j]));
            if(!(scale[i]>0))throw std::runtime_error("lattice quad singular Jacobian");
        }
        for(size_t k=0;k<n;++k) {
            size_t pivot=k;
            for(size_t i=k+1;i<n;++i)if(abs_q(a[i*n+k])/scale[i]>abs_q(a[pivot*n+k])/scale[pivot])pivot=i;
            if(abs_q(a[pivot*n+k])<=128*epsilon_q()*scale[pivot])throw std::runtime_error("lattice quad singular Jacobian");
            if(pivot!=k) {for(size_t j=k;j<n;++j)std::swap(a[k*n+j],a[pivot*n+j]);std::swap(b[k],b[pivot]);std::swap(scale[k],scale[pivot]);}
            for(size_t i=k+1;i<n;++i) {
                const real_t factor=a[i*n+k]/a[k*n+k];
                for(size_t j=k+1;j<n;++j)a[i*n+j]-=factor*a[k*n+j];
                b[i]-=factor*b[k];
            }
        }
        std::vector<real_t> direction(n);
        for(size_t reverse=n;reverse>0;--reverse) {
            const size_t i=reverse-1;real_t rhs=b[i];
            for(size_t j=i+1;j<n;++j)rhs-=a[i*n+j]*direction[j];
            direction[i]=rhs/a[i*n+i];
            if(!isfinite_q(direction[i]))throw std::runtime_error("lattice quad nonfinite direction");
        }
        bool accepted=false;real_t fraction=1;
        for(int line=0;line<24;++line,fraction/=2) {
            std::vector<real_t> trial(n),candidate;bool admissible=true,changed=false;
            for(size_t j=0;j<n;++j) {
                trial[j]=x[j]+fraction*direction[j];changed=changed || trial[j]!=x[j];
                admissible=admissible && isfinite_q(trial[j]) && context.P(j,14)<trial[j] && trial[j]<context.P(j,15);
            }
            if(!admissible || !changed) {++backtracks;continue;}
            real_t cm;evaluate(trial,candidate,cm);
            if(cm<=TCAD_CONST(0.25) || cm<old_merit || norm(candidate)<old_norm*(1-TCAD_CONST(1e-4)*fraction)) {
                x=trial;r=candidate;merit=cm;accepted=true;++iterations;break;
            }
            ++backtracks;
        }
        if(!accepted) {
            if(old_merit<=1) {evaluate(x,r,merit);break;}
            throw std::runtime_error("lattice quad line search failed physical budgets");
        }
    }
    return {iterations,backtracks};
}
}

// State: 5/cell; parameters: 16/cell, exactly the isolated-cell layout.
// Faces: owner,neighbor,G_W_K. Sources: signed total impulses, 3/cell.
// Output: isolated-cell 13-field layout/cell (no local evaluation count),
// then shared face and outward bath impulses, then global eval/iter/backtracks.
// Only when a precision retry is used, append reason 1=line search, 2=derivative, 3=singular float64 Jacobian.
inline std::vector<std::string> native_lattice_excess_raw(
        const std::vector<std::string>& state,const std::vector<std::string>& parameters,
        const std::vector<std::string>& faces,const std::vector<std::string>& source,
        const std::vector<double>& vn,const std::vector<double>& vp,double dt,double gate,int budget,
        const std::vector<std::string>& baths={},const std::vector<std::string>& varshni={}) {
    lattice_excess_detail::Context context(state,parameters,faces,source,vn,vp,dt,gate,baths,varshni);
    std::vector<double> initial,lower,upper;std::vector<real_t> quad_initial;
    int seed_evaluations=0;
    for(size_t i=0;i<context.nc;++i) {
        // Negative-a laws can have turning points: a Newton iteration started
        // at the old temperature may stall even for nearly insulated cells.
        // Use the bounded isolated roots only as a predictor. The accepted
        // state must still satisfy ALL coupled face and storage rows below.
        std::vector<std::string> local_state(state.begin()+5*i,state.begin()+5*i+5);
        std::vector<std::string> local_parameters(parameters.begin()+16*i,parameters.begin()+16*i+16);
        // Tangent capacity is only an isolated-root predictor. Accepted rows
        // above always use the exact nonlinear storage increment.
        if(!varshni.empty())local_parameters[0]=isolated_relaxation_detail::text(context.storage_capacity(i,context.S(i,2)));
        local_parameters.push_back(isolated_relaxation_detail::text(real_t(dt)));
        local_parameters.push_back(isolated_relaxation_detail::text(real_t(gate)/(4*context.nc)));
        for(size_t k=0;k<3;++k)local_parameters.push_back(isolated_relaxation_detail::text(context.q[3*i+k]));
        const auto seed=native_isolated_relaxation_raw(local_state,local_parameters,vn,vp,false,budget-seed_evaluations);
        seed_evaluations+=int(fermi_local_detail::decimals({seed.back()})[0]);
        initial.push_back(double(fermi_local_detail::decimals({seed[0]})[0]));
        quad_initial.push_back(fermi_local_detail::decimals({seed[0]})[0]);
        lower.push_back(double(context.P(i,14)));upper.push_back(double(context.P(i,15)));
    }
    std::vector<std::vector<double>> solved;int precision_retry=0;
    try {
        solved=native_fermi_newton_raw(initial,lower,upper,budget-seed_evaluations,
            lattice_excess_detail::Context::callback,&context);
    } catch(const std::runtime_error& error) {
        const std::string reason=error.what();
        if(reason=="native Newton line search failed physical budgets")precision_retry=1;
        else if(reason=="native Newton bound derivative stagnation")precision_retry=2;
        else if(reason=="native Newton singular Jacobian")precision_retry=3;
        else throw;
        const auto counts=lattice_excess_detail::quad_newton(context,quad_initial,budget-seed_evaluations);
        solved={{},{double(context.evaluations),double(counts[0]),double(counts[1])}};
    }
    std::vector<std::string> result;
    for(size_t i=0;i<context.nc;++i) {
        auto* o=context.output.data()+13*i;
        for(size_t k=0;k<2;++k) {
            context.admissible(i,k,o[0],o[1+k]);
            const real_t tau=exp_q(o[11+k]);
            if(!isfinite_q(tau) || !std::isfinite(double(tau)) || double(tau)<=0)
                throw std::invalid_argument("lattice excess effective relaxation time outside positive float64 range");
            o[11+k]=tau;
        }
    }
    for(real_t v:context.output)result.push_back(isolated_relaxation_detail::text(v));
    for(size_t k=0;k<3;++k)result.push_back(isolated_relaxation_detail::text(real_t(solved[1][k])+(k==0?seed_evaluations:0)));
    if(precision_retry)result.push_back(std::to_string(precision_retry));
    return result;
}
} // namespace tcad
