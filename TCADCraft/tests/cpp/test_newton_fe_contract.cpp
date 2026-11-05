// Independent layered displacement and nested scalar BE-LK roots.
#include "newton_solver.h"
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
real_t cubic(real_t a,real_t beta,real_t b) {
    real_t lo=-TCAD_CONST(1.0),hi=TCAD_CONST(1.0);
    for(int i=0;i<180;++i) {
        const real_t mid=(lo+hi)/TCAD_CONST(2.0);
        if((a+beta*mid*mid)*mid>b) hi=mid;else lo=mid;
    }
    return (lo+hi)/TCAD_CONST(2.0);
}
}
int main(int argc,char** argv) {
    try {
        const bool observe=argc==2 && std::string(argv[1])=="--observe";
        size_t attempted=0,rejected=0,accepted=0,preserved=0,retries=0,valid=0,finite=0,cleared=0,observable=0,dropped=0;
        real_t worst_phi=TCAD_CONST(0.0),worst_p=TCAD_CONST(0.0);
        const real_t nan=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN()),inf=static_cast<real_t>(std::numeric_limits<double>::infinity());
        const real_t alpha=-TCAD_CONST(1e8),beta=TCAD_CONST(1e12),gamma=TCAD_CONST(.1),dt=TCAD_CONST(1e-10),rate=gamma/dt,imprint=TCAD_CONST(2e5),depol=TCAD_CONST(30.0);
        const Vector eps{TCAD_CONST(12.0)*EPS0,TCAD_CONST(20.0)*EPS0,TCAD_CONST(4.0)*EPS0};
        const std::vector<char> mask{1,1,0};
        for(int axis=0;axis<3;++axis) for(bool stretched:{false,true}) for(bool logarithmic:{false,true}) for(bool coupled:{false,true}) {
            Grid3D grid{1,1,1,TCAD_CONST(1e-8),TCAD_CONST(1e-8),TCAD_CONST(1e-8)};
            Vector x{TCAD_CONST(0.0),TCAD_CONST(1e-8),TCAD_CONST(2e-8)};
            if(stretched) x={TCAD_CONST(0.0),TCAD_CONST(.7e-8),TCAD_CONST(2.2e-8)};
            if(axis==0) {grid.nx=3;if(stretched) grid.xx=x;}
            if(axis==1) {grid.ny=3;if(stretched) grid.yx=x;}
            if(axis==2) {grid.nz=3;if(stretched) grid.zx=x;}
            const int polar=(axis+int(logarithmic))%3;
            Vector seed(9);
            for(size_t node=0;node<3;++node) for(size_t c=0;c<3;++c)
                seed[3*node+c]=TCAD_CONST(.0002)*(real_t(node+1)-TCAD_CONST(.3)*real_t(c));
            NewtonOptions opt;opt.freeze_n=opt.freeze_p=true;opt.use_log_space=logarithmic;opt.record_nonlinear_history=true;
            opt.max_iter=80;opt.tol=TCAD_CONST(1e-22);opt.abs_tol=TCAD_CONST(1e-26);opt.linear_tol=TCAD_CONST(1e-28);opt.linear_solver=SolverType::DENSE_DIRECT;
            opt.transient_enabled=coupled;opt.transient_dt=dt;opt.n_prev=opt.p_prev=Vector(3,TCAD_CONST(1.0));
            NewtonSolver solver(grid,opt);solver.set_permittivity(eps);solver.set_mobility(Vector(3,TCAD_CONST(0.0)),Vector(3,TCAD_CONST(0.0)));solver.set_doping(Vector(3,TCAD_CONST(0.0)));
            solver.set_effective_dos(Vector(3,TCAD_CONST(1e16)),Vector(3,TCAD_CONST(1e16)));solver.set_bandgap(Vector(3,TCAD_CONST(6.0)));
            solver.set_phi_dirichlet({{0,TCAD_CONST(0.0)},{2,TCAD_CONST(.03)}});
            auto restore=[&]() {
                if(coupled) solver.set_transient_lk(mask,seed,alpha,beta,gamma,imprint,depol,polar);
                else solver.set_ferroelectric_polarization(mask,seed);
            };
            const real_t dl=x[1]-x[0],dr=x[2]-x[1],width=(dl+dr)/TCAD_CONST(2.0);
            const real_t el=TCAD_CONST(2.0)*eps[0]*eps[1]/(eps[0]+eps[1]),er=TCAD_CONST(2.0)*eps[1]*eps[2]/(eps[1]+eps[2]);
            const real_t stiffness=(el/dl+er/dr)/width,plain=TCAD_CONST(.03)*(dl/el)/(dl/el+dr/er);
            auto divergence=[&](const std::vector<char>& m,const Vector& p) {
                if(m.empty()) return TCAD_CONST(0.0);
                const real_t left=el*((m[0]?p[axis]/eps[0]:TCAD_CONST(0.0))+(m[1]?p[3+axis]/eps[1]:TCAD_CONST(0.0)))/TCAD_CONST(2.0);
                const real_t right=er*((m[1]?p[3+axis]/eps[1]:TCAD_CONST(0.0))+(m[2]?p[6+axis]/eps[2]:TCAD_CONST(0.0)))/TCAD_CONST(2.0);
                return (right-left)/width;
            };
            auto lk_state=[&](real_t phi) {
                const real_t field[3]={-phi/dl,-TCAD_CONST(.03)/(dl+dr),-(TCAD_CONST(.03)-phi)/dr};
                Vector p(9,TCAD_CONST(0.0));
                for(size_t node=0;node<3;++node) if(mask[node]) for(int c=0;c<3;++c) {
                    const real_t a=alpha+rate+(c==polar?TCAD_CONST(1.0)/(depol*EPS0):TCAD_CONST(0.0));
                    const real_t b=rate*seed[3*node+c]+(c==axis?field[node]:TCAD_CONST(0.0))-(c==polar?imprint:TCAD_CONST(0.0));
                    p[3*node+c]=cubic(a,beta,b);
                }
                return p;
            };
            auto solve=[&]() {
                Vector phi(3,TCAD_CONST(0.0)),n(3,TCAD_CONST(1.0)),p=n;check(solver.solve(phi,n,p),"Newton FE contract solve failed");
                check(n==Vector(3,TCAD_CONST(1.0)) && p==n,"FE frozen carriers changed");
                Vector state(phi);state.insert(state.end(),n.begin(),n.end());state.insert(state.end(),p.begin(),p.end());
                const auto& polarization=solver.ferroelectric_polarization();state.resize(18,TCAD_CONST(0.0));
                std::copy_n(polarization.begin(),std::min(size_t(9),polarization.size()),state.begin()+9);return state;
            };
            auto verify=[&](const Vector& state,real_t expected_phi,const Vector& expected_p) {
                const real_t error=abs_q(state[1]-expected_phi);worst_phi=std::max(worst_phi,error);
                check(isfinite_q(error) && error<TCAD_CONST(1e-18),"independent FE displacement/LK potential mismatch");
                for(size_t i=0;i<9;++i) {
                    const real_t pe=abs_q(state[9+i]-(expected_p.empty()?TCAD_CONST(0.0):expected_p[i]));worst_p=std::max(worst_p,pe);
                    check(isfinite_q(pe) && pe<TCAD_CONST(1e-20),"independent vector LK polarization mismatch");
                }
                check(state[0]==TCAD_CONST(0.0) && state[2]==TCAD_CONST(.03),"FE endpoints changed");
                std::cout<<"{\"case\":"<<++valid<<",\"coupled\":"<<(coupled?1:0)<<",\"values\":[";
                for(size_t i=0;i<state.size();++i) std::cout<<(i?",":"")<<'"'<<exact(state[i])<<'"';
                std::cout<<"]}\n";
            };
            auto baseline=[&]() {
                restore();const auto state=solve();real_t phi=plain-divergence(mask,seed)/stiffness;Vector expected=seed;
                if(coupled) {
                    real_t lo=-TCAD_CONST(1.0),hi=TCAD_CONST(1.0);
                    for(int i=0;i<180;++i) {
                        const real_t mid=(lo+hi)/TCAD_CONST(2.0);
                        if(stiffness*(plain-mid)-divergence(mask,lk_state(mid))>TCAD_CONST(0.0)) lo=mid;else hi=mid;
                    }
                    phi=(lo+hi)/TCAD_CONST(2.0);expected=lk_state(phi);
                }
                verify(state,phi,expected);return state;
            };
            const auto control=baseline();check(abs_q(control[1]-plain)>TCAD_CONST(1e-9),"baseline FE feedback is not observable");++observable;
            for(const auto& m:{std::vector<char>{},std::vector<char>{0,0,0},std::vector<char>{1,1,1},std::vector<char>{1,0,1},std::vector<char>{0,-1,0},std::vector<char>{0,2,0}}) {
                for(int sign:{-1,0,1}) {
                    auto p=seed;for(auto& value:p) value*=real_t(sign);
                    solver.set_ferroelectric_polarization(m,p);const auto state=solve();check(solver.ferroelectric_polarization()==p,"static FE seed changed");
                    verify(state,plain-divergence(m,p)/stiffness,p);if(m.empty()) ++cleared;
                }
            }
            solver.set_ferroelectric_polarization({},{});verify(solve(),plain,{});check(solver.ferroelectric_polarization().empty(),"empty FE clear failed");++cleared;
            solver.set_ferroelectric_polarization(mask,seed);verify(solve(),plain-divergence(mask,seed)/stiffness,seed);
            check(baseline()==control,"FE baseline restore drifted");
            auto request=[&](const std::vector<char>& m,const Vector& p,const std::string& message,bool show_drop=false) {
                const auto before_p=solver.ferroelectric_polarization(),history=solver.residuals();const auto samples=solver.nonlinear_samples();check(!history.empty() && !samples.empty(),"FE baseline history is empty");
                bool caught=false;++attempted;
                try {solver.set_ferroelectric_polarization(m,p);}catch(const std::invalid_argument& error) {check(error.what()==message,"wrong FE exception");caught=true;++rejected;}
                if(caught) {
                    check(solver.ferroelectric_polarization()==before_p && solver.residuals()==history && solver.nonlinear_samples()==samples,"rejected FE changed state/history");
                    check(solve()==control,"rejected FE changed feedback or coupled LK mode");++preserved;
                } else {
                    ++accepted;
                    if(observe && show_drop) {const auto state=solve();check(abs_q(state[1]-plain)<TCAD_CONST(1e-18) && abs_q(state[1]-control[1])>TCAD_CONST(1e-9),"malformed finite FE did not expose lost feedback");++dropped;}
                }
                if(!observe) check(caught,"invalid native Newton FE input was accepted");
                restore();check(solve()==control,"valid FE retry failed");++retries;
            };
            for(size_t length:{size_t(1),size_t(2),size_t(4),size_t(6)}) request(std::vector<char>(length,1),Vector(9,nan),"Newton FE mask size mismatch");
            for(size_t length:{size_t(0),size_t(1),size_t(3),size_t(8),size_t(10),size_t(12)}) request({0,1,1},Vector(length,nan),"Newton FE polarization size mismatch");
            for(size_t length:{size_t(1),size_t(3),size_t(8),size_t(10)}) request({},Vector(length,nan),"Newton FE polarization size mismatch");
            for(bool empty:{false,true}) for(real_t value:{nan,inf,-inf}) for(size_t node=0;node<9;++node) {
                auto p=seed;p[node]=value;request(empty?std::vector<char>{}:std::vector<char>{0,1,1},p,"FE polarization values must be finite");
            }
            request({1,1},seed,"Newton FE mask size mismatch",true);
            request(mask,Vector(8,TCAD_CONST(.001)),"Newton FE polarization size mismatch",true);
            for(real_t value:{-TCAD_CONST(0.0),TCAD_CONST(0.0),-TCAD_CONST(1e300),TCAD_CONST(1e300),-TCAD_CONST(1e400),TCAD_CONST(1e400)}) {
                solver.set_ferroelectric_polarization(mask,Vector(9,value));++finite;restore();check(solve()==control,"finite FE seed restore failed");
            }
        }
        std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"attempted\":"<<attempted<<",\"rejected\":"<<rejected<<",\"accepted\":"<<accepted<<",\"preserved\":"<<preserved<<",\"retries\":"<<retries
                 <<",\"valid_cases\":"<<valid<<",\"finite_cases\":"<<finite<<",\"cleared_cases\":"<<cleared<<",\"observable_controls\":"<<observable<<",\"dropped_feedback_cases\":"<<dropped<<",\"max_phi_error\":"<<static_cast<double>(worst_phi)<<",\"max_p_error\":"<<static_cast<double>(worst_p)<<"}\n";
        check(observe || (attempted==rejected && rejected==preserved && !accepted),"Newton FE contract failed");return 0;
    }catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
