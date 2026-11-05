#include "lk_material_field.h"
#include <cstdio>
#include <cstdlib>
using namespace tcad;
void emit(real_t value) {
    char buffer[160];
#ifdef TCAD_USE_FLOAT128
    quadmath_snprintf(buffer,sizeof(buffer),"%.38Qg",value);
#else
    snprintf(buffer,sizeof(buffer),"%.26Lg",value);
#endif
    puts(buffer);
}
int main(int argc,char** argv) {
    const int sign=argc>1 ? atoi(argv[1]) : 1;
    Grid3D g{7,1,1,TCAD_CONST(1e-8),TCAD_CONST(1e-7),TCAD_CONST(1e-6)};
    g.xx={0,TCAD_CONST(.3e-8),TCAD_CONST(1.1e-8),TCAD_CONST(2.5e-8),TCAD_CONST(4e-8),TCAD_CONST(5e-8),TCAD_CONST(6.6e-8)};
    std::vector<char> mask={1,1,0,1,1,1,0};
    std::vector<real_t> eps(7),old(21,0),phi(7);
    for(size_t i=0;i<7;++i) {
        eps[i]=(TCAD_CONST(10.0)+i)*TCAD_CONST(8.854187817e-12);
        old[3*i]=sign*(i%2 ? TCAD_CONST(-.014) : TCAD_CONST(.014));
        phi[i]=sign*(i%2 ? TCAD_CONST(-.025) : TCAD_CONST(.05));
    }
    const auto p=solve_lk_material_response_1d(g,eps,mask,old,phi,TCAD_CONST(-1e8),
        TCAD_CONST(1e12),TCAD_CONST(1e9),TCAD_CONST(0.0),TCAD_CONST(0.0),0,0);
    const auto jac=lk_material_susceptibility_1d(g,eps,mask,p,TCAD_CONST(-1e8),
        TCAD_CONST(1e12),TCAD_CONST(1e9),TCAD_CONST(0.0),0,0);
    printf("%d\n",real_mantissa_bits());
    for(const auto& v:{g.xx,eps,old,phi,p,jac}) for(real_t x:v) emit(x);
}
