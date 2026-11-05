#include "gummel_solver.h"
#include <cstdio>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

using namespace tcad;
namespace {
void require(bool ok,const char* message) {if(!ok)throw std::runtime_error(message);}
std::string exact(real_t value) {
    char text[128];
#ifdef TCAD_USE_FLOAT128
    quadmath_snprintf(text,sizeof(text),"%Qa",value);
#else
    std::snprintf(text,sizeof(text),"%La",value);
#endif
    return text;
}
// Independent Newton reference for a strictly increasing BE cubic. The
// fixture has alpha+gamma/dt > 0; no branch-selection code is shared.
real_t root(real_t alpha,real_t beta,real_t rate,real_t old,real_t field) {
    const real_t a=alpha+rate,b=rate*old+field;
    real_t x=b/a;
    for(int i=0;i<40;++i) {
        const real_t y=x-(beta*x*x*x+a*x-b)/(TCAD_CONST(3.0)*beta*x*x+a);
        if(y==x)break;
        x=y;
    }
    return x;
}
}
int main(int argc,char** argv) {
    try {
        const bool observe=argc==2 && std::string(argv[1])=="--observe";
        size_t attempted=0,rejected=0,accepted=0,preserved=0,retries=0;
        size_t valid=0,finite=0,inactive=0,fresh=0;
        real_t max_error=TCAD_CONST(0.0);
        const real_t nan=static_cast<real_t>(std::numeric_limits<double>::quiet_NaN());
        const real_t inf=static_cast<real_t>(std::numeric_limits<double>::infinity());
        const real_t alpha=-TCAD_CONST(1e8),beta=TCAD_CONST(3e12),builtin=TCAD_CONST(2e5);
        const real_t gamma=TCAD_CONST(.1),dt=TCAD_CONST(1e-10),rate=gamma/dt;
        for(int axis=0;axis<3;++axis)for(bool stretched:{false,true})for(bool seeded:{false,true}) {
            Grid3D grid{1,1,1,TCAD_CONST(1e-6),TCAD_CONST(1e-6),TCAD_CONST(1e-6)};
            if(axis==0)grid.nx=5;
            if(axis==1)grid.ny=5;
            if(axis==2)grid.nz=5;
            Vector x{TCAD_CONST(0.0),TCAD_CONST(1e-6),TCAD_CONST(2e-6),TCAD_CONST(3e-6),TCAD_CONST(4e-6)};
            if(stretched) {
                x={TCAD_CONST(0.0),TCAD_CONST(.4e-6),TCAD_CONST(1.3e-6),TCAD_CONST(2.7e-6),TCAD_CONST(4e-6)};
                if(axis==0)grid.xx=x;
                if(axis==1)grid.yx=x;
                if(axis==2)grid.zx=x;
            }
            Vector phi(5),history(15,TCAD_CONST(0.0)),play(10,TCAD_CONST(0.0));
            for(size_t i=0;i<5;++i) {
                phi[i]=-TCAD_CONST(1e5)*x[i];
                for(int c=0;c<3;++c)if(seeded)history[3*i+c]=(static_cast<real_t>(3*i+c)-TCAD_CONST(7.0))*TCAD_CONST(1e-5);
            }
            if(seeded)for(size_t i=0;i<10;++i)play[i]=static_cast<real_t>(i)*TCAD_CONST(.125);
            const std::vector<char> mask{0,1,1,1,0},other{1,0,1,0,1};
            PoissonSolver solver(grid);
            auto configure=[&]() {
                solver.set_ferroelectric(mask,alpha,beta);
                solver.set_ferroelectric_builtin_field(builtin);
                solver.set_ferroelectric_gamma(gamma);solver.set_ferroelectric_polar_axis(axis);
                solver.set_fe_polarization(history);solver.set_fe_play_state(play);
            };
            configure();
            solver.update_ferroelectric_polarization_transient(phi,dt);
            const auto control=solver.fe_polarization();configure();
            auto request=[&](const std::vector<char>& requested,real_t a,real_t b,real_t e,bool field,bool constructor,bool shape) {
                ++attempted;bool caught=false;
                const std::string message=shape?"fe_mask size mismatch":field?"FE builtin field must be finite":"FE alpha and beta must be finite";
                try {
                    if(constructor) {
                        GummelOptions options;options.ferro.enabled=true;options.ferro.fe_mask=requested;
                        options.ferro.alpha=a;options.ferro.beta=b;options.ferro.E_bi=e;
                        GummelSolver coupled(grid,options);
                    } else if(field)solver.set_ferroelectric_builtin_field(e);
                    else solver.set_ferroelectric(requested,a,b);
                } catch(const std::invalid_argument& ex) {
                    require(ex.what()==message,"wrong native FE exception");caught=true;++rejected;
                }
                if(!caught)++accepted;
                if(caught) {
                    require(solver.fe_polarization()==history && solver.fe_play_state()==play,"rejected FE request changed owned history");
                    solver.update_ferroelectric_polarization_transient(phi,dt);
                    require(solver.fe_polarization()==control && solver.fe_play_state()==play,"rejected FE request changed mask, coefficients or dynamics");
                    ++preserved;
                }
                if(!observe)require(caught,"nonfinite native FE input was accepted");
                // Accepted old nonfinite inputs are restored without evaluating
                // them. Constructor objects are destroyed without a solve.
                configure();solver.update_ferroelectric_polarization_transient(phi,dt);
                require(solver.fe_polarization()==control,"native FE valid retry failed");configure();++retries;
            };
            for(bool constructor:{false,true}) {
                for(size_t size:{size_t(0),size_t(4),size_t(6)}) {
                    // Empty masks intentionally bypass constructor FE wiring.
                    if(constructor && !size)continue;
                    request(std::vector<char>(size,1),nan,inf,builtin,false,constructor,true);
                }
                for(real_t bad:{nan,inf,-inf}) {
                    request(other,bad,beta,builtin,false,constructor,false);
                    request(other,alpha,bad,builtin,false,constructor,false);
                    request(mask,alpha,beta,bad,true,constructor,false);
                }
            }
            for(real_t bad:{nan,inf,-inf})for(bool bad_beta:{false,true}) {
                PoissonSolver pristine(grid);bool caught=false;++attempted;
                try {pristine.set_ferroelectric(other,bad_beta?alpha:bad,bad_beta?bad:beta);}
                catch(const std::invalid_argument& ex) {
                    require(std::string(ex.what())=="FE alpha and beta must be finite","wrong pristine FE exception");caught=true;++rejected;
                }
                if(!caught)++accepted;
                else {
                    require(pristine.fe_polarization().empty() && pristine.fe_play_state().empty(),"pristine rejected FE request allocated history");
                    pristine.update_ferroelectric_polarization_transient({},TCAD_CONST(-1.0));
                    ++preserved;++fresh;
                }
                if(!observe)require(caught,"nonfinite native FE input was accepted");
                pristine.set_ferroelectric(mask,alpha,beta);pristine.set_ferroelectric_builtin_field(builtin);
                pristine.set_ferroelectric_gamma(gamma);pristine.set_ferroelectric_polar_axis(axis);
                pristine.set_fe_polarization(history);pristine.set_fe_play_state(play);
                pristine.update_ferroelectric_polarization_transient(phi,dt);
                require(pristine.fe_polarization()==control && pristine.fe_play_state()==play,"pristine FE retry failed");++retries;
            }
            for(bool enabled:{false,true}) {
                GummelOptions options;options.ferro.enabled=enabled;
                options.ferro.fe_mask=enabled?std::vector<char>{}:mask;
                options.ferro.alpha=nan;options.ferro.beta=inf;options.ferro.E_bi=-inf;
                GummelSolver bypass(grid,options);
                require(bypass.fe_polarization().empty() && bypass.fe_play_state().empty(),"inactive constructor configured FE");++inactive;
            }
            // Legal sign/range policy belongs to the setter, distinct from the
            // positive-beta requirement when actually advancing LK dynamics.
            Vector limits{TCAD_CONST(-0.0),TCAD_CONST(0.0),TCAD_CONST(-1e300),TCAD_CONST(1e300)};
#ifdef TCAD_USE_FLOAT128
            limits.push_back(TCAD_CONST(-1e400));limits.push_back(TCAD_CONST(1e400));
#endif
            for(real_t value:limits)for(int slot=0;slot<3;++slot) {
                require(isfinite_q(value),"FE range fixture must be finite");
                if(slot==2)solver.set_ferroelectric_builtin_field(value);
                else solver.set_ferroelectric(other,slot==0?value:alpha,slot==1?value:beta);
                require(solver.fe_polarization()==history && solver.fe_play_state()==play,"finite FE replacement erased history");
                ++finite;configure();solver.update_ferroelectric_polarization_transient(phi,dt);
                require(solver.fe_polarization()==control,"finite FE range restore failed");configure();
            }
            for(bool replace_mask:{false,true})for(bool positive:{false,true})for(bool cross:{false,true})for(real_t e:{-builtin,TCAD_CONST(0.0),builtin}) {
                const auto& region=replace_mask?other:mask;
                const real_t a=positive?TCAD_CONST(1e8):alpha,b=positive?TCAD_CONST(1e12):beta;
                const int polar=cross?(axis+1)%3:axis;
                solver.set_ferroelectric(region,a,b);solver.set_ferroelectric_builtin_field(e);
                solver.set_ferroelectric_polar_axis(polar);solver.set_fe_polarization(history);solver.set_fe_play_state(play);
                solver.update_ferroelectric_polarization_transient(phi,dt);
                const auto& result=solver.fe_polarization();
                for(size_t i=0;i<5;++i)for(int c=0;c<3;++c) {
                    const real_t field=(c==axis?TCAD_CONST(1e5):TCAD_CONST(0.0))-(c==polar?e:TCAD_CONST(0.0));
                    const real_t expected=region[i]?root(a,b,rate,history[3*i+c],field):TCAD_CONST(0.0);
                    const real_t error=abs_q(result[3*i+c]-expected);
                    require(isfinite_q(error) && error<=TCAD_CONST(4096.0)*epsilon_q()*(TCAD_CONST(1.0)+abs_q(expected)),"independent native FE backward-Euler cubic mismatch");
                    if(error>max_error)max_error=error;
                }
                require(solver.fe_play_state()==play,"LK update changed scalar-model play memory");
                std::cout<<"{\"case\":"<<++valid<<",\"values\":[";
                for(size_t i=0;i<result.size();++i)std::cout<<(i?",":"")<<'"'<<exact(result[i])<<'"';
                std::cout<<"]}\n";
            }
        }
        std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()
                 <<",\"attempted\":"<<attempted<<",\"rejected\":"<<rejected<<",\"accepted\":"<<accepted
                 <<",\"preserved\":"<<preserved<<",\"retries\":"<<retries<<",\"valid_cases\":"<<valid
                 <<",\"finite_cases\":"<<finite<<",\"inactive_cases\":"<<inactive<<",\"fresh_disabled_checks\":"<<fresh
                 <<",\"max_reference_error\":"<<static_cast<double>(max_error)<<"}\n";
        require(observe || (attempted==rejected && preserved==rejected && !accepted),"native FE finiteness contract failed");
        return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
