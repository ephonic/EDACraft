#include "newton_solver.h"
#include <algorithm>
#include <cstdio>
#include <iostream>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>
using namespace tcad;
namespace {
using Boundary=std::map<size_t,real_t>;
void require(bool ok,const char* text) {if(!ok) throw std::runtime_error(text);}
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
        size_t attempted=0,rejected=0,accepted=0,preserved=0,retries=0,valid=0,finite=0,observable=0,optional=0,cleared=0,zero=0;
        real_t max_carrier_error=TCAD_CONST(0.0),max_phi_error=TCAD_CONST(0.0);
        const real_t nan=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN()),inf=static_cast<real_t>(std::numeric_limits<double>::infinity());
        const real_t D=TCAD_CONST(1e16),dt=TCAD_CONST(1e-11),VT=TCAD_CONST(.02585),eps=TCAD_CONST(20.0)*EPS0;
        const Boundary nbc{{0,D},{2,D}},pbc{{0,TCAD_CONST(.8)*D},{2,TCAD_CONST(.8)*D}},phibc{{0,-TCAD_CONST(.01)},{2,TCAD_CONST(.03)}};
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
            NewtonOptions opt;opt.max_iter=80;opt.tol=std::max(TCAD_CONST(1e-22),TCAD_CONST(64.0)*epsilon_q());
            opt.abs_tol=TCAD_CONST(1e-26);opt.linear_tol=TCAD_CONST(1e-28);opt.linear_solver=SolverType::DENSE_DIRECT;
            opt.freeze_phi=true;opt.use_log_space=logarithmic;opt.record_nonlinear_history=true;
            opt.transient_enabled=true;opt.transient_dt=dt;opt.n_prev=Vector(3,TCAD_CONST(3.0)*D);opt.p_prev=Vector(3,TCAD_CONST(2.0)*D);
            NewtonSolver transport(grid,opt);
            NewtonOptions electro=opt;electro.freeze_phi=false;electro.freeze_n=electro.freeze_p=true;electro.transient_enabled=false;
            NewtonSolver charge(grid,electro);
            NewtonOptions frozen=opt;frozen.freeze_n=frozen.freeze_p=true;frozen.transient_enabled=false;
            NewtonSolver checker(grid,frozen);
            auto material=[&](NewtonSolver& s) {
                s.set_permittivity(Vector(3,eps));s.set_doping(Vector(3,TCAD_CONST(0.0)));
                s.set_mobility(Vector(3,TCAD_CONST(.01)),Vector(3,TCAD_CONST(.02)));
                s.set_effective_dos(Vector(3,D),Vector(3,TCAD_CONST(2.0)*D));s.set_bandgap(Vector(3,TCAD_CONST(.015)));
                s.set_recombination(Vector(3,TCAD_CONST(1e-10)),Vector(3,TCAD_CONST(2e-10)));
                s.set_optical_generation(Vector(3,TCAD_CONST(1e26)));s.set_semiconductor_mask(std::vector<char>(3,1));s.set_thermal_voltage(VT);
            };
            material(transport);material(charge);material(checker);
            charge.set_doping(Vector(3,D));charge.set_charge_volume_fraction(Vector(3,TCAD_CONST(.375)));
            const Vector dielectric(3,eps);charge.set_edge_permittivity(dielectric,dielectric,dielectric,dielectric,dielectric,dielectric);
            transport.set_electron_bc(nbc);transport.set_hole_bc(pbc);charge.set_phi_dirichlet(phibc);
            auto solve=[&](NewtonSolver& s,bool charged) {
                Vector phi(3,TCAD_CONST(0.0)),n=charged?Vector(3,TCAD_CONST(1.0)):opt.n_prev,p=charged?n:opt.p_prev;
                require(s.solve(phi,n,p),"native Newton boundary solve failed");
                if(charged) require(n==Vector(3,TCAD_CONST(1.0)) && p==n,"frozen electrostatic carriers changed");
                else if(&s==&transport) require(phi==Vector(3,TCAD_CONST(0.0)),"frozen boundary potential drifted");
                Vector state(phi);state.insert(state.end(),n.begin(),n.end());state.insert(state.end(),p.begin(),p.end());return state;
            };
            const auto control=solve(transport,false),charge_control=solve(charge,true);
            auto emit=[&](const Vector& state) {
                std::cout<<"{\"case\":"<<++valid<<",\"values\":[";
                for(size_t i=0;i<state.size();++i) std::cout<<(i?",":"")<<'"'<<exact(state[i])<<'"';
                std::cout<<"]}\n";
            };
            auto carrier_reference=[&](real_t nb,real_t pb) {
                transport.set_electron_bc({{0,nb},{2,nb}});transport.set_hole_bc({{0,pb},{2,pb}});
                const auto state=solve(transport,false);const real_t dl=positions[1]-positions[0],dr=positions[2]-positions[1],width=(dl+dr)/TCAD_CONST(2.0);
                auto rate=[&](real_t mu) {return VT*TCAD_CONST(2.0)*mu*mu/(TCAD_CONST(2.0)*mu+TCAD_CONST(1e-30))*(TCAD_CONST(1.0)/dl+TCAD_CONST(1.0)/dr)/width;};
                const real_t kn=dt*rate(TCAD_CONST(.01)),kp=dt*rate(TCAD_CONST(.02));
                const real_t an=TCAD_CONST(3.0)+kn*nb/D+TCAD_CONST(.1),ap=TCAD_CONST(2.0)+kp*pb/D+TCAD_CONST(.1),bn=TCAD_CONST(1.0)+kn,bp=TCAD_CONST(1.0)+kp;
                const real_t ni=sqrt_q(TCAD_CONST(2.0))*exp_q(-TCAD_CONST(.015)/(TCAD_CONST(2.0)*TCAD_CONST(8.617333262e-5)*opt.temperature));
                real_t lo=-std::max(std::max(an,ap),TCAD_CONST(10.0)*ni),hi=std::min(an,ap);
                for(int iteration=0;iteration<180;++iteration) {
                    const real_t r=(lo+hi)/TCAD_CONST(2.0),nr=(an-r)/bn,pr=(ap-r)/bp;
                    const real_t rhs=dt*(nr*pr-ni*ni)/(TCAD_CONST(2e-10)*(nr+ni)+TCAD_CONST(1e-10)*(pr+ni));
                    if(r>rhs) hi=r;else lo=r;
                }
                const real_t r=(lo+hi)/TCAD_CONST(2.0);const Vector expected{TCAD_CONST(0.0),TCAD_CONST(0.0),TCAD_CONST(0.0),nb,D*(an-r)/bn,nb,pb,D*(ap-r)/bp,pb};
                for(size_t i=3;i<9;++i) {
                    const real_t error=abs_q((state[i]-expected[i])/D);require(isfinite_q(error) && error<std::max(TCAD_CONST(1e-18),TCAD_CONST(8192.0)*epsilon_q()),"independent boundary BE/SRH reference mismatch");max_carrier_error=std::max(max_carrier_error,error);
                }
                if(nb==TCAD_CONST(0.0)) require(state[3]==TCAD_CONST(0.0) && state[5]==TCAD_CONST(0.0),"zero electron reservoir lost");
                if(pb==TCAD_CONST(0.0)) require(state[6]==TCAD_CONST(0.0) && state[8]==TCAD_CONST(0.0),"zero hole reservoir lost");
                emit(state);return state;
            };
            auto charge_reference=[&](const Boundary& bc) {
                charge.set_phi_dirichlet(bc);const auto state=solve(charge,true);const real_t dl=positions[1]-positions[0],dr=positions[2]-positions[1];
                const Vector expected{bc.at(0),bc.at(0)+(bc.at(2)-bc.at(0))*dl/(dl+dr)+QE*D*TCAD_CONST(.375)*dl*dr/(TCAD_CONST(2.0)*eps),bc.at(2)};
                for(size_t i=0;i<3;++i) {
                    const real_t error=abs_q(state[i]-expected[i]);require(isfinite_q(error) && error<std::max(TCAD_CONST(1e-25),TCAD_CONST(4096.0)*epsilon_q()),"independent potential boundary reference mismatch");max_phi_error=std::max(max_phi_error,error);
                }
                emit(state);return state;
            };
            carrier_reference(D,TCAD_CONST(.8)*D);
            for(int field=0;field<2;++field) {
                const auto state=carrier_reference(field==0?TCAD_CONST(2.0)*D:D,field==1?TCAD_CONST(1.6)*D:TCAD_CONST(.8)*D);
                require(std::max(abs_q((state[4]-control[4])/D),abs_q((state[7]-control[7])/D))>TCAD_CONST(1e-7),"carrier boundary is not observable");++observable;
            }
            for(const auto pair:{std::pair<real_t,real_t>{TCAD_CONST(0.0),TCAD_CONST(.8)*D},{D,TCAD_CONST(0.0)},{TCAD_CONST(0.0),TCAD_CONST(0.0)}}) {carrier_reference(pair.first,pair.second);++zero;}
            carrier_reference(D,TCAD_CONST(.8)*D);
            charge_reference(phibc);const auto changed=charge_reference({{0,-TCAD_CONST(.02)},{2,TCAD_CONST(.06)}});
            require(abs_q(changed[1]-charge_control[1])>TCAD_CONST(1e-4),"potential boundary is not observable");++observable;charge_reference(phibc);
            const Boundary full_phi{{0,-TCAD_CONST(.01)},{1,TCAD_CONST(.02)},{2,TCAD_CONST(.03)}},full_n{{0,D},{1,TCAD_CONST(1.5)*D},{2,D}},full_p{{0,TCAD_CONST(.8)*D},{1,TCAD_CONST(1.25)*D},{2,TCAD_CONST(.8)*D}};
            auto checker_restore=[&]() {checker.set_phi_dirichlet(full_phi);checker.set_electron_bc(full_n);checker.set_hole_bc(full_p);};
            checker_restore();
            for(int field=0;field<3;++field) {
                const real_t value=field==0?-TCAD_CONST(.02):TCAD_CONST(1.5)*D;
                const real_t boundary_value=TCAD_CONST(0.0);
                for(const auto& bc:{Boundary{},Boundary{{0,boundary_value}},Boundary{{1,value}},Boundary{{2,boundary_value}},Boundary{{0,boundary_value},{2,boundary_value}},Boundary{{0,boundary_value},{1,value},{2,boundary_value}}}) {
                    checker_restore();
                    if(field==0) checker.set_phi_dirichlet(bc);
                    if(field==1) checker.set_electron_bc(bc);
                    if(field==2) checker.set_hole_bc(bc);
                    const Boundary* maps[3]={&full_phi,&full_n,&full_p};maps[field]=&bc;
                    const auto state=solve(checker,false);
                    for(size_t block=0;block<3;++block) for(size_t node=0;node<3;++node) {
                        const real_t fallback=block==0?TCAD_CONST(0.0):(block==1?TCAD_CONST(3.0)*D:TCAD_CONST(2.0)*D);
                        const real_t expected=maps[block]->count(node)?maps[block]->at(node):fallback;
                        const real_t scale=block==0?TCAD_CONST(1.0):D,error=abs_q((state[block*3+node]-expected)/scale);
                        require(isfinite_q(error) && error<std::max(TCAD_CONST(1e-18),TCAD_CONST(8192.0)*epsilon_q()),"cleared or partial boundary reference mismatch");
                        if(block>0 && maps[block]->count(node) && expected==TCAD_CONST(0.0)) require(state[block*3+node]==TCAD_CONST(0.0),"partial zero contact lost");
                    }
                    emit(state);++optional;if(bc.empty()) ++cleared;
                }
            }
            require(solve(transport,false)==control && solve(charge,true)==charge_control,"boundary reference restore failed");
            for(int field=0;field<3;++field) {
                NewtonSolver& solver=field==0?charge:transport;const auto& previous=field==0?charge_control:control;
                const std::string name=field==0?"potential":(field==1?"electron":"hole");
                auto setter=[&](const Boundary& bc) {if(field==0) solver.set_phi_dirichlet(bc);else if(field==1) solver.set_electron_bc(bc);else solver.set_hole_bc(bc);};
                auto restore=[&]() {setter(field==0?phibc:(field==1?nbc:pbc));};
                auto request=[&](const Boundary& bc,bool index_error) {
                    ++attempted;bool caught=false;const auto history=solver.residuals();const auto samples=solver.nonlinear_samples();
                    require(!history.empty() && !samples.empty(),"boundary history empty");
                    try {setter(bc);}catch(const std::out_of_range& e) {require(index_error && std::string(e.what())==name+" boundary node is outside the grid","wrong boundary index exception");caught=true;++rejected;}
                    catch(const std::invalid_argument& e) {require(!index_error && std::string(e.what())==name+" boundary value must be finite"+(field==0?"":" and nonnegative"),"wrong boundary value exception");caught=true;++rejected;}
                    if(!caught) ++accepted;
                    else {require(solver.residuals()==history && solver.nonlinear_samples()==samples,"rejected boundary changed history");require(solve(solver,field==0)==previous,"rejected boundary changed next solution");++preserved;}
                    if(!observe) require(caught,"invalid native Newton boundary was accepted");
                    restore();require(solve(solver,field==0)==previous,"boundary valid retry failed");++retries;
                };
                const real_t v=field==0?TCAD_CONST(.04):TCAD_CONST(1.7)*D;
                for(real_t value:{nan,inf,-inf}) for(size_t node=0;node<3;++node) {Boundary bc{{0,v},{1,v},{2,v}};bc[node]=value;request(bc,false);}
                for(size_t node:{size_t(3),size_t(4),std::numeric_limits<size_t>::max()}) for(real_t value:{v,nan,inf}) {Boundary bc{{0,nan},{1,v},{2,v}};bc[node]=value;request(bc,true);}
                if(field) for(real_t value:{-epsilon_q(),-TCAD_CONST(1.0),-TCAD_CONST(1e300)}) for(size_t node=0;node<3;++node) {Boundary bc{{0,v},{1,v},{2,v}};bc[node]=value;request(bc,false);}
                Vector limits{TCAD_CONST(-0.0),TCAD_CONST(0.0),TCAD_CONST(1e300)};
                if(field==0) limits.push_back(-TCAD_CONST(1e300));else limits.push_back(epsilon_q());
#ifdef TCAD_USE_FLOAT128
                limits.push_back(TCAD_CONST(1e400));if(field==0) limits.push_back(-TCAD_CONST(1e400));
#endif
                for(real_t value:limits) {setter({{0,value},{1,value},{2,value}});++finite;restore();require(solve(solver,field==0)==previous,"finite boundary restore failed");}
            }
        }
        std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()
                 <<",\"attempted\":"<<attempted<<",\"rejected\":"<<rejected<<",\"accepted\":"<<accepted<<",\"preserved\":"<<preserved<<",\"retries\":"<<retries
                 <<",\"valid_cases\":"<<valid<<",\"finite_cases\":"<<finite<<",\"observable_controls\":"<<observable<<",\"optional_boundary_cases\":"<<optional<<",\"cleared_boundary_cases\":"<<cleared<<",\"zero_transport_cases\":"<<zero
                 <<",\"max_carrier_error\":"<<static_cast<double>(max_carrier_error)<<",\"max_phi_error\":"<<static_cast<double>(max_phi_error)<<"}\n";
        require(observe || (attempted==rejected && rejected==preserved && !accepted),"boundary contract failed");return 0;
    }catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
