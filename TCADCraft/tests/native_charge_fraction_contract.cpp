#include "poisson_solver.h"
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

using namespace tcad;

int main() {
    try {
        size_t attempted=0, rejected=0, accepted=0, valid_cases=0;
        real_t max_error=TCAD_CONST(0.0);
        for (int axis=0; axis<3; ++axis) {
            Grid3D grid{1,1,1,TCAD_CONST(1e-6),TCAD_CONST(1e-6),TCAD_CONST(1e-6)};
            if(axis==0)grid.nx=3;
            if(axis==1)grid.ny=3;
            if(axis==2)grid.nz=3;
            PoissonSolver solver(grid);
            const real_t eps=EPS0*TCAD_CONST(11.7), density=TCAD_CONST(1e16);
            solver.set_permittivity(std::vector<real_t>(3,eps));
            solver.set_doping({TCAD_CONST(0.0),density,TCAD_CONST(0.0)});
            solver.set_dirichlet({{0,TCAD_CONST(0.0)},{2,TCAD_CONST(0.0)}});
            const std::vector<real_t> zero(3,TCAD_CONST(0.0));
            const std::vector<real_t> original{TCAD_CONST(.2),TCAD_CONST(.6),TCAD_CONST(.9)};
            auto solve=[&]() {
                solver.assemble(zero,zero);
                std::vector<real_t> phi(3,TCAD_CONST(0.0));
                if(!solver.solve(phi))throw std::runtime_error("Poisson did not converge");
                return phi;
            };
            solver.set_charge_volume_fraction(original);
            const auto control=solve();
            const real_t nan=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN());
            const real_t inf=static_cast<real_t>(std::numeric_limits<double>::infinity());
            const std::vector<real_t> bad{nan,inf,-inf,TCAD_CONST(-.01),TCAD_CONST(1.01)};
            auto request=[&](const std::vector<real_t>& values,const std::string& message) {
                ++attempted;
                bool caught=false;
                try { solver.set_charge_volume_fraction(values); }
                catch(const std::invalid_argument& e) {
                    if(e.what()!=message)throw std::runtime_error("unexpected validation message");
                    caught=true;
                }
                if(caught) {
                    ++rejected;
                    if(solve()!=control)throw std::runtime_error("rejected fraction changed native Poisson output");
                } else ++accepted;
                // Baseline can accept NaN; never assemble with that input.
                solver.set_charge_volume_fraction(original);
            };
            for(real_t value:bad)for(size_t pos=0;pos<3;++pos) {
                auto values=std::vector<real_t>(3,TCAD_CONST(.8));values[pos]=value;
                request(values,"Charge volume fraction must be in [0,1]");
            }
            for(size_t size:{size_t(0),size_t(2),size_t(4)})
                request(std::vector<real_t>(size,TCAD_CONST(.8)),"Charge volume fraction size mismatch");
            for(real_t fraction:{TCAD_CONST(-0.0),TCAD_CONST(0.0),TCAD_CONST(.25),TCAD_CONST(.5),TCAD_CONST(1.0)}) {
                solver.set_charge_volume_fraction(std::vector<real_t>(3,fraction));
                const auto phi=solve();
                const real_t expected=QE*density*TCAD_CONST(1e-12)*fraction/(TCAD_CONST(2.0)*eps);
                const real_t error=abs_q(phi[1]-expected);
                if(!isfinite_q(error)||error>TCAD_CONST(1e-25))throw std::runtime_error("native fraction Poisson reference mismatch");
                if(error>max_error)max_error=error;
                ++valid_cases;
            }
        }
        std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()
                 <<",\"attempted\":"<<attempted<<",\"rejected\":"<<rejected<<",\"accepted\":"<<accepted
                 <<",\"valid_cases\":"<<valid_cases<<",\"max_phi_error_V\":"<<static_cast<double>(max_error)<<"}\n";
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<e.what()<<'\n';return 1;
    }
}
