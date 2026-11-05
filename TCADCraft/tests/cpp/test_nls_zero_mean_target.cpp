// Prescribed three-node potentials have mean drive delta and a finite local
// peak. This tests the existing numerical-zero guard, not a coercive cutoff.
#include "poisson_solver.h"
#include <iostream>
#include <string>
using namespace tcad;
static void number(real_t x) {
    char b[160];
#ifdef TCAD_USE_FLOAT128
    quadmath_snprintf(b,sizeof b,"%.36Qg",x);
#else
    snprintf(b,sizeof b,"%.36Lg",x);
#endif
    std::cout<<'"'<<b<<'"';
}
int main() {
    bool all=true;
    for(int axis=0;axis<3;++axis) for(int stretched=0;stretched<2;++stretched)
    for(int partial=0;partial<2;++partial) for(int seed_sign:{-1,0,1})
    for(int perturb:{-2,-1,0,1,2}) for(real_t amplitude:{TCAD_CONST(.001),TCAD_CONST(1.0),TCAD_CONST(1000.0)}) {
        Grid3D g{size_t(axis==0?3:2),size_t(axis==1?3:2),size_t(axis==2?3:2),
                 TCAD_CONST(.5),TCAD_CONST(.5),TCAD_CONST(.5)};
        const real_t x=stretched?TCAD_CONST(.25):TCAD_CONST(.5);
        const std::vector<real_t> positions{TCAD_CONST(0.0),x,TCAD_CONST(1.0)};
        if(axis==0)g.xx=positions;else if(axis==1)g.yx=positions;else g.zx=positions;
        const real_t delta=amplitude*(perturb==0?TCAD_CONST(0.0):
            ((perturb==-1 || perturb==1)?TCAD_CONST(1e-26):TCAD_CONST(1e-20)))*(perturb<0?-TCAD_CONST(1.0):TCAD_CONST(1.0));
        const real_t seed=seed_sign*TCAD_CONST(.05);
        std::vector<char> mask(g.npts(),1);
        std::vector<real_t> phi(g.npts()),P(3*g.npts(),TCAD_CONST(0.0));
        for(size_t k=0;k<g.nz;++k)for(size_t j=0;j<g.ny;++j)for(size_t i=0;i<g.nx;++i){
            const size_t n=g.index(i,j,k),a=axis==0?i:axis==1?j:k;
            // Partial support excludes a transverse plane; each included
            // column retains the same independent mean-field identity.
            if(partial && (axis==0?j:i)==1)mask[n]=0;
            phi[n]=-(a==1?amplitude:TCAD_CONST(0.0))-delta*positions[a];
            P[3*n+axis]=seed;
        }
        PoissonSolver s(g);
        s.set_ferroelectric(mask,-TCAD_CONST(1e8),TCAD_CONST(1e18));
        s.set_ferroelectric_model(2);s.set_ferroelectric_polar_axis(axis);
        s.set_ferroelectric_preisach(TCAD_CONST(.2),TCAD_CONST(1.0),TCAD_CONST(1.0));
        s.set_ferroelectric_nls(TCAD_CONST(1.0),amplitude,TCAD_CONST(1.0));
        s.set_fe_polarization(P);
        const real_t peak=std::max(abs_q(amplitude/x+delta),abs_q(-amplitude/(TCAD_CONST(1.0)-x)+delta));
        const real_t tolerance=TCAD_CONST(1e-24)*std::max(peak,TCAD_CONST(1.0));
        const bool guarded=abs_q(delta)<=tolerance;
        const real_t target=guarded?seed:(delta>TCAD_CONST(0.0)?TCAD_CONST(.2):-TCAD_CONST(.2));
        const real_t fraction=-expm1_q(-exp_q(-amplitude/peak));
        const real_t reference=seed+fraction*(target-seed);
        s.update_ferroelectric_polarization(phi);
        real_t error=TCAD_CONST(0.0),measured=TCAD_CONST(0.0);
        for(size_t n=0;n<g.npts();++n)for(int c=0;c<3;++c){
            const real_t expected=mask[n] && c==axis?reference:TCAD_CONST(0.0);
            error=std::max(error,abs_q(s.fe_polarization()[3*n+c]-expected));
            if(mask[n] && c==axis)measured=s.fe_polarization()[3*n+c];
        }
        const bool passed=error<TCAD_CONST(1e-28);all=all && passed;
        std::cout<<"{\"axis\":"<<axis<<",\"stretched\":"<<stretched<<",\"partial\":"<<partial
                 <<",\"seed_sign\":"<<seed_sign<<",\"perturb\":"<<perturb<<",\"guarded\":"<<guarded<<",\"amplitude\":";
        number(amplitude);std::cout<<",\"delta\":";number(delta);
        std::cout<<",\"seed\":";number(seed);std::cout<<",\"reference\":";number(reference);
        std::cout<<",\"measured\":";number(measured);std::cout<<",\"error\":";number(error);
        std::cout<<",\"passed\":"<<passed<<"}\n";
    }
    return all?0:1;
}
