#include "newton_solver.h"
#include <algorithm>
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
}
int main(int argc,char** argv) {
    try {
        const bool observe=argc==2 && std::string(argv[1])=="--observe";
        size_t attempted=0,rejected=0,accepted=0,preserved=0,retries=0,valid=0,finite=0,observable=0,optional=0,cut_checks=0;
        real_t max_carrier_error=TCAD_CONST(0.0),max_phi_error=TCAD_CONST(0.0);
        const real_t nan=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN());
        const real_t inf=static_cast<real_t>(std::numeric_limits<double>::infinity());
        const real_t D=TCAD_CONST(1e16),dt=TCAD_CONST(1e-11),VT=TCAD_CONST(.02585),eps=TCAD_CONST(20.0)*EPS0;
        const Vector source(3,TCAD_CONST(1e26)),gap(3,TCAD_CONST(.015)),fraction(3,TCAD_CONST(.375));
        for(int axis=0;axis<3;++axis)for(bool stretched:{false,true})for(bool log_space:{false,true}) {
            Grid3D grid{1,1,1,TCAD_CONST(1e-6),TCAD_CONST(1e-6),TCAD_CONST(1e-6)};
            if(axis==0)grid.nx=3;if(axis==1)grid.ny=3;if(axis==2)grid.nz=3;
            Vector x{TCAD_CONST(0.0),TCAD_CONST(1e-6),TCAD_CONST(2e-6)};
            if(stretched) {
                x={TCAD_CONST(0.0),TCAD_CONST(.7e-6),TCAD_CONST(2.2e-6)};
                if(axis==0)grid.xx=x;if(axis==1)grid.yx=x;if(axis==2)grid.zx=x;
            }
            NewtonOptions opt;opt.max_iter=80;opt.tol=std::max(TCAD_CONST(1e-22),TCAD_CONST(64.0)*epsilon_q());
            opt.abs_tol=TCAD_CONST(1e-26);opt.linear_tol=TCAD_CONST(1e-28);opt.linear_solver=SolverType::DENSE_DIRECT;
            opt.freeze_phi=true;opt.use_log_space=log_space;opt.record_nonlinear_history=true;
            opt.transient_enabled=true;opt.transient_dt=dt;opt.n_prev=Vector(3,TCAD_CONST(3.0)*D);opt.p_prev=Vector(3,TCAD_CONST(2.0)*D);
            NewtonSolver transport(grid,opt);
            NewtonOptions steady=opt;steady.transient_enabled=false;steady.freeze_p=true;NewtonSolver cut(grid,steady);
            NewtonOptions electro=opt;electro.freeze_phi=false;electro.freeze_n=true;electro.freeze_p=true;electro.transient_enabled=false;
            NewtonSolver charge(grid,electro);
            auto material=[&](NewtonSolver& s) {
                s.set_permittivity(Vector(3,eps));s.set_mobility(Vector(3,TCAD_CONST(.01)),Vector(3,TCAD_CONST(.02)));
                s.set_effective_dos(Vector(3,D),Vector(3,TCAD_CONST(2.0)*D));s.set_recombination(Vector(3,TCAD_CONST(1e-10)),Vector(3,TCAD_CONST(2e-10)));
                s.set_semiconductor_mask(std::vector<char>(3,1));
            };
            auto restore_transport=[&]() {transport.set_optical_generation(source);transport.set_bandgap(gap);transport.set_thermal_voltage(VT);};
            material(transport);transport.set_doping(Vector(3,TCAD_CONST(0.0)));restore_transport();
            material(cut);cut.set_doping(Vector(3,TCAD_CONST(0.0)));cut.set_optical_generation(source);cut.set_bandgap(gap);cut.set_thermal_voltage(VT);
            Vector mn(3,TCAD_CONST(.01)),mp(3,TCAD_CONST(.02));mn[0]=mp[0]=TCAD_CONST(0.0);cut.set_mobility(mn,mp);
            cut.set_recombination(Vector(3,TCAD_CONST(1e100)),Vector(3,TCAD_CONST(1e100)));
            for(auto* s:{&transport,&cut}) {s->set_electron_bc({{0,D},{2,D}});s->set_hole_bc({{0,TCAD_CONST(.8)*D},{2,TCAD_CONST(.8)*D}});}
            material(charge);charge.set_bandgap(gap);charge.set_doping(Vector(3,D));
            const Vector dielectric(3,eps);charge.set_edge_permittivity(dielectric,dielectric,dielectric,dielectric,dielectric,dielectric);
            charge.set_phi_dirichlet({{0,TCAD_CONST(0.0)},{2,TCAD_CONST(.02)}});
            charge.set_charge_volume_fraction(fraction);cut.set_charge_volume_fraction(fraction);
            auto solve=[&](NewtonSolver& s,bool charged) {
                Vector phi(3,TCAD_CONST(0.0)),n(charged?Vector(3,TCAD_CONST(1.0)):opt.n_prev),p(charged?n:opt.p_prev);
                require(s.solve(phi,n,p),"native Newton source material solve failed");
                if(charged)require(n==Vector(3,TCAD_CONST(1.0)) && p==n,"frozen charge carriers changed");
                else require(phi==Vector(3,TCAD_CONST(0.0)),"frozen source potential changed");
                Vector state(phi);state.insert(state.end(),n.begin(),n.end());state.insert(state.end(),p.begin(),p.end());return state;
            };
            const auto control=solve(transport,false),cut_control=solve(cut,false),charge_control=solve(charge,true);
            auto emit=[&](const Vector& state) {
                std::cout<<"{\"case\":"<<++valid<<",\"values\":[";
                for(size_t i=0;i<state.size();++i)std::cout<<(i?",":"")<<'"'<<exact(state[i])<<'"';std::cout<<"]}\n";
            };
            auto carrier_reference=[&](NewtonSolver& s,const Vector& g,const Vector& eg,real_t vt,bool clipped,const Vector& f) {
                s.set_optical_generation(g);s.set_bandgap(eg);s.set_thermal_voltage(vt);
                if(clipped)s.set_charge_volume_fraction(f);
                const auto state=solve(s,false);
                const real_t dl=x[1]-x[0],dr=x[2]-x[1];
                const bool legacy=std::any_of(f.begin(),f.end(),[](real_t v){return v>TCAD_CONST(0.0) && v<TCAD_CONST(1.0);});
                const real_t width=clipped && axis!=0 && legacy?dr/TCAD_CONST(2.0):(dl+dr)/TCAD_CONST(2.0);
                auto rate=[&](real_t mu) {
                    const real_t harmonic=TCAD_CONST(2.0)*mu*mu/(mu+mu+TCAD_CONST(1e-30));
                    return vt*harmonic*( (clipped?TCAD_CONST(0.0):TCAD_CONST(1.0)/dl)+TCAD_CONST(1.0)/dr)/width;
                };
                const real_t kn=dt*rate(TCAD_CONST(.01)),kp=dt*rate(TCAD_CONST(.02));
                const real_t generation=g.size()>1?g[1]:TCAD_CONST(0.0),injection=dt*generation/D;
                const real_t storage=clipped?TCAD_CONST(0.0):TCAD_CONST(1.0);
                const real_t an=TCAD_CONST(3.0)*storage+kn+injection,ap=TCAD_CONST(2.0)*storage+TCAD_CONST(.8)*kp+injection;
                const real_t bn=storage+kn,bp=storage+kp;
                const real_t ni=sqrt_q(TCAD_CONST(2.0))*exp_q(-eg[1]/(TCAD_CONST(2.0)*TCAD_CONST(8.617333262e-5)*opt.temperature));
                real_t lo=-std::max(std::max(an,ap),TCAD_CONST(10.0)*ni),hi=std::min(an,ap);
                for(int it=0;it<180;++it) {
                    const real_t r=(lo+hi)/TCAD_CONST(2.0),n=(an-r)/bn,p=clipped?TCAD_CONST(2.0):(ap-r)/bp;
                    const real_t tn=clipped?TCAD_CONST(1e100):TCAD_CONST(1e-10),tp=clipped?TCAD_CONST(1e100):TCAD_CONST(2e-10);
                    const real_t rhs=dt*(n*p-ni*ni)/(tp*(n+ni)+tn*(p+ni));
                    if(r>rhs)hi=r;else lo=r;
                }
                const real_t r=(lo+hi)/TCAD_CONST(2.0),n=(an-r)/bn,p=clipped?TCAD_CONST(2.0):(ap-r)/bp;
                const Vector expected{TCAD_CONST(0.0),TCAD_CONST(0.0),TCAD_CONST(0.0),D,n*D,D,TCAD_CONST(.8)*D,p*D,TCAD_CONST(.8)*D};
                const real_t tolerance=std::max(TCAD_CONST(1e-18),TCAD_CONST(8192.0)*epsilon_q());
                for(size_t i=3;i<state.size();++i) {
                    const real_t error=abs_q((state[i]-expected[i])/D);
                    require(isfinite_q(error) && error<tolerance,"independent source BE/SRH reference mismatch");max_carrier_error=std::max(max_carrier_error,error);
                }
                emit(state);return state;
            };
            auto charge_reference=[&](const Vector& f) {
                charge.set_charge_volume_fraction(f);const auto state=solve(charge,true);
                const real_t dl=x[1]-x[0],dr=x[2]-x[1];
                const Vector expected{TCAD_CONST(0.0),TCAD_CONST(.02)*dl/(dl+dr)+QE*D*f[1]*dl*dr/(TCAD_CONST(2.0)*eps),TCAD_CONST(.02)};
                const real_t tolerance=std::max(TCAD_CONST(1e-25),TCAD_CONST(4096.0)*epsilon_q());
                for(size_t i=0;i<3;++i) {
                    const real_t error=abs_q(state[i]-expected[i]);
                    require(isfinite_q(error) && error<tolerance,"independent fraction charge reference mismatch");max_phi_error=std::max(max_phi_error,error);
                }
                emit(state);return state;
            };
            carrier_reference(transport,source,gap,VT,false,fraction);
            for(int field=0;field<3;++field) {
                const auto next=carrier_reference(transport,field==0?Vector(3,TCAD_CONST(2e26)):source,field==1?Vector(3,TCAD_CONST(.03)):gap,field==2?TCAD_CONST(.04):VT,false,fraction);
                require(std::max(abs_q((next[4]-control[4])/D),abs_q((next[7]-control[7])/D))>TCAD_CONST(1e-7),"source material is not observable");++observable;
            }
            carrier_reference(transport,Vector(3,-TCAD_CONST(1e26)),gap,VT,false,fraction);
            carrier_reference(transport,source,Vector(3,-TCAD_CONST(.01)),VT,false,fraction);
            carrier_reference(transport,source,gap,VT,false,fraction);
            for(size_t size:{size_t(0),size_t(1),size_t(2),size_t(4)}) {carrier_reference(transport,Vector(size,source[0]),gap,VT,false,fraction);++optional;}
            restore_transport();require(solve(transport,false)==control,"source restore failed");
            carrier_reference(cut,source,gap,VT,true,fraction);charge_reference(fraction);
            Vector zero_cut,one_cut,zero_charge,one_charge;
            for(const auto& f:{Vector(3,TCAD_CONST(0.0)),Vector(3,TCAD_CONST(-0.0)),Vector(3,TCAD_CONST(1.0)),Vector(3,TCAD_CONST(.8)),Vector{TCAD_CONST(0.0),TCAD_CONST(.4),TCAD_CONST(1.0)}}) {
                const auto c=carrier_reference(cut,source,gap,VT,true,f),q=charge_reference(f);
                if(f==Vector(3,TCAD_CONST(0.0))) {zero_cut=c;zero_charge=q;}
                if(f==Vector(3,TCAD_CONST(1.0))) {one_cut=c;one_charge=q;}
            }
            // The derived legacy-width flag must also survive rejection.
            const auto fractional_cut=carrier_reference(cut,source,gap,VT,true,fraction);
            charge_reference(fraction);
            require(abs_q(zero_charge[1]-one_charge[1])>TCAD_CONST(1e-10),"charge fraction is not observable");++observable;
            if(axis!=0) {require(abs_q((one_cut[4]-fractional_cut[4])/D)>TCAD_CONST(1e-7),"legacy width flag is not observable");++observable;}
            else require(one_cut==fractional_cut,"x fixture unexpectedly clips legacy width");
            require(zero_cut==one_cut,"nonfractional legacy flag controls disagree");++cut_checks;
            require(solve(cut,false)==cut_control && solve(charge,true)==charge_control,"fraction reference restore failed");
            auto request=[&](NewtonSolver& s,auto setter,auto restore,const Vector& previous,bool charged,const char* message) {
                ++attempted;bool caught=false;
                const auto history=s.residuals();const auto samples=s.nonlinear_samples();
                require(!history.empty() && !samples.empty(),"source material history empty");
                try {setter();}catch(const std::invalid_argument& e) {require(std::string(e.what())==message,"wrong source material exception");caught=true;++rejected;}
                if(!caught)++accepted;
                else {require(s.residuals()==history && s.nonlinear_samples()==samples,"rejected source changed history");require(solve(s,charged)==previous,"rejected source changed next solution");++preserved;}
                if(!observe)require(caught,"invalid native Newton source material was accepted");
                restore();require(solve(s,charged)==previous,"source material valid retry failed");++retries;
            };
            for(real_t value:{nan,inf,-inf}) {
                for(size_t pos=0;pos<3;++pos) {
                    Vector g(3,TCAD_CONST(2e26));g[pos]=value;
                    request(transport,[&](){transport.set_optical_generation(g);},restore_transport,control,false,"optical generation values must be finite");
                    Vector eg(3,TCAD_CONST(.03));eg[pos]=value;
                    request(transport,[&](){transport.set_bandgap(eg);},restore_transport,control,false,"bandgap values must be finite");
                }
                Vector g(4,TCAD_CONST(2e26));g[3]=value;
                request(transport,[&](){transport.set_optical_generation(g);},restore_transport,control,false,"optical generation values must be finite");
            }
            for(size_t size:{size_t(0),size_t(2),size_t(4)}) {
                const Vector eg(size,nan);request(transport,[&](){transport.set_bandgap(eg);},restore_transport,control,false,"bandgap size mismatch");
            }
            for(real_t value:{nan,inf,-inf,TCAD_CONST(-0.0),TCAD_CONST(0.0),-TCAD_CONST(.01),-TCAD_CONST(1e300)})
                request(transport,[&](){transport.set_thermal_voltage(value);},restore_transport,control,false,"thermal voltage must be finite and positive");
            for(int route=0;route<2;++route) {
                NewtonSolver& s=route?cut:charge;const auto& previous=route?cut_control:charge_control;
                auto restore=[&](){s.set_charge_volume_fraction(fraction);};
                for(size_t size:{size_t(0),size_t(2),size_t(4)}) {
                    const Vector f(size,nan);request(s,[&](){s.set_charge_volume_fraction(f);},restore,previous,!route,"charge volume fraction size mismatch");
                }
                for(real_t value:{nan,inf,-inf,-epsilon_q(),TCAD_CONST(1.0)+TCAD_CONST(8.0)*epsilon_q(),-TCAD_CONST(1e300),TCAD_CONST(1e300)})for(size_t pos=0;pos<3;++pos) {
                    Vector f(3,TCAD_CONST(1.0));f[pos]=value;
                    request(s,[&](){s.set_charge_volume_fraction(f);},restore,previous,!route,"charge volume fraction must be in [0,1]");
                }
            }
            Vector limits{TCAD_CONST(-0.0),TCAD_CONST(0.0),-TCAD_CONST(1e300),TCAD_CONST(1e300)};
#ifdef TCAD_USE_FLOAT128
            limits.push_back(-TCAD_CONST(1e400));limits.push_back(TCAD_CONST(1e400));
#endif
            for(real_t value:limits)for(int field=0;field<2;++field) {
                if(field)transport.set_bandgap(Vector(3,value));else transport.set_optical_generation(Vector(3,value));++finite;
                restore_transport();require(solve(transport,false)==control,"finite source restore failed");
            }
            Vector positive{epsilon_q(),TCAD_CONST(1e-300),TCAD_CONST(1e300)};
#ifdef TCAD_USE_FLOAT128
            positive.push_back(TCAD_CONST(1e400));
#endif
            for(real_t value:positive) {transport.set_thermal_voltage(value);++finite;restore_transport();require(solve(transport,false)==control,"finite thermal voltage restore failed");}
        }
        std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()
                 <<",\"attempted\":"<<attempted<<",\"rejected\":"<<rejected<<",\"accepted\":"<<accepted<<",\"preserved\":"<<preserved
                 <<",\"retries\":"<<retries<<",\"valid_cases\":"<<valid<<",\"finite_cases\":"<<finite<<",\"observable_controls\":"<<observable
                 <<",\"optional_generation_cases\":"<<optional<<",\"legacy_width_controls\":"<<cut_checks
                 <<",\"max_carrier_error\":"<<static_cast<double>(max_carrier_error)<<",\"max_phi_error\":"<<static_cast<double>(max_phi_error)<<"}\n";
        require(observe || (attempted==rejected && rejected==preserved && !accepted),"source material contract failed");return 0;
    }catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
