// Raw Gummel entry validation; parent/candidate executable uses the same test.
#include <algorithm>
#include <cstdio>
#include <iostream>
#include <limits>
#include <map>
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
std::vector<std::string> bits(const Vector& v){std::vector<std::string> r;for(auto q:v)r.push_back(exact(q));return r;}
void append(Vector& a,const Vector& b){a.push_back(static_cast<real_t>(b.size()));a.insert(a.end(),b.begin(),b.end());}
Vector state(const GummelSolver& s){Vector v;
    for(const auto* a:{&s.mu_n_,&s.mu_p_,&s.tau_n_,&s.tau_p_,&s.G_opt_,&s.btbt_weight_,&s.Nc_,&s.Nv_,&s.Eg_,&s.dg_.Nc_,&s.dg_.Nv_,&s.Qn_prev_,&s.Qp_prev_,&s.poisson_res_,&s.cont_res_})append(v,*a);
    for(const auto* m:{&s.n_bc_,&s.p_bc_}){v.push_back(static_cast<real_t>(m->size()));for(auto q:*m){v.push_back(static_cast<real_t>(q.first));v.push_back(q.second);}}
    for(const auto& q:s.nonlinear_samples_)append(v,q);return v;
}
Vector output(GummelSolver& s){Vector phi{0,TCAD_CONST(.001),TCAD_CONST(.003),TCAD_CONST(.004),TCAD_CONST(.006)},n(5,TCAD_CONST(1.4e20)),p(5,TCAD_CONST(1.6e20)),v;
    check(s.solve_electron_density(phi,n,p,nullptr),"electron block did not solve");
    check(s.solve_hole_density(phi,n,p,nullptr),"hole block did not solve");
    append(v,n);append(v,p);Vector b;for(size_t i=0;i<5;++i)phi[i]=static_cast<real_t>(i);
    s.compute_btbt(phi,b);append(v,b);Vector qn,qp;s.dg_.quantum_potential(n,p,qn,qp);append(v,qn);append(v,qp);
    for(auto x:v)check(isfinite_q(x),"positive reference nonfinite");return v;
}
}
int main(int argc,char** argv){try{
    const bool observe=argc==2 && std::string(argv[1])=="--observe";
    const real_t nan=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN()),inf=static_cast<real_t>(std::numeric_limits<double>::infinity()),wide=pow_q(TCAD_CONST(10.0),TCAD_CONST(400.0));
#ifdef TCAD_USE_FLOAT128
    check(isfinite_q(wide) && !std::isfinite(static_cast<double>(wide)),"wide fixture must exceed double");
#endif
    size_t attempted=0,rejected=0,accepted=0,preserved=0,retries=0,refs=0,finite=0,physical=0,bc_attempted=0,independent=0;
    real_t max_error=0;
    auto emit=[&](const char* kind,const Vector& v){std::cout<<"{\"case\":"<<++refs<<",\"kind\":\""<<kind<<"\",\"values\":[";for(size_t i=0;i<v.size();++i)std::cout<<(i?",":"")<<'"'<<exact(v[i])<<'"';std::cout<<"]}\n";};
    for(int axis=0;axis<3;++axis)for(bool graded:{false,true}){
        Grid3D g{1,1,1,TCAD_CONST(1e-8),TCAD_CONST(1e-8),TCAD_CONST(1e-8)};Vector x=graded?Vector{0,TCAD_CONST(.6e-8),TCAD_CONST(1.5e-8),TCAD_CONST(2.7e-8),TCAD_CONST(4e-8)}:Vector{0,TCAD_CONST(1e-8),TCAD_CONST(2e-8),TCAD_CONST(3e-8),TCAD_CONST(4e-8)};
        if(axis==0){g.nx=5;if(graded)g.xx=x;}if(axis==1){g.ny=5;if(graded)g.yx=x;}if(axis==2){g.nz=5;if(graded)g.zx=x;}
        GummelOptions go;go.btbt.enabled=true;GummelSolver s(g,go);
        std::vector<Vector> base{Vector(5,TCAD_CONST(.14)),Vector(5,TCAD_CONST(.045)),Vector(5,TCAD_CONST(1e-7)),Vector(5,TCAD_CONST(2e-7)),Vector(5,TCAD_CONST(3e29)),Vector(5,TCAD_CONST(.7)),Vector(5,TCAD_CONST(2.78e25)),Vector(5,TCAD_CONST(3.143e25)),Vector(5,TCAD_CONST(1.12))};
        auto set=[&](int field,const Vector& value,bool change_peer=false){
            auto a=base;if(change_peer){if(field==1)a[0].assign(5,TCAD_CONST(.21));if(field==3)a[2].assign(5,TCAD_CONST(3e-7));if(field==7)a[6].assign(5,TCAD_CONST(3e25));}a[field]=value;
            if(field<2)s.set_mobility(a[0],a[1]);else if(field<4)s.set_recombination(a[2],a[3]);else if(field==4)s.set_optical_generation(a[4]);else if(field==5)s.set_btbt_weight(a[5]);else if(field<8)s.set_effective_dos(a[6],a[7]);else s.set_bandgap(a[8]);
        };
        auto restore=[&](){for(int f=0;f<9;++f)set(f,base[f]);};restore();
        s.set_electron_bc({{0,TCAD_CONST(1e20)},{4,TCAD_CONST(2e20)}});s.set_hole_bc({{0,TCAD_CONST(1.2e20)},{4,TCAD_CONST(2.4e20)}});
        // Explicit synthetic history/cache sentinels, not a converged device.
        s.Qn_prev_.assign(5,TCAD_CONST(.002));s.Qp_prev_.assign(5,-TCAD_CONST(.003));s.poisson_res_={2,1};s.cont_res_={3};s.nonlinear_samples_={{4,2}};
        const auto control=bits(state(s)),equations=bits(output(s));emit("positive-output",output(s));++physical;
        const char* messages[]={"mobility must be finite","mobility must be finite","recombination lifetime must be finite","recombination lifetime must be finite","optical generation must be finite","BTBT weight must be finite","effective DOS must be finite","effective DOS must be finite","bandgap must be finite"};
        for(int field=0;field<9;++field)for(size_t size:{size_t(1),size_t(4),size_t(5),size_t(6)})for(size_t pos:std::set<size_t>{0,size-1})for(real_t bad:{nan,inf,-inf}){
            Vector a(size,base[field][0]*TCAD_CONST(1.1));a[pos]=bad;++attempted;bool caught=false;
            try{set(field,a,true);}catch(const std::invalid_argument& e){check(std::string(e.what())==messages[field],"wrong material diagnostic");caught=true;++rejected;}
            if(caught){check(bits(state(s))==control,"rejected material changed state/peer/DG/history");check(bits(output(s))==equations,"rejected material changed transport");++preserved;}
            else{check(observe,"nonfinite material accepted");++accepted;}
            restore();check(bits(state(s))==control && bits(output(s))==equations,"material retry mismatch");++retries;
        }
        // Keep finite shape/sign entry compatibility; restore before assembly.
        for(int field=0;field<9;++field)for(size_t size:{size_t(0),size_t(1),size_t(4),size_t(5),size_t(6)})for(real_t value:{TCAD_CONST(0.0),-TCAD_CONST(0.0),-TCAD_CONST(1.0),wide}){
            set(field,Vector(size,value));emit("finite-entry-only",state(s));++finite;restore();check(bits(state(s))==control,"finite shape restore mismatch");
        }
        for(int field=0;field<9;++field){Vector a=base[field];for(auto& q:a)q*=TCAD_CONST(1.1);set(field,a);emit("positive-output",output(s));++physical;restore();check(bits(output(s))==equations,"positive material retry mismatch");}
        // Optional short-array fallbacks must remain executable and unchanged.
        for(size_t size:{size_t(0),size_t(1),size_t(4),size_t(6)}){s.set_recombination(Vector(size,TCAD_CONST(1e-7)),Vector(size,TCAD_CONST(2e-7)));s.set_optical_generation(Vector(size,TCAD_CONST(3e29)));s.set_btbt_weight(Vector(size,TCAD_CONST(.7)));emit("optional-fallback-output",output(s));++physical;restore();}
        for(bool hole:{false,true}){
            auto& m=hole?s.p_bc_:s.n_bc_;const auto saved=m;
            auto setter=[&](const std::map<size_t,real_t>& b){if(hole)s.set_hole_bc(b);else s.set_electron_bc(b);};
            std::vector<std::map<size_t,real_t>> bads;
            for(size_t idx:{size_t(5),size_t(6),std::numeric_limits<size_t>::max()})bads.push_back({{1,TCAD_CONST(1.3e20)},{idx,TCAD_CONST(2e20)}});
            for(size_t idx:{size_t(0),size_t(2),size_t(4)})for(real_t bad:{nan,inf,-inf})bads.push_back({{1,TCAD_CONST(1.3e20)},{idx,bad}});
            // Index validation has precedence over value validation.
            bads.push_back({{1,nan},{5,inf}});
            for(const auto& b:bads){++attempted;++bc_attempted;bool caught=false;try{setter(b);}catch(const std::invalid_argument& e){const bool index=b.rbegin()->first>=5;check(std::string(e.what())==(index?"carrier boundary index out of range":"carrier boundary values must be finite"),"wrong boundary diagnostic");caught=true;++rejected;}
                if(caught){check(bits(state(s))==control,"boundary rejected after partial insertion");check(bits(output(s))==equations,"boundary rejection changed transport");++preserved;}else{check(observe,"invalid boundary accepted");++accepted;}
                // Restore directly only in observer mode; candidate uses public valid retry.
                if(observe)m=saved;setter({{0,TCAD_CONST(9e20)},{4,TCAD_CONST(9e20)}});
                check(bits(state(s))==control && bits(output(s))==equations,"boundary retry/first-wins mismatch");++retries;
            }
            for(real_t value:{TCAD_CONST(0.0),-TCAD_CONST(0.0),-TCAD_CONST(1.0),wide}){setter({{2,value},{0,TCAD_CONST(9e20)}});check(exact(m.at(2))==exact(value) && exact(m.at(0))==exact(saved.at(0)),"boundary insertion/sign/first-wins mismatch");emit("finite-bc-entry-only",state(s));++finite;m=saved;}
            setter({});check(bits(state(s))==control,"empty boundary must not clear existing contacts");
        }
        // Independent zero-field diffusion reference, including optical source.
        GummelOptions refopt;GummelSolver ref(g,refopt);ref.set_effective_dos(base[6],base[7]);ref.set_bandgap(base[8]);ref.set_recombination(Vector(5,0),Vector(5,0));ref.set_optical_generation(Vector(5,TCAD_CONST(3e30)));
        ref.set_electron_bc({{0,TCAD_CONST(1e20)},{4,TCAD_CONST(2e20)}});ref.set_hole_bc({{0,TCAD_CONST(1.2e20)},{4,TCAD_CONST(2.4e20)}});
        Vector phi(5,0),n(5,TCAD_CONST(1.5e20)),p(5,TCAD_CONST(1.8e20));check(ref.solve_electron_density(phi,n,p,nullptr) && ref.solve_hole_density(phi,n,p,nullptr),"independent diffusion solve failed");
        for(int carrier=0;carrier<2;++carrier)for(size_t i=0;i<5;++i){const real_t left=carrier?TCAD_CONST(1.2e20):TCAD_CONST(1e20),right=2*left,D=base[carrier][0]*refopt.VT;const real_t expected=left+(right-left)*x[i]/x[4]+TCAD_CONST(3e30)*x[i]*(x[4]-x[i])/(2*D);const real_t error=abs_q((carrier?p[i]:n[i])-expected)/TCAD_CONST(1e20);max_error=std::max(max_error,error);check(error<TCAD_CONST(1e-18),"independent diffusion/source reference mismatch");++independent;}
        Vector v=n;append(v,p);emit("independent-diffusion-source",v);
    }
    std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"fixtures\":6,\"attempted\":"<<attempted<<",\"rejected\":"<<rejected<<",\"accepted\":"<<accepted<<",\"preserved\":"<<preserved<<",\"retries\":"<<retries<<",\"boundary_attempted\":"<<bc_attempted<<",\"finite_entry_cases\":"<<finite<<",\"positive_output_cases\":"<<physical<<",\"independent_scalar_checks\":"<<independent<<",\"max_independent_normalized_error\":\""<<exact(max_error)<<"\",\"valid_cases\":"<<refs<<"}\n";
    return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
