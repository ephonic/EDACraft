#include <algorithm>
#include <cstdio>
#include <iostream>
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
std::string exact(real_t x){char b[160];
#ifdef TCAD_USE_FLOAT128
quadmath_snprintf(b,sizeof(b),"%Qa",x);
#else
std::snprintf(b,sizeof(b),"%La",x);
#endif
return b;}
void values(const Vector& v){std::cout<<'[';for(size_t i=0;i<v.size();++i)std::cout<<(i?",":"")<<'"'<<exact(v[i])<<'"';std::cout<<']';}
Vector difference(NewtonSolver& a,NewtonSolver& b,const Vector& x){Vector r,s;a.assemble_residual(x,r);b.assemble_residual(x,s);for(size_t i=0;i<r.size();++i)r[i]-=s[i];return r;}
Vector dense(NewtonSolver& s,const Vector& x){SparseMatrix j;s.assemble_jacobian(x,j);Vector a(x.size()*x.size());for(size_t r=0;r<x.size();++r)for(size_t k=j.row_offsets()[r];k<j.row_offsets()[r+1];++k)a[r*x.size()+j.col_indices()[k]]+=j.vals()[k];return a;}
int main(){try{
size_t cases=0,failed=0;real_t fd_max=0;
for(int mesh=0;mesh<3;++mesh)for(bool quadratic:{false,true})for(int sign:{-1,1})
for(size_t segments:{size_t(2),size_t(5),size_t(32)})for(real_t fraction:{TCAD_CONST(0.0),TCAD_CONST(.08)})
for(int pattern=0;pattern<4;++pattern)for(bool logs:{false,true}){
 Grid3D g{7,1,1,TCAD_CONST(1e-8),1,1};Vector u{0,1,2,3,4,5,6};
 if(mesh)u={0,TCAD_CONST(.7),TCAD_CONST(1.8),TCAD_CONST(3.1),TCAD_CONST(4.6),TCAD_CONST(6.3),TCAD_CONST(8.2)};
 if(mesh)for(real_t v:u)g.xx.push_back(v*TCAD_CONST(1e-8)+(mesh==2?TCAD_CONST(1e-6):0));
 const size_t N=g.npts(),M=3*N;Vector phi(N),weight;
 for(size_t i=0;i<N;++i)phi[i]=sign*(TCAD_CONST(.13)+TCAD_CONST(1.73)*u[i]+(quadratic?TCAD_CONST(.071)*u[i]*u[i]:0));
 if(pattern){weight.resize(N);for(size_t i=0;i<N;++i)weight[i]=pattern==1?TCAD_CONST(.2)+TCAD_CONST(.07)*i:pattern==2?(i%2?-TCAD_CONST(.3):TCAD_CONST(.8)):TCAD_CONST(0.0);}
 NewtonOptions o;o.enable_btbt=o.btbt_use_nonlocal=true;o.btbt_A=TCAD_CONST(1e24);o.btbt_D=TCAD_CONST(2.3);o.btbt_nonlocal_mass=TCAD_CONST(.15);o.btbt_tunnel_path_frac=fraction;o.btbt_wkb_npts=segments;o.btbt_continuity_scale=TCAD_CONST(.37);o.btbt_weight=weight;o.use_log_space=logs;
 NewtonSolver on(g,o);on.set_effective_dos(Vector(N,TCAD_CONST(1e19)),Vector(N,TCAD_CONST(1e19)));on.set_bandgap(Vector(N,TCAD_CONST(1.12)));on.set_electron_bc({{0,TCAD_CONST(1e19)}});on.set_hole_bc({{N-1,TCAD_CONST(1e19)}});
 Vector mn(N,TCAD_CONST(.14)),mp(N,TCAD_CONST(.045));mn[3]=0;mp[4]=0;on.set_mobility(mn,mp);
 NewtonSolver off=on;off.opt_.enable_btbt=false;
 GummelOptions go;go.btbt.enabled=go.btbt.use_nonlocal=true;go.btbt.A_kane=o.btbt_A;go.btbt.D=o.btbt_D;go.btbt.nonlocal_mass=o.btbt_nonlocal_mass;go.btbt.tunnel_path_frac=fraction;go.btbt.wkb_npts=segments;GummelSolver gs(g,go);gs.set_mobility(mn,mp);gs.set_bandgap(Vector(N,TCAD_CONST(1.12)));gs.set_btbt_weight(weight);Vector gen;gs.evaluate_btbt_generation(phi,gen);
 Vector rates(N),x(M),expected(M),scale(M);bool pass=true;
 for(size_t i=0;i<N;++i){rates[i]=on.compute_btbt_at(phi.data(),i);pass=pass&&rates[i]==gen[i];x[i]=phi[i];x[N+i]=x[2*N+i]=logs?log_q(TCAD_CONST(1e19)):TCAD_CONST(1e19);scale[N+i]=scale[2*N+i]=o.btbt_continuity_scale*gen[i]*g.dx_cell(i);if(i!=0&&mn[i]>=EPSILON)expected[N+i]=-scale[N+i];if(i!=N-1&&mp[i]>=EPSILON)expected[2*N+i]=-scale[2*N+i];}
 auto residual=difference(on,off,x),ja=dense(on,x),jb=dense(off,x);Vector actual,fd;real_t worst=0;
 for(size_t i=0;i<M;++i)pass=pass&&abs_q(residual[i]-expected[i])<=TCAD_CONST(1e-22)*std::max(TCAD_CONST(1.0),abs_q(expected[i]));
 const real_t h=TCAD_CONST(2e-4);
 for(size_t col=0;col<N;++col){Vector xp=x,xm=x;xp[col]+=h;xm[col]-=h;auto rp=difference(on,off,xp),rm=difference(on,off,xm);
  for(size_t row=N;row<M;++row){real_t a=ja[row*M+col]-jb[row*M+col],b=(rp[row]-rm[row])/(2*h);actual.push_back(a);fd.push_back(b);real_t error=abs_q(a-b)/std::max(TCAD_CONST(1.0),std::max(abs_q(b),abs_q(scale[row])));worst=std::max(worst,error);}}
 // Field-limited samples use an exact integer turning-point numerator.
 // No sqrt(epsilon)/h allowance is needed for this feedback fixture.
 const real_t fd_tolerance=TCAD_CONST(3e-5);
 pass=pass&&worst<fd_tolerance;fd_max=std::max(fd_max,worst);if(!pass)++failed;
 std::cout<<"{\"case\":"<<++cases<<",\"mesh\":"<<mesh<<",\"quadratic\":"<<(quadratic?"true":"false")<<",\"sign\":"<<sign<<",\"segments\":"<<segments<<",\"fraction\":\""<<exact(fraction)<<"\",\"pattern\":"<<pattern<<",\"logs\":"<<(logs?"true":"false")<<",\"passed\":"<<(pass?"true":"false")<<",\"fd_max\":\""<<exact(worst)<<"\",\"u\":";values(u);std::cout<<",\"phi\":";values(phi);std::cout<<",\"rates\":";values(rates);std::cout<<",\"residual\":";values(residual);std::cout<<",\"jacobian\":";values(actual);std::cout<<",\"finite_difference\":";values(fd);std::cout<<"}\n";
}
size_t guards=0;
for(int mode=0;mode<10;++mode){Grid3D g{3,1,1,TCAD_CONST(1e-8),1,1};NewtonOptions o;o.enable_btbt=o.btbt_use_nonlocal=true;
 if(mode==0)g.ny=2;if(mode==1)g.nx=1;if(mode==2)o.enable_quantum=true;if(mode==3)o.statistics_type=StatisticsType::FERMI_DIRAC;if(mode==4)o.transient_enabled=true;if(mode==5)o.freeze_phi=true;if(mode==6)o.freeze_n=true;if(mode==7)o.freeze_p=true;if(mode==8)o.btbt_nonlocal_mass=0;if(mode==9)o.btbt_wkb_npts=1;
 bool caught=false;try{NewtonSolver s(g,o);}catch(const std::invalid_argument&){caught=true;}if(caught)++guards;else++failed;
}
std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"cases\":"<<cases<<",\"guards\":"<<guards<<",\"failed\":"<<failed<<",\"fd_max\":\""<<exact(fd_max)<<"\"}\n";
return failed?1:0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
