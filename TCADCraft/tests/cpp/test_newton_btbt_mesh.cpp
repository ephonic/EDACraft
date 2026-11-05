// Test solver consumers and the assembled equations, not internal field helpers.
#include <algorithm>
#include <array>
#include <cstdio>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include "math_types.h"
#include "poisson_solver.h"
#include "sparse_matrix.h"
#include "linear_solver.h"
#include "statistics.h"
#define private public
#include "newton_solver.h"
#include "gummel_solver.h"
#undef private
using namespace tcad;
namespace {
void check(bool v,const char* m){if(!v)throw std::runtime_error(m);}
std::string exact(real_t x){char b[128];
#ifdef TCAD_USE_FLOAT128
    quadmath_snprintf(b,sizeof(b),"%Qa",x);
#else
    std::snprintf(b,sizeof(b),"%La",x);
#endif
    return b;
}
void values(const Vector& v){std::cout<<'[';for(size_t i=0;i<v.size();++i)std::cout<<(i?",":"")<<'"'<<exact(v[i])<<'"';std::cout<<']';}
struct Fixture {Grid3D g{1,1,1,TCAD_CONST(1e-8),TCAD_CONST(1e-8),TCAD_CONST(1e-8)};Vector phi,mu_n,mu_p;std::array<Vector,3> e;};
Fixture fixture(int geometry,int mesh,int polynomial,real_t amplitude=TCAD_CONST(1.0)){
    Fixture f;auto& g=f.g;std::array<Vector,3> x;
    for(int a=0;a<3;++a){size_t n=geometry<3?(geometry==a?5:1):geometry==3?3:geometry==4?2:1;
        x[a].resize(n);for(size_t i=0;i<n;++i){real_t u=static_cast<real_t>(i);if(mesh==2)u=TCAD_CONST(.3)+TCAD_CONST(.4)*i+TCAD_CONST(.15)*i*i;if(mesh==3)u=TCAD_CONST(.7)+TCAD_CONST(.8)*i;x[a][i]=u;}
        if(a==0)g.nx=n;if(a==1)g.ny=n;if(a==2)g.nz=n;
        if(mesh){Vector p=x[a];for(auto& q:p)q*=TCAD_CONST(1e-8);if(a==0)g.xx=p;if(a==1)g.yx=p;if(a==2)g.zx=p;}
    }
    size_t N=g.npts();f.phi.resize(N);for(auto& e:f.e)e.resize(N);f.mu_n.assign(N,TCAD_CONST(.14));f.mu_p.assign(N,TCAD_CONST(.045));
    if(N>2){f.mu_n[N/2]=0;f.mu_p[N/3]=0;}
    for(size_t k=0;k<g.nz;++k)for(size_t j=0;j<g.ny;++j)for(size_t i=0;i<g.nx;++i){size_t id=g.index(i,j,k);const size_t at[3]={i,j,k};real_t v=TCAD_CONST(.125);
        for(int a=0;a<3;++a){real_t u=x[a][at[a]];v+=(a+1)*(u+(polynomial?TCAD_CONST(.17)*u*u:0));
            if(x[a].size()>1){if(at[a]==0)u=(x[a][0]+x[a][1])/2;if(at[a]+1==x[a].size())u=(x[a][at[a]-1]+x[a][at[a]])/2;f.e[a][id]=-amplitude*(a+1)*(1+(polynomial?TCAD_CONST(.34)*u:0))*TCAD_CONST(1e8);}}
        f.phi[id]=amplitude*v;
    }return f;
}
NewtonOptions options(int mode,int variant,bool logs=false){NewtonOptions o;o.enable_btbt=true;o.use_log_space=logs;o.btbt_field_mode=mode;o.btbt_A=TCAD_CONST(2e14);o.btbt_B=TCAD_CONST(2e8);o.btbt_D=variant?TCAD_CONST(2.5):TCAD_CONST(2.0);o.btbt_continuity_scale=TCAD_CONST(.37);
    if(variant){o.btbt_field_alpha=variant==3?-TCAD_CONST(1.0):TCAD_CONST(.25);o.btbt_field_ref=TCAD_CONST(1e8);}if(variant==2)o.btbt_field_cap=TCAD_CONST(2e8);return o;}
Vector rates(const Fixture& f,const NewtonOptions& o){Vector r(f.phi.size());for(size_t i=0;i<r.size();++i){real_t e=o.btbt_field_mode?abs_q(f.e[o.btbt_field_mode-1][i]):sqrt_q(f.e[0][i]*f.e[0][i]+f.e[1][i]*f.e[1][i]+f.e[2][i]*f.e[2][i]);if(o.btbt_field_cap>0)e=std::min(e,o.btbt_field_cap);if(e<TCAD_CONST(1e4)||f.mu_n[i]<EPSILON)continue;if(o.btbt_field_alpha!=0&&o.btbt_field_ref>0)e*=pow_q(e/o.btbt_field_ref,o.btbt_field_alpha);r[i]=o.btbt_A*TCAD_CONST(1e6)*pow_q(e,o.btbt_D)*exp_q(-o.btbt_B/e);}return r;}
Vector dense(NewtonSolver& s,const Vector& x){SparseMatrix j;s.assemble_jacobian(x,j);size_t M=x.size();Vector d(M*M);for(size_t r=0;r<M;++r)for(size_t k=j.row_offsets()[r];k<j.row_offsets()[r+1];++k)d[M*r+j.col_indices()[k]]+=j.vals()[k];return d;}
Vector delta(NewtonSolver& on,NewtonSolver& off,const Vector& x){Vector a,b;on.assemble_residual(x,a);off.assemble_residual(x,b);for(size_t i=0;i<a.size();++i)a[i]-=b[i];return a;}
}
int main(int argc,char** argv){try{
    bool observe=argc==2&&std::string(argv[1])=="--observe";size_t fixtures=0,refs=0,scalars=0,failures=0,rate_checks=0,residual_checks=0,jacobian_checks=0;real_t max_error=0;
    auto emit=[&](const char* kind,bool implicit,const Vector& a,const Vector& b,const Vector& scales,real_t tol){check(a.size()==b.size()&&a.size()==scales.size(),"reference size");
        for(size_t i=0;i<a.size();++i){check(isfinite_q(a[i])&&isfinite_q(b[i]),"nonfinite check");real_t err=abs_q(a[i]-b[i])/std::max(TCAD_CONST(1.0),std::max(abs_q(b[i]),abs_q(scales[i])));max_error=std::max(max_error,err);++scalars;if(err>tol){++failures;check(observe,"Newton BTBT analytic/FD mismatch");}}
        std::cout<<"{\"case\":"<<++refs<<",\"fixture\":"<<fixtures<<",\"kind\":\""<<kind<<"\",\"implicit_uniform\":"<<(implicit?"true":"false")<<",\"values\":";values(a);std::cout<<",\"expected\":";values(b);std::cout<<",\"scales\":";values(scales);std::cout<<",\"tolerance\":\""<<exact(tol)<<"\"}\n";};
    for(int geometry=0;geometry<6;++geometry)for(int mesh=0;mesh<4;++mesh)for(int polynomial=0;polynomial<2;++polynomial)for(int mode=0;mode<4;++mode)for(int variant=0;variant<5;++variant){
        ++fixtures;auto f=fixture(geometry,mesh,polynomial,variant==4?TCAD_CONST(1e-5):TCAD_CONST(1.0));auto o=options(mode,variant);NewtonSolver n(f.g,o);n.set_mobility(f.mu_n,f.mu_p);Vector r(f.phi.size());for(size_t i=0;i<r.size();++i)r[i]=n.compute_btbt_at(f.phi.data(),i);
        auto expected=rates(f,o);emit("rate",mesh==0,r,expected,expected,TCAD_CONST(1e-25));rate_checks+=r.size();
        GummelOptions go;go.btbt.enabled=true;go.btbt.A_kane=o.btbt_A;go.btbt.B_kane=o.btbt_B;go.btbt.D=o.btbt_D;go.btbt.field_mode=mode;go.btbt.field_cap=o.btbt_field_cap;go.btbt.field_alpha=o.btbt_field_alpha;go.btbt.field_ref=o.btbt_field_ref;GummelSolver gs(f.g,go);gs.set_mobility(f.mu_n,f.mu_p);Vector gr;gs.evaluate_btbt_generation(f.phi,gr);
        emit("gummel-agreement",mesh==0,r,gr,gr,TCAD_CONST(1e-25));
    }
    for(int geometry=0;geometry<4;++geometry)for(int mesh=0;mesh<4;++mesh)for(int mode=0;mode<4;++mode)for(int variant=0;variant<5;++variant)for(bool logs:{false,true}){
        ++fixtures;auto f=fixture(geometry,mesh,1,variant==4?TCAD_CONST(1e-5):TCAD_CONST(1.0));auto o=options(mode,variant,logs);NewtonSolver on(f.g,o);size_t N=f.phi.size(),M=3*N;on.set_mobility(f.mu_n,f.mu_p);on.set_effective_dos(Vector(N,TCAD_CONST(1e19)),Vector(N,TCAD_CONST(1e19)));on.set_bandgap(Vector(N,TCAD_CONST(6.0)));on.set_electron_bc({{0,TCAD_CONST(2e19)}});on.set_hole_bc({{N-1,TCAD_CONST(1e19)}});
        NewtonSolver off=on;off.opt_.enable_btbt=false;Vector x(M);for(size_t i=0;i<N;++i){x[i]=f.phi[i];x[N+i]=logs?log_q(TCAD_CONST(2e19)):TCAD_CONST(2e19);x[2*N+i]=logs?log_q(TCAD_CONST(1e19)):TCAD_CONST(1e19);}
        auto r=rates(f,o),d=delta(on,off,x);Vector expected(M),scale(M);for(size_t i=0;i<N;++i){real_t v=o.btbt_continuity_scale*r[i]*f.g.dx_cell(i%f.g.nx);scale[N+i]=scale[2*N+i]=v;if(i!=0&&f.mu_n[i]>=EPSILON)expected[N+i]=-v;if(i!=N-1&&f.mu_p[i]>=EPSILON)expected[2*N+i]=-v;}
        emit("residual-source",mesh==0,d,expected,scale,TCAD_CONST(1e-24));residual_checks+=M;
        auto ja=dense(on,x),jb=dense(off,x);Vector actual,fd,scales;const real_t h=TCAD_CONST(1e-9);
        for(size_t column=0;column<N;++column){Vector xp=x,xm=x;xp[column]+=h;xm[column]-=h;auto dp=delta(on,off,xp),dm=delta(on,off,xm);
            for(size_t row=N;row<M;++row){actual.push_back(ja[M*row+column]-jb[M*row+column]);fd.push_back((dp[row]-dm[row])/(2*h));scales.push_back(scale[row]);}}
        emit("source-jacobian-fd",mesh==0,actual,fd,scales,TCAD_CONST(1e-14));jacobian_checks+=actual.size();
    }
    std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"fixtures\":"<<fixtures<<",\"valid_cases\":"<<refs<<",\"scalar_checks\":"<<scalars<<",\"rate_checks\":"<<rate_checks<<",\"residual_checks\":"<<residual_checks<<",\"jacobian_checks\":"<<jacobian_checks<<",\"reference_failures\":"<<failures<<",\"max_normalized_error\":\""<<exact(max_error)<<"\"}\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
