#include "lk_material_field.h"
#include <cstdio>
#include <cstdlib>
using namespace tcad;
int main(int argc,char** argv) {
    if(argc!=4) return 2;
    const int normal=atoi(argv[1]),side=atoi(argv[2]);
    const size_t n=atoi(argv[3]);
    const real_t h=TCAD_CONST(1.0)/n;
    Grid3D g{n,n,n,h,h,h};
    g.lk_zero_d_faces[2*normal+side]=true;
    const size_t N=g.npts();
    std::vector<real_t> eps(N,TCAD_CONST(2.0)),p(3*N),phi(N);
    std::vector<char> mask(N,1);
    // Manufactured divergence-free D=(u,-v,0) in a rotated pair of axes.
    // D_normal vanishes on the selected physical face, at coordinate 0 or 1.
    // phi=u*v^2; -grad(phi) and P=D-eps*E are analytic polynomials.
    const int tangent=(normal+1)%3;
    for(size_t k=0;k<n;++k) for(size_t j=0;j<n;++j) for(size_t i=0;i<n;++i) {
        const real_t x[]={h*(i+TCAD_CONST(.5)),h*(j+TCAD_CONST(.5)),h*(k+TCAD_CONST(.5))};
        const real_t v=x[normal]-(side ? TCAD_CONST(1.0):TCAD_CONST(0.0)),u=x[tangent];
        const size_t q=g.index(i,j,k);
        phi[q]=u*v*v;
        p[3*q+normal]=-v+TCAD_CONST(4.0)*u*v;
        p[3*q+tangent]=u+TCAD_CONST(2.0)*v*v;
    }
    const auto fields=lk_material_field_nd(g,eps,mask,p,phi,0);
    auto legacy=g;legacy.lk_zero_d_faces.fill(false);
    const auto old=lk_material_field_nd(legacy,eps,mask,p,phi,0);
    real_t error=0,old_error=0;
    for(size_t k=0;k<n;++k) for(size_t j=0;j<n;++j) for(size_t i=0;i<n;++i) {
        const size_t c[]={i,j,k}; if(c[normal]!=(side ? n-1:0)) continue;
        const real_t x[]={h*(i+TCAD_CONST(.5)),h*(j+TCAD_CONST(.5)),h*(k+TCAD_CONST(.5))};
        const real_t expected=-TCAD_CONST(2.0)*x[tangent]*(x[normal]-(side?TCAD_CONST(1.0):TCAD_CONST(0.0)));
        const size_t q=g.index(i,j,k);
        error=std::max(error,abs_q(fields[3*q+normal]-expected));
        old_error=std::max(old_error,abs_q(old[3*q+normal]-expected));
    }
    printf("%d %.24Le %.24Le\n",real_mantissa_bits(),(long double)error,(long double)old_error);
}
