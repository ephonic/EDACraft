// Exercise the public transient API, including its actual adaptive controller.
// Uniform pair transport has an independent scalar backward Euler reference.
#include "device_simulator.h"
#include <iostream>
#include <iomanip>
#include <string>
using namespace tcad;

int main(int argc,char** argv) {
    size_t cases=0,failures=0,steps=0,rejections=0,guard_cases=0;
    real_t max_error=0,max_balance=0;
    if(argc==2 && std::string(argv[1])=="invalid") {
        for(int bad=0;bad<4;++bad) {
            DeviceSimulator sim(3,1,1,TCAD_CONST(1e-6),TCAD_CONST(1e-6),TCAD_CONST(1e-6));
            sim.set_quantum_enabled(false);sim.set_auger_enabled(true);
            sim.set_mobility(Vector(3,TCAD_CONST(.01)),Vector(3,TCAD_CONST(.01)));
            sim.set_dirichlet_potential({{0,0},{1,0},{2,0}});
            sim.set_initial_guess(Vector(3,0),Vector(3,TCAD_CONST(1e23)),Vector(3,TCAD_CONST(1e23)));
            if(bad==0)sim.set_statistics_type(1);
            if(bad==1)sim.set_ferroelectric_enabled(true);
            if(bad==2)sim.set_mobility(Vector(3,0),Vector(3,TCAD_CONST(.01)));
            if(bad==3)sim.set_mobility(Vector(3,0),Vector(3,0));
            ++guard_cases;
            try {sim.solve_transient();++failures;}
            catch(const std::invalid_argument&) {
                if(!sim.transient_attempt_history().empty())++failures;
            } catch(...) {++failures;}
        }
    } else for(int axis=0;axis<3;++axis)for(int species=0;species<3;++species)
    for(int mode=0;mode<6;++mode) {
        const real_t initial=TCAD_CONST(1e23);
        const real_t ni=(mode==1 || mode==2)?TCAD_CONST(1e24):TCAD_CONST(1e19);
        const real_t cn=species==1?TCAD_CONST(0.0):TCAD_CONST(2.8e-43);
        const real_t cp=species==0?TCAD_CONST(0.0):TCAD_CONST(9.9e-44);
        const real_t strength=mode==1?TCAD_CONST(1e-4):(mode==0 || mode==3?TCAD_CONST(100.0):TCAD_CONST(1.0));
        const real_t dt=strength/((cn+cp)*initial*initial),end=2*dt;
        const real_t tau=mode==4?3/(2*(cn+cp)*initial*initial):TCAD_CONST(1e100);
        const real_t generation=mode==5?TCAD_CONST(.2)*initial/dt:TCAD_CONST(0.0);
        DeviceSimulator sim(axis==0?3:1,axis==1?3:1,axis==2?3:1,
                            TCAD_CONST(1e-6),TCAD_CONST(1e-6),TCAD_CONST(1e-6));
        sim.set_quantum_enabled(false);sim.set_permittivity(Vector(3,11*EPS0));
        sim.set_mobility(Vector(3,TCAD_CONST(.01)),Vector(3,TCAD_CONST(.02)));
        sim.set_effective_dos(Vector(3,ni),Vector(3,ni));sim.set_bandgap(Vector(3,0));
        sim.set_recombination(Vector(3,tau),Vector(3,tau));
        sim.set_optical_generation(Vector(3,generation));
        sim.set_auger_params(cn,cp);sim.set_auger_enabled(mode!=3);
        sim.set_dirichlet_potential({{0,0},{1,0},{2,0}});
        sim.set_initial_guess(Vector(3,0),Vector(3,initial),Vector(3,initial));
        sim.set_newton_use_log_space(true);sim.set_gummel_max_iter(60);sim.set_tolerance(TCAD_CONST(1e-18));
        sim.set_transient_dt(dt);sim.set_transient_t_final(end);
        sim.set_nonlinear_history_enabled(true);
        if(mode==2)sim.set_transient_electrical_error_control(true,TCAD_CONST(1e-8),
            TCAD_CONST(.002),TCAD_CONST(1e12),dt*TCAD_CONST(1e-8),30);
        bool valid=true;size_t local_steps=0,local_rejected=0;
        real_t error=0,balance=0;
        try {
            const auto history=sim.solve_transient();
            valid=history.size()>=3 && history.front().initial_state && history.front().time==0 &&
                history.back().converged && abs_q(history.back().time/end-1)<TCAD_CONST(1e-14);
            real_t expected=initial;
            for(size_t k=1;k<history.size();++k) {
                const auto& now=history[k];const auto& prev=history[k-1];
                const real_t h=now.time-prev.time;
                valid=valid && now.converged && h>0 && now.accepted_dt==h && !now.initial_state;
                if(!now.converged || h<=0) {valid=false;break;}
                const real_t s=mode==3?TCAD_CONST(0.0):h*(cn+cp)*expected*expected;
                const real_t b=mode==4?h/(2*tau):TCAD_CONST(0.0);
                const real_t ratio=ni/expected,g=h*generation/expected;
                real_t lo=std::min(TCAD_CONST(1.0),ratio),hi=std::max(TCAD_CONST(1.0)+g,ratio);
                for(int j=0;j<160;++j) {
                    const real_t x=(lo+hi)/2;
                    if(x+s*x*(x*x-ratio*ratio)+b*(x-ratio)>1+g)hi=x;else lo=x;
                }
                expected*=(lo+hi)/2;
                for(size_t i=0;i<3;++i) {
                    valid=valid && isfinite_q(now.n[i]) && isfinite_q(now.p[i]) && now.n[i]>0 && now.p[i]>0;
                    error=std::max(error,abs_q(now.n[i]/expected-1));
                    error=std::max(error,abs_q(now.p[i]/expected-1));
                    real_t r=mode==3?TCAD_CONST(0.0):(cn*now.n[i]+cp*now.p[i])*(now.n[i]*now.p[i]-ni*ni);
                    if(mode==4)r+=(now.n[i]*now.p[i]-ni*ni)/(tau*(now.n[i]+now.p[i]+2*ni));
                    balance=std::max(balance,abs_q((now.n[i]-prev.n[i]+h*(r-generation))/prev.n[i]));
                    balance=std::max(balance,abs_q((now.p[i]-prev.p[i]+h*(r-generation))/prev.p[i]));
                }
                ++local_steps;
            }
            for(const auto& attempt:sim.transient_attempt_history()) {
                if(!attempt.accepted)++local_rejected;
                for(const auto& trial:attempt.trials)valid=valid && trial.solver=="newton";
            }
        } catch(const std::exception&) {valid=false;}
        valid=valid && error<TCAD_CONST(1e-8) && balance<TCAD_CONST(1e-8);
        ++cases;if(!valid)++failures;steps+=local_steps;rejections+=local_rejected;
        max_error=std::max(max_error,error);max_balance=std::max(max_balance,balance);
        std::cout<<std::setprecision(17)<<"{\"axis\":"<<axis<<",\"species\":"<<species<<",\"mode\":"<<mode
            <<",\"valid\":"<<(valid?"true":"false")<<",\"steps\":"<<local_steps<<",\"rejections\":"<<local_rejected
            <<",\"error\":"<<(double)error<<",\"balance\":"<<(double)balance<<"}\n";
    }
    std::cout<<"{\"test\":\"public_auger_transient\",\"cases\":"<<cases<<",\"guards\":"<<guard_cases
        <<",\"failures\":"<<failures<<",\"steps\":"<<steps<<",\"rejections\":"<<rejections
        <<",\"max_error\":"<<(double)max_error<<",\"max_balance\":"<<(double)max_balance<<"}\n";
    return failures?1:0;
}
