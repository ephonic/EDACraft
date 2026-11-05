#include <linearized_wkb.h>
#include <cstdio>
#include <iostream>
#include <string>
using namespace tcad;
std::string exact(real_t x){char b[160];
#ifdef TCAD_USE_FLOAT128
 quadmath_snprintf(b,sizeof(b),"%Qa",x);
#else
 std::snprintf(b,sizeof(b),"%La",x);
#endif
 return b;}
int main(int argc,char** argv){try{
 const bool observe=argc>1&&std::string(argv[1])=="--observe";
 const real_t cap=(real_t)1e50,E=TCAD_CONST(0x1p24),dx=TCAD_CONST(0x1p-24);
 size_t cases=0,failed=0,helper_cases=0,kernel_cases=0;
 for(real_t D:{TCAD_CONST(-2.0),TCAD_CONST(0.0),TCAD_CONST(2.0)})
 for(real_t magnitude:{TCAD_CONST(.125),TCAD_CONST(.5),TCAD_CONST(1.0),TCAD_CONST(2.0)})
 for(int a_sign:{-1,1})for(int w_sign:{-1,1})for(int side:{-2,-1,0,1,2}){
  const real_t delta=side==0?TCAD_CONST(0.0):(abs(side)==2?TCAD_CONST(0x1p-60):TCAD_CONST(0x1p-18));
  const real_t A=a_sign*cap/(TCAD_CONST(1e6)*pow_q(E,D)*magnitude)*(1+(side<0?-delta:delta)),weight=w_sign*magnitude;
  const real_t raw=A*TCAD_CONST(1e6)*pow_q(E,D)*weight,expected=std::min(raw,cap);
  const auto actual=wkb_generation_product(A,(double)E,D,0,weight);
  const real_t error=abs_q(actual-expected)/std::max(TCAD_CONST(1.0),abs_q(expected));
  const real_t gap_error=raw>0&&side!=0?abs_q(actual-expected)/std::max(cap*TCAD_CONST(1e-30),abs_q(expected-cap)):0;
  bool passed=isfinite_q(actual)&&error<(raw>0?TCAD_CONST(1e-28):TCAD_CONST(1e-10));
  if(raw>0&&side<0)passed=passed&&actual<cap&&gap_error<TCAD_CONST(1e-4);
  if(raw>=cap)passed=passed&&actual==cap;
  if(!passed)++failed;++cases;++helper_cases;
  std::cout<<"{\"case\":"<<cases<<",\"kind\":\"product\",\"side\":"<<side<<",\"field\":\""<<exact(E)<<"\",\"D\":\""<<exact(D)<<"\",\"A\":\""<<exact(A)<<"\",\"weight\":\""<<exact(weight)<<"\",\"generation\":\""<<exact(actual)<<"\",\"expected\":\""<<exact(expected)<<"\",\"cap_gap_error\":\""<<exact(gap_error)<<"\",\"passed\":"<<(passed?"true":"false")<<"}\n";
 }
 for(int mesh=0;mesh<3;++mesh)for(bool fraction:{false,true})for(int sign:{-1,1})
 for(real_t D:{TCAD_CONST(-2.0),TCAD_CONST(0.0),TCAD_CONST(2.0)})
 for(real_t mass:{TCAD_CONST(.001),TCAD_CONST(.01)})for(int a_sign:{-1,1})for(int w_sign:{-1,1})
 for(size_t segments:{2,4,7,32,128})for(int side:{-2,-1,1,2}){
  Grid3D g{9,1,1,dx,1,1};if(mesh)for(size_t i=0;i<9;++i)g.xx.push_back(dx*i+(mesh==2?TCAD_CONST(0x1p-10):0));
  const size_t node=fraction?4:1;Vector phi;for(size_t i=0;i<9;++i)phi.push_back(sign*E*dx*i);
  const real_t gap=TCAD_CONST(1.25),weight=w_sign*TCAD_CONST(.5);
  // Calibrate around the existing double quadrature's actual exponent.
  // The independent audit separately reconstructs this exponent and the
  // physical high-precision Simpson action; they need not be identical.
  const size_t n=segments>=4?segments+segments%2:segments;
  const double mt=(double)mass*9.1093837015e-31,Eg=(double)gap*1.602176634e-19,L=(double)dx;
  double action=0;
  if(n<4)action=std::sqrt(2.0*mt*Eg)/1.054571817e-34*L;
  else{
   const double h=L/(double)n;
   for(size_t k=0;k<=n;++k){const double x=(double)k*h,b=std::max(Eg-1.602176634e-19*(double)E*x,0.0);if(b<=0)continue;
    const double w=(k==0||k==n)?1.0:(k%2?4.0:2.0);action+=w*std::sqrt(2.0*mt*b)/1.054571817e-34;}
   action*=h/3.0;
  }
  const double exponent=-2*action;
  const real_t delta=abs(side)==2?TCAD_CONST(0x1p-60):TCAD_CONST(0x1p-18);
  const real_t A=a_sign*cap/(TCAD_CONST(1e6)*pow_q(E,D)*exp_q((real_t)exponent)*abs_q(weight))*(1+(side<0?-delta:delta));
  LinearizedWKBParameters p{A,D,mass,fraction?TCAD_CONST(.125):TCAD_CONST(0.0),segments};
  const auto actual=evaluate_linearized_wkb(g,phi,node,gap,p,weight,true);
  const real_t raw=A*TCAD_CONST(1e6)*pow_q(E,D)*exp_q((real_t)exponent)*weight;
  const bool capped=raw>=cap;const real_t expected=capped?cap:raw;
  const real_t rate_error=abs_q(actual.generation-expected)/abs_q(expected);
  real_t fd[2]={0,0},fd_error=0;const bool fd_checked=abs(side)==1;
  if(fd_checked)for(int step=0;step<2;++step){
   const real_t h=step==0?TCAD_CONST(0x1p-28):TCAD_CONST(0x1p-30);Vector lo=phi,hi=phi;for(auto& v:lo)v*=1-h;for(auto& v:hi)v*=1+h;
   fd[step]=(evaluate_linearized_wkb(g,hi,node,gap,p,weight).generation-evaluate_linearized_wkb(g,lo,node,gap,p,weight).generation)/(2*E*h);
   fd_error=std::max(fd_error,abs_q(fd[step]-actual.d_generation_d_field)/std::max(TCAD_CONST(1.0),std::max(abs_q(actual.d_generation_d_field),abs_q(actual.generation/E))));
  }
  bool passed=isfinite_q(actual.generation)&&isfinite_q(actual.d_generation_d_field)&&rate_error<(raw>0?TCAD_CONST(1e-28):TCAD_CONST(1e-10))&&fd_error<TCAD_CONST(2e-5);
  if(capped)passed=passed&&actual.generation==cap&&actual.d_generation_d_field==0;
  else if(raw>0)passed=passed&&actual.generation<cap&&
      ((n<4&&D==0)?actual.d_generation_d_field==0:actual.d_generation_d_field!=0);
  if(!passed)++failed;++cases;++kernel_cases;
  std::cout<<"{\"case\":"<<cases<<",\"kind\":\"kernel\",\"mesh\":"<<mesh<<",\"fraction_window\":"<<(fraction?"true":"false")<<",\"sign\":"<<sign<<",\"side\":"<<side<<",\"segments\":"<<segments<<",\"field\":\""<<exact(E)<<"\",\"length\":\""<<exact(dx)<<"\",\"gap\":\""<<exact(gap)<<"\",\"mass\":\""<<exact(mass)<<"\",\"A\":\""<<exact(A)<<"\",\"D\":\""<<exact(D)<<"\",\"weight\":\""<<exact(weight)<<"\",\"calibration_exponent\":\""<<exact((real_t)exponent)<<"\",\"generation\":\""<<exact(actual.generation)<<"\",\"derivative\":\""<<exact(actual.d_generation_d_field)<<"\",\"expected\":\""<<exact(expected)<<"\",\"expected_capped\":"<<(capped?"true":"false")<<",\"fd_checked\":"<<(fd_checked?"true":"false")<<",\"fd_coarse\":\""<<exact(fd[0])<<"\",\"fd_fine\":\""<<exact(fd[1])<<"\",\"fd_error\":\""<<exact(fd_error)<<"\",\"passed\":"<<(passed?"true":"false")<<"}\n";
 }
 std::cout<<"{\"summary\":true,\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"cases\":"<<cases<<",\"helper_cases\":"<<helper_cases<<",\"kernel_cases\":"<<kernel_cases<<",\"failed\":"<<failed<<"}\n";
 return !observe&&failed?1:0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
