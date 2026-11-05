#include "lk_material_field.h"
#include <cstdio>
#include <string>
using namespace tcad;

void emit(real_t value) {
    char buffer[160];
#ifdef TCAD_USE_FLOAT128
    quadmath_snprintf(buffer,sizeof(buffer),"%.38Qg",value);
#else
    snprintf(buffer,sizeof(buffer),"%.26Lg",value);
#endif
    printf("%s\n",buffer);
}

int main(int argc,char** argv) {
    const int sign=argc>1 && std::string(argv[1])=="negative" ? -1 : 1;
    Grid3D g{9,1,1,TCAD_CONST(1e-9),TCAD_CONST(1e-7),TCAD_CONST(1e-6)};
    g.xx={0,TCAD_CONST(.3e-9),TCAD_CONST(1.1e-9),TCAD_CONST(2.5e-9),
        TCAD_CONST(4e-9),TCAD_CONST(5e-9),TCAD_CONST(6.6e-9),TCAD_CONST(7e-9),TCAD_CONST(8e-9)};
    std::vector<real_t> eps(9),old(27,0),p(27,0),phi(9,0);
    std::vector<char> mask(9,1);mask[7]=mask[8]=0;
    for(size_t i=0;i<9;++i) {
        eps[i]=(mask[i] ? TCAD_CONST(15.0)+i : TCAD_CONST(3.9))*TCAD_CONST(8.8542e-12);
        if(mask[i]) old[3*i]=sign*(i%2 ? TCAD_CONST(-1.4) : TCAD_CONST(1.4));
    }
    std::vector<std::vector<real_t>> samples;
    bool ok=solve_lk_material_chain(g,eps,mask,old,TCAD_CONST(-649519052.838329),
        TCAD_CONST(331387271.85629034),TCAD_CONST(.1),TCAD_CONST(0.0),TCAD_CONST(0.0),
        0,0,TCAD_CONST(5e-11),TCAD_CONST(0.0),-sign*TCAD_CONST(.25),80,phi,p,samples);
    if(!ok) return 1;
    printf("%d\n",real_mantissa_bits());
    for(real_t x:g.xx) emit(x);
    for(real_t e:eps) emit(e);
    for(real_t v:old) emit(v);
    for(real_t v:p) emit(v);
    for(real_t v:phi) emit(v);
    for(real_t v:samples.back()) emit(v);
    // A very small polynomial perturbation must survive at native precision.
    emit(lk_monotone_cubic(TCAD_CONST(1.0),TCAD_CONST(1e-25),TCAD_CONST(1.0)));
}
