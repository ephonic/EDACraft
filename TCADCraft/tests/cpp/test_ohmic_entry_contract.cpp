#include "device_simulator.h"
#include <algorithm>
#include <cstdio>
#include <functional>
#include <iostream>
#include <limits>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
using namespace tcad;
namespace {
using Shifts=std::map<size_t,real_t>; using Nodes=std::set<size_t>;
void require(bool ok,const char* message) {if(!ok) throw std::runtime_error(message);}
std::string exact(real_t v) {
    char b[128];
#ifdef TCAD_USE_FLOAT128
    quadmath_snprintf(b,sizeof(b),"%Qa",v);
#else
    std::snprintf(b,sizeof(b),"%La",v);
#endif
    return b;
}
}
int main(int argc,char** argv) {
    try {
        const bool observe=argc==2 && std::string(argv[1])=="--observe";
        size_t attempted=0,rejected=0,accepted=0,preserved=0,retries=0,valid=0,finite=0,observable=0,optional=0,cleared=0;
        real_t max_error=TCAD_CONST(0.0);
        const real_t D=TCAD_CONST(1e16),VT=TCAD_CONST(.02585),eps=TCAD_CONST(20.0)*EPS0;
        const real_t nan=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN()),inf=static_cast<real_t>(std::numeric_limits<double>::infinity());
        const Nodes baseline_nodes{1}; const Shifts baseline_n{{1,TCAD_CONST(.003)}},baseline_p{{1,-TCAD_CONST(.005)}};
        for(int axis=0;axis<3;++axis) for(bool stretched:{false,true}) for(int route=0;route<3;++route) {
            Grid3D grid{1,1,1,TCAD_CONST(1e-6),TCAD_CONST(1e-6),TCAD_CONST(1e-6)};
            if(axis==0) grid.nx=3;
            if(axis==1) grid.ny=3;
            if(axis==2) grid.nz=3;
            Vector positions{TCAD_CONST(0.0),TCAD_CONST(1e-6),TCAD_CONST(2e-6)};
            if(stretched) {
                positions={TCAD_CONST(0.0),TCAD_CONST(.7e-6),TCAD_CONST(2.2e-6)};
                if(axis==0) grid.xx=positions;
                if(axis==1) grid.yx=positions;
                if(axis==2) grid.zx=positions;
            }
            SolverOptions linear; linear.type=SolverType::DENSE_DIRECT; linear.tol=TCAD_CONST(1e-28);
            PoissonSolver poisson(grid); poisson.set_solver_options(linear); poisson.set_permittivity(Vector(3,eps)); poisson.set_doping(Vector(3,TCAD_CONST(0.0))); poisson.set_dirichlet({{0,TCAD_CONST(0.0)},{2,TCAD_CONST(0.0)}}); poisson.set_boltzmann_linearization(false,VT);
            GummelOptions opt; opt.VT=VT; opt.boltzmann_lin=false; GummelSolver gummel(grid,opt); gummel.set_poisson_solver_type(SolverType::DENSE_DIRECT); gummel.set_permittivity(Vector(3,eps)); gummel.set_doping(Vector(3,TCAD_CONST(0.0))); gummel.set_poisson_dirichlet({{0,TCAD_CONST(0.0)},{2,TCAD_CONST(0.0)}});
            DeviceSimulator device(grid.nx,grid.ny,grid.nz,grid.dx,grid.dy,grid.dz);
            if(stretched) {
                if(axis==0) device.set_grid_x(positions);
                if(axis==1) device.set_grid_y(positions);
                if(axis==2) device.set_grid_z(positions);
            }
            device.set_permittivity(Vector(3,eps)); device.set_doping(Vector(3,TCAD_CONST(0.0))); device.set_mobility(Vector(3,TCAD_CONST(.01)),Vector(3,TCAD_CONST(.02)));
            device.set_thermal_voltage(VT); device.set_dirichlet_potential({{0,TCAD_CONST(0.0)},{2,TCAD_CONST(0.0)}});
            const Shifts reservoirs{{0,D},{1,D},{2,D}}; device.set_electron_bc(reservoirs); device.set_hole_bc(reservoirs);
            device.set_effective_dos(Vector(3,D),Vector(3,D)); device.set_bandgap(Vector(3,TCAD_CONST(0.0)));
            device.set_gummel_max_iter(100); device.set_tolerance(TCAD_CONST(1e-20)); device.set_use_newton(false); device.set_poisson_solver_type(static_cast<int>(SolverType::DENSE_DIRECT)); device.set_continuity_solver_type(static_cast<int>(SolverType::DENSE_DIRECT));
            auto setter=[&](const Nodes& nodes,const Shifts& ef_n,const Shifts& ef_p,real_t ni) {
                if(route==0) poisson.set_ohmic_contacts(nodes,ef_n,ef_p,ni);
                if(route==1) gummel.set_ohmic_contacts(nodes,ef_n,ef_p,ni);
                if(route==2) device.set_ohmic_contacts(nodes,ef_n,ef_p,ni);
            };
            auto solve=[&]() {
                Vector phi(3,TCAD_CONST(0.0)),n(3,D),p(3,D);
                if(route==0) {poisson.set_leakage_field(phi); poisson.assemble(n,p); require(poisson.solve(phi),"ohmic Poisson solve failed");}
                if(route==1) require(gummel.recompute_poisson(phi,n,p),"ohmic Gummel Poisson solve failed");
                if(route==2) {
                    device.set_initial_guess(phi,n,p); const auto out=device.solve(); require(out.converged,"ohmic Device solve failed"); phi=out.phi; n=out.n; p=out.p;
                }
                require(n==Vector(3,D) && p==n,"prescribed carriers changed"); Vector state(phi); state.insert(state.end(),n.begin(),n.end()); state.insert(state.end(),p.begin(),p.end()); return state;
            };
            const real_t dl=positions[1]-positions[0],dr=positions[2]-positions[1],stiffness=TCAD_CONST(2.0)*eps/dl/dr;
            auto reference=[&](const Nodes& nodes,const Shifts& ef_n,const Shifts& ef_p,real_t ni) {
                setter(nodes,ef_n,ef_p,ni); const auto state=solve(); real_t target=TCAD_CONST(0.0);
                if(nodes.count(1)) {
                    const real_t en=ef_n.count(1)?ef_n.at(1):TCAD_CONST(0.0),ep=ef_p.count(1)?ef_p.at(1):TCAD_CONST(0.0);
                    if(route<2) target=QE*ni*(exp_q(-ep/VT)-exp_q(-en/VT))/stiffness;
                    else {
                        real_t lo=-TCAD_CONST(.1),hi=TCAD_CONST(.1);
                        for(int i=0;i<180;++i) {const real_t middle=(lo+hi)/TCAD_CONST(2.0),f=stiffness*middle-QE*ni*(exp_q(-(middle+ep)/VT)-exp_q((middle-en)/VT)); if(f>TCAD_CONST(0.0)) hi=middle; else lo=middle;}
                        target=(lo+hi)/TCAD_CONST(2.0);
                    }
                }
                require(state[0]==TCAD_CONST(0.0) && state[2]==TCAD_CONST(0.0),"potential anchors changed"); const real_t error=abs_q(state[1]-target);
                require(isfinite_q(error) && error<TCAD_CONST(1e-18),"independent ohmic electrostatic reference mismatch"); max_error=std::max(max_error,error);
                std::cout<<"{\"case\":"<<++valid<<",\"route\":"<<route<<",\"values\":["; for(size_t i=0;i<9;++i) std::cout<<(i?",":"")<<'"'<<exact(state[i])<<'"'; std::cout<<"]}\n"; return state;
            };
            const auto control=reference(baseline_nodes,baseline_n,baseline_p,D);
            auto restore=[&]() {setter(baseline_nodes,baseline_n,baseline_p,D);};
            for(int field=0;field<4;++field) {
                Nodes nodes=baseline_nodes; Shifts en=baseline_n,ep=baseline_p; real_t ni=D;
                if(field==0) ni=TCAD_CONST(1.5)*D;
                if(field==1) en[1]=TCAD_CONST(.02);
                if(field==2) ep[1]=-TCAD_CONST(.02);
                if(field==3) nodes.clear();
                const auto state=reference(nodes,en,ep,ni); require(abs_q(state[1]-control[1])>TCAD_CONST(1e-8),"ohmic parameter not observable"); ++observable;
            }
            for(const auto& nodes:{Nodes{},Nodes{0},Nodes{1},Nodes{2},Nodes{0,2},Nodes{0,1,2}}) {reference(nodes,baseline_n,baseline_p,D); ++optional; if(nodes.empty()) ++cleared;}
            for(int variant=0;variant<6;++variant) {
                Shifts en=baseline_n,ep=baseline_p; if(variant==0 || variant==2) en.clear(); if(variant==1 || variant==2) ep.clear();
                if(variant==3) {en[0]=TCAD_CONST(.2); ep[2]=-TCAD_CONST(.3);} if(variant==4) en={{0,TCAD_CONST(.2)}}; if(variant==5) ep={{2,-TCAD_CONST(.3)}};
                reference(baseline_nodes,en,ep,D); ++optional;
            }
            require(reference(baseline_nodes,baseline_n,baseline_p,D)==control,"ohmic reference restore failed");
            auto request=[&](const Nodes& nodes,const Shifts& en,const Shifts& ep,real_t ni,int error) {
                ++attempted; bool caught=false; const auto matrix=poisson.matrix().vals(),rhs=poisson.rhs();
                try {setter(nodes,en,ep,ni);} catch(const std::out_of_range& e) {require(error<2 && std::string(e.what())==(error==0?"ohmic contact node is outside the grid":"ohmic quasi-Fermi node is outside the grid"),"wrong ohmic index exception"); caught=true; ++rejected;}
                catch(const std::invalid_argument& e) {require(error>=2 && std::string(e.what())==(error==2?"ohmic quasi-Fermi values must be finite":"ohmic intrinsic density must be finite and positive"),"wrong ohmic value exception"); caught=true; ++rejected;}
                if(!caught) ++accepted;
                else {if(route==0) require(poisson.matrix().vals()==matrix && poisson.rhs()==rhs && !rhs.empty(),"rejected ohmic input changed assembled system"); require(solve()==control,"rejected ohmic input changed next solve"); ++preserved;}
                if(!observe) require(caught,"invalid native ohmic entry was accepted");
                restore(); require(solve()==control,"valid ohmic retry failed"); ++retries;
            };
            for(int field=0;field<3;++field) for(size_t index:{size_t(3),size_t(4),std::numeric_limits<size_t>::max()}) for(real_t ni:{D,nan,TCAD_CONST(0.0)}) {
                Nodes nodes{0}; Shifts en{{0,nan},{1,TCAD_CONST(.02)}},ep{{1,TCAD_CONST(.03)}};
                if(field==0) nodes.insert(index);
                if(field==1) en[index]=TCAD_CONST(.02);
                if(field==2) ep[index]=inf;
                request(nodes,en,ep,ni,field==0?0:1);
            }
            for(int field=0;field<2;++field) for(size_t node=0;node<3;++node) for(real_t value:{nan,inf,-inf}) {Shifts en{{1,TCAD_CONST(.02)}},ep{{1,TCAD_CONST(.03)}}; (field==0?en:ep)[node]=value; request({0},en,ep,D,2);}
            for(real_t ni:{nan,inf,-inf,TCAD_CONST(0.0),-epsilon_q(),-D}) request({0},{{1,TCAD_CONST(.02)}},{{1,TCAD_CONST(.03)}},ni,3);
            Vector shifts{TCAD_CONST(-0.0),TCAD_CONST(0.0),TCAD_CONST(1e300),-TCAD_CONST(1e300)},densities{epsilon_q(),TCAD_CONST(1e300)};
#ifdef TCAD_USE_FLOAT128
            shifts.push_back(TCAD_CONST(1e400)); shifts.push_back(-TCAD_CONST(1e400)); densities.push_back(TCAD_CONST(1e400));
#endif
            for(int field=0;field<2;++field) for(real_t value:shifts) {Shifts en=baseline_n,ep=baseline_p; (field==0?en:ep)[1]=value; setter(baseline_nodes,en,ep,D); ++finite; restore(); require(solve()==control,"finite ohmic shift restore failed");}
            for(real_t ni:densities) {setter(baseline_nodes,baseline_n,baseline_p,ni); ++finite; restore(); require(solve()==control,"finite ohmic density restore failed");}
        }
        std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"attempted\":"<<attempted<<",\"rejected\":"<<rejected<<",\"accepted\":"<<accepted<<",\"preserved\":"<<preserved<<",\"retries\":"<<retries<<",\"valid_cases\":"<<valid<<",\"finite_cases\":"<<finite<<",\"observable_controls\":"<<observable<<",\"optional_cases\":"<<optional<<",\"cleared_cases\":"<<cleared<<",\"max_phi_error\":"<<static_cast<double>(max_error)<<"}\n";
        require(observe || (attempted==rejected && rejected==preserved && !accepted),"ohmic entry contract failed"); return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n'; return 1;}
}
