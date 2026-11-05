// Qualify the historical hard cutoffs without differentiating across jumps.
#include <linearized_wkb.h>
#include <cstdio>
#include <iostream>
#include <string>
using namespace tcad;
namespace {
std::string exact(real_t value) {
    char buffer[160];
#ifdef TCAD_USE_FLOAT128
    quadmath_snprintf(buffer,sizeof(buffer),"%Qa",value);
#else
    std::snprintf(buffer,sizeof(buffer),"%La",value);
#endif
    return buffer;
}
struct Fixture {
    Grid3D grid;
    Vector phi;
    size_t node;
    Fixture(int mesh,bool fraction,int sign,double spacing,double field)
        :grid{9,1,1,(real_t)spacing,1,1},node(fraction?4:1) {
        for(size_t i=0;i<9;++i) {
            if(mesh)grid.xx.push_back((real_t)spacing*i+(mesh==2?TCAD_CONST(0x1p-10):0));
            phi.push_back((real_t)sign*(real_t)field*(real_t)spacing*i);
        }
    }
};
// Instrument the numerical action separately from the production source.
// Independent Python reconstruction also checks the physical Simpson action.
struct Action {double field,length,integral;bool field_limited;real_t derivative;};
Action action(const Fixture& f,real_t gap,const LinearizedWKBParameters& p) {
    const double q=1.602176634e-19,hbar=1.054571817e-34;
    const double field=std::fabs(linearized_wkb_x_field(f.grid,f.phi,f.node));
    const double spacing=(double)f.grid.dx;
    const double available=std::min((double)f.node*spacing,(double)(8-f.node)*spacing);
    const double cap=p.path_fraction>0?std::min(available,(double)p.path_fraction*(8*spacing)):available;
    const double field_length=2*((double)gap*q/(q*field));
    bool limited=field_length<=cap;
    double length=std::min(field_length,cap);
    if(std::fabs(field_length-cap)<=std::fabs(cap)/256) {
        limited=2*gap<=(real_t)field*(real_t)cap;
        length=limited?(double)(2*gap/(real_t)field):cap;
    }
    const size_t n=p.segments>=4?p.segments+p.segments%2:p.segments;
    const double mass=(double)p.mass*9.1093837015e-31,energy=(double)gap*q;
    double integral=0;real_t derivative=0;
    if(n<4)integral=std::sqrt(2*mass*energy)/hbar*length;
    else {
        const double h=length/(double)n;
        for(size_t s=0;s<=n;++s) {
            const double x=(double)s*h;
            const double barrier=limited?(s>=n/2?0:energy*(double)(n-2*s)/(double)n):std::max(energy-q*field*x,0.0);
            if(barrier<=0)continue;
            const double coefficient=s==0||s==n?1:s%2?4:2;
            const double integrand=std::sqrt(2*mass*barrier)/hbar;
            integral+=coefficient*integrand;
            if(!limited)derivative+=(real_t)(coefficient*integrand)*TCAD_CONST(.5)*(-(real_t)q*(real_t)x)/(real_t)barrier;
        }
        integral*=h/3;derivative*=(real_t)h/3;
    }
    if(limited)derivative=-(real_t)integral/(real_t)field;
    return {field,length,integral,limited,derivative};
}
size_t cases=0,failed=0,exact_transmission=0,missing_exact_transmission=0;
void emit(const char* kind,int mesh,bool fraction,bool limited,int sign,int side,
          double spacing,double field,real_t gap,real_t mass,real_t power,
          real_t weight,size_t segments) {
    Fixture f(mesh,fraction,sign,spacing,field);
    // Center the field-threshold fixture at the observed node. The implicit
    // stencil converts potentials to double before subtracting: an offset
    // can otherwise round an intended nextafter(1,+inf) field back to 1.
    if(std::string(kind)=="field")for(size_t i=0;i<f.phi.size();++i)
        f.phi[i]=(real_t)sign*(real_t)field*(real_t)spacing*((real_t)i-(real_t)f.node);
    LinearizedWKBParameters p{std::string(kind)=="transmission"?TCAD_CONST(1e300):TCAD_CONST(1.0),power,mass,fraction?TCAD_CONST(.125):TCAD_CONST(0.0),segments};
    const auto a=action(f,gap,p);
    const bool active=a.field>1&&a.length>=1e-12&&-2*a.integral>=-700;
    const auto got=evaluate_linearized_wkb(f.grid,f.phi,f.node,gap,p,weight,true);
    const auto value_only=evaluate_linearized_wkb(f.grid,f.phi,f.node,gap,p,weight,false);
    const real_t expected=active?p.A*TCAD_CONST(1e6)*pow_q((real_t)a.field,power)*exp_q((real_t)(-2*a.integral))*weight:0;
    const real_t expected_derivative=active?expected*(power/(real_t)a.field-2*a.derivative):0;
    const real_t scale=std::max(TCAD_CONST(1e-4000),std::max(abs_q(expected_derivative),abs_q(expected/(real_t)a.field)));
    const real_t rate_error=expected?abs_q(got.generation-expected)/abs_q(expected):abs_q(got.generation);
    const real_t derivative_error=abs_q(got.d_generation_d_field-expected_derivative)/scale;
    const bool fd_checked=active&&std::abs(side)==2;
    real_t fd[2]={0,0},fd_error=0;
    if(fd_checked)for(int k=0;k<2;++k) {
        const real_t step=k?TCAD_CONST(0x1p-24):TCAD_CONST(0x1p-22);
        Vector lo=f.phi,hi=f.phi;for(auto& v:lo)v*=1-step;for(auto& v:hi)v*=1+step;
        fd[k]=(evaluate_linearized_wkb(f.grid,hi,f.node,gap,p,weight).generation-evaluate_linearized_wkb(f.grid,lo,f.node,gap,p,weight).generation)/(2*(real_t)a.field*step);
        fd_error=std::max(fd_error,abs_q(fd[k]-got.d_generation_d_field)/scale);
    }
    bool passed=isfinite_q(got.generation)&&isfinite_q(got.d_generation_d_field)&&got.generation==value_only.generation&&value_only.d_generation_d_field==0&&rate_error<TCAD_CONST(1e-10)&&derivative_error<TCAD_CONST(1e-10)&&fd_error<TCAD_CONST(2e-5);
    if(std::string(kind)=="field")passed=passed&&a.field==field&&active==(side>0);
    if(std::string(kind)=="length")passed=passed&&a.length==spacing&&active==(side>=0);
    if(std::string(kind)=="transmission")passed=passed&&a.field_limited==limited&&active==(side<=0)&&(side!=0||a.integral==350);
    ++cases;if(!passed)++failed;
    std::cout<<"{\"case\":"<<cases<<",\"kind\":\""<<kind<<"\",\"mesh\":"<<mesh<<",\"fraction_window\":"<<(fraction?"true":"false")<<",\"field_limited\":"<<(a.field_limited?"true":"false")<<",\"sign\":"<<sign<<",\"side\":"<<side<<",\"segments\":"<<segments
        <<",\"spacing\":\""<<exact((real_t)spacing)<<"\",\"target_field\":\""<<exact((real_t)field)<<"\",\"field\":\""<<exact((real_t)a.field)<<"\",\"length\":\""<<exact((real_t)a.length)<<"\",\"action\":\""<<exact((real_t)a.integral)<<"\",\"gap\":\""<<exact(gap)<<"\",\"mass\":\""<<exact(mass)<<"\",\"A\":\""<<exact(p.A)<<"\",\"D\":\""<<exact(power)<<"\",\"weight\":\""<<exact(weight)
        <<"\",\"generation\":\""<<exact(got.generation)<<"\",\"derivative\":\""<<exact(got.d_generation_d_field)<<"\",\"active\":"<<(active?"true":"false")<<",\"fd_checked\":"<<(fd_checked?"true":"false")<<",\"fd_coarse\":\""<<exact(fd[0])<<"\",\"fd_fine\":\""<<exact(fd[1])<<"\",\"fd_error\":\""<<exact(fd_error)<<"\",\"passed\":"<<(passed?"true":"false")<<"}\n";
}
}
int main() {try {
    const double inf=std::numeric_limits<double>::infinity();
    for(int mesh=0;mesh<3;++mesh)for(bool fraction:{false,true})for(int sign:{-1,1})
    for(real_t power:{TCAD_CONST(-2.0),TCAD_CONST(0.0),TCAD_CONST(2.0)})
    for(real_t weight:{TCAD_CONST(-.5),TCAD_CONST(.5)})for(size_t segments:{2,3,7,32})
    for(int side:{-2,-1,0,1,2}) {
        const double e=side==-2?1-0x1p-18:side==-1?std::nextafter(1.,0.):side==0?1:side==1?std::nextafter(1.,inf):1+0x1p-18;
        emit("field",mesh,fraction,false,sign,side,0x1p-20,e,TCAD_CONST(1.0),TCAD_CONST(1e-12),power,weight,segments);
        const double l=side==-2?1e-12*(1-0x1p-18):side==-1?std::nextafter(1e-12,0.):side==0?1e-12:side==1?std::nextafter(1e-12,inf):1e-12*(1+0x1p-18);
        emit("length",mesh,fraction,false,sign,side,l,0x1p24,TCAD_CONST(1.25),TCAD_CONST(.01),power,weight,segments);
    }
    for(int mesh=0;mesh<3;++mesh)for(bool fraction:{false,true})for(bool limited:{false,true})for(int sign:{-1,1})
    for(real_t power:{TCAD_CONST(0.0),TCAD_CONST(2.0)})for(real_t weight:{TCAD_CONST(-.5),TCAD_CONST(.5)})for(size_t segments:{2,3,7,32}) {
        const real_t gap=limited?TCAD_CONST(.25):TCAD_CONST(1.25);
        Fixture f(mesh,fraction,sign,0x1p-20,0x1p20);
        LinearizedWKBParameters p{1,power,1,fraction?TCAD_CONST(.125):TCAD_CONST(0.0),segments};
        auto measure=[&](double mass){p.mass=(real_t)mass;return action(f,gap,p).integral;};
        const double coefficient=measure(1),mass0=(350/coefficient)*(350/coefficient);
        // Locate the adjacent binary64 masses around the *numerical* cutoff.
        // A representable equality is tested only when action really is 350.
        double below=mass0;size_t search=0;
        while(measure(below)>=350) {below=std::nextafter(below,0.);if(++search>4096)throw std::runtime_error("mass search lower bound");}
        while(measure(std::nextafter(below,inf))<350) {below=std::nextafter(below,inf);if(++search>4096)throw std::runtime_error("mass search upper bound");}
        double above=std::nextafter(below,inf),equal=0;
        while(measure(above)<=350) {if(measure(above)==350)equal=above;above=std::nextafter(above,inf);if(++search>4096)throw std::runtime_error("mass equality search");}
        if(equal)++exact_transmission;else ++missing_exact_transmission;
        for(int side:{-2,-1,0,1,2}) {
            if(side==0&&!equal)continue;
            const double mass=side==-2?mass0*(1-0x1p-18)*(1-0x1p-18):side==-1?below:side==0?equal:side==1?above:mass0*(1+0x1p-18)*(1+0x1p-18);
            emit("transmission",mesh,fraction,limited,sign,side,0x1p-20,0x1p20,gap,(real_t)mass,power,weight,segments);
        }
    }
    std::cout<<"{\"summary\":true,\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"cases\":"<<cases<<",\"exact_transmission_fixtures\":"<<exact_transmission<<",\"missing_exact_transmission_fixtures\":"<<missing_exact_transmission<<",\"failed\":"<<failed<<"}\n";
    return failed?1:0;
}catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 2;}}
