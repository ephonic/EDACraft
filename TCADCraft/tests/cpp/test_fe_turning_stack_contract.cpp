// Model-3 restart brackets: reject malformed tails without committing state.
#include "poisson_solver.h"
#include <algorithm>
#include <cstdio>
#include <iostream>
#include <stdexcept>
#include <string>
using namespace tcad;
namespace {
void check(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
std::string exact(real_t x){char b[128];
#ifdef TCAD_USE_FLOAT128
    quadmath_snprintf(b,sizeof(b),"%Qa",x);
#else
    std::snprintf(b,sizeof(b),"%La",x);
#endif
    return b;
}
struct Fixture {
    int axis;Grid3D grid;Vector x,seed;std::vector<char> mask;PoissonSolver solver;
    Fixture(int a,bool stretched,bool empty):axis(a),grid{1,1,1,TCAD_CONST(1e-6),TCAD_CONST(1e-6),TCAD_CONST(1e-6)},
      x{TCAD_CONST(0.0),TCAD_CONST(1e-6),TCAD_CONST(2e-6)},seed(empty?0:9,TCAD_CONST(0.0)),mask(stretched?std::vector<char>{-1,2,0}:std::vector<char>{0,1,1}),solver(make_grid(a,stretched)) {
        grid=make_grid(a,stretched);if(stretched)x={TCAD_CONST(0.0),TCAD_CONST(.7e-6),TCAD_CONST(2.2e-6)};
        for(size_t i=0;i<seed.size();++i)seed[i]=static_cast<real_t>(i+1)*TCAD_CONST(1e-4);
        SolverOptions so;so.type=SolverType::DENSE_DIRECT;so.tol=TCAD_CONST(1e-28);solver.set_solver_options(so);
        solver.set_permittivity(Vector(3,TCAD_CONST(20.0)*EPS0));solver.set_doping(Vector(3,TCAD_CONST(0.0)));
        solver.set_dirichlet({{0,TCAD_CONST(0.0)},{2,TCAD_CONST(.1)}});solver.set_boltzmann_linearization(false,TCAD_CONST(.02585));
        solver.set_ferroelectric(mask,-TCAD_CONST(1e8),TCAD_CONST(3e12));solver.set_ferroelectric_model(3);
        solver.set_ferroelectric_polar_axis(axis);solver.set_ferroelectric_preisach(TCAD_CONST(.02),TCAD_CONST(1e5),TCAD_CONST(5e4));
    }
    static Grid3D make_grid(int axis,bool stretched){Grid3D g{1,1,1,TCAD_CONST(1e-6),TCAD_CONST(1e-6),TCAD_CONST(1e-6)};
        Vector xx{TCAD_CONST(0.0),TCAD_CONST(.7e-6),TCAD_CONST(2.2e-6)};
        if(axis==0){g.nx=3;if(stretched)g.xx=xx;}if(axis==1){g.ny=3;if(stretched)g.yx=xx;}if(axis==2){g.nz=3;if(stretched)g.zx=xx;}return g;}
    Vector drive(real_t field) const {Vector phi(3);for(size_t i=0;i<3;++i)phi[i]=-field*x[i];return phi;}
    void advance(real_t field,int route){const auto phi=drive(field);if(route)solver.update_ferroelectric_polarization_transient(phi,TCAD_CONST(1e-10));else solver.update_ferroelectric_polarization(phi);}
    Vector raw(){Vector phi{TCAD_CONST(0.0),TCAD_CONST(.03),TCAD_CONST(.1)},one(3,TCAD_CONST(1.0));solver.set_leakage_field(phi);solver.assemble(one,one);check(solver.solve(phi),"turning-point Poisson solve failed");return phi;}
    Vector state(){Vector v=raw();const auto& p=solver.fe_polarization();const auto& m=solver.fe_play_state();v.insert(v.end(),p.begin(),p.end());v.insert(v.end(),m.begin(),m.end());return v;}
    Vector memory(real_t previous,int branch) const {Vector m(6);for(size_t i=0;i<3;++i){m[i]=previous;m[3+i]=static_cast<real_t>(branch);}return m;}
    Vector bad(size_t tail) const {auto m=memory(TCAD_CONST(0.0),1);for(size_t j=0;j<tail;++j)m.push_back(j%2?TCAD_CONST(.001)*static_cast<real_t>(j):static_cast<real_t>(j+1));return m;}
    Vector major(real_t previous,int branch) const {auto m=memory(previous,branch);m.insert(m.end(),{-TCAD_CONST(1e300),-TCAD_CONST(.02),TCAD_CONST(1e300),TCAD_CONST(.02)});return m;}
};
}
int main(int argc,char** argv){try{
    if(argc==6 && std::string(argv[1])=="--probe"){
        Fixture f(std::stoi(argv[2]),std::stoi(argv[3])!=0,true);const int route=std::stoi(argv[4]);const auto m=f.bad(static_cast<size_t>(std::stoi(argv[5])));
        f.solver.set_fe_polarization({});f.solver.set_fe_play_state(m);
        try{f.advance(TCAD_CONST(1e5),route);}catch(const std::invalid_argument& e){
            check(f.solver.fe_polarization().empty() && f.solver.fe_play_state()==m,"probe rejection changed history");
            const std::string message=e.what();check(message=="FE turning-point history must contain complete field/polarization pairs" || message=="FE turning-point history has incomplete wipeout bracket","wrong probe exception");
            std::cout<<"{\"probe_rejected\":true,\"message\":\""<<message<<"\"}\n";return 0;}
        throw std::runtime_error("unsafe turning-point probe was accepted");
    }
    const bool observe=argc==2 && std::string(argv[1])=="--observe";
    size_t attempted=0,rejected=0,accepted=0,preserved=0,retries=0,skipped=0,valid=0,analytic=0,restarts=0;
    real_t max_phi=TCAD_CONST(0.0),max_p=TCAD_CONST(0.0);
    for(int axis=0;axis<3;++axis)for(bool stretched:{false,true})for(bool empty:{false,true})for(int route=0;route<2;++route){
        Fixture f(axis,stretched,empty);auto& s=f.solver;
        auto prime=[&](const Vector& m){s.set_ferroelectric_model((axis+route+stretched)%2?1:3);s.set_fe_polarization(f.seed);s.set_fe_play_state(m);s.set_ferroelectric_model(3);s.set_ferroelectric_builtin_field(TCAD_CONST(0.0));};
        auto control=[&](){prime(f.major(TCAD_CONST(1.5e5),1));f.advance(TCAD_CONST(2e5),route);return f.state();};
        const auto expected_control=control();
        auto request=[&](size_t tail,bool unsafe){if(observe && unsafe){++skipped;return;}
            const auto m=f.bad(tail);prime(m);const auto before=f.state(),rhs=s.rhs(),matrix=s.matrix().vals();++attempted;bool caught=false;
            try{f.advance(unsafe?TCAD_CONST(1e5):TCAD_CONST(0.0),route);}catch(const std::invalid_argument& e){
                const std::string expected=unsafe?"FE turning-point history has incomplete wipeout bracket":"FE turning-point history must contain complete field/polarization pairs";
                check(e.what()==expected,"wrong turning-point exception");caught=true;++rejected;}
            if(!caught)++accepted;
            else {check(s.fe_polarization()==f.seed && s.fe_play_state()==m,"rejection changed P or memory");check(s.rhs()==rhs && s.matrix().vals()==matrix,"rejection changed assembled state");check(f.state()==before,"rejection changed next raw solve");++preserved;}
            if(!observe)check(caught,"malformed turning-point history was accepted");
            check(control()==expected_control,"valid turning-point retry changed continuation");++retries;};
        for(size_t tail:{size_t(5),size_t(7),size_t(9),size_t(11)})request(tail,false);
        for(size_t tail:{size_t(6),size_t(10),size_t(14)})request(tail,true);
        auto record=[&](const char* kind,bool independent,real_t expected){
            const auto phi=f.raw();const auto& p=s.fe_polarization();const auto& m=s.fe_play_state();
            check(p.size()==9,"valid update did not initialize vector P");
            for(size_t i=0;i<3;++i)for(int c=0;c<3;++c){
                const real_t target=f.mask[i] && c==axis?expected:TCAD_CONST(0.0);
                if(independent){const real_t error=abs_q(p[3*i+c]-target);max_p=std::max(max_p,error);check(isfinite_q(error) && error<TCAD_CONST(1e-20),"independent tanh endpoint interpolation mismatch");}
                check(isfinite_q(p[3*i+c]) && abs_q(p[3*i+c])<=TCAD_CONST(.020000000001),"invalid scalar polarization");}
            const real_t dl=f.x[1]-f.x[0],dr=f.x[2]-f.x[1],width=(dl+dr)/TCAD_CONST(2.0);
            const real_t stiff=TCAD_CONST(20.0)*EPS0*(TCAD_CONST(1.0)/dl+TCAD_CONST(1.0)/dr)/width;
            const real_t divergence=((f.mask[2]?p[6+axis]:TCAD_CONST(0.0))-(f.mask[0]?p[axis]:TCAD_CONST(0.0)))/(TCAD_CONST(2.0)*width);
            const real_t error=abs_q(phi[1]-(TCAD_CONST(.1)*dl/(dl+dr)-divergence/stiff));max_phi=std::max(max_phi,error);
            check(isfinite_q(error) && error<TCAD_CONST(1e-18),"independent turning-point Gauss-law mismatch");
            if(independent)++analytic;
            std::cout<<"{\"case\":"<<++valid<<",\"kind\":\""<<kind<<"\",\"values\":[";Vector v=phi;v.insert(v.end(),p.begin(),p.end());v.insert(v.end(),m.begin(),m.end());
            for(size_t i=0;i<v.size();++i)std::cout<<(i?",":"")<<'"'<<exact(v[i])<<'"';std::cout<<"]}\n";};
        for(real_t builtin:{-TCAD_CONST(2e4),TCAD_CONST(0.0),TCAD_CONST(2e4)})for(real_t factor:{-TCAD_CONST(2.0),-TCAD_CONST(1.25),-TCAD_CONST(.75),-TCAD_CONST(.25),TCAD_CONST(.25),TCAD_CONST(.75),TCAD_CONST(1.25),TCAD_CONST(2.0)}){
            const real_t field=factor*TCAD_CONST(1e5),effective=field-builtin;const int branch=effective>TCAD_CONST(0.0)?1:-1;
            prime(f.major(effective-static_cast<real_t>(branch)*TCAD_CONST(5e4),branch));s.set_ferroelectric_builtin_field(builtin);f.advance(field,route);
            record("major",true,TCAD_CONST(.02)*tanh_q((effective-static_cast<real_t>(branch)*TCAD_CONST(1e5))/TCAD_CONST(5e4)));}
        const real_t pr=TCAD_CONST(.02)*tanh_q(TCAD_CONST(2.0)),pb=(TCAD_CONST(.02)-pr)/TCAD_CONST(2.0);
        const real_t ratio=pb/TCAD_CONST(.02),eb=TCAD_CONST(1e5)+TCAD_CONST(2.5e4)*log_q((TCAD_CONST(1.0)+ratio)/(TCAD_CONST(1.0)-ratio));
        const real_t t1=tanh_q((eb+TCAD_CONST(1e5))/TCAD_CONST(5e4));
        // Solve c*tanh(x)+offset from (Eb,Pb) and negative saturation.
        const real_t boot=-TCAD_CONST(.02)+(pb+TCAD_CONST(.02))/(t1+TCAD_CONST(1.0));
        for(size_t length=0;length<10;++length){auto m=f.memory(TCAD_CONST(0.0),-1);m.resize(length,TCAD_CONST(.001));prime(m);f.advance(-TCAD_CONST(1e5),route);record("bootstrap",true,boot);}
        prime({});
        for(real_t field:{TCAD_CONST(2e5),-TCAD_CONST(1e5),TCAD_CONST(.5e5),-TCAD_CONST(.5e5),TCAD_CONST(3e5),-TCAD_CONST(3e5),TCAD_CONST(1e5),-TCAD_CONST(1e5),TCAD_CONST(4e5),-TCAD_CONST(4e5),TCAD_CONST(2e5),TCAD_CONST(0.0)}){
            const auto oldp=s.fe_polarization(),oldm=s.fe_play_state();f.advance(field,route);const auto uninterrupted=f.state();
            s.set_fe_polarization(oldp);s.set_fe_play_state(oldm);f.advance(field,route);check(f.state()==uninterrupted,"turning-point restart differs from uninterrupted cycle");++restarts;record("cycle",false,TCAD_CONST(0.0));}
    }
    std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"attempted\":"<<attempted<<",\"rejected\":"<<rejected<<",\"accepted\":"<<accepted<<",\"preserved\":"<<preserved<<",\"retries\":"<<retries<<",\"unsafe_skipped\":"<<skipped<<",\"valid_cases\":"<<valid<<",\"analytic_cases\":"<<analytic<<",\"restart_cases\":"<<restarts<<",\"max_phi_error\":"<<static_cast<double>(max_phi)<<",\"max_p_error\":"<<static_cast<double>(max_p)<<"}\n";
    check(observe || (attempted==rejected && preserved==rejected && !accepted),"turning-point contract failed");return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
