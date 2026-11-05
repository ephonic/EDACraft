// Public trap setters: signed sources, independent roots and rejection atomicity.
#include "newton_solver.h"
#include "gummel_solver.h"
#include <algorithm>
#include <cstdio>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
using namespace tcad;
namespace {
void check(bool ok,const char* message) {if(!ok) throw std::runtime_error(message);}
std::string exact(real_t value) {
    char b[128];
#ifdef TCAD_USE_FLOAT128
    quadmath_snprintf(b,sizeof(b),"%Qa",value);
#else
    std::snprintf(b,sizeof(b),"%La",value);
#endif
    return b;
}
}
int main(int argc,char** argv) {
    try {
        const bool observe=argc==2 && std::string(argv[1])=="--observe";
        size_t attempted=0,rejected=0,accepted=0,preserved=0,retries=0,valid=0,controls=0,cleared=0,finite=0;
        real_t worst=TCAD_CONST(0.0);
        const real_t nan=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN()),inf=static_cast<real_t>(std::numeric_limits<double>::infinity());
        const real_t eps=TCAD_CONST(20.0)*EPS0,dit=TCAD_CONST(1e10),energy=TCAD_CONST(.08);
        const Vector zero(3,TCAD_CONST(0.0)),carriers(3,TCAD_CONST(1.0)),dielectric(3,eps),oxide{TCAD_CONST(-2.0),TCAD_CONST(3.0),TCAD_CONST(-1.0)};
        const std::vector<char> mask{0,1,0};
        for(int axis=0;axis<3;++axis) for(bool stretched:{false,true}) for(real_t temperature:{TCAD_CONST(100.0),TCAD_CONST(300.0)}) for(int route=0;route<4;++route) {
            Grid3D grid{1,1,1,TCAD_CONST(2e-9),TCAD_CONST(3e-9),TCAD_CONST(4e-9)};
            const real_t spacing=axis==0?grid.dx:(axis==1?grid.dy:grid.dz);
            Vector x{TCAD_CONST(0.0),spacing,TCAD_CONST(2.0)*spacing};
            if(stretched) x={TCAD_CONST(0.0),TCAD_CONST(.7)*spacing,TCAD_CONST(2.2)*spacing};
            if(axis==0) {grid.nx=3;if(stretched) grid.xx=x;}
            if(axis==1) {grid.ny=3;if(stretched) grid.yx=x;}
            if(axis==2) {grid.nz=3;if(stretched) grid.zx=x;}
            const real_t vt=KB*temperature/QE,dl=x[1]-x[0],dr=x[2]-x[1],width=(dl+dr)/TCAD_CONST(2.0);
            const real_t stiffness=eps*(TCAD_CONST(1.0)/dl+TCAD_CONST(1.0)/dr)/width;
            const real_t linear=TCAD_CONST(.1)*dl/(dl+dr);
            SolverOptions linear_opt;linear_opt.type=SolverType::DENSE_DIRECT;linear_opt.tol=TCAD_CONST(1e-28);
            PoissonSolver poisson(grid);poisson.set_solver_options(linear_opt);poisson.set_permittivity(dielectric);poisson.set_doping(zero);
            poisson.set_dirichlet({{0,TCAD_CONST(0.0)},{2,TCAD_CONST(.1)}});poisson.set_boltzmann_linearization(false,vt);
            GummelOptions go;go.boltzmann_lin=false;go.VT=vt;
            GummelSolver gummel(grid,go);gummel.set_poisson_solver_type(SolverType::DENSE_DIRECT);gummel.set_permittivity(dielectric);gummel.set_doping(zero);
            gummel.set_poisson_dirichlet({{0,TCAD_CONST(0.0)},{2,TCAD_CONST(.1)}});
            NewtonOptions no;no.freeze_n=no.freeze_p=true;no.use_log_space=route==3;no.record_nonlinear_history=true;
            no.temperature=temperature;no.max_iter=80;no.tol=TCAD_CONST(1e-22);no.abs_tol=TCAD_CONST(1e-26);no.linear_tol=TCAD_CONST(1e-28);no.linear_solver=SolverType::DENSE_DIRECT;
            NewtonSolver newton(grid,no);newton.set_permittivity(dielectric);newton.set_mobility(zero,zero);newton.set_doping(zero);newton.set_thermal_voltage(vt);
            newton.set_effective_dos(Vector(3,TCAD_CONST(1e16)),Vector(3,TCAD_CONST(1e16)));newton.set_bandgap(Vector(3,TCAD_CONST(6.0)));
            newton.set_phi_dirichlet({{0,TCAD_CONST(0.0)},{2,TCAD_CONST(.1)}});
            auto set=[&](const std::vector<char>& m,real_t d,real_t e,const Vector& q) {
                if(route==0) {poisson.set_interface_traps(m,d,e);poisson.set_oxide_traps(q);}
                else if(route==1) {gummel.set_interface_traps(m,d,e);gummel.set_oxide_traps(q);}
                else newton.set_trap_charge(m,d,e,q);
            };
            auto solve=[&]() {
                Vector phi{TCAD_CONST(0.0),TCAD_CONST(.03),TCAD_CONST(.1)},n=carriers,p=carriers;
                if(route==0) {poisson.set_leakage_field(phi);poisson.assemble(n,p);check(poisson.solve(phi),"Poisson trap entry solve failed");}
                else if(route==1) check(gummel.recompute_poisson(phi,n,p),"Gummel trap entry solve failed");
                else check(newton.solve(phi,n,p),"Newton trap entry solve failed");
                check(n==carriers && p==carriers,"frozen trap carriers changed");
                Vector state(phi);state.insert(state.end(),n.begin(),n.end());state.insert(state.end(),p.begin(),p.end());return state;
            };
            auto reference=[&](const std::vector<char>& m,real_t d,real_t e,const Vector& q) {
                set(m,d,e,q);const auto state=solve();real_t thickness=spacing;
                if(!m.empty() && std::all_of(m.begin(),m.end(),[](char v){return v!=0;}))
                    thickness=std::min(std::min(grid.nx*grid.dx,grid.ny*grid.dy),grid.nz*grid.dz);
                auto source=[&](real_t phi) {
                    const real_t occupancy=TCAD_CONST(1.0)/(TCAD_CONST(1.0)+exp_q((e-phi)/vt));
                    return (q.empty()?TCAD_CONST(0.0):q[1])-(!m.empty() && m[1]?QE*d*TCAD_CONST(1e4)*(occupancy-TCAD_CONST(.5))/thickness:TCAD_CONST(0.0));
                };
                real_t expected;
                if(route<2) expected=linear+source(TCAD_CONST(.03))/stiffness;
                else {
                    real_t lo=-TCAD_CONST(1.0),hi=TCAD_CONST(1.0);
                    for(int iteration=0;iteration<180;++iteration) {
                        const real_t mid=(lo+hi)/TCAD_CONST(2.0);
                        if(stiffness*(linear-mid)+source(mid)>TCAD_CONST(0.0)) lo=mid;else hi=mid;
                    }
                    expected=(lo+hi)/TCAD_CONST(2.0);
                }
                const real_t error=abs_q(state[1]-expected);worst=std::max(worst,error);
                check(isfinite_q(error) && error<TCAD_CONST(1e-18),"independent trap source/root mismatch");
                check(state[0]==TCAD_CONST(0.0) && state[2]==TCAD_CONST(.1),"trap endpoints changed");
                std::cout<<"{\"case\":"<<++valid<<",\"route\":"<<route<<",\"values\":[";
                for(size_t i=0;i<state.size();++i) std::cout<<(i?",":"")<<'"'<<exact(state[i])<<'"';
                std::cout<<"]}\n";return state;
            };
            const auto control=reference(mask,dit,energy,oxide);
            for(int field=0;field<4;++field) {
                const auto state=reference(field==0?std::vector<char>{}:mask,field==1?dit*TCAD_CONST(2.0):dit,field==2?-energy:energy,field==3?Vector(3,-TCAD_CONST(9.0)):oxide);
                check(abs_q(state[1]-control[1])>TCAD_CONST(1e-9),"trap input is not observable");++controls;
            }
            reference({},TCAD_CONST(0.0),-energy,oxide);
            reference(mask,dit,energy,{});++cleared;
            reference({},TCAD_CONST(0.0),TCAD_CONST(0.0),{});++cleared;
            reference(std::vector<char>(3,1),dit,energy,oxide);
            // Masks are truth-valued char arrays; preserve arbitrary nonzero entries.
            reference(std::vector<char>{0,-1,0},dit,energy,oxide);
            reference(std::vector<char>{0,2,0},dit,energy,oxide);
            reference(mask,TCAD_CONST(-0.0),-energy,Vector(3,TCAD_CONST(-0.0)));
            reference(mask,dit,energy,oxide);
            auto restore=[&]() {set(mask,dit,energy,oxide);};
            auto request=[&](const std::vector<char>& m,real_t d,real_t e,const Vector& q,const std::string& message,bool oxide_only) {
                ++attempted;bool caught=false;const auto history=newton.residuals();const auto samples=newton.nonlinear_samples();
                const auto rhs=poisson.rhs(),vals=poisson.matrix().vals();const auto thickness=poisson.trap_layer_thickness();
                try {
                    if(route==0) {if(oxide_only) poisson.set_oxide_traps(q);else poisson.set_interface_traps(m,d,e);}
                    else if(route==1) {if(oxide_only) gummel.set_oxide_traps(q);else gummel.set_interface_traps(m,d,e);}
                    else newton.set_trap_charge(m,d,e,q);
                }catch(const std::invalid_argument& error) {check(error.what()==message,"wrong trap exception");caught=true;++rejected;}
                if(!caught) ++accepted;
                else {
                    if(route==0) check(poisson.rhs()==rhs && poisson.matrix().vals()==vals && poisson.trap_layer_thickness()==thickness,"rejection changed assembled trap state");
                    if(route>=2) check(newton.residuals()==history && newton.nonlinear_samples()==samples && !history.empty(),"rejection changed Newton trap history");
                    check(solve()==control,"rejected trap input changed next solution");++preserved;
                }
                if(!observe) check(caught,"invalid native trap input was accepted");
                restore();check(solve()==control,"trap valid retry failed");++retries;
            };
            for(size_t length:{size_t(1),size_t(2),size_t(4),size_t(7)}) request(std::vector<char>(length,1),nan,nan,Vector(3,nan),"trap mask size mismatch",false);
            for(real_t d:{-TCAD_CONST(1.0),nan,inf,-inf}) request(std::vector<char>(3,1),d,nan,Vector(3,nan),"interface trap density must be finite and nonnegative",false);
            for(real_t e:{nan,inf,-inf}) request(std::vector<char>(3,1),dit*TCAD_CONST(2.0),e,Vector(3,nan),"interface trap energy must be finite",false);
            for(size_t length:{size_t(1),size_t(2),size_t(4)}) request(std::vector<char>(3,1),dit*TCAD_CONST(2.0),-energy,Vector(length,nan),"oxide trap charge size mismatch",true);
            for(real_t value:{nan,inf,-inf}) for(size_t node=0;node<3;++node) {
                auto q=Vector(3,-TCAD_CONST(8.0));q[node]=value;
                request(std::vector<char>(3,1),dit*TCAD_CONST(2.0),-energy,q,"oxide trap charge must be finite",true);
            }
            // Finite native range is accepted, then restored before any solve.
            for(real_t value:{-TCAD_CONST(0.0),TCAD_CONST(0.0),TCAD_CONST(1e300),TCAD_CONST(1e400)}) {
                set(mask,value,-value,Vector(3,-value));++finite;restore();check(solve()==control,"finite trap restore failed");
            }
        }
        std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()
                 <<",\"attempted\":"<<attempted<<",\"rejected\":"<<rejected<<",\"accepted\":"<<accepted<<",\"preserved\":"<<preserved<<",\"retries\":"<<retries
                 <<",\"valid_cases\":"<<valid<<",\"observable_controls\":"<<controls<<",\"cleared_cases\":"<<cleared<<",\"finite_cases\":"<<finite<<",\"max_phi_error\":"<<static_cast<double>(worst)<<"}\n";
        check(observe || (attempted==rejected && rejected==preserved && !accepted),"trap entry contract failed");return 0;
    }catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
