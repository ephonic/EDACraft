// Public Gummel generation API; also run against the unchanged parent core.
#include "gummel_solver.h"
#include <cstdio>
#include <iostream>
#include <string>
#include <vector>
using namespace tcad;
std::string exact(real_t x) {
    char b[160];
#ifdef TCAD_USE_FLOAT128
    quadmath_snprintf(b,sizeof(b),"%Qa",x);
#else
    std::snprintf(b,sizeof(b),"%La",x);
#endif
    return b;
}
int main(int argc,char** argv) {
    bool observe=argc==2 && std::string(argv[1])=="--observe";
    struct Input { real_t A,D,w; };
    const std::vector<Input> inputs={
        {TCAD_CONST(1e300),2,TCAD_CONST(1e-300)},
        {TCAD_CONST(1e308),0,TCAD_CONST(1e-300)},
        {TCAD_CONST(1e-300),80,TCAD_CONST(1e-300)},
        {TCAD_CONST(1e-300),-38,TCAD_CONST(1e300)},
        {TCAD_CONST(1e300),2,-TCAD_CONST(1e-300)},
        {TCAD_CONST(1e-300),80,-TCAD_CONST(1e-300)},
        {0,100,1}, {TCAD_CONST(1e300),2,0},
        {TCAD_CONST(1e300),2,1}, {-TCAD_CONST(1e300),2,1},
        {TCAD_CONST(1e-400),60,TCAD_CONST(1e-30)},
        {TCAD_CONST(1e400),-50,1},
        {TCAD_CONST(1e300),2,TCAD_CONST(1e-400)},
        {TCAD_CONST(1e-300),-38,TCAD_CONST(1e400)},
        {TCAD_CONST(1e-300),-80,TCAD_CONST(1e300)},
        {TCAD_CONST(1e-300),-40,-TCAD_CONST(1e300)},
        {TCAD_CONST(1e16),2,1}
    };
    size_t cases=0,failed=0;
    for(bool explicit_mesh:{false,true}) for(size_t segments:{size_t(2),size_t(32)})
    for(size_t c=0;c<inputs.size();++c) {
        Grid3D g{3,1,1,TCAD_CONST(1e-8),1,1};
        if(explicit_mesh)g.xx={TCAD_CONST(1e-6),TCAD_CONST(1.01e-6),TCAD_CONST(1.02e-6)};
        const auto in=inputs[c]; GummelOptions opt;
        opt.btbt.enabled=opt.btbt.use_nonlocal=true;opt.btbt.A_kane=in.A;
        opt.btbt.D=in.D;opt.btbt.nonlocal_mass=TCAD_CONST(.25);
        opt.btbt.wkb_npts=segments;opt.btbt.tunnel_path_frac=0;
        GummelSolver solver(g,opt);solver.set_mobility(Vector(3,TCAD_CONST(.14)),Vector(3,TCAD_CONST(.05)));
        solver.set_bandgap(Vector(3,TCAD_CONST(1.12)));solver.set_btbt_weight(Vector(3,in.w));
        Vector phi{0,1,2},result;solver.evaluate_btbt_generation(phi,result);
        const real_t q=TCAD_CONST(1.602176634e-19),m0=TCAD_CONST(9.1093837015e-31),hb=TCAD_CONST(1.054571817e-34);
        const real_t field=TCAD_CONST(1e8),length=TCAD_CONST(1e-8),gap=TCAD_CONST(1.12)*q;
        real_t action=0;
        if(segments<4)action=sqrt_q(2*TCAD_CONST(.25)*m0*gap)/hb*length;
        else {
            real_t step=length/static_cast<real_t>(segments);
            for(size_t i=0;i<=segments;++i) {
                real_t barrier=gap-q*field*static_cast<real_t>(i)*step;
                action+=(i==0||i==segments?1:i%2?4:2)*sqrt_q(2*TCAD_CONST(.25)*m0*barrier)/hb;
            }
            action*=step/3;
        }
        real_t expected=0;
        if(in.A!=0 && in.w!=0) {
            real_t logmag=log_q(abs_q(in.A))+log_q(TCAD_CONST(1e6))+in.D*log_q(field)-2*action+log_q(abs_q(in.w));
            bool positive=(in.A>0)==(in.w>0);
            expected=positive && logmag>log_q((real_t)1e50) ? (real_t)1e50 : (positive?1:-1)*exp_q(logmag);
        }
        real_t error=expected==0 ? abs_q(result[1]) : abs_q(result[1]/expected-1);
        bool pass=isfinite_q(result[1]) && result[0]==0 && result[2]==0 && error<TCAD_CONST(3e-11);
        if(!pass)++failed;
        std::cout<<"{\"case\":"<<++cases<<",\"input\":"<<c<<",\"explicit_mesh\":"<<(explicit_mesh?"true":"false")
            <<",\"segments\":"<<segments<<",\"A\":\""<<exact(in.A)<<"\",\"D\":\""<<exact(in.D)
            <<"\",\"weight\":\""<<exact(in.w)<<"\",\"actual\":\""<<exact(result[1])<<"\",\"expected\":\""<<exact(expected)
            <<"\",\"relative_error\":\""<<exact(error)<<"\",\"passed\":"<<(pass?"true":"false")<<"}\n";
    }
    std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"cases\":"<<cases<<",\"failed\":"<<failed<<"}\n";
    return !observe && failed ? 1 : 0;
}
