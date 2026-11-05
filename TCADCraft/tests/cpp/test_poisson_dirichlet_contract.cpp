#include "poisson_solver.h"
#include <cstdio>
#include <iostream>
#include <iterator>
#include <limits>
#include <stdexcept>
#include <string>

using namespace tcad;

namespace {
void require(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}

std::string exact_value(real_t value) {
    char buffer[128];
#ifdef TCAD_USE_FLOAT128
    quadmath_snprintf(buffer,sizeof(buffer),"%Qa",value);
#else
    std::snprintf(buffer,sizeof(buffer),"%La",value);
#endif
    return buffer;
}

struct System {
    Vector values, rhs;
    std::vector<size_t> columns, offsets;
    std::vector<char> mask;
    explicit System(const PoissonSolver& solver)
        : values(solver.matrix().vals()), rhs(solver.rhs()),
          columns(solver.matrix().col_indices()), offsets(solver.matrix().row_offsets()),
          mask(solver.dirichlet_mask()) {}
    bool equals(const PoissonSolver& solver) const {
        return values == solver.matrix().vals() && rhs == solver.rhs() &&
               columns == solver.matrix().col_indices() &&
               offsets == solver.matrix().row_offsets() && mask == solver.dirichlet_mask();
    }
};
}

int main(int argc, char** argv) {
    try {
        const bool observe = argc == 2 && std::string(argv[1]) == "--observe";
        size_t attempted=0, rejected=0, accepted=0, polluted=0, preserved=0;
        size_t valid_cases=0, retries=0, clears=0, finite_boundaries=0;
        real_t max_error=TCAD_CONST(0.0);
        const real_t nan=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN());
        const real_t inf=static_cast<real_t>(std::numeric_limits<double>::infinity());
        for (int axis=0; axis<3; ++axis) for (bool stretched:{false,true})
        for (bool thermal:{false,true}) for (bool interior:{false,true}) {
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
            PoissonSolver solver(grid);
            const real_t coefficient=thermal?TCAD_CONST(1.5):EPS0*TCAD_CONST(11.7);
            const real_t source=thermal?TCAD_CONST(3e10):QE*TCAD_CONST(1e16);
            solver.set_permittivity(Vector(5,coefficient));
            solver.set_doping(Vector(5,TCAD_CONST(1e16)));
            const Vector zero(5,TCAD_CONST(0.0)), power(5,source);
            std::map<size_t,real_t> original{{0,thermal?TCAD_CONST(300.0):TCAD_CONST(.2)},
                                           {4,thermal?TCAD_CONST(315.0):TCAD_CONST(-.1)}};
            if(interior)original[2]=thermal?TCAD_CONST(304.0):TCAD_CONST(.07);
            auto assemble=[&]() {
                if(thermal)solver.assemble_thermal(power);
                else solver.assemble(zero,zero);
            };
            auto solution=[&]() {
                Vector phi(5,TCAD_CONST(0.0));
                require(solver.solve(phi),"native Dirichlet solve failed");
                return phi;
            };
            auto reference=[&](const std::map<size_t,real_t>& bc) {
                solver.set_dirichlet(bc);assemble();const auto phi=solution();
                for(size_t i=0;i<5;++i) {
                    real_t expected;
                    auto exact=bc.find(i);
                    if(exact!=bc.end())expected=exact->second;
                    else {
                        const auto right=bc.upper_bound(i), left=std::prev(right);
                        const real_t u=x[i]-x[left->first], length=x[right->first]-x[left->first];
                        expected=left->second+(right->second-left->second)*u/length+
                                 source*u*(length-u)/(TCAD_CONST(2.0)*coefficient);
                    }
                    const real_t error=abs_q(phi[i]-expected);
                    const real_t tolerance=TCAD_CONST(4096.0)*epsilon_q()*(TCAD_CONST(1.0)+abs_q(expected));
                    require(isfinite_q(error)&&error<=tolerance,"independent quadratic Dirichlet reference mismatch");
                    if(error>max_error)max_error=error;
                }
                ++valid_cases;
                std::cout<<"{\"case\":"<<valid_cases<<",\"values\":[";
                for(size_t i=0;i<phi.size();++i)std::cout<<(i?",":"")<<'"'<<exact_value(phi[i])<<'"';
                std::cout<<"]}\n";
                return phi;
            };
            const auto control=reference(original);
            const System state(solver);
            auto request=[&](const std::map<size_t,real_t>& bad,bool index_error) {
                ++attempted;bool caught=false;
                try {solver.set_dirichlet(bad);}
                catch(const std::out_of_range& e) {
                    require(index_error && std::string(e.what())=="Dirichlet index out of bounds","wrong index exception");caught=true;
                }
                catch(const std::invalid_argument& e) {
                    require(!index_error && std::string(e.what())=="Dirichlet values must be finite","wrong finite-value exception");caught=true;
                }
                if(!caught)++accepted;
                else {
                    ++rejected;
                    // Never assemble a legacy request containing NaN or infinity.
                    // Index-only failures have finite values and can be safely rebuilt.
                    bool intact=state.equals(solver);
                    if(intact) {assemble();intact=state.equals(solver)&&solution()==control;}
                    if(intact)++preserved;else ++polluted;
                }
                // A rejected request must leave the old assembled system and mask intact.
                if(!observe)require(caught && state.equals(solver),"invalid Dirichlet request accepted or changed state");
                solver.set_dirichlet(original);assemble();
                require(state.equals(solver)&&solution()==control,"valid Dirichlet retry did not restore the original solution");
                ++retries;
            };
            for(size_t index:{size_t(5),size_t(6),std::numeric_limits<size_t>::max()})
                request({{0,TCAD_CONST(.9)},{index,TCAD_CONST(.1)}},true);
            for(real_t value:{nan,inf,-inf}) for(size_t index:{size_t(0),size_t(2),size_t(4)}) {
                auto bad=original;bad[1]=TCAD_CONST(.11);bad[index]=value;request(bad,false);
            }
            auto replacement=original;
            replacement[0]+=TCAD_CONST(.04);replacement[4]-=TCAD_CONST(.02);
            reference(replacement);
            reference({{0,original.at(0)},{4,original.at(4)}}); // Removes an interior boundary.
            solver.set_dirichlet({});
            require(solver.dirichlet_mask()==std::vector<char>(5,0),"empty boundary map did not clear mask");++clears;
            reference(original);
            // Setter-level range control: finite real_t values are not narrowed to double.
            Vector finite{TCAD_CONST(-0.0),TCAD_CONST(0.0),TCAD_CONST(-1e300),TCAD_CONST(1e300)};
#ifdef TCAD_USE_FLOAT128
            finite.push_back(TCAD_CONST(1e400));finite.push_back(TCAD_CONST(-1e400));
#endif
            for(real_t value:finite) {
                require(isfinite_q(value),"finite-range fixture is not finite");
                solver.set_dirichlet({{0,value},{4,-value}});assemble();
                require(solver.rhs()[0]==value && solver.rhs()[4]==-value,"finite boundary value was narrowed or lost");
                ++finite_boundaries;
            }
            solver.set_dirichlet(original);assemble();require(solution()==control,"finite-range restore changed solution");
        }
        std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()
                 <<",\"attempted\":"<<attempted<<",\"rejected\":"<<rejected<<",\"accepted\":"<<accepted
                 <<",\"polluted\":"<<polluted<<",\"preserved\":"<<preserved<<",\"retries\":"<<retries
                 <<",\"valid_cases\":"<<valid_cases<<",\"clears\":"<<clears<<",\"finite_boundaries\":"<<finite_boundaries
                 <<",\"max_reference_error\":"<<static_cast<double>(max_error)<<"}\n";
        require(observe || (rejected==attempted && !polluted && !accepted),"Dirichlet contract failed");
        return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
