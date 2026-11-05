#include "gummel_solver.h"
#include "newton_solver.h"
#include "device_simulator.h"
#include <cstdio>
#include <iostream>
#include <limits>
#include <string>
using namespace tcad;
std::string exact(real_t x) { char b[160];
#ifdef TCAD_USE_FLOAT128
    quadmath_snprintf(b,sizeof(b),"%Qa",x);
#else
    std::snprintf(b,sizeof(b),"%La",x);
#endif
    return b;
}
void values(const Vector& a) {std::cout<<'[';for(size_t i=0;i<a.size();++i)std::cout<<(i?",":"")<<'"'<<exact(a[i])<<'"';std::cout<<']';}
bool identical(const Vector& a,const Vector& b) {if(a.size()!=b.size())return false;for(size_t i=0;i<a.size();++i)if(exact(a[i])!=exact(b[i]))return false;return true;}
int main(int argc,char** argv) {try {
 bool observe=argc>1 && std::string(argv[1])=="--observe";size_t cases=0,failed=0;
 for(size_t nodes:{size_t(3),size_t(63),size_t(64),size_t(65)})
 for(size_t segments:{size_t(0),size_t(1),size_t(2),size_t(3),size_t(4),size_t(5),size_t(1048575),size_t(1048576),size_t(1048577),std::numeric_limits<size_t>::max()-1,std::numeric_limits<size_t>::max()})
 for(int consumer=0;consumer<7;++consumer) {
  bool active=consumer==2||consumer==5||consumer==6;
  size_t rounded=segments>=4 && segments%2 && segments<1048577?segments+1:segments;
  bool allowed=!active||(segments>=2 && segments<=1048576 && nodes<=67108864/(rounded>=4?rounded+1:1));
  Grid3D g{nodes,1,1,TCAD_CONST(1e-8),1,1};bool accepted=true;
  try {
   if(consumer<3){GummelOptions o;o.btbt.enabled=consumer!=0;o.btbt.use_nonlocal=consumer!=1;o.btbt.wkb_npts=segments;GummelSolver s(g,o);}
   else if(consumer<6){NewtonOptions o;o.enable_btbt=consumer!=3;o.btbt_use_nonlocal=consumer!=4;o.btbt_wkb_npts=segments;NewtonSolver s(g,o);}
   else {DeviceSimulator s(nodes,1,1,TCAD_CONST(1e-8),1,1);s.set_btbt_nonlocal_params(TCAD_CONST(.08),segments);}
  }catch(const std::invalid_argument&){accepted=false;}
  bool pass=accepted==allowed;if(!pass)++failed;
  std::cout<<"{\"kind\":\"resource\",\"case\":"<<++cases<<",\"nodes\":"<<nodes<<",\"segments\":"<<segments<<",\"consumer\":"<<consumer<<",\"accepted\":"<<(accepted?"true":"false")<<",\"expected\":"<<(allowed?"true":"false")<<",\"passed\":"<<(pass?"true":"false")<<"}\n";
 }
 for(int mesh=0;mesh<3;++mesh)for(size_t segments:{size_t(2),size_t(5),size_t(32)})
 for(int error_mode=0;error_mode<6;++error_mode)for(int output_mode=0;output_mode<4;++output_mode) {
  Grid3D g{5,1,1,TCAD_CONST(1e-8),1,1};
  if(mesh)g.xx={0,TCAD_CONST(.7e-8),TCAD_CONST(1.8e-8),TCAD_CONST(3.1e-8),TCAD_CONST(4.8e-8)};
  if(mesh==2)for(auto& x:g.xx)x+=TCAD_CONST(1e-6);
  Vector phi{0,1,2,3,4};const Vector before_phi=phi;
  GummelOptions o;o.btbt.enabled=o.btbt.use_nonlocal=true;o.btbt.wkb_npts=segments;o.btbt.tunnel_path_frac=0;
  o.btbt.A_kane=error_mode==0?-TCAD_CONST(1.0):error_mode==2?-TCAD_CONST(1e400):TCAD_CONST(1.0);
  o.btbt.D=error_mode==2?600:1000;
  if(error_mode==3)o.btbt.A_kane=(real_t)std::numeric_limits<double>::infinity();
  if(error_mode==4)o.btbt.A_kane=(real_t)std::numeric_limits<double>::quiet_NaN();
  if(error_mode==5)o.btbt.D=(real_t)std::numeric_limits<double>::infinity();
  GummelSolver s(g,o);Vector weights(5,error_mode==1?-TCAD_CONST(1.0):TCAD_CONST(1.0));s.set_btbt_weight(weights);
  Vector output=output_mode==0?Vector{}:output_mode==1?Vector{TCAD_CONST(-7.25)}:Vector{TCAD_CONST(-0.0),42,13,97,8,3,9};
  const Vector before_output=output;bool caught=false;std::string exception;
  try {s.evaluate_btbt_generation(phi,output_mode==3?phi:output);}
  catch(const std::overflow_error&){caught=error_mode<3;exception="overflow_error";}
  catch(const std::invalid_argument&){caught=error_mode>=3;exception="invalid_argument";}
  bool unchanged=identical(phi,before_phi)&&identical(output,before_output);
  if(error_mode<3){s.set_btbt_weight(Vector(5,o.btbt.A_kane>0?TCAD_CONST(1.0):-TCAD_CONST(1.0)));}
  else {s.set_mobility(Vector(5,0),Vector(5,0));}
  Vector retry;s.evaluate_btbt_generation(before_phi,retry);bool recovered=retry.size()==5;
  for(size_t i=0;i<retry.size();++i)recovered=recovered&&retry[i]==(error_mode<3&&i>0&&i<4?(real_t)1e50:TCAD_CONST(0.0));
  bool pass=caught&&unchanged&&recovered;if(!pass)++failed;
  std::cout<<"{\"kind\":\"exception\",\"case\":"<<++cases<<",\"mesh\":"<<mesh<<",\"segments\":"<<segments<<",\"error_mode\":"<<error_mode<<",\"output_mode\":"<<output_mode<<",\"exception\":\""<<exception<<"\",\"caught_expected\":"<<(caught?"true":"false")<<",\"unchanged\":"<<(unchanged?"true":"false")<<",\"recovered\":"<<(recovered?"true":"false")<<",\"passed\":"<<(pass?"true":"false")<<"}\n";
 }
 for(int mesh=0;mesh<3;++mesh)for(size_t segments:{size_t(2),size_t(5),size_t(32)})for(bool nonlocal:{false,true}) {
  Grid3D g{5,1,1,TCAD_CONST(1e-8),1,1};if(mesh)g.xx={0,TCAD_CONST(.7e-8),TCAD_CONST(1.8e-8),TCAD_CONST(3.1e-8),TCAD_CONST(4.8e-8)};if(mesh==2)for(auto& x:g.xx)x+=TCAD_CONST(1e-6);
  GummelOptions o;o.btbt.enabled=true;o.btbt.use_nonlocal=nonlocal;o.btbt.wkb_npts=segments;o.btbt.tunnel_path_frac=0;o.btbt.A_kane=TCAD_CONST(1e-10);o.btbt.B_kane=TCAD_CONST(1e7);
  GummelSolver s(g,o);Vector phi{0,1,2,3,4},expected;s.evaluate_btbt_generation(phi,expected);Vector aliased=phi;s.evaluate_btbt_generation(aliased,aliased);
  bool pass=identical(expected,aliased);if(!pass)++failed;
  std::cout<<"{\"kind\":\"alias\",\"case\":"<<++cases<<",\"mesh\":"<<mesh<<",\"segments\":"<<segments<<",\"nonlocal\":"<<(nonlocal?"true":"false")<<",\"passed\":"<<(pass?"true":"false")<<",\"phi\":";values(phi);std::cout<<",\"x\":";values(g.xx);std::cout<<",\"expected\":";values(expected);std::cout<<",\"actual\":";values(aliased);std::cout<<"}\n";
 }
 std::cout<<"{\"summary\":true,\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"cases\":"<<cases<<",\"failed\":"<<failed<<"}\n";
 return !observe&&failed?1:0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
