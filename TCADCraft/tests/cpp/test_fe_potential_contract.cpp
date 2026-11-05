// FE potential entry: bounds, finiteness, persistent history and dwell rollback.
#include "poisson_solver.h"
#include <algorithm>
#include <cstdio>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
using namespace tcad;
namespace {
void check(bool b,const char* message){if(!b)throw std::runtime_error(message);}
std::string exact(real_t x){char b[128];
#ifdef TCAD_USE_FLOAT128
    quadmath_snprintf(b,sizeof(b),"%Qa",x);
#else
    std::snprintf(b,sizeof(b),"%La",x);
#endif
    return b;
}
struct Fixture {
    int axis,model;Vector x,seed,memory;std::vector<char> mask;PoissonSolver solver;
    static Grid3D grid(int axis,bool stretched){Grid3D g{1,1,1,TCAD_CONST(1e-6),TCAD_CONST(1e-6),TCAD_CONST(1e-6)};
        Vector x{TCAD_CONST(0.0),TCAD_CONST(.7e-6),TCAD_CONST(2.2e-6)};
        if(axis==0){g.nx=3;if(stretched)g.xx=x;}if(axis==1){g.ny=3;if(stretched)g.yx=x;}if(axis==2){g.nz=3;if(stretched)g.zx=x;}return g;}
    Fixture(int a,bool stretched,int m,bool empty,bool enabled=true):axis(a),model(m),x{TCAD_CONST(0.0),TCAD_CONST(1e-6),TCAD_CONST(2e-6)},
      seed(empty?0:9,TCAD_CONST(0.0)),mask(stretched?std::vector<char>{-1,2,0}:std::vector<char>{0,1,1}),solver(grid(a,stretched)){
        if(stretched)x={TCAD_CONST(0.0),TCAD_CONST(.7e-6),TCAD_CONST(2.2e-6)};
        for(size_t i=0;i<seed.size();++i)seed[i]=static_cast<real_t>(i+1)*TCAD_CONST(1e-5);
        SolverOptions so;so.type=SolverType::DENSE_DIRECT;so.tol=TCAD_CONST(1e-28);solver.set_solver_options(so);
        solver.set_permittivity(Vector(3,TCAD_CONST(20.0)*EPS0));solver.set_doping(Vector(3,TCAD_CONST(0.0)));
        solver.set_dirichlet({{0,TCAD_CONST(0.0)},{2,TCAD_CONST(.1)}});solver.set_boltzmann_linearization(false,TCAD_CONST(.02585));
        if(enabled)solver.set_ferroelectric(mask,-TCAD_CONST(1e8),TCAD_CONST(3e12));
        solver.set_ferroelectric_model(model);solver.set_ferroelectric_polar_axis(axis);solver.set_ferroelectric_gamma(TCAD_CONST(.1));
        solver.set_ferroelectric_preisach(TCAD_CONST(.02),TCAD_CONST(1e5),TCAD_CONST(5e4));
        solver.set_ferroelectric_nls(TCAD_CONST(1e-10),TCAD_CONST(1e5),TCAD_CONST(3e-12));
        if(model==3){memory=Vector(6,TCAD_CONST(0.0));for(size_t i=3;i<6;++i)memory[i]=TCAD_CONST(1.0);
            memory.insert(memory.end(),{-TCAD_CONST(1e300),-TCAD_CONST(.02),TCAD_CONST(1e300),TCAD_CONST(.02)});}
        else memory=Vector(model==1?3:2,TCAD_CONST(2e4));
        reset();
    }
    void reset(){solver.set_fe_polarization(seed);solver.set_fe_play_state(memory);}
    Vector drive(real_t field)const{Vector phi(3);for(size_t i=0;i<3;++i)phi[i]=-field*x[i];return phi;}
    void update(const Vector& phi,int route,real_t dt=TCAD_CONST(5e-10)){if(route)solver.update_ferroelectric_polarization_transient(phi,dt);else solver.update_ferroelectric_polarization(phi);}
    Vector raw(){Vector phi{TCAD_CONST(0.0),TCAD_CONST(.03),TCAD_CONST(.1)},one(3,TCAD_CONST(1.0));solver.set_leakage_field(phi);solver.assemble(one,one);check(solver.solve(phi),"FE potential raw Poisson failed");return phi;}
    Vector state(){auto v=raw();const auto& p=solver.fe_polarization();const auto& m=solver.fe_play_state();v.insert(v.end(),p.begin(),p.end());v.insert(v.end(),m.begin(),m.end());return v;}
};
}
int main(int argc,char** argv){try{
    if(argc==7 && std::string(argv[1])=="--probe"){
        const int model=std::stoi(argv[2]),axis=std::stoi(argv[3]),route=std::stoi(argv[5]);Fixture f(axis,std::stoi(argv[4])!=0,model,false);
        const auto p=f.solver.fe_polarization(),m=f.solver.fe_play_state();
        try{f.update(Vector(static_cast<size_t>(std::stoi(argv[6])),TCAD_CONST(.1)),route);}catch(const std::invalid_argument& e){
            check(f.solver.fe_polarization()==p && f.solver.fe_play_state()==m,"probe rejection changed history");
            check(std::string(e.what())=="FE potential size mismatch","wrong potential probe exception");
            std::cout<<"{\"probe_rejected\":true,\"message\":\""<<e.what()<<"\"}\n";return 0;}
        throw std::runtime_error("unsafe FE potential probe was accepted");
    }
    const bool observe=argc==2 && std::string(argv[1])=="--observe";
    const real_t nan=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN()),inf=static_cast<real_t>(std::numeric_limits<double>::infinity());
    size_t attempted=0,rejected=0,accepted=0,preserved=0,mutated=0,retries=0,skipped=0,valid=0,restarts=0,noops=0,dtchecks=0,dwell=0;
    real_t max_phi=TCAD_CONST(0.0);
    for(int axis=0;axis<3;++axis)for(bool stretched:{false,true})for(int model=0;model<4;++model)for(bool empty:{false,true})for(int route=0;route<2;++route){
        // Static LK requires allocated 3N P; its separate empty-P contract is
        // outside this potential-input test. Transient LK already validates phi.
        if(model==0 && (empty || route))continue;
        Fixture f(axis,stretched,model,empty);auto& s=f.solver;const auto good=f.drive(TCAD_CONST(2e5));
        f.update(good,route);const auto control=f.state();f.reset();f.update(good,0);const auto static_control=f.state();f.reset();
        auto request=[&](Vector phi,bool shape,bool unsafe){if(observe && unsafe && model!=2){++skipped;return;}
            f.reset();const auto before=f.state(),rhs=s.rhs(),matrix=s.matrix().vals();++attempted;bool caught=false;
            try{f.update(phi,route);}catch(const std::invalid_argument& e){
                const std::string expected=model==2?"NLS requires finite potential and polarization fields":shape?"FE potential size mismatch":"FE potential values must be finite";
                check(e.what()==expected,"wrong FE potential exception");caught=true;++rejected;}
            if(!caught)++accepted;
            else {const bool same=s.fe_polarization()==f.seed && s.fe_play_state()==f.memory;
                if(same){check(s.rhs()==rhs && s.matrix().vals()==matrix && f.state()==before,"potential rejection changed raw equations");++preserved;}
                else {++mutated;check(observe,"potential rejection changed P or memory");}}
            if(!observe)check(caught,"invalid native FE potential was accepted");
            f.reset();f.update(good,route);check(f.state()==control,"valid potential retry changed continuation");++retries;
            f.reset();f.update(good,0);check(f.state()==static_control,"transient rejection changed configured static dwell");if(model==2 && route)++dwell;
        };
        for(size_t n:{size_t(0),size_t(1),size_t(2),size_t(4),size_t(6)})request(Vector(n,TCAD_CONST(.1)),true,n<3);
        for(real_t v:{nan,inf,-inf})for(size_t i=0;i<3;++i){auto phi=good;phi[i]=v;request(phi,false,false);}
        request(Vector(4,nan),true,false);
        if(route)for(real_t dt:{TCAD_CONST(0.0),-TCAD_CONST(1.0),nan,inf,-inf}){
            f.reset();try{f.update({},route,dt);throw std::runtime_error("invalid FE dt accepted");}catch(const std::invalid_argument& e){
                check(std::string(e.what())=="FE transient dt must be finite and positive","transient dt precedence changed");}
            check(s.fe_polarization()==f.seed && s.fe_play_state()==f.memory,"dt rejection changed history");++dtchecks;
        }
        auto record=[&](const char* kind){const auto phi=f.raw();const auto& p=s.fe_polarization();
            const real_t dl=f.x[1]-f.x[0],dr=f.x[2]-f.x[1],width=(dl+dr)/TCAD_CONST(2.0);
            const real_t stiff=TCAD_CONST(20.0)*EPS0*(TCAD_CONST(1.0)/dl+TCAD_CONST(1.0)/dr)/width;
            const real_t div=((f.mask[2]?p[6+axis]:TCAD_CONST(0.0))-(f.mask[0]?p[axis]:TCAD_CONST(0.0)))/(TCAD_CONST(2.0)*width);
            const real_t error=abs_q(phi[1]-(TCAD_CONST(.1)*dl/(dl+dr)-div/stiff));max_phi=std::max(max_phi,error);
            check(isfinite_q(error) && error<TCAD_CONST(1e-18),"independent FE potential Gauss reference mismatch");
            std::cout<<"{\"case\":"<<++valid<<",\"kind\":\""<<kind<<"\",\"values\":[";
            Vector v=phi;v.insert(v.end(),p.begin(),p.end());v.insert(v.end(),s.fe_play_state().begin(),s.fe_play_state().end());
            for(size_t i=0;i<v.size();++i)std::cout<<(i?",":"")<<'"'<<exact(v[i])<<'"';std::cout<<"]}\n";};
        for(real_t field:{-TCAD_CONST(2e5),-TCAD_CONST(1e5),TCAD_CONST(0.0),TCAD_CONST(.5e5),TCAD_CONST(1e5),TCAD_CONST(2e5)}){
            f.reset();f.update(f.drive(field),route);record("field");}
        f.reset();
        for(real_t field:{TCAD_CONST(2e5),-TCAD_CONST(1e5),TCAD_CONST(.5e5),-TCAD_CONST(.5e5),TCAD_CONST(3e5),-TCAD_CONST(3e5)}){
            const auto p=s.fe_polarization(),m=s.fe_play_state();f.update(f.drive(field),route);const auto uninterrupted=f.state();
            s.set_fe_polarization(p);s.set_fe_play_state(m);f.update(f.drive(field),route);check(f.state()==uninterrupted,"potential reference restart changed continuation");++restarts;record("restart");}
    }
    for(int axis=0;axis<3;++axis)for(bool stretched:{false,true})for(bool empty:{false,true})for(int route=0;route<2;++route){
        Fixture f(axis,stretched,3,empty,false);
        for(real_t dt:{TCAD_CONST(5e-10),TCAD_CONST(0.0),-TCAD_CONST(1.0),nan,inf}){
            for(const auto& phi:std::vector<Vector>{{},Vector(3,nan),Vector(4,inf)}){
                f.update(phi,route,dt);check(f.solver.fe_polarization()==f.seed && f.solver.fe_play_state()==f.memory,"disabled FE no-op changed history");++noops;}
        }
    }
    std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"attempted\":"<<attempted<<",\"rejected\":"<<rejected<<",\"accepted\":"<<accepted<<",\"preserved\":"<<preserved<<",\"mutated\":"<<mutated<<",\"retries\":"<<retries<<",\"unsafe_skipped\":"<<skipped<<",\"valid_cases\":"<<valid<<",\"restart_cases\":"<<restarts<<",\"disabled_noops\":"<<noops<<",\"dt_precedence_checks\":"<<dtchecks<<",\"nls_dwell_checks\":"<<dwell<<",\"max_phi_error\":"<<static_cast<double>(max_phi)<<"}\n";
    check(observe || (attempted==rejected && rejected==preserved && !accepted && !mutated),"FE potential contract failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
