#include "device_simulator.h"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
using namespace tcad;

static void array(std::ostream& out, const std::vector<real_t>& v) {
    out << '[';
    for (size_t i=0;i<v.size();++i) { if(i)out<<',';out<<(long double)v[i]; }
    out << ']';
}

int main(int argc,char** argv) {
    std::ofstream file;
    if(argc==2) { file.open(argv[1]);if(!file)return 3; }
    size_t calls=0,failures=0;
    bool enabled_frozen=false;
    std::vector<real_t> enabled_phi,enabled_n,enabled_p;
    for(int mode=0;mode<5;++mode) {
        constexpr size_t count=17;
        const real_t ni=TCAD_CONST(1e20),vt=TCAD_CONST(8.617333262e-5)*TCAD_CONST(300.0);
        auto filled=[&](real_t v){return std::vector<real_t>(count,v);};
        auto doping=filled(0),n=filled(0),p=filled(0),phi=filled(0);
        auto neutral=[&](real_t d){return d>=0?(d+sqrt_q(d*d+4*ni*ni))/2:2*ni*ni/(sqrt_q(d*d+4*ni*ni)-d);};
        for(size_t i=0;i<count;++i) {
            doping[i]=-TCAD_CONST(1e21)*tanh_q(TCAD_CONST(8.0)*(real_t(i)/(count-1)-TCAD_CONST(.5)));
            n[i]=neutral(doping[i]);p[i]=ni*ni/n[i];phi[i]=vt*log_q(n[i]/ni);
        }
        DeviceSimulator sim(count,1,1,TCAD_CONST(1e-6)/(count-1),TCAD_CONST(8e-8),TCAD_CONST(8e-8));
        sim.set_permittivity(filled(TCAD_CONST(1e-10)));
        sim.set_mobility(filled(TCAD_CONST(.01)),filled(TCAD_CONST(.005)));
        sim.set_doping(doping);sim.set_effective_dos(filled(ni),filled(ni));
        sim.set_bandgap(filled(0));sim.set_temperature(TCAD_CONST(300.0));sim.set_thermal_voltage(vt);
        sim.set_recombination(filled(TCAD_CONST(1e100)),filled(TCAD_CONST(1e100)));
        sim.set_dirichlet_potential({{0,phi.front()},{count-1,phi.back()}});
        sim.set_electron_bc({{0,n.front()},{count-1,n.back()}});
        sim.set_hole_bc({{0,p.front()},{count-1,p.back()}});
        sim.set_initial_guess(phi,n,p);sim.set_mobility_model(1);
        sim.set_high_field_saturation(true,TCAD_CONST(1e4),TCAD_CONST(8e3),TCAD_CONST(2.0),TCAD_CONST(1.0),1);
        sim.set_use_newton(false);sim.set_gummel_max_iter(300);sim.set_tolerance(TCAD_CONST(1e-19));
        sim.set_nonlinear_history_enabled(true);
        // default, explicit on, explicit off, off->on, on->off.
        if(mode==1)sim.set_phi_freezing_enabled(true);
        if(mode==2)sim.set_phi_freezing_enabled(false);
        if(mode==3){sim.set_phi_freezing_enabled(false);sim.set_phi_freezing_enabled(true);}
        if(mode==4){sim.set_phi_freezing_enabled(true);sim.set_phi_freezing_enabled(false);}
        ++calls;auto eq=sim.solve_equilibrium(100,TCAD_CONST(1e-15));
        if(!eq.converged)return 2;
        auto initial=eq.phi;
        for(size_t i=0;i<count;++i)initial[i]+=TCAD_CONST(.05)*i/(count-1);
        sim.set_initial_guess(initial,eq.n,eq.p);
        sim.set_dirichlet_potential({{0,initial.front()},{count-1,initial.back()}});
        ++calls;auto r=sim.solve();
        bool ok=r.converged && r.nonlinear_history.size()==1 && r.nonlinear_history[0].converged &&
            r.nonlinear_history[0].solver=="gummel";
        if(mode==0){enabled_frozen=r.phi_frozen;enabled_phi=r.phi;enabled_n=r.n;enabled_p=r.p;}
        if(mode==1 || mode==3)
            ok=ok && r.phi_frozen==enabled_frozen && r.phi==enabled_phi && r.n==enabled_n && r.p==enabled_p;
        if(mode==2 || mode==4)ok=ok && !r.phi_frozen;
        if(!ok)++failures;
        if(file) {
            file<<std::setprecision(21)<<"{\"mode\":"<<mode<<",\"valid\":"<<(ok?"true":"false")
                <<",\"converged\":"<<(r.converged?"true":"false")<<",\"phi_frozen\":"<<(r.phi_frozen?"true":"false")
                <<",\"phi\":";array(file,r.phi);file<<",\"n\":";array(file,r.n);file<<",\"p\":";array(file,r.p);
            file<<",\"Jn\":";array(file,r.Jn_x);file<<",\"Jp\":";array(file,r.Jp_x);file<<"}\n";
        }
    }
    std::cout<<"{\"native_solver_calls\":"<<calls<<",\"controls\":5,\"failures\":"<<failures
             <<",\"valid\":"<<(failures?"false":"true")<<"}\n";
    return failures?1:0;
}
