// Consumer-level WKB regression: same test links parent and candidate cores.
#include <algorithm>
#include <cstdio>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include "gummel_solver.h"
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
real_t action(real_t E,real_t L,real_t eg,real_t mass,size_t segments,bool closed){
    const real_t q=TCAD_CONST(1.602176634e-19),hb=TCAD_CONST(1.054571817e-34),m0=TCAD_CONST(9.1093837015e-31),gap=eg*q;
    if(closed){const real_t end=std::max(gap-q*E*L,TCAD_CONST(0.0));return TCAD_CONST(2.0)/3*sqrt_q(2*mass*m0)/(hb*q*E)*(gap*sqrt_q(gap)-end*sqrt_q(end));}
    if(segments<4)return sqrt_q(2*mass*m0*gap)/hb*L;
    if(segments%2)++segments;
    real_t sum=0,h=L/static_cast<real_t>(segments);
    for(size_t i=0;i<=segments;++i){real_t b=std::max(gap-q*E*static_cast<real_t>(i)*h,TCAD_CONST(0.0));sum+=(i==0||i==segments?1:i%2?4:2)*sqrt_q(2*mass*m0*b)/hb;}
    return sum*h/3;
}
real_t rate(real_t E,real_t L,real_t eg,real_t mass,size_t segments,real_t A,real_t D,real_t weight,bool closed){
    if(E<=1 || L<TCAD_CONST(1e-12) || weight==0)return 0;
    real_t exponent=-2*action(E,L,eg,mass,segments,closed);if(exponent<TCAD_CONST(-700.0))return 0;
    return std::min(TCAD_CONST(1e50),A*TCAD_CONST(1e6)*pow_q(E,D)*exp_q(exponent)*weight);
}
}
int main(int argc,char** argv){try{
    const bool observe=argc==2 && std::string(argv[1])=="--observe";
    size_t refs=0,checks=0,failures=0,fixtures=0;real_t max_error=0;
    auto emit=[&](const char* kind,bool uniform,size_t node,real_t actual,real_t expected,real_t closed,real_t E,real_t L,size_t segments,real_t tolerance=TCAD_CONST(5e-10)){
        check(isfinite_q(actual)&&isfinite_q(expected)&&isfinite_q(closed),"WKB result nonfinite");
        real_t error=abs_q(actual-expected)/std::max(TCAD_CONST(1.0),abs_q(expected));max_error=std::max(max_error,error);++checks;
        if(error>tolerance){++failures;check(observe&&!uniform,"WKB discrete reference mismatch");}
        std::cout<<"{\"case\":"<<++refs<<",\"fixture\":"<<fixtures<<",\"kind\":\""<<kind<<"\",\"implicit_uniform\":"<<(uniform?"true":"false")<<",\"node\":"<<node<<",\"segments\":"<<segments<<",\"values\":[\""<<exact(actual)<<"\"],\"expected\":\""<<exact(expected)<<"\",\"closed\":\""<<exact(closed)<<"\",\"field\":\""<<exact(E)<<"\",\"path\":\""<<exact(L)<<"\",\"tolerance\":\""<<exact(tolerance)<<"\"}\n";
    };
    for(int mesh=0;mesh<5;++mesh)for(bool quadratic:{false,true})for(bool transverse:{false,true})for(size_t segments:{size_t(2),size_t(5),size_t(64),size_t(512)})for(real_t fraction:{TCAD_CONST(0.0),TCAD_CONST(.08),TCAD_CONST(.5)}){
        ++fixtures;Grid3D g{9,transverse?size_t(3):size_t(1),transverse?size_t(2):size_t(1),TCAD_CONST(5e-9),TCAD_CONST(7e-9),TCAD_CONST(9e-9)};
        Vector u{0,1,2,3,4,5,6,7,8};if(mesh==2||mesh==3)u={0,TCAD_CONST(.4),TCAD_CONST(1.1),2,TCAD_CONST(3.2),TCAD_CONST(4.7),TCAD_CONST(6.5),TCAD_CONST(8.6),11};if(mesh==4)for(auto& v:u)v*=TCAD_CONST(1.6);
        if(mesh)for(auto v:u)g.xx.push_back(v*TCAD_CONST(5e-9)+(mesh==3?TCAD_CONST(1e-6):0));
        GummelOptions go;go.btbt.enabled=go.btbt.use_nonlocal=true;go.btbt.A_kane=TCAD_CONST(1e16);go.btbt.D=quadratic?TCAD_CONST(2.5):TCAD_CONST(2.0);go.btbt.nonlocal_mass=TCAD_CONST(.15);go.btbt.wkb_npts=segments;go.btbt.tunnel_path_frac=fraction;
        GummelSolver s(g,go);size_t N=g.npts();Vector phi(N),mobility(N,TCAD_CONST(.14)),weight(N),gaps(N);for(size_t k=0;k<g.nz;++k)for(size_t j=0;j<g.ny;++j)for(size_t i=0;i<g.nx;++i){size_t id=g.index(i,j,k);phi[id]=TCAD_CONST(.13)+TCAD_CONST(.07)*j+TCAD_CONST(.03)*k+TCAD_CONST(.6)*u[i]+(quadratic?TCAD_CONST(.025)*u[i]*u[i]:0);weight[id]=id%7==0?0:TCAD_CONST(.8)+TCAD_CONST(.03)*(id%4);gaps[id]=TCAD_CONST(1.0)+TCAD_CONST(.02)*(id%4);if(id==N/2)mobility[id]=0;}
        s.set_mobility(mobility,Vector(N,TCAD_CONST(.045)));s.set_btbt_weight(weight);
        if(fraction==0)gaps.resize(4);s.set_bandgap(gaps);Vector result;s.evaluate_btbt_generation(phi,result);check(result.size()==N,"WKB output shape");
        for(size_t id=0;id<N;++id){size_t i=id%g.nx;real_t at=u[i];if(i==0)at=(u[0]+u[1])/2;if(i==8)at=(u[7]+u[8])/2;
            real_t E=(TCAD_CONST(.6)+(quadratic?TCAD_CONST(.05)*at:0))/TCAD_CONST(5e-9);real_t eg=id<gaps.size()?gaps[id]:TCAD_CONST(1.12);
            real_t L=std::min(2*eg/E,std::min(u[i]-u[0],u[8]-u[i])*TCAD_CONST(5e-9));if(fraction>0)L=std::min(L,fraction*(u[8]-u[0])*TCAD_CONST(5e-9));
            real_t w=mobility[id]==0?TCAD_CONST(0.0):weight[id];real_t expected=rate(E,L,eg,go.btbt.nonlocal_mass,segments,go.btbt.A_kane,go.btbt.D,w,false),closed=rate(E,L,eg,go.btbt.nonlocal_mass,segments,go.btbt.A_kane,go.btbt.D,w,true);
            // Existing double integration can leave O(epsilon) positive
            // barrier at an exact turning-point sample; sqrt amplifies this
            // to O(sqrt(epsilon))/segments in the action. Bound it separately
            // from the smooth integrand's ordinary double roundoff.
            real_t tolerance=TCAD_CONST(5e-10);
            if(segments>=4 && L>=eg/E)tolerance+=TCAD_CONST(4e-6)/static_cast<real_t>(segments+segments%2);
            emit("mesh-path",mesh==0,id,result[id],expected,closed,E,L,segments,tolerance);
        }
    }
    for(bool truncated:{false,true}){
        real_t previous=0;size_t n=truncated?4:64;
        for(int refinement=0;refinement<3;++refinement){++fixtures;Grid3D g{5,1,1,TCAD_CONST(2e-8),1,1};g.xx={0,TCAD_CONST(2e-8),TCAD_CONST(4e-8),TCAD_CONST(6e-8),TCAD_CONST(8e-8)};Vector phi;for(auto x:g.xx)phi.push_back(TCAD_CONST(1e8)*x);
            GummelOptions go;go.btbt.enabled=go.btbt.use_nonlocal=true;go.btbt.A_kane=TCAD_CONST(1e16);go.btbt.D=2;go.btbt.nonlocal_mass=TCAD_CONST(.15);go.btbt.wkb_npts=n;go.btbt.tunnel_path_frac=truncated?TCAD_CONST(.04):TCAD_CONST(0.0);GummelSolver s(g,go);s.set_mobility(Vector(5,TCAD_CONST(.14)),Vector(5,TCAD_CONST(.045)));s.set_bandgap(Vector(5,TCAD_CONST(1.12)));Vector result;s.evaluate_btbt_generation(phi,result);
            real_t L=truncated?TCAD_CONST(3.2e-9):TCAD_CONST(2.24e-8),E=TCAD_CONST(1e8),closed=rate(E,L,TCAD_CONST(1.12),go.btbt.nonlocal_mass,n,go.btbt.A_kane,2,1,true),expected=rate(E,L,TCAD_CONST(1.12),go.btbt.nonlocal_mass,n,go.btbt.A_kane,2,1,false),error=abs_q(result[2]/closed-1);
            if(previous&&!observe)check(previous/error>(truncated?TCAD_CONST(12.0):TCAD_CONST(5.0))&&previous/error<(truncated?TCAD_CONST(20.0):TCAD_CONST(12.0)),"WKB closed-form convergence mismatch");previous=error;
            emit(truncated?"smooth-convergence":"crossing-convergence",false,2,result[2],expected,closed,E,L,n,TCAD_CONST(5e-10)+(truncated?TCAD_CONST(0.0):TCAD_CONST(4e-6)/static_cast<real_t>(n)));n*=truncated?2:4;
        }
    }
    for(size_t nx:{size_t(1),size_t(2)}){++fixtures;Grid3D g{nx,1,1,TCAD_CONST(1e-8),1,1};g.xx={TCAD_CONST(1e-6)};if(nx==2)g.xx.push_back(TCAD_CONST(1.01e-6));GummelOptions go;go.btbt.enabled=go.btbt.use_nonlocal=true;GummelSolver s(g,go);s.set_mobility(Vector(nx,TCAD_CONST(.14)),Vector(nx,TCAD_CONST(.045)));Vector phi(nx);if(nx==2)phi[1]=1;Vector result;s.evaluate_btbt_generation(phi,result);for(size_t i=0;i<nx;++i){check(result[i]==0,"zero available path must return zero");emit("no-path",false,i,result[i],0,0,0,0,64);}}
    std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"fixtures\":"<<fixtures<<",\"valid_cases\":"<<refs<<",\"scalar_checks\":"<<checks<<",\"reference_failures\":"<<failures<<",\"max_normalized_error\":\""<<exact(max_error)<<"\"}\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
