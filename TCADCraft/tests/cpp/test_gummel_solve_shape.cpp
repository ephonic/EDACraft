#include <algorithm>
#include <cstdio>
#include <iostream>
#include <map>
#include <memory>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include "math_types.h"
#include "sparse_matrix.h"
#include "linear_solver.h"
#include "statistics.h"
#define private public
#include "poisson_solver.h"
#include "gummel_solver.h"
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
std::vector<std::string> bits(const Vector& a){std::vector<std::string> v;for(auto x:a)v.push_back(exact(x));return v;}
void append(Vector& a,const Vector& b){a.push_back(static_cast<real_t>(b.size()));a.insert(a.end(),b.begin(),b.end());}
struct Quiet {std::ostringstream out;std::streambuf* old;std::streambuf* old_error;Quiet():old(std::cout.rdbuf(out.rdbuf())),old_error(std::cerr.rdbuf(out.rdbuf())){}~Quiet(){std::cerr.rdbuf(old_error);std::cout.rdbuf(old);}};
Vector state(const GummelSolver& s){Vector v;
    for(const auto* a:{&s.mu_n_,&s.mu_p_,&s.Nc_,&s.Nv_,&s.Eg_,&s.dg_.Nc_,&s.dg_.Nv_,&s.Qn_prev_,&s.Qp_prev_,&s.poisson_res_,&s.cont_res_,&s.poisson_.leak_phi_,&s.poisson_.leak_E_mag_,&s.poisson_.rhs_})append(v,*a);
    for(auto q:s.poisson_.A_.vals())v.push_back(q);
    for(auto q:s.poisson_.A_.row_offsets())v.push_back(static_cast<real_t>(q));
    for(auto q:s.poisson_.A_.col_indices())v.push_back(static_cast<real_t>(q));
    v.insert(v.end(),{s.poisson_residual_final_,s.quantum_residual_final_,s.electron_update_final_,s.hole_update_final_,static_cast<real_t>(s.phi_was_frozen_),static_cast<real_t>(s.poisson_.assembled_),static_cast<real_t>(s.cont_e_use_banded_direct_),static_cast<real_t>(s.cont_h_use_banded_direct_)});
    for(const auto& q:s.nonlinear_samples_)append(v,q);return v;
}
bool invoke(int route,GummelSolver& s,Vector& phi,Vector& n,Vector& p){
    Quiet quiet;
    if(route==0)return s.solve(phi,n,p);
    if(route==1){check(isfinite_q(s.compute_poisson_residual(phi,n,p)),"Poisson audit nonfinite");return true;}
    if(route==2){auto q=s.compute_continuity_residuals(phi,n,p);check(isfinite_q(q.first) && isfinite_q(q.second),"continuity audit nonfinite");return true;}
    if(route==3)return s.solve_electron_density(phi,n,p,nullptr);
    if(route==4)return s.solve_hole_density(phi,n,p,nullptr);
    return s.solve_continuity(phi,n,p,TCAD_CONST(1.0));
}
}
int main(int argc,char** argv){try{
    const bool observe=argc==2 && std::string(argv[1])=="--observe";
    size_t attempted=0,rejected=0,preserved=0,retries=0,skipped=0,late=0,existing=0,changed=0,refs=0,independent=0,transport=0,undamped=0,undamped_converged=0;
    real_t max_error=0;
    auto emit=[&](const char* kind,const Vector& a){std::cout<<"{\"case\":"<<++refs<<",\"kind\":\""<<kind<<"\",\"values\":[";for(size_t i=0;i<a.size();++i)std::cout<<(i?",":"")<<'"'<<exact(a[i])<<'"';std::cout<<"]}\n";};
    for(int axis=0;axis<3;++axis)for(bool graded:{false,true})for(bool quantum:{false,true})for(bool fd:{false,true}){
        Grid3D g{1,1,1,TCAD_CONST(1e-8),TCAD_CONST(1e-8),TCAD_CONST(1e-8)};Vector pos{0,TCAD_CONST(.6e-8),TCAD_CONST(1.5e-8),TCAD_CONST(2.7e-8),TCAD_CONST(4e-8)};
        if(axis==0){g.nx=5;if(graded)g.xx=pos;}if(axis==1){g.ny=5;if(graded)g.yx=pos;}if(axis==2){g.nz=5;if(graded)g.zx=pos;}
        GummelOptions go;go.enable_quantum=quantum;go.statistics_type=fd?StatisticsType::FERMI_DIRAC:StatisticsType::BOLTZMANN;go.max_iter=4;go.cont_damping=quantum?TCAD_CONST(.5):TCAD_CONST(1.0);go.use_log_damping=false;go.boltzmann_lin=false;go.poisson_tol=go.continuity_tol=TCAD_CONST(1e-18);go.record_nonlinear_history=true;
        auto materials=[](GummelSolver& s,size_t size=5){s.set_mobility(Vector(size,TCAD_CONST(.14)),Vector(size,TCAD_CONST(.045)));s.set_effective_dos(Vector(size,TCAD_CONST(2.8e25)),Vector(size,TCAD_CONST(2.8e25)));s.set_bandgap(Vector(size,TCAD_CONST(1.12)));s.set_recombination({},{});};
        auto make=[&](){auto s=std::make_unique<GummelSolver>(g,go);materials(*s);s->set_permittivity(Vector(5,EPS0*TCAD_CONST(11.7)));s->set_doping(Vector(5,0));s->set_poisson_dirichlet({{0,0},{4,0}});s->set_electron_bc({{0,TCAD_CONST(1e20)},{4,TCAD_CONST(1e20)}});s->set_hole_bc({{0,TCAD_CONST(1e20)},{4,TCAD_CONST(1e20)}});s->set_density_gradient_coefficients(0,0);Vector phi(5,0),n(5,TCAD_CONST(1e20)),p=n;check(invoke(0,*s,phi,n,p),"equilibrium fixture failed to converge");check(!s->poisson_res_.empty(),"fixture did not produce solve history");s->set_transport_quantum_state(Vector(5,TCAD_CONST(.002)),Vector(5,-TCAD_CONST(.003)));return s;};
        auto valid=[&](int route,GummelSolver& s,bool reference=false){Vector phi(5,0),n(5,TCAD_CONST(1e20)),p=n;s.set_transport_quantum_state(Vector(5,0),Vector(5,0));check(invoke(route,s,phi,n,p),"valid retry failed");Vector v=phi;append(v,n);append(v,p);
            auto compare=[&](real_t error){if(reference){max_error=std::max(max_error,error);check(error<TCAD_CONST(1e-18),"independent equilibrium reference mismatch");++independent;}};
            if(route==0)for(auto q:phi)compare(abs_q(q));
            if(route==0 || route==3 || route==5)for(auto q:n)compare(abs_q(q-TCAD_CONST(1e20))/TCAD_CONST(1e20));
            if(route==0 || route==4 || route==5)for(auto q:p)compare(abs_q(q-TCAD_CONST(1e20))/TCAD_CONST(1e20));
            if(route==1){for(bool isolated:{false,true}){real_t q=s.compute_poisson_residual(phi,n,p,isolated);v.push_back(q);compare(abs_q(q));}}
            if(route==2){auto q=s.compute_continuity_residuals(phi,n,p);v.push_back(q.first);v.push_back(q.second);compare(abs_q(q.first));compare(abs_q(q.second));}
            return v;};
        // Malformed states: baseline executes only paths checked safe by inspection.
        for(int route=0;route<6;++route)for(int field=0;field<3;++field)for(size_t size:{size_t(0),size_t(1),size_t(4),size_t(6)}){
            auto s=make();Vector phi(5,TCAD_CONST(.007)),n(5,TCAD_CONST(1e20)),p=n;(field==0?phi:field==1?n:p).resize(size,field?TCAD_CONST(1e20):TCAD_CONST(.007));
            const auto saved=bits(state(*s)),a=bits(phi),b=bits(n),c=bits(p);++attempted;
            const bool safe=route==2 || (route==0 && field!=0 && (!fd || size==6)) || (route==1 && (!fd || field==0));
            if(observe && !safe){++skipped;continue;}
            bool caught=false;std::string message;try{invoke(route,*s,phi,n,p);}catch(const std::invalid_argument& e){caught=true;message=e.what();}
            check(caught,"invalid state shape accepted");
            if(!observe){const char* expected=route==1?"Gummel Poisson audit requires full states":route==2?"continuity audit requires full states":"Gummel solve requires full states";check(message==expected,"wrong state shape diagnostic");check(bits(state(*s))==saved && bits(phi)==a && bits(n)==b && bits(p)==c,"state rejection changed solver or input");++rejected;++preserved;}
            else if(route==2){check(bits(state(*s))==saved,"existing audit guard changed state");++existing;}
            else{++late;if(bits(state(*s))!=saved)++changed;}
            auto result=valid(route,*s);for(auto q:result)check(isfinite_q(q),"state retry nonfinite");++retries;
        }
        for(int route:{0,2,3,4,5,1})for(int field=0;field<5;++field)for(size_t size:{size_t(0),size_t(1),size_t(4)}){
            if(route==1 && (!fd || field<2 || field==4))continue;
            auto s=make();
            if(field==0)s->set_mobility(Vector(size,TCAD_CONST(.14)),Vector(5,TCAD_CONST(.045)));
            if(field==1)s->set_mobility(Vector(5,TCAD_CONST(.14)),Vector(size,TCAD_CONST(.045)));
            if(field==2)s->set_effective_dos(Vector(size,TCAD_CONST(2.8e25)),Vector(5,TCAD_CONST(2.8e25)));
            if(field==3)s->set_effective_dos(Vector(5,TCAD_CONST(2.8e25)),Vector(size,TCAD_CONST(2.8e25)));
            if(field==4)s->set_bandgap(Vector(size,TCAD_CONST(1.12)));
            const auto saved=bits(state(*s));++attempted;if(observe){++skipped;continue;}
            Vector phi(5,0),n(5,TCAD_CONST(1e20)),p=n;bool caught=false;try{invoke(route,*s,phi,n,p);}catch(const std::invalid_argument& e){caught=true;check(std::string(e.what())==(field<2?"Gummel mobility must cover all nodes":field<4?"Gummel effective DOS must cover all nodes":"Gummel bandgap must cover all nodes"),"wrong material shape diagnostic");}
            check(caught && bits(state(*s))==saved,"invalid material shape mutated state");check(bits(phi)==bits(Vector(5,0)) && bits(n)==bits(Vector(5,TCAD_CONST(1e20))) && bits(p)==bits(n),"material rejection mutated inputs");++rejected;++preserved;materials(*s);valid(route,*s);++retries;
        }
        // Optional supplied transport potential is read by each carrier block.
        for(bool hole:{false,true})for(size_t size:{size_t(0),size_t(1),size_t(4)}){
            auto s=make();++attempted;++transport;if(observe){++skipped;continue;}Vector phi(5,0),n(5,TCAD_CONST(1e20)),p=n,t(size,0);const auto saved=bits(state(*s));bool caught=false;
            try{if(hole)s->solve_hole_density(phi,n,p,&t);else s->solve_electron_density(phi,n,p,&t);}catch(const std::invalid_argument& e){check(std::string(e.what())=="Gummel transport potential must cover all nodes","wrong transport potential diagnostic");caught=true;}
            check(caught && bits(state(*s))==saved,"transport potential rejection changed state");++rejected;++preserved;valid(hole?4:3,*s);++retries;
        }
        for(int route=0;route<6;++route)for(size_t size:{size_t(5),size_t(6)}){auto s=make();materials(*s,size);emit("valid-full-or-oversized-material",valid(route,*s,true));}
        for(size_t size:{size_t(0),size_t(1),size_t(4),size_t(6)}){auto s=make();s->set_recombination(Vector(size,0),Vector(size,0));s->set_optical_generation(Vector(size,0));s->set_btbt_weight(Vector(size,TCAD_CONST(.7)));emit("optional-fallback-solve",valid(0,*s));}
        if(!fd){auto s=make();s->set_mobility(Vector(5,0),Vector(5,0));s->set_effective_dos({},{});s->set_bandgap({});emit("frozen-no-dos-audit",valid(2,*s));}
        if(quantum){auto s=make();s->opt_.cont_damping=1;Vector phi(5,0),n(5,TCAD_CONST(1e20)),p=n;++undamped;const bool ok=invoke(0,*s,phi,n,p);
            if(ok)++undamped_converged;
            if(observe){check(!ok && s->quantum_residual_final_<0,"parent stale quantum audit not reproduced");}
            else{check(ok && s->quantum_residual_final_>=0 && s->quantum_residual_final_<TCAD_CONST(1e-8),"undamped quantum equilibrium not audited/accepted");for(size_t i=0;i<5;++i)check(abs_q(phi[i])<TCAD_CONST(1e-18) && abs_q(n[i]-TCAD_CONST(1e20))/TCAD_CONST(1e20)<TCAD_CONST(1e-18) && abs_q(p[i]-TCAD_CONST(1e20))/TCAD_CONST(1e20)<TCAD_CONST(1e-18),"undamped quantum equilibrium fields mismatch");}
        }
    }
    std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"fixtures\":24,\"attempted\":"<<attempted<<",\"rejected\":"<<rejected<<",\"preserved\":"<<preserved<<",\"retries\":"<<retries<<",\"unsafe_parent_skipped\":"<<skipped<<",\"parent_late_rejections\":"<<late<<",\"existing_state_rejections\":"<<existing<<",\"parent_changed_state\":"<<changed<<",\"transport_attempted\":"<<transport<<",\"independent_scalar_checks\":"<<independent<<",\"max_independent_error\":\""<<exact(max_error)<<"\",\"valid_cases\":"<<refs<<",\"undamped_quantum_cases\":"<<undamped<<",\"undamped_quantum_converged\":"<<undamped_converged<<"}\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
