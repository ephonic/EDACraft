#pragma once

// Native iteration, with an explicit Python-dispatched residual boundary.
// Physical kernels may be native; this interface does not imply a fully native
// device driver. Callback errors and rejected iterates never commit state.
#include "math_types.h"
#include <algorithm>
#include <stdexcept>
#include <vector>

namespace tcad {
// Only explicit native constitutive state-domain failures may reject a trial.
// Input/schema errors, Python callback exceptions and solver failures remain
// fatal. The initial state is always evaluated without recovery.
struct FermiStateDomainError : std::invalid_argument {
    using std::invalid_argument::invalid_argument;
};

using FermiResidualCallback = int (*)(void*, const std::vector<double>&,
                                     std::vector<double>&, double*);

inline std::vector<double> fermi_newton_direction(
        const std::vector<double>& matrix, const std::vector<double>& residual) {
    const size_t n=residual.size();
    std::vector<real_t> a(matrix.begin(),matrix.end()),b(n),row_scale(n);
    for(size_t i=0;i<n;++i) {
        b[i]=-real_t(residual[i]);
        for(size_t j=0;j<n;++j) row_scale[i]=std::max(row_scale[i],abs_q(a[i*n+j]));
        if(!(row_scale[i]>0)) throw std::runtime_error("native Newton singular Jacobian");
    }
    // Scaled partial pivoting; the nonlinear Jacobian need not be SPD.
    for(size_t k=0;k<n;++k) {
        size_t pivot=k;
        for(size_t i=k+1;i<n;++i)
            if(abs_q(a[i*n+k])/row_scale[i]>abs_q(a[pivot*n+k])/row_scale[pivot]) pivot=i;
        if(abs_q(a[pivot*n+k])<=128*epsilon_q()*row_scale[pivot])
            throw std::runtime_error("native Newton singular Jacobian");
        if(pivot!=k) {
            for(size_t j=k;j<n;++j) std::swap(a[k*n+j],a[pivot*n+j]);
            std::swap(b[k],b[pivot]);std::swap(row_scale[k],row_scale[pivot]);
        }
        for(size_t i=k+1;i<n;++i) {
            const real_t factor=a[i*n+k]/a[k*n+k];
            for(size_t j=k+1;j<n;++j) a[i*n+j]-=factor*a[k*n+j];
            b[i]-=factor*b[k];
        }
    }
    std::vector<real_t> x(n);std::vector<double> exported(n);
    for(size_t reverse=n;reverse>0;--reverse) {
        const size_t i=reverse-1;real_t rhs=b[i];
        for(size_t j=i+1;j<n;++j) rhs-=a[i*n+j]*x[j];
        x[i]=rhs/a[i*n+i];exported[i]=double(x[i]);
        if(!std::isfinite(exported[i])) throw std::runtime_error("native Newton nonfinite direction");
    }
    return exported;
}

inline std::vector<std::vector<double>> native_fermi_newton_raw(
        const std::vector<double>& initial,const std::vector<double>& lower,
        const std::vector<double>& upper,int max_nfev,
        FermiResidualCallback callback,void* context) {
    const size_t n=initial.size();
    if(n==0 || n>1024 || lower.size()!=n || upper.size()!=n || max_nfev<1 || !callback)
        throw std::invalid_argument("native Newton invalid dimensions or evaluation budget");
    for(size_t j=0;j<n;++j)
        if(!std::isfinite(initial[j]) || !std::isfinite(lower[j]) || !std::isfinite(upper[j]) ||
                !(lower[j]<initial[j] && initial[j]<upper[j]))
            throw std::invalid_argument("native Newton requires finite strict bounds");
    int evaluations=0,iterations=0,backtracks=0;
    std::vector<double> history;
    auto evaluate=[&](const std::vector<double>& x,std::vector<double>& r,double& merit) {
        if(evaluations>=max_nfev) throw std::runtime_error("native Newton evaluation budget exhausted");
        ++evaluations;
        if(callback(context,x,r,&merit)!=0) throw std::runtime_error("native Newton residual callback failed");
        if(r.size()!=n || !std::isfinite(merit) || merit<0)
            throw std::invalid_argument("native Newton invalid residual or physical merit");
        for(double value:r) if(!std::isfinite(value))
            throw std::invalid_argument("native Newton nonfinite residual");
    };
    auto norm=[](const std::vector<double>& r) {
        real_t value=0;for(double v:r) value+=real_t(v)*real_t(v);return value;
    };
    std::vector<double> x=initial,r;double merit=0;
    evaluate(x,r,merit);
    while(merit>0.25) {
        const real_t old_norm=norm(r);const double old_merit=merit;
        std::vector<double> jac(n*n),plus=x,minus=x,rplus,rminus;
        for(size_t j=0;j<n;++j) {
            double h=std::min(1e-7,0.25*std::min(x[j]-lower[j],upper[j]-x[j]));
            const double initial_h=h;
            bool differentiated=false,domain_rejected=false;
            for(int probe=0;probe<16;++probe) {
                if(!(h>0) || x[j]+h==x[j] || x[j]-h==x[j]) {
                    if(domain_rejected) break;
                    throw std::runtime_error("native Newton bound derivative stagnation");
                }
                plus[j]=x[j]+h;minus[j]=x[j]-h;double unused;
                try {
                    evaluate(plus,rplus,unused);evaluate(minus,rminus,unused);
                } catch(const FermiStateDomainError&) {
                    domain_rejected=true;
                    plus[j]=minus[j]=x[j];h*=0.5;++backtracks;continue;
                }
                for(size_t i=0;i<n;++i) jac[i*n+j]=(rplus[i]-rminus[i])/(2*h);
                plus[j]=minus[j]=x[j];differentiated=true;break;
            }
            // A valid state can lie closer to a constitutive boundary than a
            // central stencil can resolve. Preserve the established central
            // path; only after it fails, try an admissible one-sided secant.
            // Its truncation error affects the direction, never the final
            // physical acceptance test. Every callback uses the same budget.
            if(!differentiated && domain_rejected) {
                h=initial_h;
                for(int probe=0;probe<16 && !differentiated;++probe,h*=0.5) {
                    for(double sign:{1.,-1.}) {
                        std::vector<double> trial=x,sample;double unused;
                        trial[j]=x[j]+sign*h;
                        if(trial[j]==x[j] || !(lower[j]<trial[j] && trial[j]<upper[j])) continue;
                        try {
                            evaluate(trial,sample,unused);
                        } catch(const FermiStateDomainError&) {
                            ++backtracks;continue;
                        }
                        const double step=trial[j]-x[j];
                        for(size_t i=0;i<n;++i) jac[i*n+j]=(sample[i]-r[i])/step;
                        differentiated=true;break;
                    }
                }
            }
            if(!differentiated)
                throw std::runtime_error("native Newton constitutive derivative domain exhausted");
        }
        const auto direction=fermi_newton_direction(jac,r);
        bool accepted=false;
        for(int line=0;line<16;++line) {
            const double fraction=std::ldexp(1.0,-line);
            std::vector<double> trial(n);bool admissible=true,changed=false;
            for(size_t j=0;j<n;++j) {
                trial[j]=x[j]+fraction*direction[j];
                admissible=admissible && std::isfinite(trial[j]) && lower[j]<trial[j] && trial[j]<upper[j];
                changed=changed || trial[j]!=x[j];
            }
            if(!admissible || !changed) {++backtracks;continue;}
            std::vector<double> candidate;double candidate_merit;
            // Reevaluate the same constitutive equations at a smaller trial.
            // Never catch unrelated failures or clip a constitutive value.
            try {
                evaluate(trial,candidate,candidate_merit);
            } catch(const FermiStateDomainError&) {
                ++backtracks;continue;
            }
            if(candidate_merit<=0.25 || candidate_merit<old_merit ||
                    norm(candidate)<old_norm*real_t(1-1e-4*fraction)) {
                x=trial;r=candidate;merit=candidate_merit;accepted=true;++iterations;
                history.insert(history.end(),{double(evaluations),merit,fraction});break;
            }
            ++backtracks;
        }
        if(!accepted) {
            // The absolute physical budgets are the final stopping criterion.
            if(old_merit<=1.0) {evaluate(x,r,merit);break;}
            throw std::runtime_error("native Newton line search failed physical budgets");
        }
    }
    // Restore the dispatcher's cache to the accepted iterate after Jacobian probes.
    // A successful final trial already populated it; no unbudgeted callback here.
    return {x,{double(evaluations),double(iterations),double(backtracks),merit},history};
}
} // namespace tcad
