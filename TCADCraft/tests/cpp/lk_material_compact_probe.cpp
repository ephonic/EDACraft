#include "lk_material_field.h"
#include <cstdio>
#include <cstdlib>
#include <stdexcept>
using namespace tcad;
int main(int argc,char** argv) {
    if(argc!=6 && argc!=7) return 2;
    Grid3D g{size_t(atoi(argv[1])),size_t(atoi(argv[2])),size_t(atoi(argv[3])),
        TCAD_CONST(1e-8),TCAD_CONST(1.3e-8),TCAD_CONST(1.7e-8)};
    const int polar=atoi(argv[4]);const bool partial=atoi(argv[5]);
    const size_t n=g.npts(),sizes[]={g.nx,g.ny,g.nz},strides[]={1,g.nx,g.nx*g.ny};
    if(argc==7) for(int a=0;a<3;++a) if(sizes[a]>1)
        for(int side=0;side<2;++side) g.lk_zero_d_faces[2*a+side]=atoi(argv[6])&(1<<(2*a+side));
    std::vector<real_t>* axes[]={&g.xx,&g.yx,&g.zx};
    for(int a=0;a<3;++a) for(size_t q=0;q<sizes[a];++q)
        axes[a]->push_back(TCAD_CONST(1e-8)*(q+TCAD_CONST(.07)*q*q)*(a+1));
    std::vector<real_t> eps(n),phi(n),old(3*n,0);std::vector<char> mask(n);
    for(size_t i=0;i<n;++i) {
        eps[i]=(TCAD_CONST(8.0)+i%7)*EPS0;mask[i]=!partial || i%3!=0;
        phi[i]=TCAD_CONST(.03)*int(i%5)-TCAD_CONST(.05);
        for(int a=0;a<3;++a) old[3*i+a]=TCAD_CONST(.001)*int((i+a)%4)-TCAD_CONST(.0015);
    }
    const real_t alpha=TCAD_CONST(-1e8),beta=TCAD_CONST(1e12),rate=TCAD_CONST(1e9),depol=TCAD_CONST(17.0);
    auto response=[&](const std::vector<real_t>& v) {return solve_lk_material_response_nd(
        g,eps,mask,old,v,alpha,beta,rate,TCAD_CONST(2e4),depol,polar,0);};
    const auto p=response(phi);
    const auto dense=lk_material_susceptibility_nd(g,eps,mask,p,alpha,beta,rate,depol,polar,0);
    const auto packed=lk_material_susceptibility_lines(g,eps,mask,p,alpha,beta,rate,depol,polar,0);
    size_t expected=0;for(int a=0;a<3;++a) if(sizes[a]>1) expected+=n*sizes[a];
    if(packed.size()!=expected) throw std::runtime_error("storage count");
    real_t worst=0,scale=0;const real_t h=TCAD_CONST(1e-12);
    for(size_t c=0;c<n;++c) {
        auto plus=phi,minus=phi;plus[c]+=h;minus[c]-=h;
        const auto pp=response(plus),pm=response(minus);
        for(int a=0;a<3;++a) for(size_t r=0;r<n;++r) {
            real_t d=0;
            if(sizes[a]>1 && r-((r/strides[a])%sizes[a])*strides[a]==c-((c/strides[a])%sizes[a])*strides[a])
                d=packed[lk_material_line_offset(g,a)+r*sizes[a]+(c/strides[a])%sizes[a]];
            if(d!=dense[(a*n+r)*n+c]) throw std::runtime_error("dense equivalence");
            const real_t fd=(pp[3*r+a]-pm[3*r+a])/(TCAD_CONST(2.0)*h);
            worst=std::max(worst,abs_q(d-fd));scale=std::max(scale,abs_q(d));
        }
    }
    if(worst>TCAD_CONST(1e-17)*std::max(scale,TCAD_CONST(1e-30)))
        throw std::runtime_error("finite difference");
    printf("%d %zu %zu %zu\n",real_mantissa_bits(),n,packed.size(),dense.size());
}
