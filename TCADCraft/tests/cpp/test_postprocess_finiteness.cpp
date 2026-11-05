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
Vector state(const GummelSolver& s){Vector v;
    for(const auto* a:{&s.mu_n_,&s.mu_p_,&s.Nc_,&s.Nv_,&s.Eg_,&s.dg_.Nc_,&s.dg_.Nv_,&s.Qn_prev_,&s.Qp_prev_,&s.poisson_res_,&s.cont_res_,&s.poisson_.rhs_,&s.poisson_.leak_phi_,&s.poisson_.leak_E_mag_})append(v,*a);
    for(auto q:s.poisson_.A_.vals())v.push_back(q);for(auto q:s.poisson_.A_.row_offsets())v.push_back(static_cast<real_t>(q));for(auto q:s.poisson_.A_.col_indices())v.push_back(static_cast<real_t>(q));
    for(const auto& q:s.nonlinear_samples_)append(v,q);v.insert(v.end(),{s.poisson_residual_final_,s.quantum_residual_final_,s.electron_update_final_,s.hole_update_final_,static_cast<real_t>(s.poisson_.assembled_)});return v;
}
}
int main(int argc,char** argv){try{
    const bool observe=argc==2 && std::string(argv[1])=="--observe";
    size_t attempted=0,rejected=0,preserved=0,retries=0,accepted=0,skipped=0,shapes=0,shape_skipped=0,refs=0,finite_entries=0,dg_fallback=0;
    const real_t nan=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN()),inf=static_cast<real_t>(std::numeric_limits<double>::infinity()),wide=pow_q(TCAD_CONST(10.0),TCAD_CONST(400.0));
    check(isfinite_q(wide) && !std::isfinite(static_cast<double>(wide)),"wide fixture not wider than double");
    auto emit=[&](const char* kind,const Vector& a){std::cout<<"{\"case\":"<<++refs<<",\"kind\":\""<<kind<<"\",\"values\":[";for(size_t i=0;i<a.size();++i){check(isfinite_q(a[i]),"legal reference nonfinite");std::cout<<(i?",":"")<<'"'<<exact(a[i])<<'"';}std::cout<<"]}\n";};
    for(int axis=0;axis<3;++axis)for(bool graded:{false,true})for(bool quantum:{false,true}){
        Grid3D g{1,1,1,TCAD_CONST(1e-8),TCAD_CONST(1e-8),TCAD_CONST(1e-8)};Vector positions{0,TCAD_CONST(.6e-8),TCAD_CONST(1.5e-8),TCAD_CONST(2.7e-8),TCAD_CONST(4e-8)};
        if(axis==0){g.nx=5;if(graded)g.xx=positions;}if(axis==1){g.ny=5;if(graded)g.yx=positions;}if(axis==2){g.nz=5;if(graded)g.zx=positions;}if(!graded)for(size_t i=0;i<5;++i)positions[i]=static_cast<real_t>(i)*g.dx;
        GummelOptions go;go.enable_quantum=quantum;go.max_iter=4;go.cont_damping=1;go.boltzmann_lin=false;go.use_log_damping=false;go.record_nonlinear_history=true;
        GummelSolver s(g,go);const Vector carrier(5,TCAD_CONST(1e20));s.set_mobility(Vector(5,TCAD_CONST(.14)),Vector(5,TCAD_CONST(.045)));s.set_effective_dos(Vector(5,TCAD_CONST(2.8e25)),Vector(5,TCAD_CONST(3.1e25)));s.set_bandgap(Vector(5,TCAD_CONST(1.12)));s.set_recombination({},{});s.set_doping(Vector(5,0));s.set_permittivity(Vector(5,EPS0*TCAD_CONST(11.7)));s.set_poisson_dirichlet({{0,0},{4,0}});s.set_electron_bc({{0,carrier[0]},{4,carrier[4]}});s.set_hole_bc({{0,carrier[0]},{4,carrier[4]}});s.set_density_gradient_coefficients(0,0);
        Vector initial(5,0),a=carrier,b=carrier;{Quiet q;check(s.solve(initial,a,b),"history solve failed");}check(!s.poisson_res_.empty(),"solve history missing");s.set_density_gradient_coefficients(TCAD_CONST(4.885e-20),TCAD_CONST(3.432e-20));
        const Vector qn{0,TCAD_CONST(.001),TCAD_CONST(-.002),TCAD_CONST(.003),0},qp{0,TCAD_CONST(-.003),TCAD_CONST(.002),TCAD_CONST(-.001),0};s.set_transport_quantum_state(qn,qp);Vector phi(5);for(size_t i=0;i<5;++i)phi[i]=TCAD_CONST(1e8)*positions[i];
        s.opt_.btbt.enabled=s.opt_.ii.enabled=true;s.opt_.btbt.D=TCAD_CONST(2.5);
        auto mask=[&](const std::vector<char>& m){s.poisson_.set_leakage(m,0,0,1,0,0,1,1,1);};
        auto invoke=[&](int route,Vector& x,const Vector& n,const Vector& p,Vector& out,const Vector* qn_in=nullptr,const Vector* qp_in=nullptr){Quiet q;s.opt_.btbt.use_nonlocal=route==2;s.opt_.hfs.enabled=route==4;
            if(route==0){s.poisson_.set_leakage_field(x);Vector v;append(v,s.poisson_.leak_phi_);append(v,s.poisson_.leak_E_mag_);return v;}
            if(route==5){check(s.recompute_poisson(x,n,p),"valid Poisson recompute failed");return x;}
            if(route<3)s.evaluate_btbt_generation(x,out);else s.evaluate_impact_ionization(x,n,p,out,qn_in,qp_in);return out;
        };
        auto badcase=[&](int route,int field,size_t size,size_t index,real_t bad){
            Vector x=phi,n=carrier,p=carrier,u=qn,v=qp;Vector* fields[]={&x,&n,&p,&u,&v};fields[field]->resize(size,field==0?TCAD_CONST(.017):field<3?TCAD_CONST(1e20):TCAD_CONST(.004));if(field>=3){for(auto& q:u)q*=TCAD_CONST(1.1);for(auto& q:v)q*=TCAD_CONST(1.2);}
            Vector legal_x=x,out;const auto expected=bits(invoke(route,legal_x,n,p,out,field>=3?&u:nullptr,field>=3?&v:nullptr));const auto saved=bits(state(s));auto backup=s.poisson_;const real_t original=(*fields[field])[index];(*fields[field])[index]=bad;
            const auto xi=bits(x),ni=bits(n),pi=bits(p),ui=bits(u),vi=bits(v);out={2,1,-1};const auto oi=bits(out);++attempted;
            if(observe && route==5){++skipped;s.poisson_=backup;return;}
            bool caught=false;try{invoke(route,x,n,p,out,field>=3?&u:nullptr,field>=3?&v:nullptr);}catch(const std::invalid_argument& e){caught=true;const char* message=route==0||route==5&&field==0?"leakage potential must be finite":route<3?"BTBT potential must be finite":route==5?"Gummel Poisson carrier states must be finite":field>=3?"impact ionization transport Q must be finite":"impact ionization states must be finite";check(std::string(e.what())==message,"wrong nonfinite diagnostic");}
            check(bits(n)==ni && bits(p)==pi && bits(u)==ui && bits(v)==vi && bits(x)==xi,"nonfinite call changed inputs");
            if(caught){check(bits(state(s))==saved && bits(out)==oi,"nonfinite rejection changed output/cache/history");++rejected;++preserved;}
            else{check(observe,"nonfinite input accepted");++accepted;}
            (*fields[field])[index]=original;s.poisson_=backup;out.clear();const auto actual=bits(invoke(route,x,n,p,out,field>=3?&u:nullptr,field>=3?&v:nullptr));check(actual==expected && bits(state(s))==saved,"legal retry differs from reference/state");++retries;
        };
        for(bool leak:{false,true}){mask(leak?std::vector<char>{0,1,1,1,0}:std::vector<char>{});for(size_t size:{size_t(1),size_t(4),size_t(5),size_t(6)}){if(leak && size<5)continue;for(size_t i:std::set<size_t>{0,size/2,size-1})for(real_t bad:{nan,inf,-inf})badcase(0,0,size,i,bad);}}
        mask({0,1,1,1,0});for(int mode=0;mode<5;++mode){Vector x(mode<3?(mode==0?0:mode==1?1:4):(mode==3?1:4),0);if(mode>=3)x[0]=nan;const auto saved=bits(state(s)),xi=bits(x);if(observe){++shape_skipped;continue;}bool caught=false;try{s.poisson_.set_leakage_field(x);}catch(const std::invalid_argument& e){check(std::string(e.what())=="leakage potential must cover all nodes","shape must precede finite check");caught=true;}check(caught && bits(state(s))==saved && bits(x)==xi,"leakage shape guard mutated state");++shapes;}
        mask({});
        for(int route=1;route<5;++route)for(int field=0;field<(route<3?1:3);++field)for(size_t size:{size_t(5),size_t(6)})for(size_t i:std::set<size_t>{0,size/2,size-1})for(real_t bad:{nan,inf,-inf})badcase(route,field,size,i,bad);
        for(int field=0;field<3;++field)for(size_t i:{size_t(0),size_t(2),size_t(4)})for(real_t bad:{nan,inf,-inf})badcase(5,field,5,i,bad);
        if(quantum)for(int route:{3,4})for(int field:{3,4})for(size_t i:{size_t(0),size_t(2),size_t(4)})for(real_t bad:{nan,inf,-inf})badcase(route,field,5,i,bad);
        for(int route=0;route<6;++route){Vector x=phi,out;emit("positive-output",invoke(route,x,carrier,carrier,out));}
        for(int m=0;m<3;++m){std::vector<char> msk;if(m){msk.assign(m==1?5:6,0);if(m==2)msk[5]=1;}mask(msk);for(size_t size:{size_t(0),size_t(1),size_t(4),size_t(5),size_t(6)}){Vector x(size,TCAD_CONST(.02)),out;emit("inactive-leakage-finite-shape",invoke(0,x,carrier,carrier,out));}}
        mask({0,1,1,1,0});for(size_t size:{size_t(5),size_t(6)}){Vector x=phi,out;x.resize(size,TCAD_CONST(.02));emit("active-leakage-full-shape",invoke(0,x,carrier,carrier,out));}
        mask({});for(size_t size:{size_t(0),size_t(1),size_t(4),size_t(5),size_t(6)})for(real_t value:{TCAD_CONST(0.0),-TCAD_CONST(0.0),-TCAD_CONST(1.0),wide,-wide}){Vector x(size,value);s.poisson_.set_leakage_field(x);check(bits(s.poisson_.leak_phi_)==bits(x),"finite entry changed bits");Vector result;append(result,s.poisson_.leak_phi_);emit("finite-entry-only",result);++finite_entries;}
        for(int route:{3,4})for(int mode=0;mode<8;++mode){if(quantum && mode==7)continue;Vector x=phi,u=qn,v=qp,out;const Vector* un=&u;const Vector* vp=&v;
            if(mode==0){un=nullptr;vp=nullptr;}if(mode==1){u[2]=nan;vp=nullptr;}if(mode==2){un=nullptr;v[2]=inf;}if(mode==3){u.resize(4);u[2]=nan;}if(mode==4){v.resize(6);v[2]=inf;}if(mode==5){u.resize(6);v.resize(6);u[5]=nan;v[5]=-inf;}if(mode==7){u[2]=nan;v[2]=inf;}
            emit("optional-quantum-selection",invoke(route,x,carrier,carrier,out,un,vp));
        }
        const Vector oldn=s.Qn_prev_,oldp=s.Qp_prev_;s.Qn_prev_.clear();s.Qp_prev_.clear();Vector dn{TCAD_CONST(1e20),TCAD_CONST(9e20),TCAD_CONST(16e20),TCAD_CONST(9e20),TCAD_CONST(1e20)},dp{TCAD_CONST(1e20),TCAD_CONST(4e20),TCAD_CONST(9e20),TCAD_CONST(4e20),TCAD_CONST(1e20)},un,vp;s.dg_.quantum_potential(dn,dp,un,vp);for(const auto& bc:s.n_bc_)un[bc.first]=0;for(const auto& bc:s.p_bc_)vp[bc.first]=0;
        for(int route:{3,4}){Vector x=phi,out,y=phi,out2;auto result=invoke(route,x,dn,dp,out);const auto reference=invoke(route,y,dn,dp,out2,&un,&vp);check(bits(result)==bits(reference) && s.Qn_prev_.empty() && s.Qp_prev_.empty(),"DG empty-cache fallback changed/cache populated");emit("empty-cache-dg-fallback",result);++dg_fallback;}s.Qn_prev_=oldn;s.Qp_prev_=oldp;
        s.opt_.btbt.enabled=s.opt_.ii.enabled=false;for(int route:{1,3}){Vector x(1,nan),bad(1,inf),out;auto result=invoke(route,x,bad,bad,out,&bad,&bad);check(bits(result)==bits(Vector(5,0)),"disabled model validated ignored input");emit("disabled-model",result);}s.opt_.btbt.enabled=s.opt_.ii.enabled=true;
        for(size_t size:{size_t(0),size_t(1),size_t(4),size_t(6)})for(real_t bad:{nan,inf,-inf}){if(size==0 && bad==bad)continue;Vector x(size,bad),out;auto raw=s.poisson_;Vector expected(5,0);{Quiet q;raw.set_leakage_field(expected);raw.assemble(carrier,carrier);check(raw.solve(expected),"zero-guess reference failed");}const auto actual=invoke(5,x,carrier,carrier,out);check(bits(actual)==bits(expected),"ignored nonfinite initial guess did not reset");emit("ignored-initial-guess",actual);}
    }
    Grid3D singleton{1,1,1,1,1,1};PoissonSolver single(singleton);single.set_leakage({1},0,0,1,0,0,1,1,1);for(const Vector& v:{Vector{},Vector{0},Vector{-TCAD_CONST(1.0)}}){single.set_leakage_field(v);check(bits(single.leak_phi_)==bits(v) && bits(single.leak_E_mag_)==bits(Vector(1,0)),"edge-free grid compatibility changed");Vector result;append(result,single.leak_phi_);append(result,single.leak_E_mag_);emit("edge-free-grid",result);}
    std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"fixtures\":12,\"attempted\":"<<attempted<<",\"rejected\":"<<rejected<<",\"preserved\":"<<preserved<<",\"retries\":"<<retries<<",\"parent_accepted\":"<<accepted<<",\"unsafe_parent_skipped\":"<<skipped<<",\"raw_shape_rejections\":"<<shapes<<",\"raw_shape_parent_skipped\":"<<shape_skipped<<",\"finite_entry_cases\":"<<finite_entries<<",\"dg_fallback_cases\":"<<dg_fallback<<",\"valid_cases\":"<<refs<<"}\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
