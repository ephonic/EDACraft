// Reference charge neutrality uses independent DLMF integral quadrature.
#include "statistics.h"
#include <algorithm>
#include <iostream>
#include <iomanip>
#include <limits>
#include <stdexcept>
#include <string>
using namespace tcad;
static long double integral(long double eta,int intervals) {
    const auto upper=std::sqrt(std::max(eta,0.L)+80.L),h=upper/intervals;
    auto f=[&](long double u){auto v=eta-u*u;return u*u*(v>=0?1/(1+std::exp(-v)):std::exp(v)/(1+std::exp(v)));};
    auto sum=f(0)+f(upper);
    for(int i=1;i<intervals;++i)sum+=(i%2?4:2)*f(h*i);
    return 4/std::sqrt(std::acos(-1.L))*h/3*sum;
}
static long double reference(long double gap,long double nc,long double nv,int intervals) {
    const long double middle=-gap/2,lc=std::log(nc),lv=std::log(nv);
    long double hi=std::abs(middle)+std::abs(lv-lc)+4,lo=-hi;
    for(int i=0;i<56;++i) {
        const auto x=(lo+hi)/2;
        if(lc+std::log(integral(middle+x,intervals))>lv+std::log(integral(middle-x,intervals)))hi=x;else lo=x;
    }
    const auto x=(lo+hi)/2;
    return std::exp((lc+std::log(integral(middle+x,intervals))+lv+std::log(integral(middle-x,intervals)))/2);
}
// Invert each species separately to test the common-energy constraint,
// rather than repeating the production shift-neutrality root algorithm.
static real_t inverse(real_t value) {
    if(value<exp_q(-TCAD_CONST(80.0)))return log_q(value);
    real_t lo=-TCAD_CONST(80.0),hi=TCAD_CONST(1e4);
    for(int i=0;i<180;++i) {
        const real_t mid=(lo+hi)/2;
        if(mid==lo || mid==hi)break;
        if(fermi_dirac_half(mid)>value)hi=mid;else lo=mid;
    }
    return (lo+hi)/2;
}
int main(int argc,char** argv) {
    size_t cases=0,accuracy_failures=0,resolution_failures=0,closure_failures=0;
    size_t symmetry_failures=0,scaling_failures=0,mb_checks=0,mb_failures=0;
    size_t range_checks=0,range_failures=0,invalid_checks=0,invalid_failures=0,exceptions=0;
    long double worst=0,resolution=0;real_t worst_closure=0;
    if(argc==2 && std::string(argv[1])=="invalid") {
        auto rejects=[&](real_t eg,real_t t,real_t nc,real_t nv) {
            ++invalid_checks;
            try{intrinsic_density(eg,t,nc,nv,StatisticsType::FERMI_DIRAC);++invalid_failures;}
            catch(const std::invalid_argument&){}catch(...){++invalid_failures;}
        };
        for(real_t v:{(real_t)std::numeric_limits<double>::quiet_NaN(),
                       (real_t)std::numeric_limits<double>::infinity(),
                      -(real_t)std::numeric_limits<double>::infinity()}) {
            rejects(v,300,1,1);rejects(1,v,1,1);rejects(1,300,v,1);rejects(1,300,1,v);
        }
        for(real_t v:{TCAD_CONST(0.0),-TCAD_CONST(1.0)}) {
            rejects(1,v,1,1);rejects(1,300,v,1);rejects(1,300,1,v);
        }
        rejects(TCAD_CONST(1e4000),TCAD_CONST(1e-4000),1,1);
    } else {
        for(real_t t:{TCAD_CONST(77.0),TCAD_CONST(300.0),TCAD_CONST(900.0)})
        for(real_t eg:{-TCAD_CONST(.1),TCAD_CONST(0.0),TCAD_CONST(.02),TCAD_CONST(.1),TCAD_CONST(.5),TCAD_CONST(1.12),TCAD_CONST(3.4)})
        for(real_t ratio:{TCAD_CONST(1.0),TCAD_CONST(1e-4),TCAD_CONST(1e4),TCAD_CONST(1e12)}) {
            ++cases;const real_t nc=TCAD_CONST(1e22),nv=nc*ratio,vt=TCAD_CONST(8.617333262e-5)*t,gap=eg/vt;
            const auto coarse=reference((long double)gap,(long double)nc,(long double)nv,1024);
            const auto fine=reference((long double)gap,(long double)nc,(long double)nv,2048);
            const auto diff=std::abs(coarse/fine-1);resolution=std::max(resolution,diff);
            if(diff>1e-10L)++resolution_failures;
            try {
                const real_t ni=intrinsic_density(eg,t,nc,nv,StatisticsType::FERMI_DIRAC);
                const auto error=std::abs((long double)ni/fine-1);worst=std::max(worst,error);
                if(!isfinite_q(ni) || ni<=0 || error>=.0041L)++accuracy_failures;
                if(isfinite_q(ni) && ni>0) {
                    const real_t closure=abs_q(inverse(ni/nc)+inverse(ni/nv)+gap);
                    worst_closure=std::max(worst_closure,closure);
                    if(closure>TCAD_CONST(8192.0)*epsilon_q()*(1+abs_q(gap)))++closure_failures;
                } else ++closure_failures;
                const real_t swapped=intrinsic_density(eg,t,nv,nc,StatisticsType::FERMI_DIRAC);
                if(!isfinite_q(swapped) || abs_q(swapped/ni-1)>TCAD_CONST(8192.0)*epsilon_q())++symmetry_failures;
                const real_t scaled=intrinsic_density(eg,t,nc*TCAD_CONST(1e3),nv*TCAD_CONST(1e3),StatisticsType::FERMI_DIRAC);
                if(!isfinite_q(scaled) || abs_q(scaled/ni/TCAD_CONST(1e3)-1)>TCAD_CONST(8192.0)*epsilon_q())++scaling_failures;
            } catch(const std::exception&){++exceptions;}
            const real_t argument=-eg/(TCAD_CONST(2.0)*vt);
            const real_t expected=argument<-TCAD_CONST(500.0)?TCAD_CONST(1e-20):sqrt_q(nc*nv)*exp_q(argument);
            ++mb_checks;if(intrinsic_density(eg,t,nc,nv,StatisticsType::BOLTZMANN)!=expected)++mb_failures;
        }
        auto range=[&](real_t eg,real_t t,real_t nc,real_t nv,real_t expected) {
            ++range_checks;
            try {
                const real_t measured=intrinsic_density(eg,t,nc,nv,StatisticsType::FERMI_DIRAC);
                if(!isfinite_q(measured) || (expected==0?measured!=0:abs_q(measured/expected-1)>TCAD_CONST(1e-12)))++range_failures;
            }catch(...){++range_failures;}
        };
        const real_t t=300,vt=TCAD_CONST(8.617333262e-5)*t;
        range(2000*vt,t,TCAD_CONST(1e20),TCAD_CONST(1e20),TCAD_CONST(1e20)*exp_q(-TCAD_CONST(1000.0)));
        range(0,t,TCAD_CONST(1e4000),TCAD_CONST(1e4000),TCAD_CONST(1e4000)*fermi_dirac_half(0));
        range(0,t,TCAD_CONST(1e-4000),TCAD_CONST(1e-4000),TCAD_CONST(1e-4000)*fermi_dirac_half(0));
        range(1,TCAD_CONST(.1),TCAD_CONST(1e20),TCAD_CONST(1e20),0);
        // Both occupation factors individually underflow, but large DOS
        // rescales the common density into the representable range.
        const real_t gap=TCAD_CONST(22000.0);
        range(gap*vt,t,TCAD_CONST(1e4000),TCAD_CONST(1e4000),exp_q(log_q(TCAD_CONST(1e4000))-gap/2));
        for(real_t argument:{-TCAD_CONST(501.0),-TCAD_CONST(500.0),TCAD_CONST(0.0)}) {
            const real_t eg=-2*vt*argument;
            const real_t a=-eg/(2*vt),expected=a<-TCAD_CONST(500.0)?TCAD_CONST(1e-20):sqrt_q(TCAD_CONST(1e20)*TCAD_CONST(1e20))*exp_q(a);
            ++mb_checks;if(intrinsic_density(eg,t,TCAD_CONST(1e20),TCAD_CONST(1e20),StatisticsType::BOLTZMANN)!=expected)++mb_failures;
        }
    }
    const size_t failures=accuracy_failures+resolution_failures+closure_failures+symmetry_failures+scaling_failures+mb_failures+range_failures+invalid_failures+exceptions;
    std::cout<<std::setprecision(17)<<"{\"test\":\"fd_intrinsic\",\"profile\":\""<<constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()
        <<",\"cases\":"<<cases<<",\"accuracy_failures\":"<<accuracy_failures<<",\"resolution_failures\":"<<resolution_failures
        <<",\"maximum_relative_error\":"<<(double)worst<<",\"maximum_reference_resolution_difference\":"<<(double)resolution
        <<",\"closure_failures\":"<<closure_failures<<",\"maximum_closure\":"<<(double)worst_closure
        <<",\"symmetry_failures\":"<<symmetry_failures<<",\"scaling_failures\":"<<scaling_failures
        <<",\"mb_checks\":"<<mb_checks<<",\"mb_failures\":"<<mb_failures
        <<",\"range_checks\":"<<range_checks<<",\"range_failures\":"<<range_failures
        <<",\"invalid_checks\":"<<invalid_checks<<",\"invalid_failures\":"<<invalid_failures
        <<",\"exceptions\":"<<exceptions<<",\"failures\":"<<failures<<"}\n";
    return failures?1:0;
}
