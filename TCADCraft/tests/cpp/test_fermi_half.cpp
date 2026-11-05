// Integral reference follows NIST DLMF 25.12.14, with t=u^2.
// Composite Simpson in hardware long double is independent of the production
// algebraic approximation. Doubling the mesh checks reference resolution.
#include "statistics.h"
#ifdef TCAD_FERMI_INTEGRATION
#include "gummel_solver.h"
#endif
#include <algorithm>
#include <iomanip>
#include <iostream>
#include <vector>
using namespace tcad;

static long double integral(long double eta, int intervals) {
    const long double upper=std::sqrt(std::max(eta,0.L)+80.L);
    const long double step=upper/intervals;
    auto integrand=[&](long double u) {
        const long double v=eta-u*u;
        const long double f=v>=0 ? 1/(1+std::exp(-v)) :
            std::exp(v)/(1+std::exp(v));
        return u*u*f;
    };
    long double sum=integrand(0)+integrand(upper);
    for(int i=1;i<intervals;++i)sum+=(i%2 ? 4 : 2)*integrand(i*step);
    return 4/std::sqrt(std::acos(-1.L))*step/3*sum;
}

int main() {
    size_t references=0,accuracy_failures=0,reference_failures=0;
    size_t monotonic=0,monotonic_failures=0,continuity=0,continuity_failures=0;
    size_t carriers=0,carrier_failures=0,boltzmann=0,boltzmann_failures=0;
    size_t extremes=0,extreme_failures=0;
    size_t poisson_checks=0,poisson_failures=0;
    long double poisson_error=0;
    long double worst=0,worst_eta=0,reference_difference=0;
    for(int grid=0;grid<2;++grid) {
        real_t previous=0;
        const int count=grid==0 ? 2000 : 1000;
        for(int i=0;i<=count;++i) {
            const real_t eta=grid==0 ? -TCAD_CONST(80.0)+TCAD_CONST(280.0)*i/count :
                -TCAD_CONST(2.0)+TCAD_CONST(8.0)*i/count;
            const auto coarse=integral((long double)eta,4096);
            const auto reference=integral((long double)eta,8192);
            const auto difference=std::abs(coarse/reference-1);
            reference_difference=std::max(reference_difference,difference);
            ++references;if(difference>1e-11L)++reference_failures;
            const real_t value=fermi_dirac_half(eta);
            const auto error=std::abs((long double)value/reference-1);
            if(error>worst){worst=error;worst_eta=(long double)eta;}
            if(!isfinite_q(value) || value<=0 || error>=.004L)++accuracy_failures;
            if(i) {++monotonic;if(!(value>previous))++monotonic_failures;}
            previous=value;
        }
    }
    // Old physical seams (-1,5) and the candidate's algebraic/range seams.
    for(real_t eta:{-TCAD_CONST(80.0),-TCAD_CONST(1.0),TCAD_CONST(1.0),
                    TCAD_CONST(5.0),TCAD_CONST(64.0)}) {
        const real_t h=TCAD_CONST(1e-9)*std::max(TCAD_CONST(1.0),abs_q(eta));
        const auto left=fermi_dirac_half(eta-h),mid=fermi_dirac_half(eta),right=fermi_dirac_half(eta+h);
        ++continuity;
        if(!(left<=mid && mid<=right) || (right-left)/mid>TCAD_CONST(1e-6))++continuity_failures;
    }
    for(real_t temperature:{TCAD_CONST(77.0),TCAD_CONST(300.0),TCAD_CONST(450.0)})
    for(real_t dos:{TCAD_CONST(1e16),TCAD_CONST(1e25)})
    for(real_t eta:{-TCAD_CONST(80.0),-TCAD_CONST(10.0),-TCAD_CONST(1.0),TCAD_CONST(0.0),
                   TCAD_CONST(1.0),TCAD_CONST(5.0),TCAD_CONST(20.0),TCAD_CONST(200.0)}) {
        const real_t vt=TCAD_CONST(8.617333262e-5)*temperature;
        const long double expected=(long double)dos*integral((long double)eta,8192);
        for(real_t value:{carrier_density_n(-vt*eta,0,temperature,dos,StatisticsType::FERMI_DIRAC),
                          carrier_density_p(vt*eta,0,temperature,dos,StatisticsType::FERMI_DIRAC)}) {
            ++carriers;if(!isfinite_q(value) || std::abs((long double)value/expected-1)>=.004L)++carrier_failures;
        }
        for(real_t value:{carrier_density_n(-vt*eta,0,temperature,dos,StatisticsType::BOLTZMANN),
                          carrier_density_p(vt*eta,0,temperature,dos,StatisticsType::BOLTZMANN)}) {
            ++boltzmann;const real_t expected_mb=dos*exp_q((vt*eta)/vt);
            if(value!=expected_mb)++boltzmann_failures;
        }
    }
    for(real_t eta:{TCAD_CONST(1e3),TCAD_CONST(1e10),TCAD_CONST(1e1000),TCAD_CONST(1e3000)}) {
        const real_t value=fermi_dirac_half(eta);
        const real_t scaled=value/eta/sqrt_q(eta);
        ++extremes;
        if(!isfinite_q(value) || value<=0 ||
           abs_q(scaled/(TCAD_CONST(4.0)/(3*sqrt_q(PI)))-1)>TCAD_CONST(2e-6))++extreme_failures;
    }
    ++extremes;if(fermi_dirac_half(-TCAD_CONST(1e3000))!=0)++extreme_failures;
    ++extremes;if(fermi_dirac_half(-TCAD_CONST(100.0))!=exp_q(-TCAD_CONST(100.0)))++extreme_failures;
#ifdef TCAD_FERMI_INTEGRATION
    for(int axis:{0,1,2})for(bool graded:{false,true})for(bool holes:{false,true})
    for(real_t eta:{-TCAD_CONST(5.0),-TCAD_CONST(1.0),TCAD_CONST(0.0),
                   TCAD_CONST(1.0),TCAD_CONST(5.0),TCAD_CONST(20.0)}) {
        Grid3D grid{axis==0?5u:1u,axis==1?5u:1u,axis==2?5u:1u,
                    TCAD_CONST(1e-7),TCAD_CONST(1e-7),TCAD_CONST(1e-7)};
        if(graded) {
            std::vector<real_t> pos={0,TCAD_CONST(.7e-7),TCAD_CONST(1.8e-7),TCAD_CONST(3e-7),TCAD_CONST(4e-7)};
            if(axis==0)grid.xx=pos;else if(axis==1)grid.yx=pos;else grid.zx=pos;
        }
        const real_t dos=TCAD_CONST(1e22);
        std::vector<real_t> phi(5,0),doping(5,0),eps(5,11*EPS0),DOS(5,dos);
        const auto minor=exp_q(-TCAD_CONST(20.0)),major=exp_q(eta);
        std::vector<real_t> n(5,dos*(holes?minor:major)),p(5,dos*(holes?major:minor));
        const auto nref=dos*(real_t)integral(holes?-20.L:(long double)eta,8192);
        const auto pref=dos*(real_t)integral(holes?(long double)eta:-20.L,8192);
        GummelOptions opt;opt.enable_quantum=false;opt.statistics_type=StatisticsType::FERMI_DIRAC;
        // Audit physical charge: the stabilized iteration's D*phi term can
        // dominate its RHS norm and hide deliberately incorrect densities.
        opt.boltzmann_lin=false;
        GummelSolver solver(grid,opt);
        solver.set_permittivity(eps);solver.set_doping(doping);solver.set_effective_dos(DOS,DOS);
        solver.set_poisson_dirichlet({{0,0},{4,0}});
        PoissonSolver reference(grid);reference.set_permittivity(eps);reference.set_doping(doping);
        reference.set_boltzmann_linearization(false,opt.VT);
        reference.set_dirichlet({{0,0},{4,0}});
        SolverOptions reference_options;reference_options.type=SolverType::DENSE_DIRECT;
        reference_options.tol=TCAD_CONST(1e-28);reference.set_solver_options(reference_options);
        reference.assemble(std::vector<real_t>(5,nref),std::vector<real_t>(5,pref));
        const bool solved=reference.solve(phi);
        const real_t expected=reference.residual_norm(phi,std::vector<real_t>(5,nref),std::vector<real_t>(5,pref));
        const real_t actual=solver.compute_poisson_residual(phi,n,p,true,false);
        // At the independent reference solution this norm measures the
        // approximate FD charge error. phi=0 would make both norms one.
        const auto error=std::abs((long double)actual);
        poisson_error=std::max(poisson_error,error);++poisson_checks;
        if(!solved || expected>TCAD_CONST(1e-24) || !isfinite_q(actual) || error>=.0041L)++poisson_failures;
        auto wrong_n=n,wrong_p=p;
        for(real_t& value:(holes?wrong_p:wrong_n))value*=exp_q(TCAD_CONST(2.0));
        const real_t damaged=solver.compute_poisson_residual(phi,wrong_n,wrong_p,true,false);
        if(!isfinite_q(damaged) || damaged<=TCAD_CONST(.0041))++poisson_failures;
    }
#endif
    const size_t failures=accuracy_failures+reference_failures+monotonic_failures+
        continuity_failures+carrier_failures+boltzmann_failures+extreme_failures+poisson_failures;
    std::cout<<std::setprecision(17)<<"{\"profile\":\""<<constants_profile_name()
        <<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"reference_evaluations\":"<<references
        <<",\"accuracy_failures\":"<<accuracy_failures<<",\"reference_failures\":"<<reference_failures
        <<",\"max_reference_resolution_difference\":"<<(double)reference_difference
        <<",\"maximum_relative_error\":"<<(double)worst<<",\"worst_eta\":"<<(double)worst_eta
        <<",\"monotonic_comparisons\":"<<monotonic<<",\"monotonic_failures\":"<<monotonic_failures
        <<",\"continuity_checks\":"<<continuity<<",\"continuity_failures\":"<<continuity_failures
        <<",\"fd_carrier_checks\":"<<carriers<<",\"fd_carrier_failures\":"<<carrier_failures
        <<",\"boltzmann_checks\":"<<boltzmann<<",\"boltzmann_failures\":"<<boltzmann_failures
        <<",\"range_checks\":"<<extremes<<",\"range_failures\":"<<extreme_failures
        <<",\"poisson_mapping_checks\":"<<poisson_checks<<",\"poisson_mapping_failures\":"<<poisson_failures
        <<",\"maximum_poisson_mapping_relative_error\":"<<(double)poisson_error
        <<",\"failures\":"<<failures<<",\"anchors\":[";
    bool first=true;
    for(real_t eta:{-TCAD_CONST(1.000000000001),-TCAD_CONST(1.0),-TCAD_CONST(.999999999999),
                   TCAD_CONST(0.0),TCAD_CONST(4.999999999999),TCAD_CONST(5.0),TCAD_CONST(5.000000000001)}) {
        if(!first)std::cout<<',';first=false;
        std::cout<<"["<<(double)eta<<","<<(double)fermi_dirac_half(eta)<<"]";
    }
    std::cout<<"]}\n";
    return failures ? 1 : 0;
}
