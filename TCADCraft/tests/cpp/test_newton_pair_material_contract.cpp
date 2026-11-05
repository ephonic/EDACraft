#include "newton_solver.h"
#include <algorithm>
#include <array>
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
using Parameters=std::array<Vector,6>; // mu_n,mu_p,tau_n,tau_p,Nc,Nv
}
int main(int argc,char** argv) {
    try {
        const bool observe=argc==2 && std::string(argv[1])=="--observe";
        size_t attempted=0,rejected=0,accepted=0,preserved=0,retries=0,valid=0,finite=0,observable=0,optional=0;
        real_t max_error=TCAD_CONST(0.0);
        const real_t nan=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN());
        const real_t inf=static_cast<real_t>(std::numeric_limits<double>::infinity());
        for(int axis=0;axis<3;++axis)for(bool stretched:{false,true})for(bool log_space:{false,true}) {
            Grid3D grid{1,1,1,TCAD_CONST(1e-6),TCAD_CONST(1e-6),TCAD_CONST(1e-6)};
            if(axis==0)grid.nx=3;if(axis==1)grid.ny=3;if(axis==2)grid.nz=3;
            Vector x{TCAD_CONST(0.0),TCAD_CONST(1e-6),TCAD_CONST(2e-6)};
            if(stretched) {
                x={TCAD_CONST(0.0),TCAD_CONST(.7e-6),TCAD_CONST(2.2e-6)};
                if(axis==0)grid.xx=x;if(axis==1)grid.yx=x;if(axis==2)grid.zx=x;
            }
            const real_t D=TCAD_CONST(1e16),dt=TCAD_CONST(1e-11),VT=TCAD_CONST(.02585);
            NewtonOptions opt;opt.max_iter=80;opt.tol=std::max(TCAD_CONST(1e-22),TCAD_CONST(64.0)*epsilon_q());
            opt.abs_tol=TCAD_CONST(1e-26);opt.linear_tol=TCAD_CONST(1e-28);opt.linear_solver=SolverType::DENSE_DIRECT;
            opt.freeze_phi=true;opt.use_log_space=log_space;opt.record_nonlinear_history=true;
            opt.transient_enabled=true;opt.transient_dt=dt;opt.n_prev=Vector(3,TCAD_CONST(3.0)*D);opt.p_prev=Vector(3,TCAD_CONST(2.0)*D);
            NewtonSolver solver(grid,opt);
            solver.set_doping(Vector(3,TCAD_CONST(0.0)));solver.set_bandgap(Vector(3,TCAD_CONST(0.0)));
            solver.set_thermal_voltage(VT);solver.set_semiconductor_mask(std::vector<char>(3,1));
            solver.set_electron_bc({{0,D},{2,D}});solver.set_hole_bc({{0,TCAD_CONST(.8)*D},{2,TCAD_CONST(.8)*D}});
            const Parameters original{Vector(3,TCAD_CONST(.01)),Vector(3,TCAD_CONST(.02)),Vector(3,TCAD_CONST(1e-10)),Vector(3,TCAD_CONST(2e-10)),Vector(3,D),Vector(3,TCAD_CONST(2.0)*D)};
            Parameters changed=original;
            for(int slot=0;slot<6;++slot)for(auto& v:changed[slot])v*=TCAD_CONST(1.7);
            auto set_pair=[&](const Parameters& p,int family) {
                if(family==0)solver.set_mobility(p[0],p[1]);
                if(family==1)solver.set_recombination(p[2],p[3]);
                if(family==2)solver.set_effective_dos(p[4],p[5]);
            };
            auto configure=[&](const Parameters& p) {for(int family=0;family<3;++family)set_pair(p,family);};
            auto solve=[&]() {
                Vector phi(3,TCAD_CONST(0.0)),n(opt.n_prev),p(opt.p_prev);
                require(solver.solve(phi,n,p),"native Newton paired material solve failed");
                require(phi==Vector(3,TCAD_CONST(0.0)),"frozen potential changed");
                Vector state(phi);state.insert(state.end(),n.begin(),n.end());state.insert(state.end(),p.begin(),p.end());return state;
            };
            configure(original);const auto control=solve();
            auto reference=[&](const Parameters& material) {
                configure(material);const auto state=solve();
                const real_t dl=x[1]-x[0],dr=x[2]-x[1],width=(dl+dr)/TCAD_CONST(2.0);
                auto rate=[&](const Vector& mu) {
                    const real_t a=TCAD_CONST(2.0)*mu[0]*mu[1]/(mu[0]+mu[1]+TCAD_CONST(1e-30));
                    const real_t b=TCAD_CONST(2.0)*mu[1]*mu[2]/(mu[1]+mu[2]+TCAD_CONST(1e-30));
                    return VT*(a/dl+b/dr)/width;
                };
                const real_t kn=dt*rate(material[0]),kp=dt*rate(material[1]);
                const real_t an=TCAD_CONST(3.0)+kn,ap=TCAD_CONST(2.0)+TCAD_CONST(.8)*kp;
                const real_t bn=TCAD_CONST(1.0)+kn,bp=TCAD_CONST(1.0)+kp;
                const real_t ni=sqrt_q(material[4][1]/D)*sqrt_q(material[5][1]/D);
                const real_t tn=material[2].size()>1?material[2][1]:TCAD_CONST(1e100);
                const real_t tp=material[3].size()>1?material[3][1]:TCAD_CONST(1e100);
                // Both carrier balances share one SRH rate. Eliminate their
                // densities and bisect this scalar, monotone balance; do not
                // call production SRH, intrinsic-density, or Newton helpers.
                real_t lo=-std::max(std::max(an,ap),TCAD_CONST(10.0)*ni),hi=std::min(an,ap);
                for(int it=0;it<180;++it) {
                    const real_t r=(lo+hi)/TCAD_CONST(2.0),n=(an-r)/bn,p=(ap-r)/bp;
                    const real_t rhs=dt*(n*p-ni*ni)/(tp*(n+ni)+tn*(p+ni));
                    if(r>rhs)hi=r;else lo=r;
                }
                const real_t r=(lo+hi)/TCAD_CONST(2.0),n=(an-r)/bn,p=(ap-r)/bp;
                Vector expected{TCAD_CONST(0.0),TCAD_CONST(0.0),TCAD_CONST(0.0),D,n*D,D,TCAD_CONST(.8)*D,p*D,TCAD_CONST(.8)*D};
                const real_t tolerance=std::max(TCAD_CONST(1e-18),TCAD_CONST(8192.0)*epsilon_q());
                for(size_t i=0;i<state.size();++i) {
                    const real_t error=abs_q((state[i]-expected[i])/D);
                    require(isfinite_q(error) && error<tolerance,"independent paired material BE/SRH reference mismatch");
                    max_error=std::max(max_error,error);
                }
                std::cout<<"{\"case\":"<<++valid<<",\"values\":[";
                for(size_t i=0;i<state.size();++i)std::cout<<(i?",":"")<<'"'<<exact(state[i])<<'"';std::cout<<"]}\n";
                return state;
            };
            reference(original);
            for(int slot=0;slot<6;++slot) {
                Parameters material=original;material[slot]=changed[slot];const auto next=reference(material);
                require(std::max(abs_q((next[4]-control[4])/D),abs_q((next[7]-control[7])/D))>TCAD_CONST(1e-7),"paired material is not observable");++observable;
            }
            reference(changed);reference(original);configure(original);require(solve()==control,"paired control restore failed");
            auto request=[&](const Parameters& bad,int family,bool shape) {
                ++attempted;bool caught=false;
                const auto history=solver.residuals();const auto samples=solver.nonlinear_samples();
                require(!history.empty() && !samples.empty(),"paired material history is empty");
                const std::string label=family==0?"mobility":family==1?"recombination lifetime":"effective DOS";
                try {set_pair(bad,family);}
                catch(const std::invalid_argument& e) {
                    require(e.what()==label+(shape?" size mismatch":" values must be finite"),"wrong paired material exception");caught=true;++rejected;
                }
                if(!caught)++accepted;
                else {
                    require(solver.residuals()==history && solver.nonlinear_samples()==samples,"rejected paired material changed history");
                    require(solve()==control,"rejected paired material changed next solution");++preserved;
                }
                if(!observe)require(caught,"invalid native Newton paired material was accepted");
                configure(original);require(solve()==control,"paired material valid retry failed");++retries;
            };
            for(int family=0;family<3;++family)for(int member=0;member<2;++member) {
                const int slot=2*family+member;
                if(family!=1)for(size_t size:{size_t(0),size_t(2),size_t(4)}) {
                    Parameters bad=changed;if(member)bad[2*family][0]=nan;
                    bad[slot].assign(size,nan);request(bad,family,true);
                }
                for(real_t value:{nan,inf,-inf})for(size_t pos=0;pos<3;++pos) {
                    Parameters bad=changed;bad[slot][pos]=value;request(bad,family,false);
                }
                if(family==1)for(real_t value:{nan,inf,-inf}) {
                    Parameters bad=changed;bad[slot].push_back(value);request(bad,family,false);
                }
            }
            for(int slot=2;slot<4;++slot)for(size_t size:{size_t(0),size_t(1),size_t(2),size_t(4)}) {
                Parameters material=original;material[slot].assign(size,original[slot][0]);reference(material);++optional;
            }
            Parameters empty=original;empty[2].clear();empty[3].clear();reference(empty);++optional;
            configure(original);require(solve()==control,"optional lifetime restore failed");
            Vector limits{TCAD_CONST(-0.0),TCAD_CONST(0.0),TCAD_CONST(-1e300),TCAD_CONST(1e300)};
#ifdef TCAD_USE_FLOAT128
            limits.push_back(TCAD_CONST(-1e400));limits.push_back(TCAD_CONST(1e400));
#endif
            for(real_t value:limits)for(int slot=0;slot<6;++slot) {
                require(isfinite_q(value),"finite pair fixture invalid");
                Parameters material=original;material[slot].assign(3,value);set_pair(material,slot/2);++finite;
                configure(original);require(solve()==control,"finite pair restore failed");
            }
        }
        std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()
                 <<",\"attempted\":"<<attempted<<",\"rejected\":"<<rejected<<",\"accepted\":"<<accepted
                 <<",\"preserved\":"<<preserved<<",\"retries\":"<<retries<<",\"valid_cases\":"<<valid
                 <<",\"finite_cases\":"<<finite<<",\"observable_controls\":"<<observable<<",\"optional_lifetime_cases\":"<<optional
                 <<",\"max_reference_error\":"<<static_cast<double>(max_error)<<"}\n";
        require(observe || (attempted==rejected && rejected==preserved && !accepted),"paired material contract failed");return 0;
    }catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
