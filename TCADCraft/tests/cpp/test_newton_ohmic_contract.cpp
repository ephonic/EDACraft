#include "newton_solver.h"
#include <algorithm>
#include <cstdio>
#include <iostream>
#include <limits>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
using namespace tcad;
namespace {
using Shifts=std::map<size_t,real_t>;
using Nodes=std::set<size_t>;
void require(bool ok,const char* message) {if(!ok) throw std::runtime_error(message);}
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
        size_t attempted=0,rejected=0,accepted=0,preserved=0,retries=0,valid=0,finite=0,observable=0,optional=0,cleared=0;
        real_t max_error=TCAD_CONST(0.0);
        const real_t nan=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN()),inf=static_cast<real_t>(std::numeric_limits<double>::infinity());
        const real_t D=TCAD_CONST(1e16),dt=TCAD_CONST(1e-11),VT=TCAD_CONST(.02585);
        const Nodes baseline_nodes{0,2};
        const Shifts baseline_n{{0,TCAD_CONST(.003)},{2,-TCAD_CONST(.004)}},baseline_p{{0,-TCAD_CONST(.002)},{2,TCAD_CONST(.005)}};
        const Shifts reservoir_n{{0,TCAD_CONST(.9)*D},{2,TCAD_CONST(1.1)*D}},reservoir_p{{0,TCAD_CONST(1.2)*D},{2,TCAD_CONST(.7)*D}};
        for(int axis=0;axis<3;++axis) for(bool stretched:{false,true}) for(bool logarithmic:{false,true}) {
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
            NewtonOptions opt; opt.max_iter=80; opt.tol=std::max(TCAD_CONST(1e-22),TCAD_CONST(64.0)*epsilon_q());
            opt.abs_tol=TCAD_CONST(1e-26); opt.linear_tol=TCAD_CONST(1e-28); opt.linear_solver=SolverType::DENSE_DIRECT;
            opt.freeze_phi=true; opt.use_log_space=logarithmic; opt.record_nonlinear_history=true;
            opt.transient_enabled=true; opt.transient_dt=dt; opt.n_prev=Vector(3,TCAD_CONST(3.0)*D); opt.p_prev=Vector(3,TCAD_CONST(2.0)*D);
            NewtonSolver solver(grid,opt);
            solver.set_permittivity(Vector(3,TCAD_CONST(20.0)*EPS0)); solver.set_doping(Vector(3,TCAD_CONST(0.0)));
            solver.set_mobility(Vector(3,TCAD_CONST(.01)),Vector(3,TCAD_CONST(.02)));
            solver.set_effective_dos(Vector(3,D),Vector(3,TCAD_CONST(2.0)*D)); solver.set_bandgap(Vector(3,TCAD_CONST(.015)));
            solver.set_recombination(Vector(3,TCAD_CONST(1e-10)),Vector(3,TCAD_CONST(2e-10)));
            solver.set_optical_generation(Vector(3,TCAD_CONST(1e26))); solver.set_semiconductor_mask(std::vector<char>(3,1)); solver.set_thermal_voltage(VT);
            solver.set_electron_bc(reservoir_n); solver.set_hole_bc(reservoir_p);
            auto restore=[&]() {solver.set_ohmic_contacts(baseline_nodes,baseline_n,baseline_p,D);};
            auto solve=[&]() {
                Vector phi(3,TCAD_CONST(0.0)),n=opt.n_prev,p=opt.p_prev;
                require(solver.solve(phi,n,p),"native Newton ohmic solve failed"); require(phi==Vector(3,TCAD_CONST(0.0)),"frozen ohmic potential changed");
                Vector state(phi); state.insert(state.end(),n.begin(),n.end()); state.insert(state.end(),p.begin(),p.end()); return state;
            };
            auto reference=[&](const Nodes& nodes,const Shifts& ef_n,const Shifts& ef_p,real_t ni) {
                solver.set_ohmic_contacts(nodes,ef_n,ef_p,ni); const auto state=solve();
                auto target=[&](size_t node,const Shifts& ef,const Shifts& bc) {return nodes.count(node)?ni*exp_q(-(ef.count(node)?ef.at(node):TCAD_CONST(0.0))/VT):bc.at(node);};
                const real_t nl=target(0,ef_n,reservoir_n),nr=target(2,ef_n,reservoir_n),pl=target(0,ef_p,reservoir_p),pr=target(2,ef_p,reservoir_p);
                const real_t dl=positions[1]-positions[0],dr=positions[2]-positions[1],width=(dl+dr)/TCAD_CONST(2.0);
                auto diffusion=[&](real_t mu,real_t length) {return dt*VT*TCAD_CONST(2.0)*mu*mu/(TCAD_CONST(2.0)*mu+TCAD_CONST(1e-30))/length/width;};
                const real_t knl=diffusion(TCAD_CONST(.01),dl),knr=diffusion(TCAD_CONST(.01),dr),kpl=diffusion(TCAD_CONST(.02),dl),kpr=diffusion(TCAD_CONST(.02),dr);
                const real_t an=TCAD_CONST(3.1)+(knl*nl+knr*nr)/D,ap=TCAD_CONST(2.1)+(kpl*pl+kpr*pr)/D,bn=TCAD_CONST(1.0)+knl+knr,bp=TCAD_CONST(1.0)+kpl+kpr;
                const real_t intrinsic=sqrt_q(TCAD_CONST(2.0))*exp_q(-TCAD_CONST(.015)/(TCAD_CONST(2.0)*TCAD_CONST(8.617333262e-5)*opt.temperature));
                real_t lo=-std::max(std::max(an,ap),TCAD_CONST(10.0)*intrinsic),hi=std::min(an,ap);
                for(int iteration=0;iteration<180;++iteration) {
                    const real_t r=(lo+hi)/TCAD_CONST(2.0),n=(an-r)/bn,p=(ap-r)/bp;
                    const real_t rhs=dt*(n*p-intrinsic*intrinsic)/(TCAD_CONST(2e-10)*(n+intrinsic)+TCAD_CONST(1e-10)*(p+intrinsic));
                    if(r>rhs) hi=r; else lo=r;
                }
                const real_t r=(lo+hi)/TCAD_CONST(2.0); const Vector expected{nl,D*(an-r)/bn,nr,pl,D*(ap-r)/bp,pr};
                for(size_t i=0;i<6;++i) {
                    const real_t error=abs_q((state[i+3]-expected[i])/D);
                    require(isfinite_q(error) && error<std::max(TCAD_CONST(1e-18),TCAD_CONST(8192.0)*epsilon_q()),"independent ohmic BE/SRH reference mismatch"); max_error=std::max(max_error,error);
                }
                std::cout<<"{\"case\":"<<++valid<<",\"values\":[";
                for(size_t i=0;i<state.size();++i) std::cout<<(i?",":"")<<'"'<<exact(state[i])<<'"';
                std::cout<<"]}\n"; return state;
            };
            const auto control=reference(baseline_nodes,baseline_n,baseline_p,D);
            for(int field=0;field<4;++field) {
                Nodes nodes=baseline_nodes; Shifts ef_n=baseline_n,ef_p=baseline_p; real_t ni=D;
                if(field==0) ni=TCAD_CONST(1.5)*D;
                if(field==1) ef_n[0]=TCAD_CONST(.02);
                if(field==2) ef_p[2]=-TCAD_CONST(.02);
                if(field==3) nodes={0};
                const auto state=reference(nodes,ef_n,ef_p,ni);
                require(std::max(abs_q((state[4]-control[4])/D),abs_q((state[7]-control[7])/D))>TCAD_CONST(1e-7),"ohmic parameter not observable"); ++observable;
            }
            for(const auto& nodes:{Nodes{},Nodes{0},Nodes{1},Nodes{2},Nodes{0,2},Nodes{0,1,2}}) {
                reference(nodes,baseline_n,baseline_p,D); ++optional; if(nodes.empty()) ++cleared;
            }
            for(int variant=0;variant<6;++variant) {
                Shifts ef_n=baseline_n,ef_p=baseline_p;
                if(variant==0 || variant==2) ef_n.clear();
                if(variant==1 || variant==2) ef_p.clear();
                if(variant==3) {ef_n[1]=-TCAD_CONST(.3); ef_p[1]=TCAD_CONST(.4);}
                if(variant==4) {ef_n.erase(2); ef_p.erase(2);}
                if(variant==5) {ef_n.erase(0); ef_p.erase(0);}
                reference(baseline_nodes,ef_n,ef_p,D); ++optional;
            }
            require(reference(baseline_nodes,baseline_n,baseline_p,D)==control,"ohmic reference restore failed");
            auto request=[&](const Nodes& nodes,const Shifts& ef_n,const Shifts& ef_p,real_t ni,int error) {
                ++attempted; bool caught=false; const auto history=solver.residuals(); const auto samples=solver.nonlinear_samples();
                require(!history.empty() && !samples.empty(),"ohmic history empty");
                try {solver.set_ohmic_contacts(nodes,ef_n,ef_p,ni);}
                catch(const std::out_of_range& e) {require(error<2 && std::string(e.what())==(error==0?"ohmic contact node is outside the grid":"ohmic quasi-Fermi node is outside the grid"),"wrong ohmic index exception"); caught=true; ++rejected;}
                catch(const std::invalid_argument& e) {require(error>=2 && std::string(e.what())==(error==2?"ohmic quasi-Fermi values must be finite":"ohmic intrinsic density must be finite and positive"),"wrong ohmic value exception"); caught=true; ++rejected;}
                if(!caught) ++accepted;
                else {require(solver.residuals()==history && solver.nonlinear_samples()==samples,"rejected ohmic input changed history"); require(solve()==control,"rejected ohmic input changed next solution"); ++preserved;}
                if(!observe) require(caught,"invalid native Newton ohmic input was accepted");
                restore(); require(solve()==control,"ohmic valid retry failed"); ++retries;
            };
            for(int field=0;field<3;++field) for(size_t index:{size_t(3),size_t(4),std::numeric_limits<size_t>::max()}) for(real_t ni:{D,nan,TCAD_CONST(0.0)}) {
                Nodes nodes{0}; Shifts ef_n{{0,nan},{2,TCAD_CONST(.03)}},ef_p{{0,TCAD_CONST(.02)},{2,TCAD_CONST(.04)}};
                if(field==0) nodes.insert(index);
                if(field==1) ef_n[index]=TCAD_CONST(.02);
                if(field==2) ef_p[index]=inf;
                request(nodes,ef_n,ef_p,ni,field==0?0:1);
            }
            for(int field=0;field<2;++field) for(size_t node=0;node<3;++node) for(real_t value:{nan,inf,-inf}) {
                Shifts ef_n{{0,TCAD_CONST(.02)},{2,TCAD_CONST(.03)}},ef_p{{0,TCAD_CONST(.04)},{2,TCAD_CONST(.05)}};
                (field==0?ef_n:ef_p)[node]=value; request({0},ef_n,ef_p,D,2);
            }
            for(real_t ni:{nan,inf,-inf,TCAD_CONST(0.0),-epsilon_q(),-D}) request({0},{{0,TCAD_CONST(.02)}},{{0,TCAD_CONST(.03)}},ni,3);
            Vector shifts{TCAD_CONST(-0.0),TCAD_CONST(0.0),TCAD_CONST(1e300),-TCAD_CONST(1e300)};
            Vector densities{epsilon_q(),TCAD_CONST(1e300)};
#ifdef TCAD_USE_FLOAT128
            shifts.push_back(TCAD_CONST(1e400)); shifts.push_back(-TCAD_CONST(1e400)); densities.push_back(TCAD_CONST(1e400));
#endif
            for(int field=0;field<2;++field) for(real_t value:shifts) {
                Shifts ef_n=baseline_n,ef_p=baseline_p; (field==0?ef_n:ef_p)[0]=value;
                solver.set_ohmic_contacts(baseline_nodes,ef_n,ef_p,D); ++finite; restore(); require(solve()==control,"finite shift restore failed");
            }
            for(real_t ni:densities) {solver.set_ohmic_contacts(baseline_nodes,baseline_n,baseline_p,ni); ++finite; restore(); require(solve()==control,"finite ohmic density restore failed");}
        }
        std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()
                 <<",\"attempted\":"<<attempted<<",\"rejected\":"<<rejected<<",\"accepted\":"<<accepted<<",\"preserved\":"<<preserved<<",\"retries\":"<<retries
                 <<",\"valid_cases\":"<<valid<<",\"finite_cases\":"<<finite<<",\"observable_controls\":"<<observable<<",\"optional_cases\":"<<optional<<",\"cleared_cases\":"<<cleared
                 <<",\"max_carrier_error\":"<<static_cast<double>(max_error)<<"}\n";
        require(observe || (attempted==rejected && rejected==preserved && !accepted),"ohmic input contract failed"); return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n'; return 1;}
}
