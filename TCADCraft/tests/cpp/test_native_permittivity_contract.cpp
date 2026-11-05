#include "gummel_solver.h"
#include <array>
#include <cstdio>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
using namespace tcad;
namespace {
void require(bool ok,const char* text) {if(!ok)throw std::runtime_error(text);}
std::string exact(real_t value) {
    char text[128];
#ifdef TCAD_USE_FLOAT128
    quadmath_snprintf(text,sizeof(text),"%Qa",value);
#else
    std::snprintf(text,sizeof(text),"%La",value);
#endif
    return text;
}
struct System {
    Vector values,rhs;std::vector<size_t> columns,offsets;
    explicit System(const PoissonSolver& p):values(p.matrix().vals()),rhs(p.rhs()),columns(p.matrix().col_indices()),offsets(p.matrix().row_offsets()) {}
    bool equals(const PoissonSolver& p) const {return values==p.matrix().vals() && rhs==p.rhs() && columns==p.matrix().col_indices() && offsets==p.matrix().row_offsets();}
};
using Faces=std::array<Vector,6>;
}
int main(int argc,char** argv) {
    try {
        const bool observe=argc==2 && std::string(argv[1])=="--observe";
        size_t attempted=0,rejected=0,accepted=0,preserved=0,retries=0,valid=0,finite=0;
        real_t max_error=TCAD_CONST(0.0);
        const real_t nan=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN());
        const real_t inf=static_cast<real_t>(std::numeric_limits<double>::infinity());
        const char* names[]={"x_plus","x_minus","y_plus","y_minus","z_plus","z_minus"};
        for(int axis=0;axis<3;++axis)for(bool stretched:{false,true})for(int route=0;route<3;++route) {
            // route 0: electrostatic Poisson; 1: steady thermal Poisson;
            // 2: Gummel's delegated recompute_poisson, without carrier solve.
            Grid3D grid{1,1,1,TCAD_CONST(1e-6),TCAD_CONST(1e-6),TCAD_CONST(1e-6)};
            if(axis==0)grid.nx=5;if(axis==1)grid.ny=5;if(axis==2)grid.nz=5;
            Vector x{TCAD_CONST(0.0),TCAD_CONST(1e-6),TCAD_CONST(2e-6),TCAD_CONST(3e-6),TCAD_CONST(4e-6)};
            if(stretched) {
                x={TCAD_CONST(0.0),TCAD_CONST(.4e-6),TCAD_CONST(1.3e-6),TCAD_CONST(2.7e-6),TCAD_CONST(4e-6)};
                if(axis==0)grid.xx=x;if(axis==1)grid.yx=x;if(axis==2)grid.zx=x;
            }
            PoissonSolver p(grid);GummelOptions opt;opt.boltzmann_lin=false;GummelSolver g(grid,opt);
            const Vector zero(5,TCAD_CONST(0.0)),original(5,TCAD_CONST(20.0)*EPS0);
            Faces original_faces;for(auto& v:original_faces)v.assign(5,TCAD_CONST(5.0)*EPS0);
            const Vector original_links{TCAD_CONST(3.0)*EPS0,TCAD_CONST(11.0)*EPS0,TCAD_CONST(7.0)*EPS0,TCAD_CONST(5.0)*EPS0};
            auto pair=[&](Faces& f,const Vector& links) {
                for(size_t i=0;i<5;++i) {f[2*axis][i]=links[std::min(i,size_t(3))];f[2*axis+1][i]=links[i?i-1:0];}
            };
            pair(original_faces,original_links);
            auto nodal=[&](const Vector& v) {if(route==2)g.set_permittivity(v);else p.set_permittivity(v);};
            auto edges=[&](const Faces& f) {
                if(route==2)g.set_edge_permittivity(f[0],f[1],f[2],f[3],f[4],f[5]);
                else p.set_edge_permittivity(f[0],f[1],f[2],f[3],f[4],f[5]);
            };
            const real_t left=route==1?TCAD_CONST(300.0):TCAD_CONST(0.0),right=route==1?TCAD_CONST(310.0):TCAD_CONST(.2);
            p.set_dirichlet({{0,left},{4,right}});g.set_poisson_dirichlet({{0,left},{4,right}});
            auto solve=[&]() {
                Vector out(5,TCAD_CONST(0.0));
                if(route==2)require(g.recompute_poisson(out,zero,zero),"Gummel permittivity solve failed");
                else {if(route==1)p.assemble_thermal(zero);else p.assemble(zero,zero);require(p.solve(out),"Poisson permittivity solve failed");}
                return out;
            };
            auto restore=[&]() {nodal(original);edges(original_faces);};
            restore();const auto control=solve();const System system(p);
            auto request=[&](const Vector& eps,const Faces& f,int slot,bool shape) {
                ++attempted;bool caught=false;
                const std::string message=shape?(slot<0?"Permittivity size mismatch":std::string("edge_eps_")+names[slot]+" size mismatch"):
                    (slot<0?"permittivity values must be finite":"edge permittivity values must be finite");
                try {if(slot<0)nodal(eps);else edges(f);}
                catch(const std::invalid_argument& e) {require(e.what()==message,"wrong permittivity exception");caught=true;++rejected;}
                if(!caught)++accepted;
                else {
                    if(route!=2)require(system.equals(p),"rejected permittivity changed assembled system");
                    require(solve()==control,"rejected permittivity changed next solution");
                    if(route!=2)require(system.equals(p),"rejected permittivity changed reassembled operator");
                    ++preserved;
                }
                if(!observe)require(caught,"nonfinite native permittivity was accepted");
                // Accepted old NaN/infinity inputs are restored before assembly.
                restore();require(solve()==control,"valid permittivity retry failed");++retries;
            };
            for(size_t size:{size_t(0),size_t(4),size_t(6)})request(Vector(size,nan),original_faces,-1,true);
            for(real_t bad:{nan,inf,-inf})for(size_t i=0;i<5;++i) {
                Vector v(5,TCAD_CONST(9.0)*EPS0);v[i]=bad;request(v,original_faces,-1,false);
            }
            for(int slot=0;slot<6;++slot) {
                for(size_t size:{size_t(4),size_t(6)}) {
                    Faces f;for(auto& v:f)v.assign(5,TCAD_CONST(9.0)*EPS0);
                    // Size errors retain precedence over a nonfinite value in
                    // an earlier field, without any state write.
                    if(slot)f[0][0]=nan;f[slot].assign(size,nan);request(original,f,slot,true);
                }
                for(real_t bad:{nan,inf,-inf})for(size_t i=0;i<5;++i) {
                    Faces f;for(auto& v:f)v.assign(5,TCAD_CONST(9.0)*EPS0);
                    f[slot][i]=bad;request(original,f,slot,false);
                }
            }
            Vector limits{TCAD_CONST(-0.0),TCAD_CONST(0.0),TCAD_CONST(-1e300),TCAD_CONST(1e300)};
#ifdef TCAD_USE_FLOAT128
            limits.push_back(TCAD_CONST(-1e400));limits.push_back(TCAD_CONST(1e400));
#endif
            for(real_t value:limits)for(int slot=-1;slot<6;++slot) {
                require(isfinite_q(value),"finite permittivity fixture invalid");
                if(slot<0)nodal(Vector(5,value));
                else {Faces f=original_faces;f[slot].assign(5,value);edges(f);}
                ++finite;restore();require(solve()==control,"finite permittivity restore failed");
            }
            auto reference=[&](const Vector& eps,const Faces& f) {
                nodal(eps);edges(f);const auto out=solve();
                // Independent series-resistance solution of the charge-free
                // conservative finite-volume operator, including sentinels.
                Vector resistance(5,TCAD_CONST(0.0));
                for(size_t i=0;i<4;++i) {
                    const real_t harmonic=TCAD_CONST(2.0)*eps[i]*eps[i+1]/(eps[i]+eps[i+1]);
                    const auto& plus=f[2*axis];const auto& minus=f[2*axis+1];
                    const real_t a=!plus.empty() && plus[i]>TCAD_CONST(0.0)?plus[i]:harmonic;
                    const real_t b=!minus.empty() && minus[i+1]>TCAD_CONST(0.0)?minus[i+1]:harmonic;
                    require(a==b,"reference requires reciprocal face inputs");
                    resistance[i+1]=resistance[i]+(x[i+1]-x[i])/a;
                }
                for(size_t i=0;i<5;++i) {
                    const real_t expected=left+(right-left)*resistance[i]/resistance[4];
                    const real_t error=abs_q(out[i]-expected);
                    require(isfinite_q(error) && error<=TCAD_CONST(4096.0)*epsilon_q()*(TCAD_CONST(1.0)+abs_q(expected)),"independent permittivity series reference mismatch");
                    if(error>max_error)max_error=error;
                }
                std::cout<<"{\"case\":"<<++valid<<",\"values\":[";
                for(size_t i=0;i<5;++i)std::cout<<(i?",":"")<<'"'<<exact(out[i])<<'"';std::cout<<"]}\n";
            };
            const Vector varied{TCAD_CONST(4.0)*EPS0,TCAD_CONST(6.0)*EPS0,TCAD_CONST(9.0)*EPS0,TCAD_CONST(13.0)*EPS0,TCAD_CONST(20.0)*EPS0};
            reference(original,original_faces);reference(varied,Faces{});
            Faces uniform;for(auto& v:uniform)v.assign(5,TCAD_CONST(12.0)*EPS0);reference(varied,uniform);
            Faces mixed=original_faces;mixed[2*axis][1]=TCAD_CONST(0.0);mixed[2*axis+1][2]=-EPS0;reference(varied,mixed);
            Faces fallback;for(auto& v:fallback)v.assign(5,-EPS0);reference(varied,fallback);
            for(auto& v:fallback)v.assign(5,TCAD_CONST(-0.0));reference(varied,fallback);
        }
        std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()
                 <<",\"attempted\":"<<attempted<<",\"rejected\":"<<rejected<<",\"accepted\":"<<accepted
                 <<",\"preserved\":"<<preserved<<",\"retries\":"<<retries<<",\"valid_cases\":"<<valid
                 <<",\"finite_cases\":"<<finite<<",\"max_reference_error\":"<<static_cast<double>(max_error)<<"}\n";
        require(observe || (attempted==rejected && rejected==preserved && !accepted),"native permittivity contract failed");
        return 0;
    }catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
