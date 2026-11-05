// Compare actual parent inline setters with prevalidated candidate setters.
#include <algorithm>
#include <cstdio>
#include <iostream>
#include <limits>
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
Vector state(const GummelSolver& s,const DensityGradient& d){Vector v;
    for(const auto* a:{&d.Nc_,&d.Nv_,&d.L_conf_,&s.dg_.Nc_,&s.dg_.Nv_,&s.Qn_prev_,&s.Qp_prev_,&s.poisson_res_,&s.cont_res_,&s.poisson_.rhs_,&s.poisson_.leak_phi_,&s.poisson_.leak_E_mag_})append(v,*a);
    for(auto q:d.semi_)v.push_back(q);for(auto q:d.N_conf_)v.push_back(static_cast<real_t>(q));
    for(auto q:s.poisson_.A_.vals())v.push_back(q);for(auto q:s.poisson_.A_.row_offsets())v.push_back(static_cast<real_t>(q));for(auto q:s.poisson_.A_.col_indices())v.push_back(static_cast<real_t>(q));
    for(const auto& q:s.nonlinear_samples_)append(v,q);
    v.insert(v.end(),{d.bn_,d.bp_,d.VT_,s.poisson_residual_final_,s.quantum_residual_final_,s.electron_update_final_,s.hole_update_final_,static_cast<real_t>(s.poisson_.assembled_)});return v;
}
}
int main(int argc,char** argv){try{
    const bool observe=argc==2 && std::string(argv[1])=="--observe";
    size_t fixtures=0,attempted=0,rejected=0,preserved=0,retries=0,accepted=0,shape_cases=0,finite_cases=0,refs=0,observable=0;
    const real_t nan=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN()),inf=static_cast<real_t>(std::numeric_limits<double>::infinity()),wide=pow_q(TCAD_CONST(10.0),TCAD_CONST(400.0));
    check(isfinite_q(wide) && !std::isfinite(static_cast<double>(wide)),"wide finite fixture is not wider than double");
    auto emit=[&](const char* kind,const Vector& a){std::cout<<"{\"case\":"<<++refs<<",\"kind\":\""<<kind<<"\",\"values\":[";for(size_t i=0;i<a.size();++i)std::cout<<(i?",":"")<<'"'<<exact(a[i])<<'"';std::cout<<"]}\n";};
    for(int axis=0;axis<3;++axis)for(bool graded:{false,true})for(bool quantum:{false,true}){
        Grid3D g{1,1,1,TCAD_CONST(1e-8),TCAD_CONST(1e-8),TCAD_CONST(1e-8)};Vector pos{0,TCAD_CONST(.6e-8),TCAD_CONST(1.5e-8),TCAD_CONST(2.7e-8),TCAD_CONST(4e-8)};
        if(axis==0){g.nx=5;if(graded)g.xx=pos;}if(axis==1){g.ny=5;if(graded)g.yx=pos;}if(axis==2){g.nz=5;if(graded)g.zx=pos;}
        GummelOptions go;go.enable_quantum=quantum;go.max_iter=4;go.cont_damping=1;go.boltzmann_lin=false;go.use_log_damping=false;go.record_nonlinear_history=true;
        GummelSolver s(g,go);s.set_mobility(Vector(5,TCAD_CONST(.14)),Vector(5,TCAD_CONST(.045)));s.set_effective_dos(Vector(5,TCAD_CONST(2.8e25)),Vector(5,TCAD_CONST(3.1e25)));s.set_bandgap(Vector(5,TCAD_CONST(1.12)));s.set_recombination({},{});s.set_doping(Vector(5,0));s.set_permittivity(Vector(5,EPS0*TCAD_CONST(11.7)));s.set_poisson_dirichlet({{0,0},{4,0}});s.set_electron_bc({{0,TCAD_CONST(1e20)},{4,TCAD_CONST(1e20)}});s.set_hole_bc({{0,TCAD_CONST(1e20)},{4,TCAD_CONST(1e20)}});s.set_density_gradient_coefficients(0,0);
        Vector phi(5,0),carrier(5,TCAD_CONST(1e20)),n=carrier,p=carrier;{Quiet q;check(s.solve(phi,n,p),"equilibrium fixture failed");}check(!s.poisson_res_.empty(),"solve history empty");
        DensityGradient d(g);d.set_semiconductor_mask({0,1,1,1,0});
        const Vector Nc(5,TCAD_CONST(2.8e25)),Nv(5,TCAD_CONST(3.1e25)),qn{0,TCAD_CONST(.001),TCAD_CONST(-.002),TCAD_CONST(.003),0},qp{0,TCAD_CONST(-.003),TCAD_CONST(.002),TCAD_CONST(-.001),0};
        auto restore=[&](){d.set_effective_dos(Nc,Nv);s.set_transport_quantum_state(qn,qp);};restore();
        Vector dn{TCAD_CONST(1e20),TCAD_CONST(9e20),TCAD_CONST(16e20),TCAD_CONST(9e20),TCAD_CONST(1e20)},dp{TCAD_CONST(1e20),TCAD_CONST(4e20),TCAD_CONST(9e20),TCAD_CONST(4e20),TCAD_CONST(1e20)};
        auto output=[&](bool full){Quiet quiet;Vector a,b,c,e,v;d.quantum_potential(dn,dp,a,b);d.correct(dn,dp,c,e);for(const auto* z:{&a,&b,&c,&e})append(v,*z);if(full){d.quantum_potential_potential_form(dn,dp,qn,qp,a,b);append(v,a);append(v,b);}auto r=s.compute_continuity_residuals(phi,carrier,carrier);v.push_back(r.first);v.push_back(r.second);for(auto x:v)check(isfinite_q(x),"valid output nonfinite");return v;};
        const auto control=bits(state(s,d)),quick=bits(output(false)),full=bits(output(true));emit("positive-output",output(true));
        // A valid first array is deliberately different when the second is invalid.
        // Parent observation only stores and restores invalid arrays; never solves them.
        for(int route=0;route<2;++route)for(size_t size:{size_t(1),size_t(4),size_t(5),size_t(6)}){
            if(route==1 && size!=5)continue;
            for(int field=0;field<2;++field)for(size_t index:std::set<size_t>{0,size/2,size-1})for(real_t bad:{nan,inf,-inf}){
                Vector a(route==0?size:5,route==0?TCAD_CONST(3.5e25):TCAD_CONST(.004)),b(route==0?size:5,route==0?TCAD_CONST(4.2e25):-TCAD_CONST(.005));(field==0?a:b)[index]=bad;
                const auto ai=bits(a),bi=bits(b);++attempted;bool caught=false;try{if(route==0)d.set_effective_dos(a,b);else s.set_transport_quantum_state(a,b);}catch(const std::invalid_argument& e){caught=true;check(std::string(e.what())==(route==0?"DG effective DOS must be finite":"transport quantum state must be finite"),"wrong finite diagnostic");++rejected;}
                check(bits(a)==ai && bits(b)==bi,"setter changed inputs");
                if(caught){check(bits(state(s,d))==control && bits(output(false))==quick,"rejection changed state/equations");++preserved;}
                else{check(observe,"nonfinite input accepted");++accepted;check(bits(state(s,d))!=control,"parent mutation not observed");const auto& stored=route==0?(field==0?d.Nc_:d.Nv_):(field==0?s.Qn_prev_:s.Qp_prev_);check(!isfinite_q(stored[index]),"parent nonfinite not stored");}
                restore();check(bits(state(s,d))==control && bits(output(false))==quick,"valid retry did not restore state");++retries;
            }
        }
        // Shape validation retains precedence over finite validation for either array.
        for(int field=0;field<2;++field)for(size_t size:{size_t(0),size_t(1),size_t(4),size_t(6)})for(bool bad:{false,true}){
            Vector a(5,TCAD_CONST(.004)),b(5,-TCAD_CONST(.005));(field==0?a:b).resize(size,0);if(bad)(field==0?b:a)[2]=nan;bool caught=false;
            try{s.set_transport_quantum_state(a,b);}catch(const std::invalid_argument& e){check(std::string(e.what())=="transport quantum state size mismatch","shape precedence changed");caught=true;}
            check(caught && bits(state(s,d))==control && bits(output(false))==quick,"shape failure changed state");++shape_cases;
        }
        // Preserve arbitrary DOS lengths, both signs, signed zero and float128 range.
        for(int route=0;route<2;++route)for(size_t size:{size_t(0),size_t(1),size_t(4),size_t(5),size_t(6)}){
            if(route==1 && size!=5)continue;
            for(real_t value:{TCAD_CONST(0.0),-TCAD_CONST(0.0),-TCAD_CONST(1.0),wide,-wide}){
                Vector a(size,value),b(size,-value);if(route==0){d.set_effective_dos(a,b);check(bits(d.Nc_)==bits(a) && bits(d.Nv_)==bits(b),"finite DOS changed");}else{s.set_transport_quantum_state(a,b);check(bits(s.transport_quantum_n())==bits(a) && bits(s.transport_quantum_p())==bits(b),"finite Q changed");}
                emit("finite-entry-only",state(s,d));++finite_cases;restore();check(bits(state(s,d))==control,"finite restore failed");
            }
        }
        for(size_t size:{size_t(0),size_t(1),size_t(4),size_t(5),size_t(6)}){d.set_effective_dos(Vector(size,TCAD_CONST(3.5e25)),Vector(size,TCAD_CONST(4.2e25)));emit("positive-dos-shape-output",output(true));restore();}
        s.set_transport_quantum_state(Vector(5,0),Vector(5,0));const auto no_q=bits(output(false));restore();if(quantum){check(no_q!=quick,"nonuniform transport Q has no observable effect");++observable;}else check(no_q==quick,"disabled quantum affected transport");
        check(bits(output(true))==full && bits(state(s,d))==control,"final restore failed");++fixtures;
    }
    std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"fixtures\":"<<fixtures<<",\"attempted\":"<<attempted<<",\"rejected\":"<<rejected<<",\"preserved\":"<<preserved<<",\"retries\":"<<retries<<",\"parent_accepted\":"<<accepted<<",\"shape_precedence_cases\":"<<shape_cases<<",\"finite_entry_cases\":"<<finite_cases<<",\"observable_quantum_cases\":"<<observable<<",\"valid_cases\":"<<refs<<"}\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
