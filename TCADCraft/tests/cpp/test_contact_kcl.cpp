#include <bits/stdc++.h>
#define private public
#include "newton_solver.h"
#undef private
using namespace tcad;
using V=std::vector<real_t>;
static void require(bool b,const char* m){if(!b)throw std::runtime_error(m);}
static real_t mobility(real_t l,real_t r,real_t h,bool hole,int hfs,bool policy,bool contact){
    real_t mu=hole?TCAD_CONST(.05):TCAD_CONST(.1);
    if(hfs==2&&(policy||!contact)){
        const real_t force=TCAD_CONST(.02585)*abs_q(log_q(r/l))/h;
        const real_t ratio=mu*force/(hole?TCAD_CONST(4e4):TCAD_CONST(5e4));
        if(ratio>TCAD_CONST(1e-12))mu/=hole?TCAD_CONST(1.0)+ratio:sqrt_q(TCAD_CONST(1.0)+ratio*ratio);
    }
    return mu;
}
static real_t particle_flux(real_t l,real_t r,real_t h,bool hole,int hfs,bool policy,bool contact){
    return mobility(l,r,h,hole,hfs,policy,contact)*TCAD_CONST(.02585)*(r-l)/h;
}
static V profile(const V& pos,const std::map<size_t,real_t>& bc,bool hole,int hfs,bool policy){
    V c(7);c[0]=hole?TCAD_CONST(1.2e19):TCAD_CONST(2e19);
    real_t rate=c[0]*(hole?TCAD_CONST(.05):TCAD_CONST(.1))*TCAD_CONST(.02585)/TCAD_CONST(1e-7)*(hole?TCAD_CONST(.03):TCAD_CONST(.05));
    for(size_t i=0;i<6;++i){
        if(i&&bc.count(i))rate*=hole?TCAD_CONST(.6):TCAD_CONST(1.7);
        const real_t h=pos[i+1]-pos[i];const bool contact=bc.count(i)||bc.count(i+1);
        real_t low=c[i],high=c[i]*TCAD_CONST(4.0);
        require(particle_flux(c[i],high,h,hole,hfs,policy,contact)>rate,"profile bracket");
        for(size_t k=0;k<100;++k){real_t mid=(low+high)/TCAD_CONST(2.0);if(particle_flux(c[i],mid,h,hole,hfs,policy,contact)<rate)low=mid;else high=mid;}
        c[i+1]=(low+high)/TCAD_CONST(2.0);
    }return c;
}
static bool spread_ok(const V& j,size_t a,size_t b){
    real_t lo=j[a],hi=j[a],scale=abs_q(j[a]);
    for(size_t i=a+1;i<b;++i){lo=std::min(lo,j[i]);hi=std::max(hi,j[i]);scale=std::max(scale,abs_q(j[i]));}
    return hi-lo<=TCAD_CONST(1e-8)||(hi-lo)/(scale+TCAD_CONST(1e-30))<=TCAD_CONST(.01);
}
int main(int argc,char** argv){
    const bool parent=argc>1&&std::string(argv[1])=="--parent";
    size_t cases=0,rows=0,false_rejects=0,accepted=0,rejected=0,cache_checks=0,free_species_rows=0;
    try{
        for(int axis:{0,1,2})for(bool graded:{false,true})for(bool logs:{false,true})for(bool quantum:{false,true})
        for(int hfs:{0,1,2})for(bool policy:{false,true})for(int layout:{0,1,2,3,4})for(int bad:{0,1,2}){
            const real_t H=TCAD_CONST(1e-7);Grid3D g{axis==0?7u:1u,axis==1?7u:1u,axis==2?7u:1u,H,H,H};
            V pos={0,H,TCAD_CONST(2.0)*H,TCAD_CONST(3.0)*H,TCAD_CONST(4.0)*H,TCAD_CONST(5.0)*H,TCAD_CONST(6.0)*H};
            if(graded){pos={0,H,TCAD_CONST(2.3)*H,TCAD_CONST(3.8)*H,TCAD_CONST(5.0)*H,TCAD_CONST(6.5)*H,TCAD_CONST(8.0)*H};if(axis==0)g.xx=pos;if(axis==1)g.yx=pos;if(axis==2)g.zx=pos;}
            std::map<size_t,real_t> nb{{0,0},{6,0}},pb=nb;
            if(layout==1||layout==3)nb[3]=0;if(layout==2||layout==3)pb[3]=0;if(layout==4){nb[2]=0;pb[4]=0;}
            V n=profile(pos,nb,false,hfs,policy),p=profile(pos,pb,true,hfs,policy),phi(7,0),qn(7,0),qp(7,0),x(21);
            if(bad==1)n[1]*=TCAD_CONST(1.08);if(bad==2)p[5]*=TCAD_CONST(1.08);
            for(auto& bc:nb)bc.second=n[bc.first];for(auto& bc:pb)bc.second=p[bc.first];
            if(quantum)for(size_t i=1;i<6;++i)if(!nb.count(i)&&!pb.count(i)){phi[i]=TCAD_CONST(.003)*i*(6-i);qn[i]=-phi[i];qp[i]=phi[i];}
            NewtonOptions o;o.enable_quantum=quantum;o.use_log_space=logs;o.hfs_enabled=hfs>0;o.hfs_driving=hfs==1?1:0;o.hfs_qf_at_contacts=policy;
            o.hfs_vsat_n=TCAD_CONST(5e4);o.hfs_vsat_p=TCAD_CONST(4e4);o.hfs_beta_n=TCAD_CONST(2.0);o.hfs_beta_p=TCAD_CONST(1.0);
            NewtonSolver s(g,o);s.set_semiconductor_mask(std::vector<char>(7,1));s.set_mobility(V(7,TCAD_CONST(.1)),V(7,TCAD_CONST(.05)));
            s.set_effective_dos(V(7,TCAD_CONST(1e19)),V(7,TCAD_CONST(1e19)));s.set_bandgap(V(7,TCAD_CONST(6.0)));s.set_recombination(V(7,TCAD_CONST(1e100)),V(7,TCAD_CONST(1e100)));
            s.set_electron_bc(nb);s.set_hole_bc(pb);s.lagged_Qn_=qn;s.lagged_Qp_=qp;s.use_lagged_quantum_potential_=true;
            for(size_t i=0;i<7;++i){x[i]=phi[i];x[7+i]=logs?log_q(n[i]):n[i];x[14+i]=logs?log_q(p[i]):p[i];}
            V j(6),jn(6),jp(6);for(size_t i=0;i<6;++i){jn[i]=QE*particle_flux(n[i],n[i+1],pos[i+1]-pos[i],false,hfs,policy,nb.count(i)||nb.count(i+1));jp[i]=-QE*particle_flux(p[i],p[i+1],pos[i+1]-pos[i],true,hfs,policy,pb.count(i)||pb.count(i+1));j[i]=jn[i]+jp[i];}
            bool expected=true;size_t start=0;for(size_t i=1;i<7;++i)if(i==6||nb.count(i)||pb.count(i)){expected=expected&&spread_ok(j,start,i);start=i;}
            require(expected==(bad==0),"independent section fixture classification");
            const bool old=spread_ok(j,0,6),actual=s.steady_1d_kcl_ok(x);
            require(actual==(parent?old:expected),"actual production KCL classification");
            if(expected&&!actual)++false_rejects;if(actual)++accepted;else ++rejected;
            require(s.lagged_Qn_==qn&&s.lagged_Qp_==qp&&s.use_lagged_quantum_potential_,"guard changed quantum state");++cache_checks;
            V f;s.assemble_residual(x,f);real_t scale=TCAD_CONST(1.0);for(auto v:j)scale=std::max(scale,abs_q(v));
            for(size_t i=1;i<6;++i){const real_t weight=axis==0?TCAD_CONST(1.0):H/((pos[i+1]-pos[i-1])/TCAD_CONST(2.0));
                if(!nb.count(i)&&!pb.count(i)){require(abs_q(QE*(f[14+i]-f[7+i])/weight-(j[i]-j[i-1]))<TCAD_CONST(1e-24)*scale,"independent continuity divergence");++rows;}
                if(bad==0&&nb.count(i)!=pb.count(i)){
                    const bool hole=nb.count(i);const auto& js=hole?jp:jn;const real_t physical=QE*f[(hole?14:7)+i]/weight;
                    const real_t independent=(hole?TCAD_CONST(1.0):-TCAD_CONST(1.0))*(js[i]-js[i-1]);
                    require(abs_q(physical-independent)<TCAD_CONST(1e-24)*scale,"unconstrained contact species row removed");++free_species_rows;
                }
            }++cases;
        }
        require(cases==2160&&rows==8640&&cache_checks==2160&&free_species_rows==576,"matrix counts");
        require(false_rejects==(parent?576u:0u),"false reject counts");
        std::cout<<"{\"profile\":\""<<compiled_constants_profile_name()<<"\",\"parent\":"<<(parent?"true":"false")<<",\"cases\":"<<cases<<",\"independent_divergence_rows\":"<<rows<<",\"false_rejects\":"<<false_rejects<<",\"accepted\":"<<accepted<<",\"rejected\":"<<rejected<<",\"cache_checks\":"<<cache_checks<<",\"unconstrained_contact_species_rows\":"<<free_species_rows<<"}\n";
    }catch(const std::exception& e){std::cerr<<"case="<<cases<<" "<<e.what()<<'\n';return 1;}
}
