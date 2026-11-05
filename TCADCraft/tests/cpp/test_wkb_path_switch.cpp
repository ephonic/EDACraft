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
 size_t cases=0,failed=0;real_t smooth_max=0,right_max=0;
 for(int mesh=0;mesh<3;++mesh)for(bool fraction:{false,true})for(int cap_units:{1,7})
 for(int sign:{-1,1})for(real_t mass:{TCAD_CONST(.00001),TCAD_CONST(.0001)})
 for(real_t weight:{-TCAD_CONST(.3),TCAD_CONST(0.0),TCAD_CONST(.8)})
 for(size_t segments:{2,3,4,6,7,32,128})for(int side:{-2,-1,0,1,2}){
  const real_t dx=TCAD_CONST(0x1p-24),L=cap_units*dx;
  Grid3D g{17,1,1,dx,1,1};
  if(mesh)for(size_t i=0;i<17;++i)g.xx.push_back(dx*i+(mesh==2?TCAD_CONST(0x1p-10):0));
  const size_t node=fraction?8:cap_units;
  const real_t request=1/dx,delta=side==0?TCAD_CONST(0.0):(abs(side)==2?TCAD_CONST(0x1p-60):TCAD_CONST(0x1p-18));
  const real_t gap=TCAD_CONST(.5)*cap_units*(1+(side<0?-delta:delta));
  Vector phi;for(size_t i=0;i<17;++i)phi.push_back(sign*request*dx*i);
  LinearizedWKBParameters p{TCAD_CONST(1e14),TCAD_CONST(2.3),mass,fraction?(real_t)cap_units/16:TCAD_CONST(0.0),segments};
  const auto actual=evaluate_linearized_wkb(g,phi,node,gap,p,weight,true);
  const real_t E=abs_q((real_t)linearized_wkb_x_field(g,phi,node));
  auto rate=[&](real_t f){Vector v=phi;for(auto& a:v)a*=f;return evaluate_linearized_wkb(g,v,node,gap,p,weight).generation;};
  real_t left[2]={0,0},right[2]={0,0},central[2]={0,0},error=0,growth=0;
  const bool fd=abs(side)!=2;
  if(fd)for(int step=0;step<2;++step){
   const real_t h=side==0?(step==0?TCAD_CONST(0x1p-16):TCAD_CONST(0x1p-18)):(step==0?TCAD_CONST(0x1p-26):TCAD_CONST(0x1p-28));
   const real_t lo=rate(1-h),hi=rate(1+h),inc=E*h;
   left[step]=(actual.generation-lo)/inc;right[step]=(hi-actual.generation)/inc;central[step]=(hi-lo)/(2*inc);
   const real_t estimate=side==0?right[step]:central[step];
   error=std::max(error,abs_q(estimate-actual.d_generation_d_field)/std::max(TCAD_CONST(1.0),std::max(abs_q(actual.d_generation_d_field),abs_q(actual.generation/E))));
  }
  if(side==0&&weight!=0&&segments>=4)growth=(left[1]-right[1])/(left[0]-right[0]);
  bool passed=isfinite_q(actual.generation)&&isfinite_q(actual.d_generation_d_field)&&(!fd||error<(side==0?TCAD_CONST(1e-3):TCAD_CONST(2e-5)));
  if(side==0&&weight!=0&&segments>=4)passed=passed&&growth>TCAD_CONST(1.9)&&growth<TCAD_CONST(2.1);
  if(weight==0)passed=passed&&actual.generation==0&&actual.d_generation_d_field==0;
  if(!passed)++failed;++cases;if(side==0)right_max=std::max(right_max,error);else smooth_max=std::max(smooth_max,error);
  std::cout<<"{\"case\":"<<cases<<",\"mesh\":"<<mesh<<",\"fraction_window\":"<<(fraction?"true":"false")<<",\"cap_units\":"<<cap_units<<",\"sign\":"<<sign<<",\"side\":"<<side<<",\"segments\":"<<segments<<",\"field\":\""<<exact(E)<<"\",\"length\":\""<<exact(L)<<"\",\"gap\":\""<<exact(gap)<<"\",\"mass\":\""<<exact(mass)<<"\",\"weight\":\""<<exact(weight)<<"\",\"generation\":\""<<exact(actual.generation)<<"\",\"derivative\":\""<<exact(actual.d_generation_d_field)<<"\",\"fd_checked\":"<<(fd?"true":"false")<<",\"fd_left_coarse\":\""<<exact(left[0])<<"\",\"fd_left_fine\":\""<<exact(left[1])<<"\",\"fd_right_coarse\":\""<<exact(right[0])<<"\",\"fd_right_fine\":\""<<exact(right[1])<<"\",\"fd_central_coarse\":\""<<exact(central[0])<<"\",\"fd_central_fine\":\""<<exact(central[1])<<"\",\"fd_error\":\""<<exact(error)<<"\",\"left_excess_growth\":\""<<exact(growth)<<"\",\"passed\":"<<(passed?"true":"false")<<"}\n";
 }
 std::cout<<"{\"summary\":true,\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"cases\":"<<cases<<",\"failed\":"<<failed<<",\"smooth_fd_max\":\""<<exact(smooth_max)<<"\",\"right_corner_fd_max\":\""<<exact(right_max)<<"\"}\n";
 return !observe&&failed?1:0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
