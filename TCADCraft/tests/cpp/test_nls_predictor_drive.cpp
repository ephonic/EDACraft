// Public, read-only NLS observation on an actual frozen-carrier/P Gauss
// predictor. The bisection below is a diagnostic, not a transient controller.
#include "poisson_solver.h"
#include <algorithm>
#include <iostream>
#include <stdexcept>
using namespace tcad;
using Values=std::vector<real_t>;
static void require(bool good,const char* why){if(!good)throw std::runtime_error(why);}
static void number(real_t value){char b[160];
#ifdef TCAD_USE_FLOAT128
    quadmath_snprintf(b,sizeof b,"%.36Qg",value);
#else
    snprintf(b,sizeof b,"%.36Lg",value);
#endif
    std::cout<<'"'<<b<<'"';
}
static void values(const Values& data){std::cout<<'[';for(size_t i=0;i<data.size();++i){if(i)std::cout<<',';number(data[i]);}std::cout<<']';}
static void drive(const FerroelectricNlsDrive& d){values({d.raw_mean_field,d.mean_field,d.peak_field,d.mean_polarization,d.volume,d.zero_field_tolerance});}
static bool same(const FerroelectricNlsDrive& a,const FerroelectricNlsDrive& b){
    return a.active==b.active && a.raw_mean_field==b.raw_mean_field && a.mean_field==b.mean_field && a.peak_field==b.peak_field && a.mean_polarization==b.mean_polarization && a.volume==b.volume && a.zero_field_tolerance==b.zero_field_tolerance;
}
static void fixture(int dim,int axis,bool partial,int seed,bool depol){
    size_t shape[3]={3,3,3};shape[axis]=5;if(dim==2)shape[(axis+2)%3]=1;
    Grid3D g{shape[0],shape[1],shape[2],TCAD_CONST(1e-7),TCAD_CONST(1.3e-7),TCAD_CONST(.8e-7)};
    Values axes[3];const real_t spacing[3]={g.dx,g.dy,g.dz};
    for(int a=0;a<3;++a){
        for(size_t i=0;i<shape[a];++i)axes[a].push_back(spacing[a]*i*(TCAD_CONST(1.0)+TCAD_CONST(.1)*i));
    }
    g.xx=axes[0];g.yx=axes[1];g.zx=axes[2];const size_t N=g.npts();
    Values eps(N),n(N),p(N),doping(N),P(3*N,TCAD_CONST(0.0));std::vector<char> mask(N,1);
    const real_t builtin=(axis-1)*TCAD_CONST(750.0)+TCAD_CONST(123.0),epsfe=depol?TCAD_CONST(25.0):TCAD_CONST(0.0);
    for(size_t k=0;k<g.nz;++k)for(size_t j=0;j<g.ny;++j)for(size_t i=0;i<g.nx;++i){
        const size_t idx=g.index(i,j,k),xyz[3]={i,j,k};
        eps[idx]=TCAD_CONST(11.7)*TCAD_CONST(8.854187817e-12)*(TCAD_CONST(1.0)+TCAD_CONST(.05)*(i+2*j+3*k));
        n[idx]=TCAD_CONST(1e20)*(TCAD_CONST(1.0)+TCAD_CONST(.04)*i+TCAD_CONST(.03)*j);
        p[idx]=TCAD_CONST(1e20)*(TCAD_CONST(.93)+TCAD_CONST(.025)*k);
        doping[idx]=TCAD_CONST(1e19)*(TCAD_CONST(.6)-TCAD_CONST(.05)*(i+j+k));
        if(partial && (xyz[axis]==0 || (xyz[axis]==3 && xyz[(axis+1)%3]==1)))mask[idx]=0;
        P[3*idx+axis]=seed*TCAD_CONST(1e-6)*(TCAD_CONST(.5)+TCAD_CONST(.03)*(i+2*j+k));
    }
    PoissonSolver s(g);s.set_permittivity(eps);s.set_doping(doping);
    s.set_ferroelectric(mask,-TCAD_CONST(1e8),TCAD_CONST(1e18));s.set_ferroelectric_model(2);s.set_ferroelectric_polar_axis(axis);
    s.set_ferroelectric_preisach(TCAD_CONST(2e-6),TCAD_CONST(1.0),TCAD_CONST(1.0));
    s.set_ferroelectric_builtin_field(builtin);s.set_ferroelectric_depol(epsfe);
    s.set_ferroelectric_nls(TCAD_CONST(1e-11),TCAD_CONST(2000.0),TCAD_CONST(1e-14));s.set_fe_polarization(P);
    const Values play{TCAD_CONST(.123),TCAD_CONST(-.321)};s.set_fe_play_state(play);
    auto predict=[&](real_t voltage,Values& phi){
        std::map<size_t,real_t> bc;
        for(size_t k=0;k<g.nz;++k)for(size_t j=0;j<g.ny;++j)for(size_t i=0;i<g.nx;++i){
            const size_t xyz[3]={i,j,k};if(xyz[axis]==0)bc[g.index(i,j,k)]=0;
            else if(xyz[axis]+1==shape[axis])bc[g.index(i,j,k)]=voltage;
        }
        s.set_dirichlet(bc);s.assemble(n,p);phi.assign(N,TCAD_CONST(0.0));require(s.solve(phi),"predictor solve");
        const auto entered_phi=phi,entered_rhs=s.rhs(),entered_vals=s.matrix().vals();
        const auto& readonly=s;auto d=readonly.ferroelectric_nls_drive(phi);auto repeated=readonly.ferroelectric_nls_drive(phi);
        require(d.active && same(d,repeated),"repeatable active observation");
        require(phi==entered_phi && s.rhs()==entered_rhs && s.matrix().vals()==entered_vals && s.fe_polarization()==P && s.fe_play_state()==play,"observation changed state");
        return d;
    };
    Values low_phi,high_phi,phi;real_t low=TCAD_CONST(-.1),high=TCAD_CONST(.1);
    const auto low_drive=predict(low,low_phi),high_drive=predict(high,high_phi);
    require(low_drive.raw_mean_field>0 && high_drive.raw_mean_field<0,"initial root bracket");
    for(int iteration=0;iteration<76;++iteration){
        const real_t middle=(low+high)/TCAD_CONST(2.0);auto d=predict(middle,phi);
        if(d.raw_mean_field>0)low=middle;else high=middle;
    }
    const real_t root=(low+high)/TCAD_CONST(2.0);const auto root_drive=predict(root,phi);
    // Observe a definite side, then prove its report is also the advancing
    // kernel's drive. Every node's post-update P is independently audited.
    const real_t probe=root+TCAD_CONST(1e-5);const auto report=predict(probe,phi);
    s.update_ferroelectric_polarization_transient(phi,TCAD_CONST(1e-14));
    const auto after=s.fe_polarization();require(s.fe_play_state()==play,"NLS consumed play history");
    std::cout<<"{\"dimension\":"<<dim<<",\"axis\":"<<axis<<",\"partial\":"<<partial<<",\"seed\":"<<seed<<",\"depol\":"<<depol;
    std::cout<<",\"shape\":["<<shape[0]<<','<<shape[1]<<','<<shape[2]<<"],\"axes\":[";values(axes[0]);std::cout<<',';values(axes[1]);std::cout<<',';values(axes[2]);std::cout<<']';
    std::cout<<",\"mask\":[";for(size_t i=0;i<N;++i){if(i)std::cout<<',';std::cout<<int(mask[i]);}std::cout<<']';
#define FIELD(name) std::cout<<",\"" #name "\":";values(name)
    FIELD(eps);FIELD(n);FIELD(p);FIELD(doping);FIELD(P);FIELD(phi);FIELD(low_phi);FIELD(high_phi);FIELD(after);
#undef FIELD
    std::cout<<",\"parameters\":";values({builtin,epsfe,TCAD_CONST(2e-6),TCAD_CONST(1e-11),TCAD_CONST(2000.0),TCAD_CONST(1e-14)});
    std::cout<<",\"voltages\":";values({TCAD_CONST(-.1),TCAD_CONST(.1),low,high,root,probe});
    std::cout<<",\"low_drive\":";drive(low_drive);std::cout<<",\"high_drive\":";drive(high_drive);std::cout<<",\"root_drive\":";drive(root_drive);std::cout<<",\"probe_drive\":";drive(report);
    std::cout<<",\"passed\":true}"<<std::endl;
}
static void invalid_inputs(){
    Grid3D g{3,1,1,TCAD_CONST(1.0),TCAD_CONST(1.0),TCAD_CONST(1.0)};PoissonSolver s(g);Values phi(3,TCAD_CONST(0.0));int rejected=0;
    auto rejects=[&](auto operation){const auto P=s.fe_polarization(),play=s.fe_play_state();try{operation();}catch(const std::exception&){++rejected;require(s.fe_polarization()==P && s.fe_play_state()==play,"invalid observation changed memory");return;}throw std::runtime_error("invalid observation accepted");};
    rejects([&]{s.ferroelectric_nls_drive(phi);});
    s.set_ferroelectric(std::vector<char>(3,1),-TCAD_CONST(1.0),TCAD_CONST(1.0));rejects([&]{s.ferroelectric_nls_drive(phi);});
    s.set_ferroelectric_model(2);rejects([&]{s.ferroelectric_nls_drive({});});
    auto bad=phi;bad[1]=static_cast<real_t>(std::numeric_limits<double>::infinity());rejects([&]{s.ferroelectric_nls_drive(bad);});
    s.set_fe_polarization({});rejects([&]{s.ferroelectric_nls_drive(phi);});
    s.set_ferroelectric(std::vector<char>(3,0),-TCAD_CONST(1.0),TCAD_CONST(1.0));require(!s.ferroelectric_nls_drive(phi).active,"empty support active");
    require(rejected==5,"invalid case count");std::cout<<"{\"invalid_rejected\":"<<rejected<<",\"empty_support_inactive\":true}"<<std::endl;
}
int main(){try{for(int dim:{2,3})for(int axis:{0,1,2})for(bool partial:{false,true})for(int seed:{-1,1})for(bool depol:{false,true})fixture(dim,axis,partial,seed,depol);invalid_inputs();return 0;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
