// Raw DG/Newton/Gummel nonfinite rejection and finite-input compatibility.
#include <algorithm>
#include <cstdio>
#include <functional>
#include <initializer_list>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
#include "math_types.h"
#include "poisson_solver.h"
#include "sparse_matrix.h"
#include "linear_solver.h"
#include "statistics.h"
#define private public
#include "gummel_solver.h"
#include "newton_solver.h"
#undef private
using namespace tcad;
namespace {
void check(bool b,const char* m){if(!b)throw std::runtime_error(m);}
std::string exact(real_t x){char b[128];
#ifdef TCAD_USE_FLOAT128
    quadmath_snprintf(b,sizeof(b),"%Qa",x);
#else
    std::snprintf(b,sizeof(b),"%La",x);
#endif
    return b;
}
void append(Vector& a,const Vector& b){a.push_back(static_cast<real_t>(b.size()));a.insert(a.end(),b.begin(),b.end());}
std::vector<std::string> bits(const Vector& v){std::vector<std::string> r;for(auto q:v)r.push_back(exact(q));return r;}
Vector parameters(const DensityGradient& d){return {d.bn_,d.bp_,d.silicon_ml_,d.silicon_mt_,d.interface_distance_factor_,d.step_e_barrier_eV_,d.step_h_barrier_eV_,d.step_e_mass_,d.step_h_mass_,d.step_e_gamma_,d.step_h_gamma_,d.step_e_theta_,d.step_h_theta_,d.VT_};}
Vector parameters(const NewtonSolver& s){return {s.dg_bn_,s.dg_bp_,s.dg_silicon_ml_,s.dg_silicon_mt_,s.dg_interface_distance_factor_,s.dg_step_e_barrier_eV_,s.dg_step_h_barrier_eV_,s.dg_step_e_mass_,s.dg_step_h_mass_,s.dg_step_e_gamma_,s.dg_step_h_gamma_,s.dg_step_e_theta_,s.dg_step_h_theta_};}
Vector dgstate(const DensityGradient& d){Vector v=parameters(d);v.push_back(d.silicon_multivalley_);v.push_back(d.step_boundary_enabled_);v.push_back(static_cast<real_t>(d.silicon_subbands_));append(v,d.L_conf_);append(v,d.Nc_);append(v,d.Nv_);for(char q:d.semi_)v.push_back(q);for(auto q:d.N_conf_)v.push_back(static_cast<real_t>(q));return v;}
}
int main(int argc,char** argv){try{
    const bool observe=argc==2 && std::string(argv[1])=="--observe";
    size_t fixtures=0,attempted=0,rejected=0,accepted=0,preserved=0,retries=0,refs=0,stored_nonfinite=0,cache_loss=0,finite_cases=0,subband_cases=0,physical_cases=0;
    const real_t nan=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN()),inf=static_cast<real_t>(std::numeric_limits<double>::infinity()),wide=pow_q(TCAD_CONST(10.0),TCAD_CONST(400.0));
    check(isfinite_q(wide) && !std::isfinite(static_cast<double>(wide)),"wide finite fixture is not wider than double");
    const Vector base{TCAD_CONST(4.885e-20),TCAD_CONST(3.432e-20),TCAD_CONST(.916),TCAD_CONST(.190),TCAD_CONST(1.0),TCAD_CONST(.1),TCAD_CONST(.15),TCAD_CONST(.42),TCAD_CONST(1.0),TCAD_CONST(1.0),TCAD_CONST(1.0),TCAD_CONST(.5),TCAD_CONST(.5),TCAD_CONST(.02585)};
    const int starts[]={0,2,4,5,13},sizes[]={2,2,1,8,1};
    const char* errors[]={"DG coefficients must be finite","DG silicon effective masses must be finite","DG interface distance factor must be finite","DG step-boundary parameters must be finite","DG thermal voltage must be finite"};
    auto emit=[&](int route,const char* kind,const Vector& v){std::cout<<"{\"case\":"<<++refs<<",\"route\":"<<route<<",\"kind\":\""<<kind<<"\",\"values\":[";for(size_t i=0;i<v.size();++i)std::cout<<(i?",":"")<<'"'<<exact(v[i])<<'"';std::cout<<"]}\n";};
    for(int axis=0;axis<3;++axis)for(bool graded:{false,true})for(bool enabled:{false,true})for(int route=0;route<3;++route){
        Grid3D grid{1,1,1,TCAD_CONST(1e-8),TCAD_CONST(1e-8),TCAD_CONST(1e-8)};Vector pos{0,TCAD_CONST(.6e-8),TCAD_CONST(1.5e-8),TCAD_CONST(2.7e-8),TCAD_CONST(4e-8)};
        if(axis==0){grid.nx=5;if(graded)grid.xx=pos;}if(axis==1){grid.ny=5;if(graded)grid.yx=pos;}if(axis==2){grid.nz=5;if(graded)grid.zx=pos;}
        DensityGradient dg(grid);NewtonOptions no;no.enable_quantum=enabled;NewtonSolver ns(grid,no);GummelOptions go;go.enable_quantum=enabled;GummelSolver gs(grid,go);
        dg.set_semiconductor_mask({0,1,1,1,0});gs.dg_.set_semiconductor_mask({0,1,1,1,0});ns.set_semiconductor_mask({0,1,1,1,0});
        dg.set_effective_dos(Vector(5,TCAD_CONST(2.780e25)),Vector(5,TCAD_CONST(3.143e25)));gs.dg_.set_effective_dos(Vector(5,TCAD_CONST(2.780e25)),Vector(5,TCAD_CONST(3.143e25)));
        ns.set_effective_dos(Vector(5,TCAD_CONST(2.780e25)),Vector(5,TCAD_CONST(3.143e25)));ns.set_bandgap(Vector(5,TCAD_CONST(6.0)));
        ns.set_electron_bc({{0,TCAD_CONST(1e20)},{4,TCAD_CONST(1e20)}});ns.set_hole_bc({{0,TCAD_CONST(1e20)},{4,TCAD_CONST(1e20)}});
        auto set=[&](int group,const Vector& a,bool flag,size_t subbands=4){
            if(route==0){if(group==0)dg.set_coefficients(a[0],a[1]);if(group==1)dg.set_silicon_multivalley(flag,a[2],a[3],subbands);if(group==2)dg.set_interface_distance_factor(a[4]);if(group==3)dg.set_step_boundary(flag,a[5],a[6],a[7],a[8],a[9],a[10],a[11],a[12]);if(group==4)dg.set_thermal_voltage(a[13]);}
            if(route==1){if(group==0)ns.set_density_gradient_coefficients(a[0],a[1]);if(group==1)ns.set_density_gradient_silicon_multivalley(flag,a[2],a[3],subbands);if(group==2)ns.set_density_gradient_interface_distance_factor(a[4]);if(group==3)ns.set_density_gradient_step_boundary(flag,a[5],a[6],a[7],a[8],a[9],a[10],a[11],a[12]);}
            if(route==2){if(group==0)gs.set_density_gradient_coefficients(a[0],a[1]);if(group==1)gs.set_density_gradient_silicon_multivalley(flag,a[2],a[3],subbands);if(group==2)gs.set_density_gradient_interface_distance_factor(a[4]);if(group==3)gs.set_density_gradient_step_boundary(flag,a[5],a[6],a[7],a[8],a[9],a[10],a[11],a[12]);}
        };
        const int groups=route==0?5:4;
        for(int group=0;group<groups;++group)set(group,base,enabled);
        // Stored histories are deliberate sentinels, not claimed solve output.
        ns.residuals_={TCAD_CONST(2.0),TCAD_CONST(1.0)};ns.nonlinear_samples_={{TCAD_CONST(3.0)}};ns.use_lagged_quantum_potential_=true;ns.lagged_Qn_.assign(5,TCAD_CONST(.002));ns.lagged_Qp_.assign(5,-TCAD_CONST(.003));
        gs.poisson_res_={TCAD_CONST(2.0),TCAD_CONST(1.0)};gs.cont_res_={TCAD_CONST(3.0)};gs.nonlinear_samples_={{TCAD_CONST(4.0)}};
        auto seed=[&](){if(route==2)gs.set_transport_quantum_state(Vector(5,TCAD_CONST(.002)),Vector(5,-TCAD_CONST(.003)));};seed();
        auto raw=[&](){return route==0?parameters(dg):route==1?parameters(ns):parameters(gs.dg_);};
        auto state=[&](){if(route==0)return dgstate(dg);if(route==2){Vector v=dgstate(gs.dg_);append(v,gs.Qn_prev_);append(v,gs.Qp_prev_);append(v,gs.poisson_res_);append(v,gs.cont_res_);for(const auto& q:gs.nonlinear_samples_)append(v,q);return v;}
            Vector v=parameters(ns);v.push_back(ns.dg_silicon_multivalley_);v.push_back(ns.dg_step_boundary_enabled_);v.push_back(static_cast<real_t>(ns.dg_silicon_subbands_));v.push_back(ns.use_lagged_quantum_potential_);append(v,ns.lagged_Qn_);append(v,ns.lagged_Qp_);append(v,ns.residuals_);for(const auto& q:ns.nonlinear_samples_)append(v,q);for(char q:ns.semi_mask_)v.push_back(q);return v;};
        Vector n{TCAD_CONST(1e20),TCAD_CONST(9e20),TCAD_CONST(16e20),TCAD_CONST(9e20),TCAD_CONST(1e20)},p{TCAD_CONST(1e20),TCAD_CONST(4e20),TCAD_CONST(9e20),TCAD_CONST(4e20),TCAD_CONST(1e20)};
        auto output=[&](bool full=true){Vector v;if(route==1){const bool saved=ns.use_lagged_quantum_potential_;for(bool cached:{false,true}){ns.use_lagged_quantum_potential_=cached;Vector x(15);for(size_t i=0;i<5;++i){x[i]=TCAD_CONST(.01)*i;x[5+i]=n[i];x[10+i]=p[i];}Vector f;ns.assemble_residual(x,f);v.insert(v.end(),f.begin(),f.end());SparseMatrix j;ns.assemble_jacobian(x,j);Vector dense(225,0);for(size_t r=0;r<15;++r)for(size_t k=j.row_offsets()[r];k<j.row_offsets()[r+1];++k)dense[15*r+j.col_indices()[k]]+=j.vals()[k];v.insert(v.end(),dense.begin(),dense.end());}ns.use_lagged_quantum_potential_=saved;}
            else{auto& d=route==0?dg:gs.dg_;Vector qn,qp,nq,pq,pfn,pfp;d.quantum_potential(n,p,qn,qp);d.correct(n,p,nq,pq);if(full)d.quantum_potential_potential_form(n,p,Vector(5,0),Vector(5,0),pfn,pfp);for(const auto* a:{&qn,&qp,&nq,&pq,&pfn,&pfp})v.insert(v.end(),a->begin(),a->end());}
            for(auto q:v)check(isfinite_q(q),"positive DG parameter reference nonfinite");return v;};
        const auto control=bits(state()),equations=bits(output()),quick=bits(output(false));emit(route,"positive-output",output());++physical_cases;
        for(int group=0;group<groups;++group)for(int field=starts[group];field<starts[group]+sizes[group];++field)for(real_t bad:{nan,inf,-inf}){
            Vector a=base;for(int i=starts[group];i<starts[group]+sizes[group];++i)a[i]*=TCAD_CONST(1.1);a[field]=bad;
            ++attempted;bool caught=false;try{set(group,a,!enabled,7);}catch(const std::invalid_argument& e){check(std::string(e.what())==errors[group],"wrong DG parameter diagnostic");caught=true;++rejected;}
            if(caught){check(bits(state())==control,"rejected DG parameter changed stored state");check(bits(output(false))==quick,"rejected DG parameter changed equations");++preserved;}
            else{++accepted;check(observe,"nonfinite DG parameter accepted");const auto values=raw();check(!isfinite_q(values[field]),"accepted nonfinite parameter was not stored");++stored_nonfinite;if(route==2){check(gs.Qn_prev_.empty() && gs.Qp_prev_.empty(),"parent Gummel cache loss not reproduced");++cache_loss;}}
            check(observe || caught,"nonfinite DG parameter accepted");set(group,base,enabled);seed();check(bits(state())==control && bits(output(false))==quick,"DG finite retry did not restore state/equations");++retries;
        }
        // Entry compatibility only: do not evaluate singular/negative/wide
        // physical inputs or imply that finite arithmetic cannot overflow.
        for(int group=0;group<groups;++group)for(int field=starts[group];field<starts[group]+sizes[group];++field)for(real_t value:{TCAD_CONST(0.0),-TCAD_CONST(0.0),-TCAD_CONST(1.0),wide}){
            Vector a=base;a[field]=value;set(group,a,enabled);check(exact(raw()[field])==exact(value),"finite/signed-zero parameter changed");emit(route,"finite-entry-only",state());++finite_cases;
            set(group,base,enabled);seed();check(bits(state())==control && bits(output(false))==quick,"finite DG entry restore failed");
        }
        for(size_t subbands:{size_t(0),size_t(1),size_t(32),size_t(33)}){set(1,base,enabled,subbands);emit(route,"subband-entry-only",state());++subband_cases;set(1,base,enabled);seed();check(bits(state())==control,"subband restore failed");}
        for(int group=0;group<groups;++group){Vector a=base;for(int field=starts[group];field<starts[group]+sizes[group];++field)a[field]*=TCAD_CONST(1.1);set(group,a,enabled);emit(route,"positive-output",output());++physical_cases;set(group,base,enabled);seed();check(bits(state())==control && bits(output(false))==quick,"positive parameter restore failed");}
        check(bits(output())==equations,"batch potential-form/Jacobian restore failed");
        ++fixtures;
    }
    std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"fixtures\":"<<fixtures<<",\"attempted\":"<<attempted<<",\"rejected\":"<<rejected<<",\"accepted\":"<<accepted<<",\"preserved\":"<<preserved<<",\"retries\":"<<retries<<",\"stored_nonfinite\":"<<stored_nonfinite<<",\"gummel_cache_loss\":"<<cache_loss<<",\"finite_entry_cases\":"<<finite_cases<<",\"subband_entry_cases\":"<<subband_cases<<",\"positive_output_cases\":"<<physical_cases<<",\"valid_cases\":"<<refs<<"}\n";
    return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
