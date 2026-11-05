#include "gummel_solver.h"
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
struct System {
    Vector values,rhs;
    std::vector<size_t> columns,offsets;
    explicit System(const PoissonSolver& solver)
        :values(solver.matrix().vals()),rhs(solver.rhs()),
         columns(solver.matrix().col_indices()),offsets(solver.matrix().row_offsets()) {}
    bool equals(const PoissonSolver& solver) const {
        return values==solver.matrix().vals() && rhs==solver.rhs() &&
               columns==solver.matrix().col_indices() && offsets==solver.matrix().row_offsets();
    }
};
}

int main(int argc,char** argv) {
    try {
        const bool observe=argc==2 && std::string(argv[1])=="--observe";
        size_t attempted=0,rejected=0,accepted=0,preserved=0,polluted=0;
        size_t deferred=0,retries=0,valid=0,finite=0,cache_probes=0;
        real_t max_error=TCAD_CONST(0.0);
        const real_t nan=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN());
        const real_t inf=static_cast<real_t>(std::numeric_limits<double>::infinity());
        for(int axis=0;axis<3;++axis)for(bool stretched:{false,true})for(bool seeded:{false,true}) {
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
            const real_t eps=TCAD_CONST(20.0)*EPS0,fraction=TCAD_CONST(.375),density=TCAD_CONST(1e16);
            const Vector zero(5,TCAD_CONST(0.0)),original(5,density);
            PoissonSolver poisson(grid);
            GummelOptions options;options.enable_quantum=true;options.boltzmann_lin=false;
            options.max_iter=0;options.cont_damping=TCAD_CONST(1.0);options.use_log_damping=false;
            GummelSolver gummel(grid,options);
            poisson.set_permittivity(Vector(5,eps));gummel.set_permittivity(Vector(5,eps));
            poisson.set_charge_volume_fraction(Vector(5,fraction));gummel.set_charge_volume_fraction(Vector(5,fraction));
            poisson.set_dirichlet({{0,TCAD_CONST(0.0)},{4,TCAD_CONST(0.0)}});
            gummel.set_poisson_dirichlet({{0,TCAD_CONST(0.0)},{4,TCAD_CONST(0.0)}});
            gummel.set_mobility(zero,zero);
            gummel.set_density_gradient_potential_form(true);
            const Vector qn=seeded?Vector(5,TCAD_CONST(.001)):Vector{};
            const Vector qp=seeded?Vector(5,TCAD_CONST(-.002)):Vector{};
            auto restore_cache=[&]() {if(seeded)gummel.set_transport_quantum_state(qn,qp);};
            restore_cache();
            auto psolve=[&]() {
                poisson.assemble(zero,zero);Vector phi(zero);
                require(poisson.solve(phi),"native doping Poisson solve failed");return phi;
            };
            auto gsolve=[&]() {
                Vector phi(zero);require(gummel.recompute_poisson(phi,zero,zero),"native doping Gummel Poisson solve failed");return phi;
            };
            auto check_reference=[&](const Vector& phi,real_t doping,const char* route) {
                for(size_t i=0;i<5;++i) {
                    const real_t expected=QE*fraction*doping*x[i]*(x[4]-x[i])/(TCAD_CONST(2.0)*eps);
                    const real_t error=abs_q(phi[i]-expected);
                    require(isfinite_q(error) && error<=TCAD_CONST(4096.0)*epsilon_q()*(TCAD_CONST(1.0)+abs_q(expected)),"independent doping quadratic reference mismatch");
                    if(error>max_error)max_error=error;
                }
                ++valid;
                std::cout<<"{\"case\":"<<valid<<",\"route\":\""<<route<<"\",\"values\":[";
                for(size_t i=0;i<5;++i)std::cout<<(i?",":"")<<'"'<<exact(phi[i])<<'"';
                std::cout<<"]}\n";
            };
            poisson.set_doping(original);gummel.set_doping(original);
            const auto pcontrol=psolve(),gcontrol=gsolve();const System system(poisson);
            require(pcontrol==gcontrol,"native routes disagree at control state");
            auto probe_cache=[&]() {
                Vector phi(gcontrol),n(zero),p(zero);
                const bool solved=gummel.solve(phi,n,p);
                ++cache_probes;
                // A zero-iteration, quantum-enabled request intentionally cannot
                // claim quantum convergence. It exposes the local node-count
                // dependent warm-start cache handling without touching bad data.
                require(!solved,"zero-budget quantum diagnostic unexpectedly accepted");
                return phi==gcontrol && n==zero && p==zero &&
                       gummel.transport_quantum_n()==qn && gummel.transport_quantum_p()==qp;
            };
            require(probe_cache(),"valid control lost its quantum cache");
            auto request=[&](const Vector& bad,bool shape,bool coupled) {
                ++attempted;bool caught=false;
                try {if(coupled)gummel.set_doping(bad);else poisson.set_doping(bad);}
                catch(const std::invalid_argument& e) {
                    require(std::string(e.what())==(shape?"Doping size mismatch":"Doping must be finite"),"wrong native doping exception");caught=true;
                }
                if(!caught)++accepted;
                else {
                    ++rejected;
                    if(observe && coupled && bad.size()>5) {
                        // The legacy local node count is now too large for its
                        // mobility arrays. Restore it before any solve to avoid
                        // intentionally invoking an out-of-bounds read.
                        ++deferred;
                    } else {
                        bool intact;
                        if(coupled)intact=gsolve()==gcontrol && probe_cache();
                        else intact=system.equals(poisson) && psolve()==pcontrol && system.equals(poisson);
                        if(intact)++preserved;else ++polluted;
                        if(!observe)require(intact,"rejected doping changed native state or quantum cache");
                    }
                }
                if(!observe)require(caught,"nonfinite native doping was accepted");
                // Never assemble an accepted legacy NaN/infinity request.
                if(coupled)gummel.set_doping(original);else poisson.set_doping(original);
                restore_cache();
                require(psolve()==pcontrol && gsolve()==gcontrol && probe_cache(),"valid native doping retry failed");
                ++retries;
            };
            for(bool coupled:{false,true}) {
                for(size_t size:{size_t(0),size_t(4),size_t(6)})request(Vector(size,TCAD_CONST(2e16)),true,coupled);
                for(real_t value:{nan,inf,-inf})for(size_t pos=0;pos<5;++pos) {
                    Vector bad(5,TCAD_CONST(-2e16));bad[pos]=value;request(bad,false,coupled);
                }
            }
            for(real_t value:{density,-TCAD_CONST(2e16),TCAD_CONST(0.0),density}) {
                poisson.set_doping(Vector(5,value));gummel.set_doping(Vector(5,value));
                check_reference(psolve(),value,"poisson");check_reference(gsolve(),value,"gummel_poisson");
                require(gummel.transport_quantum_n()==qn && gummel.transport_quantum_p()==qp,"valid replacement changed quantum cache");
            }
            Vector limits{TCAD_CONST(-0.0),TCAD_CONST(0.0),TCAD_CONST(-1e300),TCAD_CONST(1e300)};
#ifdef TCAD_USE_FLOAT128
            limits.push_back(TCAD_CONST(1e400));limits.push_back(TCAD_CONST(-1e400));
#endif
            for(real_t value:limits) {
                require(isfinite_q(value),"finite doping fixture is not finite");
                poisson.set_doping(Vector(5,value));poisson.assemble(zero,zero);
                // This storage probe uses the assembled charge coefficient's
                // operation order; the independent physical reference is above.
                require(poisson.rhs()[2]==(-QE*fraction)*value,"finite doping was narrowed or lost");++finite;
                gummel.set_doping(Vector(5,value));++finite;
            }
            poisson.set_doping(original);gummel.set_doping(original);
            require(psolve()==pcontrol && gsolve()==gcontrol && probe_cache(),"finite-range native doping restore failed");
        }
        std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()
                 <<",\"attempted\":"<<attempted<<",\"rejected\":"<<rejected<<",\"accepted\":"<<accepted
                 <<",\"preserved\":"<<preserved<<",\"polluted\":"<<polluted<<",\"deferred\":"<<deferred
                 <<",\"retries\":"<<retries<<",\"valid_cases\":"<<valid<<",\"finite_cases\":"<<finite
                 <<",\"cache_probes\":"<<cache_probes<<",\"max_reference_error\":"<<static_cast<double>(max_error)<<"}\n";
        require(observe || (rejected==attempted && !accepted && !polluted && !deferred),"native doping contract failed");
        return 0;
    }catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
