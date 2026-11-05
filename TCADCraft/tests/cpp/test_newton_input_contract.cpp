#include "newton_solver.h"
#include <algorithm>
#include <cstdio>
#include <iostream>
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
void invoke(NewtonSolver& solver,int entry,Vector& phi,Vector& n,Vector& p) {
    if(entry==0) check(solver.solve(phi,n,p),"Newton input reference solve failed");
    else if(entry==1) (void)solver.debug_fd_jacobian_check(phi,n,p);
    else solver.debug_solve_probe(phi,n,p);
}
}
int main(int argc,char** argv) {
    try {
        const bool references=argc==2 && std::string(argv[1])=="--references";
        const bool child=argc==5 && std::string(argv[1])=="--missing";
        const int child_entry=child?std::stoi(argv[2]):-1,child_material=child?std::stoi(argv[3]):-1,child_log=child?std::stoi(argv[4]):-1;
        size_t rejected=0,retries=0,valid=0,material_rejected=0,state_rejected=0,debug_valid=0;
        real_t worst=TCAD_CONST(0.0);
        for(int axis=0;axis<(child?1:3);++axis) for(bool stretched:{false,true}) for(bool logarithmic:{false,true}) {
            if(child && (stretched || logarithmic!=bool(child_log))) continue;
            Grid3D grid{1,1,1,TCAD_CONST(1e-6),TCAD_CONST(1e-6),TCAD_CONST(1e-6)};
            Vector x{TCAD_CONST(0.0),TCAD_CONST(1e-6),TCAD_CONST(2e-6)};
            if(stretched) x={TCAD_CONST(0.0),TCAD_CONST(.7e-6),TCAD_CONST(2.2e-6)};
            if(axis==0) {grid.nx=3;if(stretched) grid.xx=x;}
            if(axis==1) {grid.ny=3;if(stretched) grid.yx=x;}
            if(axis==2) {grid.nz=3;if(stretched) grid.zx=x;}
            const real_t eps=TCAD_CONST(20.0)*EPS0;
            NewtonOptions opt;opt.freeze_n=opt.freeze_p=true;opt.use_log_space=logarithmic;opt.record_nonlinear_history=true;
            opt.max_iter=80;opt.tol=TCAD_CONST(1e-22);opt.abs_tol=TCAD_CONST(1e-26);opt.linear_tol=TCAD_CONST(1e-28);opt.linear_solver=SolverType::DENSE_DIRECT;
            auto basic=[&](NewtonSolver& solver) {
                solver.set_permittivity(Vector(3,eps));solver.set_mobility(Vector(3,TCAD_CONST(0.0)),Vector(3,TCAD_CONST(0.0)));solver.set_doping(Vector(3,TCAD_CONST(0.0)));
                solver.set_phi_dirichlet({{0,-TCAD_CONST(.01)},{2,TCAD_CONST(.03)}});solver.set_trap_charge({},TCAD_CONST(0.0),TCAD_CONST(0.0),Vector(3,TCAD_CONST(3.0)));
                solver.set_electron_bc({{0,TCAD_CONST(1.0)},{1,TCAD_CONST(1.0)},{2,TCAD_CONST(1.0)}});solver.set_hole_bc({{0,TCAD_CONST(1.0)},{1,TCAD_CONST(1.0)},{2,TCAD_CONST(1.0)}});
            };
            auto dos=[](NewtonSolver& solver) {solver.set_effective_dos(Vector(3,TCAD_CONST(1e16)),Vector(3,TCAD_CONST(1e16)));};
            auto gap=[](NewtonSolver& solver) {solver.set_bandgap(Vector(3,TCAD_CONST(6.0)));};
            auto cold=[&](NewtonSolver& solver) {
                Vector phi(3,TCAD_CONST(0.0)),n(3,TCAD_CONST(1.0)),p=n;invoke(solver,0,phi,n,p);
                Vector out(phi);out.insert(out.end(),n.begin(),n.end());out.insert(out.end(),p.begin(),p.end());return out;
            };
            if(child) {
                NewtonSolver solver(grid,opt);basic(solver);
                if(child_material==1) dos(solver);
                if(child_material==2) gap(solver);
                Vector phi(3,TCAD_CONST(0.0)),n(3,TCAD_CONST(1.0)),p=n;
                invoke(solver,child_entry,phi,n,p);throw std::runtime_error("missing native material was not rejected");
            }
            NewtonSolver solver(grid,opt);basic(solver);dos(solver);gap(solver);
            const auto control=cold(solver);const real_t dl=x[1]-x[0],dr=x[2]-x[1];
            const real_t expected=-TCAD_CONST(.01)+TCAD_CONST(.04)*dl/(dl+dr)+TCAD_CONST(3.0)*dl*dr/(TCAD_CONST(2.0)*eps);
            const real_t error=abs_q(control[1]-expected);worst=std::max(worst,error);check(error<TCAD_CONST(1e-18),"independent input Poisson reference mismatch");
            check(control[0]==-TCAD_CONST(.01) && control[2]==TCAD_CONST(.03),"Newton input endpoints changed");
            check(std::all_of(control.begin()+3,control.end(),[](real_t v){return v==TCAD_CONST(1.0);}),"Newton input frozen carriers changed");
            std::cout<<"{\"case\":"<<++valid<<",\"values\":[";
            for(size_t i=0;i<control.size();++i) std::cout<<(i?",":"")<<'"'<<exact(control[i])<<'"';
            std::cout<<"]}\n";
            if(references) continue;
            for(int entry=0;entry<3;++entry) {
                for(int state=0;state<3;++state) for(size_t length:{size_t(0),size_t(1),size_t(2),size_t(4),size_t(6)}) {
                    Vector phi(3,TCAD_CONST(0.0)),n(3,TCAD_CONST(1.0)),p=n;
                    (state==0?phi:(state==1?n:p)).assign(length,TCAD_CONST(.02));
                    const auto before_phi=phi,before_n=n,before_p=p,history=solver.residuals();const auto samples=solver.nonlinear_samples();bool caught=false;
                    try {invoke(solver,entry,phi,n,p);}catch(const std::invalid_argument& e) {check(std::string(e.what())=="Newton state size mismatch","wrong state shape exception");caught=true;}
                    check(caught,"invalid Newton state size was accepted");++rejected;++state_rejected;
                    check(phi==before_phi && n==before_n && p==before_p && solver.residuals()==history && solver.nonlinear_samples()==samples,"invalid state changed caller or history");
                    check(cold(solver)==control,"state shape retry drifted");++retries;
                }
                for(int material=0;material<3;++material) {
                    NewtonSolver partial(grid,opt);basic(partial);if(material==1) dos(partial);if(material==2) gap(partial);
                    Vector phi(3,TCAD_CONST(0.0)),n(3,TCAD_CONST(1.0)),p=n;const auto before_phi=phi,before_n=n,before_p=p;bool caught=false;
                    try {invoke(partial,entry,phi,n,p);}catch(const std::invalid_argument& e) {
                        check(std::string(e.what())==(material==1?"Newton bandgap is not initialized":"Newton effective density of states is not initialized"),"wrong material initialization exception");caught=true;
                    }
                    check(caught,"missing native material was not rejected");++rejected;++material_rejected;
                    check(phi==before_phi && n==before_n && p==before_p && partial.residuals().empty() && partial.nonlinear_samples().empty(),"missing material changed state");
                    dos(partial);gap(partial);check(cold(partial)==control,"material initialization retry drifted");++retries;
                }
            }
            Vector phi(control.begin(),control.begin()+3),n(3,TCAD_CONST(1.0)),p=n;
            check(solver.debug_fd_jacobian_check(phi,n,p)==0,"valid initialized Jacobian probe failed");++debug_valid;
            solver.debug_solve_probe(phi,n,p);++debug_valid;check(cold(solver)==control,"valid initialized probe changed solution");
        }
        std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"valid_cases\":"<<valid
                 <<",\"rejected\":"<<rejected<<",\"state_rejected\":"<<state_rejected<<",\"material_rejected\":"<<material_rejected<<",\"retries\":"<<retries<<",\"debug_valid\":"<<debug_valid<<",\"max_phi_error\":"<<static_cast<double>(worst)<<"}\n";return 0;
    }catch(const std::invalid_argument& error) {
        if(argc==5 && std::string(argv[1])=="--missing") {std::cout<<error.what()<<'\n';return 0;}
        std::cerr<<error.what()<<'\n';return 1;
    }catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
