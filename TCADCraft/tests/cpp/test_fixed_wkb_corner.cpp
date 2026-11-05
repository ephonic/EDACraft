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
 struct Sample{size_t segments,turn;real_t gap,drop;};
 const Sample samples[]={{4,3,TCAD_CONST(.75),1},{6,4,1,TCAD_CONST(1.5)},{7,5,TCAD_CONST(.625),1},{32,24,TCAD_CONST(1.5),2},{128,96,TCAD_CONST(.75),1}};
 size_t cases=0,failed=0;real_t fd_max=0,corner_max=0;
 for(int mesh=0;mesh<3;++mesh)for(bool fraction:{false,true})for(int sign:{-1,1})
 for(real_t mass:{TCAD_CONST(.001),TCAD_CONST(.01)})for(real_t weight:{-TCAD_CONST(.3),TCAD_CONST(0.0),TCAD_CONST(.8)})
 for(const auto t:samples)for(int side:{-1,0,1}){
  const real_t dx=TCAD_CONST(0x1p-24);Grid3D g{9,1,1,dx,1,1};
  if(mesh)for(size_t i=0;i<9;++i)g.xx.push_back(dx*i+(mesh==2?TCAD_CONST(0x1p-10):0));
  const size_t node=fraction?4:1;const real_t request=t.drop/dx*(1+side*TCAD_CONST(0x1p-18));
  Vector phi;for(size_t i=0;i<9;++i)phi.push_back(sign*request*dx*i);
  LinearizedWKBParameters p{TCAD_CONST(1e14),TCAD_CONST(2.3),mass,fraction?TCAD_CONST(.125):TCAD_CONST(0.0),t.segments};
  const auto actual=evaluate_linearized_wkb(g,phi,node,t.gap,p,weight,true);
  const real_t E=abs_q((real_t)linearized_wkb_x_field(g,phi,node));
  auto rate=[&](real_t f){Vector v=phi;for(auto& a:v)a*=f;return evaluate_linearized_wkb(g,v,node,t.gap,p,weight).generation;};
  real_t left[2],right[2],central[2],error=0,growth=0;
  for(int step=0;step<2;++step){
   const real_t h=side==0?(step==0?TCAD_CONST(0x1p-16):TCAD_CONST(0x1p-18)):(step==0?TCAD_CONST(0x1p-26):TCAD_CONST(0x1p-28));
   const real_t lo=rate(1-h),hi=rate(1+h),inc=E*h;
   left[step]=(actual.generation-lo)/inc;right[step]=(hi-actual.generation)/inc;central[step]=(hi-lo)/(2*inc);
   const real_t estimate=side==0?right[step]:central[step];
   error=std::max(error,abs_q(estimate-actual.d_generation_d_field)/std::max(TCAD_CONST(1.0),std::max(abs_q(actual.d_generation_d_field),abs_q(actual.generation/E))));
  }
  if(side==0&&weight!=0)growth=(left[1]-right[1])/(left[0]-right[0]);
  bool passed=isfinite_q(actual.generation)&&isfinite_q(actual.d_generation_d_field)&&error<(side==0?TCAD_CONST(1e-3):TCAD_CONST(2e-5));
  if(side==0&&weight!=0)passed=passed&&growth>TCAD_CONST(1.9)&&growth<TCAD_CONST(2.1);
  if(weight==0)passed=passed&&actual.generation==0&&actual.d_generation_d_field==0;
  if(!passed)++failed;++cases;if(side==0)corner_max=std::max(corner_max,error);else fd_max=std::max(fd_max,error);
  std::cout<<"{\"case\":"<<cases<<",\"mesh\":"<<mesh<<",\"fraction_window\":"<<(fraction?"true":"false")<<",\"sign\":"<<sign<<",\"side\":"<<side<<",\"segments\":"<<t.segments<<",\"turn\":"<<t.turn<<",\"field\":\""<<exact(E)<<"\",\"length\":\""<<exact(dx)<<"\",\"gap\":\""<<exact(t.gap)<<"\",\"mass\":\""<<exact(mass)<<"\",\"weight\":\""<<exact(weight)<<"\",\"generation\":\""<<exact(actual.generation)<<"\",\"derivative\":\""<<exact(actual.d_generation_d_field)<<"\",\"fd_left_coarse\":\""<<exact(left[0])<<"\",\"fd_left_fine\":\""<<exact(left[1])<<"\",\"fd_right_coarse\":\""<<exact(right[0])<<"\",\"fd_right_fine\":\""<<exact(right[1])<<"\",\"fd_central_coarse\":\""<<exact(central[0])<<"\",\"fd_central_fine\":\""<<exact(central[1])<<"\",\"fd_error\":\""<<exact(error)<<"\",\"left_excess_growth\":\""<<exact(growth)<<"\",\"passed\":"<<(passed?"true":"false")<<"}\n";
 }
 std::cout<<"{\"summary\":true,\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"cases\":"<<cases<<",\"failed\":"<<failed<<",\"fd_max\":\""<<exact(fd_max)<<"\",\"right_corner_fd_max\":\""<<exact(corner_max)<<"\"}\n";
 return !observe&&failed?1:0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
