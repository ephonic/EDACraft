// DG mask shape rejection, confinement cache preservation and valid closures.
#include "density_gradient.h"
#include <algorithm>
#include <cstdio>
#include <iostream>
#include <stdexcept>
#include <string>
using namespace tcad;
namespace {
void check(bool b,const char* m){if(!b)throw std::runtime_error(m);}
std::string exact(real_t x){char b[128];
#ifdef TCAD_USE_FLOAT128
    quadmath_snprintf(b,sizeof(b),"%Qa",x);
#else
    std::snprintf(b,sizeof(b),"%La",x);
#endif
    return b;
}
struct Fixture {
    Grid3D grid;Vector x,n,p;std::vector<char> mask;DensityGradient dg;
    static Grid3D make_grid(int axis,bool stretched){
        Grid3D g{1,1,1,TCAD_CONST(1e-8),TCAD_CONST(1e-8),TCAD_CONST(1e-8)};
        Vector x{TCAD_CONST(0.0),TCAD_CONST(.6e-8),TCAD_CONST(1.5e-8),TCAD_CONST(2.7e-8),TCAD_CONST(4e-8)};
        if(axis==0){g.nx=5;if(stretched)g.xx=x;}if(axis==1){g.ny=5;if(stretched)g.yx=x;}if(axis==2){g.nz=5;if(stretched)g.zx=x;}
        return g;
    }
    Fixture(int axis,bool stretched,int closure,int kind):grid(make_grid(axis,stretched)),
      x{TCAD_CONST(0.0),TCAD_CONST(1e-8),TCAD_CONST(2e-8),TCAD_CONST(3e-8),TCAD_CONST(4e-8)},dg(grid){
        if(stretched)x={TCAD_CONST(0.0),TCAD_CONST(.6e-8),TCAD_CONST(1.5e-8),TCAD_CONST(2.7e-8),TCAD_CONST(4e-8)};
        if(kind==1)mask=std::vector<char>(5,0);if(kind==2)mask=std::vector<char>(5,1);
        if(kind==3)mask={0,-1,2,1,0};
        dg.set_silicon_multivalley(closure==1);
        dg.set_step_boundary(closure==2,TCAD_CONST(.1),TCAD_CONST(.15),TCAD_CONST(.42),TCAD_CONST(1.0),TCAD_CONST(1.0),TCAD_CONST(1.0),TCAD_CONST(.5),TCAD_CONST(.5));
        dg.set_effective_dos(Vector(5,TCAD_CONST(2.780e25)),Vector(5,TCAD_CONST(3.143e25)));
        dg.set_semiconductor_mask(mask);carriers(1);
    }
    void carriers(int profile){n=Vector(5,TCAD_CONST(1e20));p=n;
        if(profile==1){Vector rn{TCAD_CONST(1.0),TCAD_CONST(3.0),TCAD_CONST(4.0),TCAD_CONST(3.0),TCAD_CONST(1.0)},rp{TCAD_CONST(1.0),TCAD_CONST(2.0),TCAD_CONST(3.0),TCAD_CONST(2.0),TCAD_CONST(1.0)};
            for(size_t i=0;i<5;++i){n[i]*=rn[i]*rn[i];p[i]*=rp[i]*rp[i];}}
        if(profile==2){n=Vector(5,TCAD_CONST(1e26));p=n;}}
    Vector state(bool full=true){Vector qn,qp,nq,pq,ln,lp;dg.quantum_potential(n,p,qn,qp);dg.correct(n,p,nq,pq);
        if(full)dg.quantum_potential_potential_form(n,p,Vector(5,TCAD_CONST(0.0)),Vector(5,TCAD_CONST(0.0)),ln,lp);
        Vector v;for(const auto* a:{&qn,&qp,&nq,&pq,&ln,&lp}){for(auto z:*a)check(isfinite_q(z),"DG output is nonfinite");v.insert(v.end(),a->begin(),a->end());}return v;}
    bool active(size_t i)const{return mask.empty() || mask[i]!=0;}
    // Independent one-dimensional finite-volume curvature and flat-well limit.
    Vector oracle(const Vector& f,real_t b,real_t dos)const{Vector q(5,TCAD_CONST(0.0));
        const real_t well=mask.size()==5 && !mask[0] && !mask[4] && mask[1] && mask[2] && mask[3]
            ?(x[3]+x[4]-x[0]-x[1])/TCAD_CONST(2.0):TCAD_CONST(0.0);
        for(size_t i=0;i<5;++i){
            if(!active(i) || f[i]>=TCAD_CONST(5e25))continue;
            if(i>0 && i<4 && (active(i-1)||active(i+1))){const real_t hm=x[i]-x[i-1],hp=x[i+1]-x[i];
                const real_t a=active(i-1)?sqrt_q(f[i-1]):TCAD_CONST(0.0),c=sqrt_q(f[i]),d=active(i+1)?sqrt_q(f[i+1]):TCAD_CONST(0.0);
                q[i]=b*TCAD_CONST(2.0)/(hm+hp)*((d-c)/hp-(c-a)/hm)/c;
            }
            if(well>TCAD_CONST(0.0)){
                if(abs_q(q[i])<=TCAD_CONST(1e-15))q[i]=-TCAD_CONST(9.8696)*b/(well*well)/(TCAD_CONST(1.0)+(f[i]/dos)*(f[i]/dos));
                else q[i]=std::max(-TCAD_CONST(16.0)*TCAD_CONST(.02585),std::min(TCAD_CONST(16.0)*TCAD_CONST(.02585),q[i]));
            }else q[i]=std::max(-TCAD_CONST(4.0)*TCAD_CONST(.02585),std::min(TCAD_CONST(4.0)*TCAD_CONST(.02585),q[i]));
        }return q;
    }
};
}
int main(int argc,char** argv){try{
    const bool observe=argc==2 && std::string(argv[1])=="--observe";
    size_t attempts=0,rejected=0,accepted=0,preserved=0,changed=0,retries=0,refs=0,oracles=0,nulls=0,clears=0;
    real_t max_q=TCAD_CONST(0.0),max_density_relative=TCAD_CONST(0.0);
    for(int axis=0;axis<3;++axis)for(bool stretched:{false,true})for(int closure=0;closure<3;++closure)for(int kind=0;kind<4;++kind){
        Fixture f(axis,stretched,closure,kind);const auto full_control=f.state(),control=f.state(false);
        for(size_t length:{size_t(1),size_t(2),size_t(4),size_t(6),size_t(10)})for(int pattern=0;pattern<2;++pattern){
            std::vector<char> bad(length,0);if(pattern)for(size_t i=0;i<length;++i)bad[i]=(i%3==0?0:i%2?-1:2);
            ++attempts;bool caught=false;
            try{f.dg.set_semiconductor_mask(bad);}catch(const std::invalid_argument& e){check(std::string(e.what())=="DG semiconductor mask size mismatch","wrong DG mask diagnostic");caught=true;++rejected;}
            if(!caught)++accepted;
            const auto after=f.state(false);if(caught){check(after==control,"DG rejected mask changed density/confinement state");++preserved;}
            else if(after!=control)++changed;
            check(observe || caught,"malformed DG mask was accepted");
            f.dg.set_semiconductor_mask(f.mask);check(f.state(false)==control,"DG valid mask retry mismatch");++retries;
        }
        check(f.state()==full_control,"DG potential-form state changed after rejection/retry cycle");
        for(int profile=0;profile<3;++profile){
            f.carriers(profile);const auto v=f.state();
            if(closure==0){const auto qn=f.oracle(f.n,TCAD_CONST(4.885e-20),TCAD_CONST(2.780e25)),qp=f.oracle(f.p,TCAD_CONST(3.432e-20),TCAD_CONST(3.143e25));
                for(size_t i=0;i<5;++i){max_q=std::max(max_q,std::max(abs_q(v[i]-qn[i]),abs_q(v[5+i]-qp[i])));
                    const real_t en=f.n[i]*exp_q(std::max(-TCAD_CONST(4.0),std::min(TCAD_CONST(4.0),qn[i]/TCAD_CONST(.02585))));
                    const real_t ep=f.p[i]*exp_q(std::max(-TCAD_CONST(4.0),std::min(TCAD_CONST(4.0),qp[i]/TCAD_CONST(.02585))));
                    max_density_relative=std::max(max_density_relative,std::max(abs_q(v[10+i]-en)/f.n[i],abs_q(v[15+i]-ep)/f.p[i]));
                }++oracles;
            }
            if(profile==2 || kind==1 || (profile==0 && (kind==0||kind==2))){
                for(size_t i=0;i<5;++i){check(abs_q(v[i])<TCAD_CONST(1e-25) && abs_q(v[5+i])<TCAD_CONST(1e-25),"DG null density reference mismatch");
                    check(abs_q(v[20+i])<TCAD_CONST(1e-8) && abs_q(v[25+i])<TCAD_CONST(1e-8),"DG null potential reference mismatch");}++nulls;
            }
            f.dg.set_semiconductor_mask({});Fixture empty(axis,stretched,closure,0);empty.carriers(profile);
            check(f.state()==empty.state(),"DG empty mask did not clear confinement");++clears;
            f.dg.set_semiconductor_mask(f.mask);check(f.state()==v,"DG mask clear/restore changed results");
            std::cout<<"{\"case\":"<<++refs<<",\"values\":[";for(size_t i=0;i<v.size();++i)std::cout<<(i?",":"")<<'"'<<exact(v[i])<<'"';std::cout<<"]}\n";
        }
    }
    check(max_q<TCAD_CONST(1e-25) && max_density_relative<TCAD_CONST(1e-25),"independent DG curvature/density mismatch");
    std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"attempted\":"<<attempts<<",\"rejected\":"<<rejected<<",\"accepted\":"<<accepted<<",\"preserved\":"<<preserved<<",\"observable_changes\":"<<changed<<",\"retries\":"<<retries<<",\"valid_cases\":"<<refs<<",\"independent_density_cases\":"<<oracles<<",\"null_cases\":"<<nulls<<",\"clear_restore_cases\":"<<clears<<",\"max_q_error\":"<<static_cast<double>(max_q)<<",\"max_density_relative_error\":"<<static_cast<double>(max_density_relative)<<"}\n";
    return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
