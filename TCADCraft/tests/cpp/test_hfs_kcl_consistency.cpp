// Candidate282 plus the pinned mobility fixes; no Python binding is involved.
#include "device_simulator.h"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
using namespace tcad;
static size_t calls=0, records=0; static int bias_sign=0, hfs_mode=0; static std::string route; static real_t bias_abs=0;
static void vector_json(std::ostream& out,const std::vector<real_t>& values) {
    out << '[';
    for (size_t i=0;i<values.size();++i) {if(i)out<<',';out<<(long double)values[i];}
    out << ']';
}
static void field(std::ostream& out,const char* name,const std::vector<real_t>& value) {
    out << ",\"" << name << "\":"; vector_json(out,value);
}
static void scalar(std::ostream& out,const char* name,real_t value) {
    out << ",\"" << name << "\":" << (long double)value;
}
static void flag(std::ostream& out,const char* name,bool value) {
    out << ",\"" << name << "\":" << (value?"true":"false");
}
static void emit(std::ostream& out,const char* group,int axis,int sign,int count,
                 int model,bool hfs,real_t temperature,const SimulationResult& r) {
    out << std::setprecision(21) << "{\"group\":\""<<group<<"\",\"axis\":"<<axis
        <<",\"sign\":"<<sign<<",\"count\":"<<count<<",\"model\":"<<model
        <<",\"hfs\":"<<(hfs?"true":"false")<<",\"reference_temperature\":"<<(long double)temperature;
    out<<",\"bias_sign\":"<<bias_sign<<",\"hfs_mode\":"<<hfs_mode
       <<",\"route\":\""<<route<<"\",\"nonlinear_history\":[";
    for(size_t i=0;i<r.nonlinear_history.size();++i) {
        if(i)out<<','; const auto& h=r.nonlinear_history[i];
        out<<"{\"solver\":\""<<h.solver<<"\",\"converged\":"<<(h.converged?"true":"false")<<",\"samples\":[";
        for(size_t j=0;j<h.samples.size();++j){if(j)out<<',';vector_json(out,h.samples[j]);}out<<"]}";
    }out<<']';
    field(out,"steady_gummel_audit",r.steady_gummel_audit);
    scalar(out,"bias_abs_V",bias_abs);
    flag(out,"converged",r.converged); flag(out,"phi_frozen",r.phi_frozen);
    field(out,"phi",r.phi); field(out,"n",r.n); field(out,"p",r.p);
    field(out,"temperature",r.temperature);
    field(out,"Jn_x",r.Jn_x);field(out,"Jn_y",r.Jn_y);field(out,"Jn_z",r.Jn_z);
    field(out,"Jp_x",r.Jp_x);field(out,"Jp_y",r.Jp_y);field(out,"Jp_z",r.Jp_z);
    field(out,"Jleak_x",r.Jleak_x);field(out,"Jleak_y",r.Jleak_y);field(out,"Jleak_z",r.Jleak_z);
    const auto& h=r.thermal;
    out<<",\"thermal_ledger\":{\"available\":"<<(h.available?"true":"false");
    flag(out,"linear_solve_converged",h.linear_solve_converged);
    flag(out,"current_projected",h.current_projected);
    scalar(out,"projected_Jx_A_m2",h.projected_Jx);
    scalar(out,"source_power_W",h.source_power);scalar(out,"outward_heat_W",h.outward_heat);
    scalar(out,"balance_residual_W",h.balance_residual);scalar(out,"max_cell_residual_W",h.max_cell_residual);
    field(out,"node_volumes_m3",h.node_volumes);field(out,"power_density_W_m3",h.power_density);
    field(out,"flux_x_W",h.flux_x);field(out,"flux_y_W",h.flux_y);field(out,"flux_z_W",h.flux_z);
    field(out,"bath_heat_W",h.bath_heat);
    out<<",\"bath_nodes\":[";
    for(size_t i=0;i<h.bath_nodes.size();++i){if(i)out<<',';out<<h.bath_nodes[i];}out<<']';
    field(out,"bath_temperatures_K",h.bath_temperatures);
    flag(out,"mobility_feedback",h.mobility_feedback);flag(out,"feedback_converged",h.feedback_converged);
    scalar(out,"feedback_residual_K",h.feedback_residual);
    flag(out,"transient_storage",h.transient_storage);
    scalar(out,"dt_s",h.dt);scalar(out,"storage_power_W",h.storage_power);
    scalar(out,"carrier_reference_temperature_K",h.carrier_temperature);
    scalar(out,"carrier_reference_VT_V",h.carrier_VT);
    field(out,"mobility_temperature_K",h.mobility_temperature);
    field(out,"mobility_n_m2_V_s",h.mobility_n);field(out,"mobility_p_m2_V_s",h.mobility_p);
    field(out,"previous_temperature_K",h.previous_temperature);
    field(out,"heat_capacity_J_m3_K",h.heat_capacity);field(out,"node_storage_power_W",h.node_storage_power);
    out<<"}}\n";out.flush();++records;
    if(!r.converged || r.phi_frozen)throw std::runtime_error("native state rejected");
}
static std::unique_ptr<DeviceSimulator> make(int axis,int count,int model,bool hfs,real_t temperature,
                            real_t length,real_t bias,int orientation,bool pn) {
    const real_t step=length/(count-1),ni=TCAD_CONST(1e20),D=TCAD_CONST(1e21);
    const real_t vt=TCAD_CONST(8.617333262e-5)*temperature;
    auto owner=std::make_unique<DeviceSimulator>(axis==0?count:1,axis==1?count:1,axis==2?count:1,
                        axis==0?step:TCAD_CONST(8e-8),
                        axis==1?step:TCAD_CONST(8e-8),
                        axis==2?step:TCAD_CONST(8e-8));
    auto& sim=*owner;
    auto values=[&](real_t value){return std::vector<real_t>(count,value);};
    auto doping=values(-D),phi=values(0),n=values(ni),p=values(ni);
    if(pn)for(int i=0;i<count;++i)doping[i]=orientation*D*tanh_q(TCAD_CONST(8.0)*(real_t(i)/(count-1)-TCAD_CONST(.5)));
    auto neutral_n=[&](real_t d){return d>=0?(d+sqrt_q(d*d+4*ni*ni))/2:2*ni*ni/(sqrt_q(d*d+4*ni*ni)-d);};
    real_t left=vt*log_q(neutral_n(doping.front())/ni);
    real_t right=vt*log_q(neutral_n(doping.back())/ni)+bias;
    for(int i=0;i<count;++i) {
        phi[i]=left+(right-left)*i/(count-1);
        n[i]=pn?ni*exp_q(phi[i]/vt):neutral_n(-D);
        p[i]=ni*ni/n[i];
    }
    sim.set_permittivity(values(TCAD_CONST(1e-10)));
    sim.set_mobility(values(TCAD_CONST(.01)),values(TCAD_CONST(.005)));
    sim.set_doping(doping);sim.set_effective_dos(values(ni),values(ni));
    sim.set_bandgap(values(0));sim.set_temperature(temperature);sim.set_thermal_voltage(vt);
    sim.set_recombination(values(TCAD_CONST(1e100)),values(TCAD_CONST(1e100)));
    sim.set_dirichlet_potential({{0,left},{size_t(count-1),right}});
    sim.set_electron_bc({{0,neutral_n(doping.front())},{size_t(count-1),neutral_n(doping.back())}});
    sim.set_hole_bc({{0,ni*ni/neutral_n(doping.front())},{size_t(count-1),ni*ni/neutral_n(doping.back())}});
    sim.set_initial_guess(phi,n,p);
    sim.set_use_newton(true);sim.set_newton_primary(true);
    sim.set_newton_use_log_space(true);sim.set_newton_use_log_damping(true);
    sim.set_phi_freezing_enabled(false);sim.set_gummel_max_iter(300);sim.set_tolerance(TCAD_CONST(1e-19));
    sim.set_mobility_model(model);
    sim.set_high_field_saturation(hfs,TCAD_CONST(1e4),TCAD_CONST(8e3),TCAD_CONST(2.0),TCAD_CONST(1.0),1);
    // No regularizing reference density: Arora+positive-reference remains
    // outside the parent candidate's declared supported scope.

    return owner;
}
static real_t read_real(std::istream& in){long double v;in>>v;if(!in)throw std::runtime_error("invalid seed");return real_t(v);}
int main(int argc,char** argv) {
    if(argc!=3)return 3;std::ifstream input(argv[1]);std::ofstream out(argv[2]);if(!input || !out)return 3;
    size_t controls=0,failures=0;input>>controls;
    for(size_t k=0;k<controls;++k) {
        int orientation,count,model;input>>orientation>>count>>model>>hfs_mode>>bias_sign;bias_abs=read_real(input);
        Vector phi(count),n(count),p(count);
        for(auto& v:phi)v=read_real(input);for(auto& v:n)v=read_real(input);for(auto& v:p)v=read_real(input);
        auto owner=make(0,count,model,false,TCAD_CONST(300.0),TCAD_CONST(1e-6),0,orientation,true);
        auto& sim=*owner;sim.set_initial_guess(phi,n,p);
        sim.set_dirichlet_potential({{0,phi.front()},{size_t(count-1),phi.back()}});
        sim.set_high_field_saturation(hfs_mode!=0,TCAD_CONST(1e4),TCAD_CONST(8e3),TCAD_CONST(2.0),TCAD_CONST(1.0),hfs_mode==1?1:0);
        sim.set_nonlinear_history_enabled(true);route="newton";++calls;auto result=sim.solve();
        bool valid=result.converged && !result.phi_frozen && result.nonlinear_history.size()==1 &&
            result.nonlinear_history[0].converged && result.nonlinear_history[0].solver=="newton";
        try{emit(out,"pn_warm",0,orientation,count,model,hfs_mode!=0,TCAD_CONST(300.0),result);}catch(const std::exception&){valid=false;}
        if(!valid)++failures;
    }
    std::cout<<"{\"valid\":"<<(failures?"false":"true")<<",\"native_solver_calls\":"<<calls
        <<",\"records\":"<<records<<",\"failures\":"<<failures<<",\"mantissa_bits\":"<<real_mantissa_bits()<<"}\n";
    return failures?2:0;
}
