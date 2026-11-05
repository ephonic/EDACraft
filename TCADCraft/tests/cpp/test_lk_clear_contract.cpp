// Static LK after explicit clear: pristine zero state, continuation and Gauss law.
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
void prepare_clear(Fixture& f,int protocol){
    if(protocol==1)f.update(f.drive(TCAD_CONST(3e5)),0);
    if(protocol==2){f.solver.set_ferroelectric_model(1);f.update(f.drive(-TCAD_CONST(3e5)),0);}
    f.solver.set_fe_polarization({});
    f.solver.set_ferroelectric_model(0);
}
int main(int argc,char** argv){try{
    if(argc==5 && std::string(argv[1])=="--probe"){
        Fixture f(std::stoi(argv[2]),std::stoi(argv[3])!=0,0,false);
        prepare_clear(f,std::stoi(argv[4]));const auto memory=f.solver.fe_play_state();
        f.update(f.drive(TCAD_CONST(2e5)),0);
        check(f.solver.fe_polarization().size()==9 && f.solver.fe_play_state()==memory,"clear probe failed");
        std::cout<<"{\"probe_initialized\":true}\n";return 0;
    }
    const bool observe=argc==2 && std::string(argv[1])=="--observe";
    size_t refs=0,clears=0,roots=0,restarts=0,guards=0,transient=0,noops=0;
    real_t max_phi=TCAD_CONST(0.0),max_p=TCAD_CONST(0.0);
    for(int axis=0;axis<3;++axis)for(bool stretched:{false,true})for(int protocol=0;protocol<3;++protocol)
      for(int correction=0;correction<3;++correction)for(int sign=-1;sign<=1;++sign){
        Fixture f(axis,stretched,0,false),control(axis,stretched,0,false);
        const real_t imprint=correction==1?TCAD_CONST(2e4):TCAD_CONST(0.0);
        for(auto* fixture:{&f,&control}){
            fixture->solver.set_ferroelectric_builtin_field(imprint);
            fixture->solver.set_ferroelectric_depol(correction==2?TCAD_CONST(25.0):TCAD_CONST(0.0));
            prepare_clear(*fixture,protocol);
        }
        control.solver.set_fe_polarization(Vector(9,TCAD_CONST(0.0)));
        // Never execute cleared-P static LK on an ordinary parent binary.
        if(observe)f.solver.set_fe_polarization(Vector(9,TCAD_CONST(0.0)));
        const real_t field=imprint+static_cast<real_t>(sign)*TCAD_CONST(2e5);
        for(int step=0;step<3;++step){
            const real_t drive=step==0?field:step==1?-TCAD_CONST(1e4):TCAD_CONST(3e5);
            const auto phi=f.drive(drive);f.update(phi,0);control.update(phi,0);
            check(f.state()==control.state(),"cleared LK differs from allocated zero control");
            if(step==0){
                if(!observe)++clears;
                const real_t Ps=sqrt_q(TCAD_CONST(1e8)/TCAD_CONST(3e12));
                for(size_t i=0;i<3;++i)for(int c=0;c<3;++c){
                    const real_t expected=f.mask[i] && c==axis?static_cast<real_t>(sign)*Ps:TCAD_CONST(0.0);
                    const real_t error=abs_q(f.solver.fe_polarization()[3*i+c]-expected);
                    max_p=std::max(max_p,error);check(error<TCAD_CONST(1e-25),"independent pristine LK root mismatch");
                }++roots;
            }
            const auto p=f.solver.fe_polarization(),memory=f.solver.fe_play_state();const auto state=f.state();
            f.solver.set_fe_polarization(p);f.solver.set_fe_play_state(memory);
            check(f.state()==state,"LK saved state restore changed raw equations");++restarts;
            const auto raw=f.raw();const real_t dl=f.x[1]-f.x[0],dr=f.x[2]-f.x[1],width=(dl+dr)/TCAD_CONST(2.0);
            const real_t stiff=TCAD_CONST(20.0)*EPS0*(TCAD_CONST(1.0)/dl+TCAD_CONST(1.0)/dr)/width;
            const real_t div=((f.mask[2]?p[6+axis]:TCAD_CONST(0.0))-(f.mask[0]?p[axis]:TCAD_CONST(0.0)))/(TCAD_CONST(2.0)*width);
            const real_t error=abs_q(raw[1]-(TCAD_CONST(.1)*dl/(dl+dr)-div/stiff));
            max_phi=std::max(max_phi,error);check(isfinite_q(error) && error<TCAD_CONST(1e-18),"independent cleared LK Gauss mismatch");
            std::cout<<"{\"case\":"<<++refs<<",\"values\":[";
            const auto values=f.state();for(size_t i=0;i<values.size();++i)std::cout<<(i?",":"")<<'"'<<exact(values[i])<<'"';
            std::cout<<"]}\n";
        }
    }
    const real_t nan=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN());
    for(int axis=0;axis<3;++axis)for(bool stretched:{false,true})for(int protocol=0;protocol<3;++protocol){
        Fixture f(axis,stretched,0,false);prepare_clear(f,protocol);const auto memory=f.solver.fe_play_state();
        for(const Vector& phi:std::vector<Vector>{{},Vector(2,TCAD_CONST(0.0)),Vector(4,nan),Vector(3,nan)}){
            try{f.update(phi,0);throw std::runtime_error("invalid phi accepted after clear");}
            catch(const std::invalid_argument& e){check(std::string(e.what())==(phi.size()==3?"FE potential values must be finite":"FE potential size mismatch"),"clear phi error priority");}
            check(f.solver.fe_polarization().empty() && f.solver.fe_play_state()==memory,"clear phi rejection changed state");++guards;
        }
        for(real_t dt:{TCAD_CONST(0.0),-TCAD_CONST(1.0),nan,TCAD_CONST(1e-10)}){
            try{f.update(f.drive(TCAD_CONST(2e5)),1,dt);throw std::runtime_error("transient empty P accepted");}
            catch(const std::invalid_argument& e){check(std::string(e.what())==(isfinite_q(dt)&&dt>TCAD_CONST(0.0)?"LK requires finite fields/coefficients and positive beta":"FE transient dt must be finite and positive"),"transient clear diagnostic changed");}
            check(f.solver.fe_polarization().empty() && f.solver.fe_play_state()==memory,"transient clear rejection changed state");++transient;
        }
        f.solver.set_ferroelectric(std::vector<char>(3,0),-TCAD_CONST(1e8),TCAD_CONST(3e12));
        f.solver.set_fe_polarization({});f.update(f.drive(TCAD_CONST(2e5)),0);
        check(f.solver.fe_polarization().empty() && f.solver.fe_play_state()==memory,"zero support clear should remain no-op");++noops;
        Fixture disabled(axis,stretched,0,true,false);
        for(int route=0;route<2;++route){disabled.update(Vector(3,nan),route,TCAD_CONST(0.0));
            check(disabled.solver.fe_polarization().empty() && disabled.solver.fe_play_state()==disabled.memory,"disabled clear no-op changed");++noops;}
    }
    std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()
      <<",\"valid_cases\":"<<refs<<",\"cleared_initializations\":"<<clears<<",\"independent_root_cases\":"<<roots
      <<",\"restart_cases\":"<<restarts<<",\"potential_guards\":"<<guards<<",\"transient_guards\":"<<transient
      <<",\"noops\":"<<noops<<",\"max_phi_error\":"<<static_cast<double>(max_phi)<<",\"max_p_error\":"<<static_cast<double>(max_p)<<"}\n";
    return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
