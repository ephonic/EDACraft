// Exercise the actual consumers; do not include structured_field.h here.
#include <algorithm>
#include <array>
#include <cstdio>
#include <iostream>
#include <map>
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
// Coordinates are normalized by 10 nm. Separable quadratic potentials make
// exact derivatives independent of the implementation's three-point weights.
real_t potential(const std::array<real_t,3>& u,int polynomial){
    real_t v=TCAD_CONST(.125);
    for(int a=0;a<3;++a)v+=(a+1)*u[a]+(polynomial?TCAD_CONST(.17)*(a+1)*u[a]*u[a]:0);
    return v;
}
std::array<real_t,3> reference(const std::array<Vector,3>& x,const std::array<size_t,3>& at,int polynomial){
    std::array<real_t,3> e{};
    for(int a=0;a<3;++a){size_t i=at[a],n=x[a].size();if(n<=1)continue;
        real_t u=x[a][i];if(i==0)u=(x[a][0]+x[a][1])/2;if(i+1==n)u=(x[a][i-1]+x[a][i])/2;
        e[a]=-(a+1)*(1+(polynomial?TCAD_CONST(.34)*u:0))*TCAD_CONST(1e8);
    }return e;
}
}
int main(int argc,char** argv){try{
    const bool observe=argc==2 && std::string(argv[1])=="--observe";
    size_t fixtures=0,refs=0,scalars=0,failures=0,field_checks=0,rate_checks=0;real_t max_error=0;
    auto emit=[&](const char* kind,bool implicit,const Vector& actual,const Vector& expected){
        check(actual.size()==expected.size(),"reference size");
        for(size_t i=0;i<actual.size();++i){check(isfinite_q(actual[i]) && isfinite_q(expected[i]),"nonfinite result");
            const real_t error=abs_q(actual[i]-expected[i])/std::max(TCAD_CONST(1.0),abs_q(expected[i]));
            max_error=std::max(max_error,error);++scalars;if(error>TCAD_CONST(1e-25)){++failures;check(observe && !implicit,"analytic field/rate mismatch");}}
        std::cout<<"{\"case\":"<<++refs<<",\"fixture\":"<<fixtures<<",\"kind\":\""<<kind<<"\",\"implicit_uniform\":"<<(implicit?"true":"false")<<",\"values\":";values(actual);std::cout<<",\"expected\":";values(expected);std::cout<<"}\n";
    };
    for(int geometry=0;geometry<6;++geometry)for(int mesh=0;mesh<4;++mesh)for(int polynomial=0;polynomial<2;++polynomial){
        ++fixtures;Grid3D g{1,1,1,TCAD_CONST(1e-8),TCAD_CONST(1e-8),TCAD_CONST(1e-8)};
        std::array<Vector,3> x{{{0},{0},{0}}};
        for(int a=0;a<3;++a){size_t n=geometry<3?(geometry==a?5:1):geometry==3?5:geometry==4?2:1;
            x[a].resize(n);for(size_t i=0;i<n;++i)x[a][i]=static_cast<real_t>(i);
            if(mesh==2){for(size_t i=0;i<n;++i)x[a][i]=TCAD_CONST(.3)+TCAD_CONST(.4)*i+TCAD_CONST(.15)*i*i;}
            if(mesh==3){for(size_t i=0;i<n;++i)x[a][i]=TCAD_CONST(.7)+TCAD_CONST(.8)*i;}
            if(a==0)g.nx=n;if(a==1)g.ny=n;if(a==2)g.nz=n;
            if(mesh){Vector positions=x[a];for(auto& q:positions)q*=TCAD_CONST(1e-8);if(a==0)g.xx=positions;if(a==1)g.yx=positions;if(a==2)g.zx=positions;}
        }
        const size_t N=g.npts();Vector phi(N),norm(N),mobility(N,TCAD_CONST(.14)),weight(N);std::array<Vector,3> components;for(auto& v:components)v.resize(N);
        for(size_t k=0;k<g.nz;++k)for(size_t j=0;j<g.ny;++j)for(size_t i=0;i<g.nx;++i){const size_t id=g.index(i,j,k);phi[id]=potential({x[0][i],x[1][j],x[2][k]},polynomial);auto e=reference(x,{i,j,k},polynomial);for(int a=0;a<3;++a)components[a][id]=e[a];norm[id]=sqrt_q(e[0]*e[0]+e[1]*e[1]+e[2]*e[2]);weight[id]=TCAD_CONST(.6)+TCAD_CONST(.02)*(id%7);if(N>2 && id==N/2)mobility[id]=0;}
        PoissonSolver p(g);p.set_leakage(std::vector<char>(N,1),0,0,1,0,0,1,1,1);p.set_leakage_field(phi);emit("leakage-all",mesh==0,p.leak_E_mag_,norm);field_checks+=N;
        std::vector<char> mask(N);Vector masked=norm;for(size_t i=0;i<N;++i){mask[i]=i%2==0;if(!mask[i])masked[i]=0;}
        p.set_leakage(mask,0,0,1,0,0,1,1,1);p.set_leakage_field(phi);emit("leakage-mask",mesh==0,p.leak_E_mag_,masked);field_checks+=N;
        for(int mode=0;mode<4;++mode)for(int variant=0;variant<2;++variant){
            GummelOptions go;go.btbt.enabled=true;go.btbt.field_mode=mode;go.btbt.D=variant?TCAD_CONST(2.5):TCAD_CONST(2.0);go.btbt.A_kane=TCAD_CONST(2e14);go.btbt.B_kane=TCAD_CONST(2e8);
            if(variant){go.btbt.field_cap=TCAD_CONST(3e8);go.btbt.field_alpha=TCAD_CONST(.25);go.btbt.field_ref=TCAD_CONST(1e8);}
            GummelSolver s(g,go);s.set_mobility(mobility,Vector(N,TCAD_CONST(.045)));s.set_btbt_weight(weight);Vector rate,expected(N);
            s.evaluate_btbt_generation(phi,rate);
            for(size_t i=0;i<N;++i){real_t e=mode?abs_q(components[mode-1][i]):norm[i];if(variant)e=std::min(e,TCAD_CONST(3e8));if(e<TCAD_CONST(1e4) || mobility[i]==0)continue;if(variant)e*=pow_q(e/TCAD_CONST(1e8),TCAD_CONST(.25));expected[i]=go.btbt.A_kane*TCAD_CONST(1e6)*pow_q(e,go.btbt.D)*exp_q(-go.btbt.B_kane/e)*weight[i];}
            emit("local-kane",mesh==0,rate,expected);rate_checks+=N;
        }
    }
    // A cubic potential on a smoothly graded family has O(h^2) interior
    // error. Endpoints are deliberately excluded: their contract is O(h).
    real_t previous=0;
    for(size_t intervals:{size_t(8),size_t(16),size_t(32)}){
        ++fixtures;Grid3D g{intervals+1,1,1,TCAD_CONST(1e-8)/intervals,1,1};Vector phi(g.npts());
        for(size_t i=0;i<=intervals;++i){real_t t=static_cast<real_t>(i)/intervals,u=(t+t*t)/2;g.xx.push_back(u*TCAD_CONST(1e-8));phi[i]=u+u*u*u;}
        PoissonSolver p(g);p.set_leakage(std::vector<char>(g.npts(),1),0,0,1,0,0,1,1,1);p.set_leakage_field(phi);real_t error=0;
        for(size_t i=1;i<intervals;++i){real_t u=g.xx[i]*TCAD_CONST(1e8);error=std::max(error,abs_q(p.leak_E_mag_[i]-(1+3*u*u)*TCAD_CONST(1e8))/TCAD_CONST(1e8));}
        check(error>0,"cubic must have truncation error");if(previous && !observe)check(previous/error>TCAD_CONST(3.0) && previous/error<TCAD_CONST(4.5),"graded interior must converge quadratically");
        emit("cubic-convergence",false,{error}, {error});previous=error;
    }
    std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"fixtures\":"<<fixtures<<",\"valid_cases\":"<<refs<<",\"scalar_checks\":"<<scalars<<",\"field_checks\":"<<field_checks<<",\"rate_checks\":"<<rate_checks<<",\"analytic_failures\":"<<failures<<",\"max_normalized_error\":\""<<exact(max_error)<<"\"}\n";
    return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
