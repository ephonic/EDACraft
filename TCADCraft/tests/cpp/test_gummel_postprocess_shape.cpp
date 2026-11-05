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
struct Quiet {std::ostringstream out;std::streambuf* old;std::streambuf* err;Quiet():old(std::cout.rdbuf(out.rdbuf())),err(std::cerr.rdbuf(out.rdbuf())){}~Quiet(){std::cerr.rdbuf(err);std::cout.rdbuf(old);}};
Vector state(const GummelSolver& s){Vector v;
    for(const auto* a:{&s.mu_n_,&s.mu_p_,&s.Nc_,&s.Nv_,&s.Eg_,&s.dg_.Nc_,&s.dg_.Nv_,&s.Qn_prev_,&s.Qp_prev_,&s.poisson_res_,&s.cont_res_,&s.poisson_.rhs_,&s.poisson_.leak_phi_,&s.poisson_.leak_E_mag_})append(v,*a);
    for(auto q:s.poisson_.A_.vals())v.push_back(q);for(auto q:s.poisson_.A_.row_offsets())v.push_back(static_cast<real_t>(q));for(auto q:s.poisson_.A_.col_indices())v.push_back(static_cast<real_t>(q));
    for(const auto& q:s.nonlinear_samples_)append(v,q);v.insert(v.end(),{s.poisson_residual_final_,s.quantum_residual_final_,s.electron_update_final_,s.hole_update_final_,static_cast<real_t>(s.poisson_.assembled_)});return v;
}
}
int main(int argc,char** argv){try{
    const bool observe=argc==2 && std::string(argv[1])=="--observe";
    size_t attempted=0,rejected=0,preserved=0,retries=0,skipped=0,changed=0,refs=0,independent=0,fallback=0,fallback_skipped=0;
    real_t max_error=0;
    auto compare=[&](real_t a,real_t b){real_t e=abs_q(a-b)/std::max(TCAD_CONST(1.0),abs_q(b));max_error=std::max(max_error,e);check(e<TCAD_CONST(1e-25),"independent reference mismatch");++independent;};
    auto emit=[&](const char* kind,const Vector& a){std::cout<<"{\"case\":"<<++refs<<",\"kind\":\""<<kind<<"\",\"values\":[";for(size_t i=0;i<a.size();++i){check(isfinite_q(a[i]),"valid reference nonfinite");std::cout<<(i?",":"")<<'"'<<exact(a[i])<<'"';}std::cout<<"]}\n";};
    for(int axis=0;axis<3;++axis)for(bool graded:{false,true})for(bool quantum:{false,true}){
        Grid3D g{1,1,1,TCAD_CONST(1e-8),TCAD_CONST(1e-8),TCAD_CONST(1e-8)};Vector positions{0,TCAD_CONST(.6e-8),TCAD_CONST(1.5e-8),TCAD_CONST(2.7e-8),TCAD_CONST(4e-8)};
        if(axis==0){g.nx=5;if(graded)g.xx=positions;}if(axis==1){g.ny=5;if(graded)g.yx=positions;}if(axis==2){g.nz=5;if(graded)g.zx=positions;}
        if(!graded)for(size_t i=0;i<5;++i)positions[i]=static_cast<real_t>(i)*g.dx;
        GummelOptions go;go.enable_quantum=quantum;go.max_iter=4;go.cont_damping=1;go.boltzmann_lin=false;go.use_log_damping=false;go.record_nonlinear_history=true;
        GummelSolver s(g,go);const Vector carrier(5,TCAD_CONST(1e20));
        auto materials=[&](size_t size=5){s.set_mobility(Vector(size,TCAD_CONST(.14)),Vector(size,TCAD_CONST(.045)));s.set_effective_dos(Vector(size,TCAD_CONST(2.8e25)),Vector(size,TCAD_CONST(3.1e25)));s.set_bandgap(Vector(size,TCAD_CONST(1.12)));};materials();s.set_recombination({},{});s.set_doping(Vector(5,0));s.set_permittivity(Vector(5,EPS0*TCAD_CONST(11.7)));s.set_poisson_dirichlet({{0,0},{4,0}});s.set_electron_bc({{0,carrier[0]},{4,carrier[4]}});s.set_hole_bc({{0,carrier[0]},{4,carrier[4]}});s.set_density_gradient_coefficients(0,0);
        Vector initial(5,0),n=carrier,p=carrier;{Quiet q;check(s.solve(initial,n,p),"history equilibrium failed");}check(!s.poisson_res_.empty(),"history missing");
        const Vector qn{0,TCAD_CONST(.001),TCAD_CONST(-.002),TCAD_CONST(.003),0},qp{0,TCAD_CONST(-.003),TCAD_CONST(.002),TCAD_CONST(-.001),0};
        auto seed=[&](){s.set_transport_quantum_state(qn,qp);};seed();
        Vector phi(5);for(size_t i=0;i<5;++i)phi[i]=TCAD_CONST(1e8)*positions[i];
        s.opt_.btbt.enabled=true;s.opt_.btbt.D=TCAD_CONST(2.5);s.opt_.ii.enabled=true;
        auto generation=[&](int route,const Vector& x,const Vector& a,const Vector& b,Vector& out,const Vector* an=nullptr,const Vector* ap=nullptr){
            s.opt_.btbt.use_nonlocal=route==1;s.opt_.hfs.enabled=route==3;
            if(route<2)s.evaluate_btbt_generation(x,out);else s.evaluate_impact_ionization(x,a,b,out,an,ap);
        };
        auto positive=[&](int route){Vector out;generation(route,phi,carrier,carrier,out);return out;};
        // Malformed read arrays: no undefined parent reads are executed.
        for(int route=0;route<4;++route){
            s.opt_.hfs.enabled=route==3;const auto model_control=positive(route);
            const int fields=route<2?2:route==2?5:7;
            for(int field=0;field<fields;++field)for(size_t size:{size_t(0),size_t(1),size_t(4)}){
                Vector x=phi,a=carrier,b=carrier;materials();seed();
                if(field==0)x.resize(size);
                if(route<2){if(field==1)s.set_mobility(Vector(size,TCAD_CONST(.14)),Vector(5,TCAD_CONST(.045)));}
                else{
                    if(field==1)a.resize(size);if(field==2)b.resize(size);
                    if(field==3)s.set_mobility(Vector(size,TCAD_CONST(.14)),Vector(5,TCAD_CONST(.045)));
                    if(field==4)s.set_mobility(Vector(5,TCAD_CONST(.14)),Vector(size,TCAD_CONST(.045)));
                    if(field==5)s.set_effective_dos(Vector(size,TCAD_CONST(2.8e25)),Vector(5,TCAD_CONST(3.1e25)));
                    if(field==6)s.set_effective_dos(Vector(5,TCAD_CONST(2.8e25)),Vector(size,TCAD_CONST(3.1e25)));
                }
                const auto saved=bits(state(s)),xi=bits(x),ai=bits(a),bi=bits(b);Vector out{2,1,-1};const auto oi=bits(out);++attempted;
                if(observe){++skipped;continue;}
                bool caught=false;try{generation(route,x,a,b,out);}catch(const std::invalid_argument& e){caught=true;const char* expected=route<2?(field==0?"BTBT potential must cover all nodes":"BTBT electron mobility must cover all nodes"):field<3?"impact ionization requires full states":field<5?"impact ionization mobility must cover all nodes":"Gummel effective DOS must cover all nodes";check(std::string(e.what())==expected,"wrong postprocess shape diagnostic");}
                check(caught && bits(state(s))==saved && bits(x)==xi && bits(a)==ai && bits(b)==bi && bits(out)==oi,"postprocess rejection partially updated output/state");++rejected;++preserved;
                materials();seed();check(bits(positive(route))==bits(model_control),"generation valid retry changed");++retries;
            }
            materials();seed();
        }
        // Poisson checks carriers before touching leakage caches, with leakage on/off.
        for(bool leak:{false,true})for(int field=0;field<2;++field)for(size_t size:{size_t(0),size_t(1),size_t(4),size_t(6)}){
            s.poisson_.set_leakage(leak?std::vector<char>{0,1,1,1,0}:std::vector<char>{},0,0,1,0,0,1,1,1);s.poisson_.set_leakage_field(Vector(5,0));auto backup=s.poisson_;
            Vector x=phi,a=carrier,b=carrier;(field==0?a:b).resize(size,TCAD_CONST(1e20));const auto saved=bits(state(s)),xi=bits(x),ai=bits(a),bi=bits(b);++attempted;
            bool caught=false;try{Quiet q;s.recompute_poisson(x,a,b);}catch(const std::invalid_argument& e){check(std::string(e.what())=="Carrier density size mismatch","Poisson diagnostic changed");caught=true;}
            check(caught && bits(x)==xi && bits(a)==ai && bits(b)==bi,"Poisson invalid carrier accepted or input changed");
            if(observe){check(bits(state(s))!=saved,"parent cache change not reproduced");++changed;}
            else{check(bits(state(s))==saved,"Poisson rejection changed cache/assembly");++rejected;++preserved;}
            s.poisson_=backup;x=phi;{Quiet q;check(s.recompute_poisson(x,carrier,carrier),"Poisson retry failed");}for(auto v:x)check(isfinite_q(v),"Poisson retry nonfinite");++retries;s.poisson_=backup;
        }
        s.poisson_.set_leakage({},0,0,1,0,0,1,1,1);
        for(int route=0;route<4;++route)for(size_t size:{size_t(5),size_t(6)}){
            materials(size);seed();Vector x=phi,a=carrier,b=carrier;x.resize(size,0);a.resize(size,carrier[0]);b.resize(size,carrier[0]);Vector out;generation(route,x,a,b,out);emit("full-or-oversized-generation",out);
            if(size==5 && route==0){for(size_t i=0;i<5;++i){const real_t E=TCAD_CONST(1e8); // Independent slope of the prescribed linear potential.
                compare(out[i],s.opt_.btbt.A_kane*TCAD_CONST(1e6)*pow_q(E,s.opt_.btbt.D)*exp_q(-s.opt_.btbt.B_kane/E));}}
            if(size==5 && route==2){Vector expected(5,0);for(size_t i=0;i<4;++i){const real_t d=positions[i+1]-positions[i],delta=phi[i+1]-phi[i],E=abs_q(delta/d);const real_t mn=TCAD_CONST(.14)/(1+TCAD_CONST(1e-30)/(2*TCAD_CONST(.14))),mp=TCAD_CONST(.045)/(1+TCAD_CONST(1e-30)/(2*TCAD_CONST(.045)));real_t a_n=s.opt_.ii.A_n*exp_q(-s.opt_.ii.B_n/E),a_p=s.opt_.ii.A_p*exp_q(-s.opt_.ii.B_p/E);real_t flux=(a_n*mn*carrier[i]*abs_q(delta+(quantum?qn[i+1]-qn[i]:TCAD_CONST(0.0)))+a_p*mp*carrier[i]*abs_q(delta-(quantum?qp[i+1]-qp[i]:TCAD_CONST(0.0))))/d/2;expected[i]+=flux;expected[i+1]+=flux;}for(size_t i=0;i<5;++i)compare(out[i],expected[i]);}
        }
        materials();seed();
        for(int route=0;route<2;++route)for(size_t gap:{size_t(0),size_t(1),size_t(4),size_t(6)})for(size_t weight:{size_t(0),size_t(1),size_t(4),size_t(5),size_t(6)}){s.set_bandgap(Vector(gap,TCAD_CONST(1.12)));s.set_btbt_weight(Vector(weight,TCAD_CONST(.7)));emit("btbt-optional-fallback",positive(route));}materials();s.set_btbt_weight({});seed();
        for(int route:{2,3})for(int mode=0;mode<6;++mode){Vector a=qn,b=qp;if(mode==3){a.resize(4);b.resize(4);}if(mode==4){a.resize(6);b.resize(6);}if(mode==5){for(auto& v:a)v*=2;for(auto& v:b)v*=2;}Vector out;generation(route,phi,carrier,carrier,out,mode==0||mode==2?nullptr:&a,mode==0||mode==1?nullptr:&b);emit("optional-quantum-fallback",out);}
        s.set_effective_dos({},{});
        for(int mode=0;mode<3;++mode){Vector out,x=phi;s.opt_.hfs.enabled=true;if(mode==0)s.set_mobility(Vector(5,0),Vector(5,0));else materials();s.set_effective_dos({},{});if(mode==1)x.assign(5,0);const auto ii=s.opt_.ii;if(mode==2){s.opt_.ii.A_n=0;s.opt_.ii.A_p=0;}generation(3,x,carrier,carrier,out);check(bits(out)==bits(Vector(5,0)),"inactive HFS empty-DOS path changed");emit("inactive-hfs-no-dos",out);s.opt_.ii=ii;}
        materials();seed();s.opt_.btbt.enabled=false;s.opt_.ii.enabled=false;s.set_mobility({},{});Vector out;generation(0,{},{},{},out);check(bits(out)==bits(Vector(5,0)),"disabled BTBT changed");emit("disabled-model",out);generation(3,{},{},{},out);check(bits(out)==bits(Vector(5,0)),"disabled II changed");emit("disabled-model",out);materials();seed();s.opt_.btbt.enabled=true;s.opt_.ii.enabled=true;
        // Full initial guesses preserve parent output; malformed guesses use zero
        // consistently for the linear solve, leakage field and trap occupancy.
        s.poisson_.set_dirichlet({{0,0},{4,TCAD_CONST(.1)}});
        for(bool leak:{false,true})for(bool traps:{false,true}){
            s.poisson_.set_leakage(leak?std::vector<char>{0,1,1,1,0}:std::vector<char>{},0,0,1,0,0,1,1,1);s.poisson_.set_interface_traps(traps?std::vector<char>{0,1,1,1,0}:std::vector<char>{},TCAD_CONST(1e4),0);
            auto original=s.poisson_;Vector x=phi;{Quiet q;check(s.recompute_poisson(x,carrier,carrier),"valid Poisson failed");}emit("poisson-full-initial-guess",x);if(!leak && !traps)for(size_t i=0;i<5;++i)compare(x[i],TCAD_CONST(.1)*positions[i]/positions[4]);s.poisson_=original;
            for(size_t size:{size_t(0),size_t(1),size_t(4),size_t(6)}){
                if(observe && (leak || traps)){++fallback_skipped;continue;}
                Vector a(size,TCAD_CONST(.017));auto raw=original;Vector expected(5,0);{Quiet q;raw.set_leakage_field(expected);raw.assemble(carrier,carrier);check(raw.solve(expected),"raw Poisson reference failed");check(s.recompute_poisson(a,carrier,carrier),"initial-guess fallback failed");}
                check(bits(a)==bits(expected),"initial-guess fallback differs from explicit zero");if(!observe){check(bits(s.poisson_.leak_phi_)==bits(Vector(5,0)),"fallback cache not normalized");++fallback;}
                if(!leak && !traps)emit("poisson-size-fallback-compatible",a);s.poisson_=original;
            }
        }
    }
    std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"fixtures\":12,\"attempted\":"<<attempted<<",\"rejected\":"<<rejected<<",\"preserved\":"<<preserved<<",\"retries\":"<<retries<<",\"unsafe_parent_skipped\":"<<skipped<<",\"parent_changed_cache\":"<<changed<<",\"initial_guess_fallback_checks\":"<<fallback<<",\"parent_fallback_skipped\":"<<fallback_skipped<<",\"independent_scalar_checks\":"<<independent<<",\"max_independent_error\":\""<<exact(max_error)<<"\",\"valid_cases\":"<<refs<<"}\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
