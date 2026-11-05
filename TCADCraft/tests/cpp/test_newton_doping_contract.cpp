#include "newton_solver.h"
#include <algorithm>
#include <cstdio>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

using namespace tcad;
namespace {
void require(bool ok,const char* message) {if(!ok)throw std::runtime_error(message);}
std::string exact(real_t value) {
    char text[128];
#ifdef TCAD_USE_FLOAT128
    quadmath_snprintf(text,sizeof(text),"%Qa",value);
#else
    std::snprintf(text,sizeof(text),"%La",value);
#endif
    return text;
}
}

int main(int argc,char** argv) {
    try {
        const bool observe=argc==2 && std::string(argv[1])=="--observe";
        size_t attempted=0,rejected=0,accepted=0,preserved=0,retries=0,valid=0,finite=0,observable=0;
        real_t max_error=TCAD_CONST(0.0);
        const real_t nan=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN());
        const real_t inf=static_cast<real_t>(std::numeric_limits<double>::infinity());
        for(int axis=0;axis<3;++axis)for(bool stretched:{false,true})
        for(bool log_space:{false,true})for(real_t fraction:{TCAD_CONST(1.0),TCAD_CONST(.375)}) {
            Grid3D grid{1,1,1,TCAD_CONST(1e-6),TCAD_CONST(1e-6),TCAD_CONST(1e-6)};
            if(axis==0)grid.nx=5;
            if(axis==1)grid.ny=5;
            if(axis==2)grid.nz=5;
            Vector x{TCAD_CONST(0.0),TCAD_CONST(1e-6),TCAD_CONST(2e-6),TCAD_CONST(3e-6),TCAD_CONST(4e-6)};
            if(stretched) {
                x={TCAD_CONST(0.0),TCAD_CONST(.4e-6),TCAD_CONST(1.3e-6),TCAD_CONST(2.7e-6),TCAD_CONST(4e-6)};
                if(axis==0)grid.xx=x;
                if(axis==1)grid.yx=x;
                if(axis==2)grid.zx=x;
            }
            NewtonOptions options;
            options.max_iter=40;
            options.tol=std::max(TCAD_CONST(1e-28),TCAD_CONST(64.0)*epsilon_q());
            options.abs_tol=std::max(TCAD_CONST(1e-30),TCAD_CONST(64.0)*epsilon_q());
            options.linear_tol=options.abs_tol;
            options.linear_solver=SolverType::DENSE_DIRECT;
            options.use_log_space=log_space;
            options.freeze_n=true;options.freeze_p=true;
            options.record_nonlinear_history=true;
            NewtonSolver solver(grid,options);
            const real_t eps=TCAD_CONST(20.0)*EPS0,D=TCAD_CONST(1e16);
            const real_t left=TCAD_CONST(.01),right=TCAD_CONST(.02);
            const Vector zero(5,TCAD_CONST(0.0)),dielectric(5,eps),carriers(5,TCAD_CONST(1.0));
            const Vector original{D/TCAD_CONST(2.0),-D/TCAD_CONST(3.0),D*TCAD_CONST(1.2),D*TCAD_CONST(.8),D*TCAD_CONST(2.0)};
            solver.set_permittivity(dielectric);
            // Exact explicit faces avoid the nodal harmonic regularizer in
            // the independent constant-epsilon charged reference.
            solver.set_edge_permittivity(dielectric,dielectric,dielectric,dielectric,dielectric,dielectric);
            solver.set_charge_volume_fraction(Vector(5,fraction));
            solver.set_mobility(zero,zero);
            solver.set_effective_dos(Vector(5,D),Vector(5,D));
            solver.set_bandgap(Vector(5,TCAD_CONST(6.0)));
            solver.set_semiconductor_mask(std::vector<char>(5,0));
            solver.set_phi_dirichlet({{0,left},{4,right}});
            auto solve=[&]() {
                Vector phi(zero),n(carriers),p(carriers);
                require(solver.solve(phi,n,p),"native Newton doping solve failed");
                require(n==carriers && p==carriers,"Newton doping changed frozen carrier state");
                return phi;
            };
            solver.set_doping(original);const auto control=solve();
            solver.set_doping(zero);const auto uncharged=solve();
            require(abs_q(control[2]-uncharged[2])>TCAD_CONST(1e-10),"doping control is not observable");
            ++observable;solver.set_doping(original);require(solve()==control,"doping control restore failed");
            auto request=[&](const Vector& bad,bool shape) {
                ++attempted;bool caught=false;
                const auto history=solver.residuals();const auto samples=solver.nonlinear_samples();
                require(!history.empty() && !samples.empty(),"doping history control is empty");
                try {solver.set_doping(bad);}
                catch(const std::invalid_argument& e) {
                    require(std::string(e.what())==(shape?"Doping size mismatch":"Doping must be finite"),"wrong native Newton doping exception");
                    caught=true;++rejected;
                }
                if(!caught)++accepted;
                else {
                    require(solver.residuals()==history && solver.nonlinear_samples()==samples,"rejected doping changed Newton history");
                    require(solve()==control,"rejected doping changed Newton next solution");
                    ++preserved;
                }
                if(!observe)require(caught,"invalid native Newton doping was accepted");
                // Never assemble accepted parent short arrays or nonfinite values.
                solver.set_doping(original);require(solve()==control,"native Newton doping valid retry failed");++retries;
            };
            // Nonfinite contents in wrong-sized arrays also verify that the
            // shape error has priority, including the empty-vector case.
            for(size_t size:{size_t(0),size_t(4),size_t(6)})request(Vector(size,nan),true);
            for(real_t value:{nan,inf,-inf})for(size_t pos=0;pos<5;++pos) {
                Vector bad(5,-TCAD_CONST(2.0)*D);bad[pos]=value;request(bad,false);
            }
            auto reference=[&](const Vector& doping,bool constant) {
                solver.set_doping(doping);const auto phi=solve();
                // Integrate the finite-volume charge independently. For each
                // interior cell the dielectric flux drops by rho*cell_width;
                // determine the left flux from the two potential boundaries.
                Vector accumulated(4,TCAD_CONST(0.0));
                for(size_t i=1;i<4;++i)
                    accumulated[i]=accumulated[i-1]+QE*fraction*doping[i]*(x[i+1]-x[i-1])/TCAD_CONST(2.0);
                real_t weighted=TCAD_CONST(0.0);
                for(size_t i=0;i<4;++i)weighted+=(x[i+1]-x[i])*accumulated[i]/eps;
                const real_t flux=(right-left+weighted)*eps/(x[4]-x[0]);
                Vector expected(5,left);
                for(size_t i=0;i<4;++i)expected[i+1]=expected[i]+(x[i+1]-x[i])*(flux-accumulated[i])/eps;
                const real_t tolerance=std::max(TCAD_CONST(1e-25),TCAD_CONST(4096.0)*epsilon_q());
                for(size_t i=0;i<5;++i) {
                    if(constant) {
                        const real_t quadratic=left+(right-left)*x[i]/x[4]+QE*fraction*doping[0]*x[i]*(x[4]-x[i])/(TCAD_CONST(2.0)*eps);
                        require(abs_q(expected[i]-quadratic)<=tolerance*(TCAD_CONST(1.0)+abs_q(quadratic)),"charge-integral and quadratic references disagree");
                    }
                    const real_t error=abs_q(phi[i]-expected[i]);
                    require(isfinite_q(error) && error<=tolerance*(TCAD_CONST(1.0)+abs_q(expected[i])),"independent Newton charge-integral reference mismatch");
                    if(error>max_error)max_error=error;
                }
                std::cout<<"{\"case\":"<<++valid<<",\"values\":[";
                for(size_t i=0;i<5;++i)std::cout<<(i?",":"")<<'"'<<exact(phi[i])<<'"';
                std::cout<<"]}\n";
            };
            reference(original,false);
            reference(Vector(5,D),true);
            reference(Vector(5,-TCAD_CONST(2.0)*D),true);
            reference(zero,true);
            Vector opposite(original);for(auto& value:opposite)value=-value;
            reference(opposite,false);reference(original,false);
            Vector limits{TCAD_CONST(-0.0),TCAD_CONST(0.0),TCAD_CONST(-1e300),TCAD_CONST(1e300)};
#ifdef TCAD_USE_FLOAT128
            limits.push_back(TCAD_CONST(-1e400));limits.push_back(TCAD_CONST(1e400));
#endif
            for(real_t value:limits) {
                require(isfinite_q(value),"finite doping fixture is not finite");
                solver.set_doping(Vector(5,value));++finite;
                solver.set_doping(original);require(solve()==control,"finite doping restore failed");
            }
        }
        std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()
                 <<",\"attempted\":"<<attempted<<",\"rejected\":"<<rejected<<",\"accepted\":"<<accepted
                 <<",\"preserved\":"<<preserved<<",\"retries\":"<<retries<<",\"valid_cases\":"<<valid
                 <<",\"finite_cases\":"<<finite<<",\"observable_controls\":"<<observable
                 <<",\"max_reference_error\":"<<static_cast<double>(max_error)<<"}\n";
        require(observe || (attempted==rejected && rejected==preserved && !accepted),"native Newton doping contract failed");
        return 0;
    }catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
