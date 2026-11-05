// Independent prescribed-state FV rows and transactional quantum-cache checks.
#include <bits/stdc++.h>
#define private public
#include "device_simulator.h"
#undef private
using namespace tcad;
using V=std::vector<real_t>;
static void require(bool b,const char* m){if(!b)throw std::runtime_error(m);}
static real_t B(real_t x){return abs_q(x)<TCAD_CONST(1e-25)?TCAD_CONST(1.0)-x/TCAD_CONST(2.0):x/expm1_q(x);}
static void close(real_t a,real_t b,const char* m){require(abs_q(a-b)<TCAD_CONST(1e-24)*std::max(TCAD_CONST(1.0),std::max(abs_q(a),abs_q(b))),m);}
static V dg(const V& c,const V& pos,real_t coefficient,real_t vt){
    V q(5,0);for(size_t i=1;i<4;++i){const real_t u=sqrt_q(c[i]);
        const real_t lap=TCAD_CONST(2.0)/(pos[i+1]-pos[i-1])*((sqrt_q(c[i+1])-u)/(pos[i+1]-pos[i])-(u-sqrt_q(c[i-1]))/(pos[i]-pos[i-1]));
        q[i]=std::max(-TCAD_CONST(4.0)*vt,std::min(TCAD_CONST(4.0)*vt,coefficient*lap/u));}return q;
}
struct Flux {V j,d,bp,bm;};
static Flux flux(const V& phi,const V& c,const V& q,const V& pos,const std::map<size_t,real_t>& bc,bool hole,int hfs,bool policy){
    Flux f{V(4),V(4),V(4),V(4)};const real_t vt=TCAD_CONST(.02585),sign=hole?-TCAD_CONST(1.0):TCAD_CONST(1.0);
    const real_t mu=hole?TCAD_CONST(.05):TCAD_CONST(.1),vs=hole?TCAD_CONST(4e4):TCAD_CONST(5e4),beta=hole?TCAD_CONST(1.0):TCAD_CONST(2.0);
    for(size_t i=0;i<4;++i){const real_t h=pos[i+1]-pos[i],dv=phi[i+1]+sign*q[i+1]-phi[i]-sign*q[i];real_t m=TCAD_CONST(2.0)*mu*mu/(TCAD_CONST(2.0)*mu+TCAD_CONST(1e-30));
        if(hfs){real_t force=abs_q(dv)/h;if(hfs==2&&(policy||!(bc.count(i)||bc.count(i+1))))force=abs_q(dv-sign*vt*log_q(c[i+1]/c[i]))/h;
            const real_t r=m*force/vs;if(r>TCAD_CONST(1e-12))m/=pow_q(TCAD_CONST(1.0)+pow_q(r,beta),TCAD_CONST(1.0)/beta);}
        f.d[i]=m*vt/h;f.bp[i]=B(dv/vt);f.bm[i]=B(-dv/vt);f.j[i]=QE*f.d[i]*(hole?c[i]*f.bp[i]-c[i+1]*f.bm[i]:c[i+1]*f.bp[i]-c[i]*f.bm[i]);}return f;
}
int main(){
    size_t cases=0,audits=0,independent_rows=0,cache_checks=0,exception_checks=0,public_initializations=0,invalid_state_checks=0,invalid_q_checks=0;
    try{
        for(int axis:{0,1,2})for(bool graded:{false,true})for(int hfs:{0,1,2})for(bool policy:{false,true})for(int layout:{0,1,2})for(bool ii:{false,true})for(bool reactions:{false,true}){
            const real_t H=TCAD_CONST(1e-7),vt=TCAD_CONST(.02585),eps=TCAD_CONST(11.7)*TCAD_CONST(8.854187817e-12),doping=TCAD_CONST(1.5e18);
            size_t shape[3]={1,1,1};shape[axis]=5;DeviceSimulator d(shape[0],shape[1],shape[2],H,H,H);
            V pos={0,H,TCAD_CONST(2.0)*H,TCAD_CONST(3.0)*H,TCAD_CONST(4.0)*H};if(graded){pos={0,H,TCAD_CONST(2.5)*H,TCAD_CONST(4.0)*H,TCAD_CONST(6.0)*H};if(axis==0)d.set_grid_x(pos);if(axis==1)d.set_grid_y(pos);if(axis==2)d.set_grid_z(pos);}
            V phi={0,TCAD_CONST(.025),TCAD_CONST(.07),TCAD_CONST(.13),TCAD_CONST(.205)},n(5),p(5);
            for(size_t i=0;i<5;++i){n[i]=TCAD_CONST(2e19)*(TCAD_CONST(1.0)+TCAD_CONST(.07)*i*i);p[i]=TCAD_CONST(1.2e19)*(TCAD_CONST(1.0)+TCAD_CONST(.11)*i*i);}
            std::map<size_t,real_t> nb,pb;if(layout==0){nb={{0,n[0]},{4,n[4]}};pb={{0,p[0]},{4,p[4]}};}if(layout==1){nb={{1,n[1]}};pb={{3,p[3]}};}
            d.set_quantum_enabled(true);d.set_density_gradient_coefficients(TCAD_CONST(1e-15),TCAD_CONST(7e-16));d.set_thermal_voltage(vt);d.set_mobility(V(5,TCAD_CONST(.1)),V(5,TCAD_CONST(.05)));
            d.set_permittivity(V(5,eps));d.set_doping(V(5,doping));d.set_effective_dos(V(5,TCAD_CONST(1e19)),V(5,TCAD_CONST(1e19)));d.set_bandgap(V(5,TCAD_CONST(6.0)));
            const real_t tn=reactions?TCAD_CONST(1e-12):TCAD_CONST(1e100),tp=reactions?TCAD_CONST(2e-12):TCAD_CONST(1e100),light=reactions?TCAD_CONST(1e29):TCAD_CONST(0.0),cn=reactions?TCAD_CONST(2.8e-43):TCAD_CONST(0.0),cp=reactions?TCAD_CONST(9.9e-44):TCAD_CONST(0.0);
            d.set_recombination(V(5,tn),V(5,tp));d.set_optical_generation(V(5,light));d.set_auger_enabled(reactions);d.set_auger_params(cn,cp);
            d.set_dirichlet_potential({{0,phi[0]},{4,phi[4]}});d.set_electron_bc(nb);d.set_hole_bc(pb);
            d.set_high_field_saturation(hfs>0,TCAD_CONST(5e4),TCAD_CONST(4e4),TCAD_CONST(2.0),TCAD_CONST(1.0),hfs==1?1:0);d.set_hfs_quasi_fermi_at_contacts(policy);
            d.set_ii_params(TCAD_CONST(1e5),TCAD_CONST(2e5),TCAD_CONST(2e5),TCAD_CONST(3e5));d.set_ii_enabled(ii);
            d.set_use_newton(true);d.set_newton_primary(true);d.set_gummel_max_iter(0);d.set_initial_guess(phi,n,p);
            auto initial=d.solve();require(!initial.converged,"zero-budget initialization unexpectedly converged");++public_initializations;
            V qn=dg(n,pos,TCAD_CONST(1e-15),vt),qp=dg(p,pos,TCAD_CONST(7e-16),vt);for(auto bc:nb)qn[bc.first]=0;for(auto bc:pb)qp[bc.first]=0;
            const Flux fn=flux(phi,n,qn,pos,nb,false,hfs,policy),fp=flux(phi,p,qp,pos,pb,true,hfs,policy);V gen(5,0);
            if(ii)for(size_t i=0;i<4;++i){const real_t field=abs_q(phi[i+1]-phi[i])/(pos[i+1]-pos[i]);if(field>=TCAD_CONST(1e5)){const real_t edge=TCAD_CONST(.5)*(TCAD_CONST(1e5)*exp_q(-TCAD_CONST(2e5)/field)*abs_q(fn.j[i])+TCAD_CONST(2e5)*exp_q(-TCAD_CONST(3e5)/field)*abs_q(fp.j[i]))/QE;gen[i]+=edge;gen[i+1]+=edge;}}
            V expected(3,0);for(size_t i=0;i<5;++i){const real_t width=i==0?pos[1]-pos[0]:(i==4?pos[4]-pos[3]:(pos[i+1]-pos[i-1])/TCAD_CONST(2.0)),source_width=axis==0?width:H,weight=axis==0?TCAD_CONST(1.0):H/width;
                if(i>0&&i<4){const real_t l=eps/(width*(pos[i]-pos[i-1])),r=eps/(width*(pos[i+1]-pos[i])),rhs=QE*(p[i]-n[i]+doping),applied=l*(phi[i]-phi[i-1])+r*(phi[i]-phi[i+1]);expected[0]=std::max(expected[0],abs_q(applied-rhs)/(TCAD_CONST(2.0)*vt*(l+r)+QE*(n[i]+p[i]+doping)+abs_q(rhs)));}
                // Eg=6 eV makes ni/n < 1e-49 in these fixtures. Terms omitted
                // below are far below the 1e-24 absolute comparison threshold.
                const real_t den=tp*n[i]+tn*p[i],srh=n[i]*p[i]/den,reaction=srh+(cn*n[i]+cp*p[i])*n[i]*p[i];
                for(bool hole:{false,true}){const auto& bc=hole?pb:nb;if(bc.count(i))continue;const auto& f=hole?fp:fn;const auto& c=hole?p:n;
                    const real_t dr=hole?tp*n[i]*n[i]/(den*den):tn*p[i]*p[i]/(den*den);real_t diagonal=dr*source_width,neighbors=0;
                    if(i){diagonal+=weight*f.d[i-1]*(hole?f.bm[i-1]:f.bp[i-1]);neighbors+=weight*f.d[i-1]*(hole?f.bp[i-1]:f.bm[i-1])*c[i-1];}
                    if(i<4){diagonal+=weight*f.d[i]*(hole?f.bp[i]:f.bm[i]);neighbors+=weight*f.d[i]*(hole?f.bm[i]:f.bp[i])*c[i+1];}
                    diagonal*=c[i];const real_t rhs=(light+gen[i]-reaction+dr*c[i])*source_width;expected[hole?2:1]=std::max(expected[hole?2:1],abs_q(diagonal-neighbors-rhs)/(abs_q(diagonal)+abs_q(neighbors)+abs_q(rhs)));}}
            for(int cache:{0,1,2}){
                if(cache)d.gummel_.set_transport_quantum_state(V(5,TCAD_CONST(.31)),V(5,-TCAD_CONST(.29)));else{d.gummel_.Qn_prev_.clear();d.gummel_.Qp_prev_.clear();}
                if(cache==2)d.gummel_.Qp_prev_.clear();
                const V oldn=d.gummel_.Qn_prev_,oldp=d.gummel_.Qp_prev_;
                SimulationResult r;r.phi=phi;r.n=n;r.p=p;r.Qn=V(5,TCAD_CONST(.333));r.Qp=V(5,-TCAD_CONST(.444));r.converged=false;
                d.audit_steady_equations(r,true);require(r.steady_gummel_audit_status=="available_quantum_newton_sg"&&r.steady_gummel_audit.size()==6,"quantum audit unavailable");
                for(size_t i=0;i<3;++i){close(r.steady_gummel_audit[i],expected[i],"independent physical DG FV audit row");++independent_rows;}
                require(r.phi==phi&&r.n==n&&r.p==p&&r.Qn==V(5,TCAD_CONST(.333))&&r.Qp==V(5,-TCAD_CONST(.444))&&!r.converged,"audit changed returned fields/verdict");
                require(d.gummel_.Qn_prev_==oldn&&d.gummel_.Qp_prev_==oldp,"physical audit committed transport cache");++cache_checks;++audits;
                bool threw=false;try{d.gummel_.compute_quantum_continuity_residuals(V(4,0),n,p,qn,qp);}catch(const std::invalid_argument&){threw=true;}
                require(threw&&d.gummel_.Qn_prev_==oldn&&d.gummel_.Qp_prev_==oldp,"throwing audit did not restore cache");++exception_checks;
                if(cases==0){
                    for(int bad:{0,1,2}){SimulationResult invalid=r;if(bad==0)invalid.n.pop_back();if(bad==1)invalid.n[2]=sqrt_q(-TCAD_CONST(1.0));if(bad==2)invalid.p[2]=-TCAD_CONST(1.0);
                        d.audit_steady_equations(invalid,true);require(invalid.steady_gummel_audit.empty()&&invalid.steady_gummel_audit_status.find("reassembly_failed: ")==0,"invalid state retained passing rows");
                        require(d.gummel_.Qn_prev_==oldn&&d.gummel_.Qp_prev_==oldp,"invalid state changed cache");++invalid_state_checks;}
                    for(int bad:{0,1}){V invalid=qn;if(bad==0)invalid.pop_back();else invalid[2]=sqrt_q(-TCAD_CONST(1.0));bool caught=false;
                        try{d.gummel_.compute_quantum_continuity_residuals(phi,n,p,invalid,qp);}catch(const std::invalid_argument&){caught=true;}
                        require(caught&&d.gummel_.Qn_prev_==oldn&&d.gummel_.Qp_prev_==oldp,"invalid Q changed cache");++invalid_q_checks;}
                }
            }
            ++cases;
        }
        std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"cases\":"<<cases<<",\"audits\":"<<audits<<",\"independent_rows\":"<<independent_rows<<",\"cache_checks\":"<<cache_checks<<",\"exception_restorations\":"<<exception_checks<<",\"public_zero_budget_initializations\":"<<public_initializations<<",\"invalid_state_checks\":"<<invalid_state_checks<<",\"invalid_q_checks\":"<<invalid_q_checks<<"}\n";
    }catch(const std::exception& e){std::cerr<<"case="<<cases<<" "<<e.what()<<'\n';return 1;}
}
