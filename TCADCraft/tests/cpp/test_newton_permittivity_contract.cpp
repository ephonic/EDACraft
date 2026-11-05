#include "newton_solver.h"
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
using Faces=std::array<Vector,6>;
}
int main(int argc,char** argv) {
    try {
        const bool observe=argc==2 && std::string(argv[1])=="--observe";
        size_t attempted=0,rejected=0,accepted=0,preserved=0,retries=0,valid=0,finite=0;
        real_t max_error=TCAD_CONST(0.0);
        const real_t nan=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN());
        const real_t inf=static_cast<real_t>(std::numeric_limits<double>::infinity());
        
        for(int axis=0;axis<3;++axis)for(bool stretched:{false,true})for(bool log_space:{false,true}) {
            Grid3D grid{1,1,1,TCAD_CONST(1e-6),TCAD_CONST(1e-6),TCAD_CONST(1e-6)};
            if(axis==0)grid.nx=5;if(axis==1)grid.ny=5;if(axis==2)grid.nz=5;
            Vector x{TCAD_CONST(0.0),TCAD_CONST(1e-6),TCAD_CONST(2e-6),TCAD_CONST(3e-6),TCAD_CONST(4e-6)};
            if(stretched) {
                x={TCAD_CONST(0.0),TCAD_CONST(.4e-6),TCAD_CONST(1.3e-6),TCAD_CONST(2.7e-6),TCAD_CONST(4e-6)};
                if(axis==0)grid.xx=x;if(axis==1)grid.yx=x;if(axis==2)grid.zx=x;
            }
            NewtonOptions opt;opt.max_iter=40;opt.tol=TCAD_CONST(1e-28);
            opt.abs_tol=TCAD_CONST(1e-30);opt.linear_tol=TCAD_CONST(1e-30);
            opt.linear_solver=SolverType::DENSE_DIRECT;opt.use_log_space=log_space;
            opt.freeze_n=true;opt.freeze_p=true;opt.record_nonlinear_history=true;
            NewtonSolver solver(grid,opt);
            solver.set_mobility(Vector(5,TCAD_CONST(0.0)),Vector(5,TCAD_CONST(0.0)));
            solver.set_doping(Vector(5,TCAD_CONST(0.0)));
            solver.set_effective_dos(Vector(5,TCAD_CONST(1e16)),Vector(5,TCAD_CONST(1e16)));
            solver.set_bandgap(Vector(5,TCAD_CONST(6.0)));
            solver.set_semiconductor_mask(std::vector<char>(5,0));
            const Vector zero(5,TCAD_CONST(0.0)),original(5,TCAD_CONST(20.0)*EPS0);
            Faces original_faces;for(auto& v:original_faces)v.assign(5,TCAD_CONST(5.0)*EPS0);
            const Vector original_links{TCAD_CONST(3.0)*EPS0,TCAD_CONST(11.0)*EPS0,TCAD_CONST(7.0)*EPS0,TCAD_CONST(5.0)*EPS0};
            auto pair=[&](Faces& f,const Vector& links) {
                for(size_t i=0;i<5;++i) {f[2*axis][i]=links[std::min(i,size_t(3))];f[2*axis+1][i]=links[i?i-1:0];}
            };
            pair(original_faces,original_links);
            auto nodal=[&](const Vector& v) {solver.set_permittivity(v);};
            auto edges=[&](const Faces& f) {solver.set_edge_permittivity(f[0],f[1],f[2],f[3],f[4],f[5]);};
            const real_t left=TCAD_CONST(0.0),right=TCAD_CONST(.2);
            solver.set_phi_dirichlet({{0,left},{4,right}});
            auto solve=[&]() {
                Vector out(5,TCAD_CONST(0.0)),n(5,TCAD_CONST(1.0)),p(n);
                require(solver.solve(out,n,p),"native Newton permittivity solve failed");
                require(n==Vector(5,TCAD_CONST(1.0)) && p==n,"frozen Newton carrier state changed");
                return out;
            };
            auto restore=[&]() {nodal(original);edges(original_faces);};
            restore();const auto control=solve();
            auto request=[&](const Vector& eps,const Faces& f,int slot,bool shape) {
                ++attempted;bool caught=false;
                const auto history=solver.residuals();const auto samples=solver.nonlinear_samples();
                const std::string message=shape?(slot<0?"Newton permittivity size mismatch":"Newton edge permittivity size mismatch"):
                    (slot<0?"permittivity values must be finite":"edge permittivity values must be finite");
                try {if(slot<0)nodal(eps);else edges(f);}
                catch(const std::invalid_argument& e) {require(e.what()==message,"wrong permittivity exception");caught=true;++rejected;}
                if(!caught)++accepted;
                else {
                    require(solver.residuals()==history && solver.nonlinear_samples()==samples,"rejected Newton permittivity changed iteration history");
                    require(solve()==control,"rejected permittivity changed next solution");

                    ++preserved;
                }
                if(!observe)require(caught,"invalid native Newton permittivity was accepted");
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
                // conservative discrete operator, including its existing 1e-30
                // harmonic-denominator regularizer and face sentinels.
                Vector resistance(5,TCAD_CONST(0.0));
                for(size_t i=0;i<4;++i) {
                    const real_t harmonic=TCAD_CONST(2.0)*eps[i]*eps[i+1]/(eps[i]+eps[i+1]+TCAD_CONST(1e-30));
                    const auto& plus=f[2*axis];const auto& minus=f[2*axis+1];
                    const real_t a=!plus.empty() && plus[i]>TCAD_CONST(0.0)?plus[i]:harmonic;
                    const real_t b=!minus.empty() && minus[i+1]>TCAD_CONST(0.0)?minus[i+1]:harmonic;
                    require(a==b,"reference requires reciprocal face inputs");
                    resistance[i+1]=resistance[i]+(x[i+1]-x[i])/a;
                }
                for(size_t i=0;i<5;++i) {
                    const real_t expected=left+(right-left)*resistance[i]/resistance[4];
                    const real_t error=abs_q(out[i]-expected);
                    const real_t tolerance=std::max(TCAD_CONST(1e-25),TCAD_CONST(4096.0)*epsilon_q());
                    require(isfinite_q(error) && error<=tolerance*(TCAD_CONST(1.0)+abs_q(expected)),"independent Newton series reference mismatch");
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
