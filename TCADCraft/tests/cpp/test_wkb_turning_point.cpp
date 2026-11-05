#include "linearized_wkb.h"
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
 size_t cases=0,failed=0;real_t max_rate=0,max_derivative=0,max_fd=0;
 for(int mesh=0;mesh<3;++mesh)for(int sign:{-1,1})
 for(real_t field:{TCAD_CONST(2e7),TCAD_CONST(7.3e7),TCAD_CONST(1.73e8),TCAD_CONST(9e8)})
 for(real_t gap:{TCAD_CONST(.8),TCAD_CONST(1.12)})
 for(real_t mass:{TCAD_CONST(.01),TCAD_CONST(.15)})
 for(size_t segments:{size_t(2),size_t(5),size_t(6),size_t(32),size_t(128)})
 for(real_t weight:{-TCAD_CONST(.3),TCAD_CONST(0.0),TCAD_CONST(.8)}){
  Grid3D g{9,1,1,TCAD_CONST(1e-6),1,1};
  if(mesh)for(size_t i=0;i<9;++i)g.xx.push_back(TCAD_CONST(1e-6)*i+(mesh==2?TCAD_CONST(1e-3):0));
  Vector phi;for(size_t i=0;i<9;++i)phi.push_back(sign*field*(mesh?g.xx[i]-g.xx[0]:TCAD_CONST(1e-6)*i));
  LinearizedWKBParameters p{TCAD_CONST(1e10),TCAD_CONST(2.3),mass,0,segments};
  const auto actual=evaluate_linearized_wkb(g,phi,4,gap,p,weight,true);
  const real_t E=abs_q((real_t)linearized_wkb_x_field(g,phi,4));
  const size_t n=segments>=4?segments+segments%2:segments;
  const real_t q=TCAD_CONST(1.602176634e-19),m0=TCAD_CONST(9.1093837015e-31),hb=TCAD_CONST(1.054571817e-34);
  const real_t L=2*gap/E;real_t total=0;
  if(n>=4){for(size_t k=0;k<n/2;++k){const real_t b=gap*q*(real_t)(n-2*k)/(real_t)n;total+=(k==0?1:k%2?4:2)*sqrt_q(2*mass*m0*b)/hb;}total*=L/(3*(real_t)n);}
  else total=sqrt_q(2*mass*m0*gap*q)/hb*L;
  const real_t exponent=-2*total;
  const real_t ref=weight==0||exponent<-700?TCAD_CONST(0.0):p.A*TCAD_CONST(1e6)*pow_q(E,p.D)*exp_q(exponent)*weight;
  const real_t deriv=ref*(p.D+2*total)/E;
  const real_t rate_error=ref==0?abs_q(actual.generation):abs_q(actual.generation/ref-1);
  const real_t derivative_error=deriv==0?abs_q(actual.d_generation_d_field):abs_q(actual.d_generation_d_field/deriv-1);
  real_t fd_error=0;real_t fd_values[2];
  for(int step=0;step<2;++step){const real_t rel=step==0?TCAD_CONST(1e-6):TCAD_CONST(5e-7);Vector plus=phi,minus=phi;
   for(size_t i=0;i<9;++i){plus[i]*=1+rel;minus[i]*=1-rel;}
   const real_t ep=abs_q((real_t)linearized_wkb_x_field(g,plus,4)),em=abs_q((real_t)linearized_wkb_x_field(g,minus,4));
   const auto gp=evaluate_linearized_wkb(g,plus,4,gap,p,weight).generation,gm=evaluate_linearized_wkb(g,minus,4,gap,p,weight).generation;
   fd_values[step]=(gp-gm)/(ep-em);
   fd_error=std::max(fd_error,abs_q(fd_values[step]-actual.d_generation_d_field)/std::max(TCAD_CONST(1.0),std::max(abs_q(actual.d_generation_d_field),abs_q(actual.generation/E))));
  }
  const bool passed=rate_error<TCAD_CONST(1e-11)&&derivative_error<TCAD_CONST(1e-11)&&fd_error<TCAD_CONST(3e-7);
  if(!passed)++failed;++cases;max_rate=std::max(max_rate,rate_error);max_derivative=std::max(max_derivative,derivative_error);max_fd=std::max(max_fd,fd_error);
  std::cout<<"{\"case\":"<<cases<<",\"mesh\":"<<mesh<<",\"sign\":"<<sign<<",\"segments\":"<<segments<<",\"field\":\""<<exact(E)<<"\",\"gap\":\""<<exact(gap)<<"\",\"mass\":\""<<exact(mass)<<"\",\"weight\":\""<<exact(weight)<<"\",\"generation\":\""<<exact(actual.generation)<<"\",\"derivative\":\""<<exact(actual.d_generation_d_field)<<"\",\"reference\":\""<<exact(ref)<<"\",\"reference_derivative\":\""<<exact(deriv)<<"\",\"fd_coarse\":\""<<exact(fd_values[0])<<"\",\"fd_fine\":\""<<exact(fd_values[1])<<"\",\"passed\":"<<(passed?"true":"false")<<"}\n";
 }
 std::cout<<"{\"summary\":true,\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"cases\":"<<cases<<",\"failed\":"<<failed<<",\"rate_error\":\""<<exact(max_rate)<<"\",\"derivative_error\":\""<<exact(max_derivative)<<"\",\"fd_error\":\""<<exact(max_fd)<<"\"}\n";
 return !observe&&failed?1:0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
