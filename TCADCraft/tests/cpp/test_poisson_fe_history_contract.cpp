// Persistent native FE state: rejection atomicity, raw feedback and restart.
#include "gummel_solver.h"
#include <algorithm>
#include <cstdio>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
using namespace tcad;
namespace {
void check(bool b,const char* message) {if(!b)throw std::runtime_error(message);}
std::string exact(real_t x) {
    char b[128];
#ifdef TCAD_USE_FLOAT128
    quadmath_snprintf(b,sizeof(b),"%Qa",x);
#else
    std::snprintf(b,sizeof(b),"%La",x);
#endif
    return b;
}
}
int main(int argc,char** argv) {
 try {
    const bool observe=argc==2 && std::string(argv[1])=="--observe";
    size_t attempted=0,rejected=0,accepted=0,preserved=0,retries=0,valid=0,cleared=0,finite=0,dropped=0,restarts=0;
    real_t worst=TCAD_CONST(0.0);
    const real_t nan=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN()),inf=static_cast<real_t>(std::numeric_limits<double>::infinity());
    const real_t eps=TCAD_CONST(20.0)*EPS0,alpha=-TCAD_CONST(1e8),beta=TCAD_CONST(3e12),dt=TCAD_CONST(1e-10);
    const Vector zero(3,TCAD_CONST(0.0)),ones(3,TCAD_CONST(1.0)),dielectric(3,eps);
    const std::vector<char> mask{0,1,1};
    for(int axis=0;axis<3;++axis)for(bool stretched:{false,true})for(int model=0;model<4;++model)for(int route=0;route<2;++route) {
        Grid3D grid{1,1,1,TCAD_CONST(1e-6),TCAD_CONST(1e-6),TCAD_CONST(1e-6)};
        Vector x{TCAD_CONST(0.0),TCAD_CONST(1e-6),TCAD_CONST(2e-6)};
        if(stretched)x={TCAD_CONST(0.0),TCAD_CONST(.7e-6),TCAD_CONST(2.2e-6)};
        if(axis==0){grid.nx=3;if(stretched)grid.xx=x;}
        if(axis==1){grid.ny=3;if(stretched)grid.yx=x;}
        if(axis==2){grid.nz=3;if(stretched)grid.zx=x;}
        Vector seed(9),drive(3);for(size_t i=0;i<9;++i)seed[i]=static_cast<real_t>(i+1)*TCAD_CONST(1e-5);
        for(size_t i=0;i<3;++i)drive[i]=-TCAD_CONST(2e5)*x[i];
        PoissonSolver poisson(grid);SolverOptions so;so.type=SolverType::DENSE_DIRECT;so.tol=TCAD_CONST(1e-28);
        poisson.set_solver_options(so);poisson.set_permittivity(dielectric);poisson.set_doping(zero);
        poisson.set_dirichlet({{0,TCAD_CONST(0.0)},{2,TCAD_CONST(.1)}});poisson.set_boltzmann_linearization(false,TCAD_CONST(.02585));
        poisson.set_ferroelectric(mask,alpha,beta);poisson.set_ferroelectric_model(model);poisson.set_ferroelectric_polar_axis(axis);
        poisson.set_ferroelectric_gamma(TCAD_CONST(.1));poisson.set_ferroelectric_preisach(TCAD_CONST(.02),TCAD_CONST(1e5),TCAD_CONST(5e4));
        poisson.set_ferroelectric_nls(TCAD_CONST(1e-10),TCAD_CONST(1e5),dt);
        // Obtain nonempty, internally generated scalar history before seeding
        // raw vector feedback. LK/NLS deliberately retain unused finite memory.
        poisson.set_fe_polarization(seed);poisson.set_fe_play_state(Vector(3,TCAD_CONST(2e4)));
        poisson.update_ferroelectric_polarization_transient(drive,dt);
        const auto memory=poisson.fe_play_state();
        GummelOptions go;go.boltzmann_lin=false;go.ferro.enabled=true;go.ferro.fe_mask=mask;go.ferro.alpha=alpha;go.ferro.beta=beta;go.ferro.model=static_cast<FerroelectricModel>(model);go.ferro.polar_axis=axis;
        GummelSolver gummel(grid,go);gummel.set_poisson_solver_type(SolverType::DENSE_DIRECT);gummel.set_permittivity(dielectric);gummel.set_doping(zero);
        gummel.set_poisson_dirichlet({{0,TCAD_CONST(0.0)},{2,TCAD_CONST(.1)}});
        auto setp=[&](const Vector& p){if(route)gummel.set_fe_polarization(p);else poisson.set_fe_polarization(p);};
        auto setm=[&](const Vector& m){if(route)gummel.set_fe_play_state(m);else poisson.set_fe_play_state(m);};
        auto getp=[&]()->const Vector&{return route?gummel.fe_polarization():poisson.fe_polarization();};
        auto getm=[&]()->const Vector&{return route?gummel.fe_play_state():poisson.fe_play_state();};
        auto restore=[&](){setp(seed);setm(memory);};
        auto solve=[&](){Vector phi{TCAD_CONST(0.0),TCAD_CONST(.03),TCAD_CONST(.1)};
            if(route)check(gummel.recompute_poisson(phi,ones,ones),"Gummel raw FE solve failed");
            else {poisson.set_leakage_field(phi);poisson.assemble(ones,ones);check(poisson.solve(phi),"Poisson raw FE solve failed");}return phi;};
        const real_t dl=x[1]-x[0],dr=x[2]-x[1],width=(dl+dr)/TCAD_CONST(2.0);
        const real_t stiffness=eps*(TCAD_CONST(1.0)/dl+TCAD_CONST(1.0)/dr)/width;
        const real_t linear=TCAD_CONST(.1)*dl/(dl+dr);
        auto reference=[&](){const auto phi=solve();const auto& p=getp();
            // Equal-epsilon half layers: each interface averages its two P's.
            const real_t divergence=p.empty()?TCAD_CONST(0.0):p[6+axis]/(TCAD_CONST(2.0)*width);
            const real_t error=abs_q(phi[1]-(linear-divergence/stiffness));worst=std::max(worst,error);
            check(isfinite_q(error) && error<TCAD_CONST(1e-18),"independent FE Gauss-law reference mismatch");
            std::cout<<"{\"case\":"<<++valid<<",\"route\":"<<route<<",\"model\":"<<model<<",\"kind\":\"flux\",\"values\":[";
            Vector state=phi;state.insert(state.end(),p.begin(),p.end());state.insert(state.end(),getm().begin(),getm().end());
            for(size_t i=0;i<state.size();++i)std::cout<<(i?",":"")<<'"'<<exact(state[i])<<'"';std::cout<<"]}\n";return phi;};
        restore();const auto control=reference();check(abs_q(control[1]-linear)>TCAD_CONST(1e-9),"FE feedback unobservable");
        auto advance=[&](){poisson.update_ferroelectric_polarization_transient(drive,dt);Vector v=poisson.fe_polarization();v.insert(v.end(),poisson.fe_play_state().begin(),poisson.fe_play_state().end());return v;};
        Vector continuation;if(!route){restore();continuation=advance();restore();}
        auto request=[&](const Vector& bad,bool play,bool shape){++attempted;bool caught=false;
            try {if(play)setm(bad);else setp(bad);}catch(const std::invalid_argument& e){
                const std::string expected=play?"FE play state values must be finite":shape?"FE polarization size mismatch":"FE polarization values must be finite";
                check(e.what()==expected,"wrong FE history exception");caught=true;++rejected;}
            if(!caught)++accepted;
            else {check(getp()==seed && getm()==memory,"rejection changed FE history");check(solve()==control,"rejection changed next FE solve");
                if(!route){check(advance()==continuation,"rejection changed FE continuation");restore();}++preserved;}
            if(!observe)check(caught,"invalid native FE history was accepted");
            // Only finite wrong-size vectors are evaluated by the old version;
            // its divergence shape guard safely suppresses their feedback.
            if(!caught && shape){check(abs_q(solve()[1]-linear)<TCAD_CONST(1e-18),"old shape did not drop feedback");++dropped;}
            restore();check(solve()==control,"FE history valid retry failed");++retries;};
        for(size_t n:{size_t(1),size_t(8),size_t(10)})request(Vector(n,TCAD_CONST(1e-4)),false,true);
        // Wrong shape has priority even when a component is nonfinite.
        request(Vector(8,nan),false,true);
        for(real_t bad:{nan,inf,-inf})for(size_t i=0;i<9;++i){auto p=seed;p[i]=bad;request(p,false,false);}
        for(size_t n:{size_t(1),size_t(3),size_t(6),size_t(12)})for(real_t bad:{nan,inf,-inf})for(size_t i=0;i<n;++i){Vector m(n,TCAD_CONST(0.0));m[i]=bad;request(m,true,false);}
        setp({});reference();++cleared;setm({});reference();++cleared;restore();
        // Finite arbitrary memory lengths are intentionally accepted. Model
        // normalization remains separate from validation of serialized history.
        for(size_t n:{size_t(0),size_t(1),size_t(3),size_t(6),size_t(12)}){setm(Vector(n,TCAD_CONST(2e4)));reference();restore();}
        Vector limits{TCAD_CONST(-0.0),TCAD_CONST(0.0),TCAD_CONST(-1e300),TCAD_CONST(1e300)};
#ifdef TCAD_USE_FLOAT128
        limits.push_back(TCAD_CONST(-1e400));limits.push_back(TCAD_CONST(1e400));
#endif
        for(real_t value:limits){check(isfinite_q(value),"finite range fixture invalid");setp(Vector(9,value));setm(Vector(12,value));++finite;restore();check(solve()==control,"finite range restore failed");}
        if(!route){
            // Restart round trip after a field reversal includes both P and
            // generated turning points; compare with uninterrupted continuation.
            restore();advance();const auto savedp=poisson.fe_polarization(),savedm=poisson.fe_play_state();
            for(auto& v:drive)v=-v;const auto uninterrupted=advance();
            poisson.set_fe_polarization(savedp);poisson.set_fe_play_state(savedm);check(advance()==uninterrupted,"FE restart differs from uninterrupted continuation");++restarts;
            std::cout<<"{\"case\":"<<++valid<<",\"route\":0,\"model\":"<<model<<",\"kind\":\"restart\",\"values\":[";
            for(size_t i=0;i<uninterrupted.size();++i)std::cout<<(i?",":"")<<'"'<<exact(uninterrupted[i])<<'"';std::cout<<"]}\n";
        }
    }
    std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"attempted\":"<<attempted<<",\"rejected\":"<<rejected<<",\"accepted\":"<<accepted<<",\"preserved\":"<<preserved<<",\"retries\":"<<retries<<",\"valid_cases\":"<<valid<<",\"finite_cases\":"<<finite<<",\"cleared_cases\":"<<cleared<<",\"restart_cases\":"<<restarts<<",\"dropped_feedback_cases\":"<<dropped<<",\"max_phi_error\":"<<static_cast<double>(worst)<<"}\n";
    check(observe || (attempted==rejected && preserved==rejected && !accepted),"FE history contract failed");return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
