#include "newton_solver.h"
#include <algorithm>
#include <cstdio>
#include <iostream>
#include <stdexcept>
#include <string>
using namespace tcad;
namespace {
void require(bool ok,const char* text) { if(!ok) throw std::runtime_error(text); }
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
        size_t cases=0,passed=0,failed=0,linear_passed=0,log_passed=0;
        real_t max_error=TCAD_CONST(0.0),max_balance=TCAD_CONST(0.0),max_kcl=TCAD_CONST(0.0);
        for(int axis=0;axis<3;++axis) for(bool stretched:{false,true})
        for(bool logarithmic:{false,true}) for(bool weak:{false,true})
        for(bool blocked:{true,false}) for(real_t fraction:{TCAD_CONST(.375),TCAD_CONST(0.0),TCAD_CONST(1.0)})
        for(real_t generation_rate:{TCAD_CONST(1e10),TCAD_CONST(0.0),TCAD_CONST(1e8)})
        for(real_t D:{TCAD_CONST(1e16),TCAD_CONST(1e10),TCAD_CONST(1e24)}) {
            ++cases;
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
            const real_t VT=TCAD_CONST(.02585),Eg=TCAD_CONST(.015);
            const real_t tn=weak?TCAD_CONST(1e100):TCAD_CONST(1e-10),tp=weak?TCAD_CONST(1e100):TCAD_CONST(2e-10);
            NewtonOptions opt;opt.max_iter=80;opt.tol=std::max(TCAD_CONST(1e-22),TCAD_CONST(64.0)*epsilon_q());
            opt.abs_tol=TCAD_CONST(1e-26);opt.linear_tol=TCAD_CONST(1e-28);opt.linear_solver=SolverType::DENSE_DIRECT;
            opt.freeze_phi=true;opt.use_log_space=logarithmic;opt.record_nonlinear_history=true;
            // Stale transient arrays must not set a steady residual scale.
            opt.n_prev=Vector(3,TCAD_CONST(1e100));opt.p_prev=opt.n_prev;
            NewtonSolver solver(grid,opt);
            solver.set_permittivity(Vector(3,TCAD_CONST(20.0)*EPS0));solver.set_doping(Vector(3,TCAD_CONST(0.0)));
            Vector mn(3,TCAD_CONST(.01)),mp(3,TCAD_CONST(.02));
            if(blocked) mn[0]=mp[0]=TCAD_CONST(0.0);
            solver.set_mobility(mn,mp);solver.set_recombination(Vector(3,tn),Vector(3,tp));
            solver.set_effective_dos(Vector(3,D),Vector(3,TCAD_CONST(2.0)*D));solver.set_bandgap(Vector(3,Eg));
            solver.set_optical_generation(Vector(3,generation_rate*D));solver.set_semiconductor_mask(std::vector<char>(3,1));
            solver.set_charge_volume_fraction(Vector(3,fraction));solver.set_thermal_voltage(VT);
            solver.set_electron_bc({{0,D},{2,D}});solver.set_hole_bc({{0,TCAD_CONST(.8)*D},{2,TCAD_CONST(.8)*D}});
            Vector phi(3,TCAD_CONST(0.0)),n(3,TCAD_CONST(3.0)*D),p(3,TCAD_CONST(2.0)*D);
            const bool ok=solver.solve(phi,n,p);
            if(ok) {
                ++passed;if(logarithmic) ++log_passed;else ++linear_passed;
                require(phi==Vector(3,TCAD_CONST(0.0)),"steady frozen potential drifted");
                require(!solver.residuals().empty() && !solver.nonlinear_samples().empty(),"steady history missing");
                const real_t dl=positions[1]-positions[0],dr=positions[2]-positions[1];
                const real_t width=blocked && axis!=0 && fraction>TCAD_CONST(0.0) && fraction<TCAD_CONST(1.0)
                    ?dr/TCAD_CONST(2.0):(dl+dr)/TCAD_CONST(2.0);
                auto harmonic=[](real_t mu) { return TCAD_CONST(2.0)*mu*mu/(TCAD_CONST(2.0)*mu+TCAD_CONST(1e-30)); };
                auto rate=[&](real_t mu) { return VT*harmonic(mu)*((blocked?TCAD_CONST(0.0):TCAD_CONST(1.0)/dl)+TCAD_CONST(1.0)/dr)/width; };
                const real_t rn=rate(TCAD_CONST(.01)),rp=rate(TCAD_CONST(.02)),dt=TCAD_CONST(1e-11);
                const real_t kn=dt*rn,kp=dt*rp,an=kn+dt*generation_rate,ap=TCAD_CONST(.8)*kp+dt*generation_rate;
                const real_t ni=sqrt_q(TCAD_CONST(2.0))*exp_q(-Eg/(TCAD_CONST(2.0)*TCAD_CONST(8.617333262e-5)*opt.temperature));
                real_t lo=-std::max(std::max(an,ap),TCAD_CONST(10.0)*ni),hi=std::min(an,ap);
                for(int iteration=0;iteration<180;++iteration) {
                    const real_t r=(lo+hi)/TCAD_CONST(2.0),nr=(an-r)/kn,pr=(ap-r)/kp;
                    const real_t rhs=dt*(nr*pr-ni*ni)/(tp*(nr+ni)+tn*(pr+ni));
                    if(r>rhs) hi=r;else lo=r;
                }
                const real_t r=(lo+hi)/TCAD_CONST(2.0);
                const Vector expected_n{D,D*(an-r)/kn,D},expected_p{TCAD_CONST(.8)*D,D*(ap-r)/kp,TCAD_CONST(.8)*D};
                for(size_t i=0;i<3;++i) {
                    const real_t error=std::max(abs_q((n[i]-expected_n[i])/D),abs_q((p[i]-expected_p[i])/D));
                    require(isfinite_q(error) && error<std::max(TCAD_CONST(1e-18),TCAD_CONST(8192.0)*epsilon_q()),"independent steady SRH/diffusion reference mismatch");
                    max_error=std::max(max_error,error);
                }
                const real_t nr=n[1]/D,pr=p[1]/D,R=(nr*pr-ni*ni)/(tp*(nr+ni)+tn*(pr+ni));
                for(real_t transport:{rn*(nr-TCAD_CONST(1.0)),rp*(pr-TCAD_CONST(.8))}) {
                    const real_t balance=abs_q(transport+R-generation_rate)/(abs_q(transport)+abs_q(R)+generation_rate+TCAD_CONST(1.0));
                    require(isfinite_q(balance) && balance<std::max(TCAD_CONST(1e-18),TCAD_CONST(8192.0)*epsilon_q()),"steady continuity balance mismatch");
                    max_balance=std::max(max_balance,balance);
                }
                // A zero-current equilibrium has no usable relative-current
                // denominator. Normalize by the local thermal transport scale
                // as well as the actual electron/hole flux magnitudes.
                real_t current[2],scale=VT*(harmonic(TCAD_CONST(.01))+harmonic(TCAD_CONST(.02)))*D/std::min(dl,dr);
                for(size_t edge=0;edge<2;++edge) {
                    const real_t d=positions[edge+1]-positions[edge];
                    const real_t en=blocked && edge==0?TCAD_CONST(0.0):VT*harmonic(TCAD_CONST(.01))*(n[edge+1]-n[edge])/d;
                    const real_t hp=blocked && edge==0?TCAD_CONST(0.0):VT*harmonic(TCAD_CONST(.02))*(p[edge]-p[edge+1])/d;
                    current[edge]=en+hp;scale=std::max(scale,abs_q(en)+abs_q(hp));
                }
                const real_t kcl=abs_q(current[1]-current[0])/scale;
                require(isfinite_q(kcl) && kcl<std::max(TCAD_CONST(1e-18),TCAD_CONST(8192.0)*epsilon_q()),"independent steady pair KCL mismatch");
                max_kcl=std::max(max_kcl,kcl);
            } else { ++failed;require(observe,"steady linear-density solve did not converge"); }
            std::cout<<"{\"case\":"<<cases<<",\"axis\":"<<axis<<",\"stretched\":"<<stretched<<",\"logarithmic\":"<<logarithmic
                     <<",\"weak\":"<<weak<<",\"blocked\":"<<blocked<<",\"fraction\":\""<<exact(fraction)<<"\",\"generation_rate\":\""<<exact(generation_rate)
                     <<"\",\"density\":\""<<exact(D)<<"\",\"converged\":"<<ok<<",\"values\":[";
            Vector state(phi);state.insert(state.end(),n.begin(),n.end());state.insert(state.end(),p.begin(),p.end());
            for(size_t i=0;i<state.size();++i) std::cout<<(i?",":"")<<'"'<<exact(state[i])<<'"';
            std::cout<<"]}\n";
        }
        std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()
                 <<",\"cases\":"<<cases<<",\"passed\":"<<passed<<",\"failed\":"<<failed<<",\"linear_passed\":"<<linear_passed<<",\"log_passed\":"<<log_passed
                 <<",\"max_reference_error\":"<<static_cast<double>(max_error)<<",\"max_continuity_error\":"<<static_cast<double>(max_balance)<<",\"max_pair_kcl_error\":"<<static_cast<double>(max_kcl)<<"}\n";
        require(cases==1296,"steady fixture count mismatch");return 0;
    } catch(const std::exception& e) { std::cerr<<e.what()<<'\n';return 1; }
}
