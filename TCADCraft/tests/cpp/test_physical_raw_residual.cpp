// Analytic three-node charge equations; no production Poisson reference solve.
#include "gummel_solver.h"
#include "statistics.h"
#include <iostream>
#include <iomanip>
#include <limits>
#include <string>
using namespace tcad;

int main(int argc,char** argv) {
    size_t cases=0,raw_checks=0,gummel_checks=0,state_checks=0,invalid_checks=0;
    size_t failures=0,hidden_damage=0;
    real_t max_error=0;
    auto check=[&](bool ok){if(!ok)++failures;};
    auto close=[&](real_t measured,real_t expected) {
        const real_t error=abs_q(measured-expected);
        if(isfinite_q(error))max_error=std::max(max_error,error);
        check(isfinite_q(measured) && error<TCAD_CONST(1e-24));
    };
    if(argc==2 && std::string(argv[1])=="invalid") {
        Grid3D grid{3,1,1,TCAD_CONST(1e-7),TCAD_CONST(1e-7),TCAD_CONST(1e-7)};
        PoissonSolver op(grid);op.set_permittivity(Vector(3,11*EPS0));
        op.set_dirichlet({{0,0},{2,0}});
        Vector phi(3,0),n(3,TCAD_CONST(1e22)),p(n);
        op.set_leakage_field(phi);op.assemble(n,p);
        const auto vals=op.matrix().vals(),rhs=op.rhs();
        auto rejects=[&](const Vector& v,const Vector& a,const Vector& b) {
            ++invalid_checks;
            try{op.residual_norm(v,a,b);++failures;}
            catch(const std::invalid_argument&){}
            catch(...){++failures;}
            ++state_checks;check(op.matrix().vals()==vals && op.rhs()==rhs);
        };
        for(size_t size:{0u,2u,4u}) {
            rejects(Vector(size,0),n,p);rejects(phi,Vector(size,0),p);rejects(phi,n,Vector(size,0));
        }
        for(real_t bad:{(real_t)std::numeric_limits<double>::quiet_NaN(),
                        (real_t)std::numeric_limits<double>::infinity(),
                        -(real_t)std::numeric_limits<double>::infinity()}) {
            auto v=phi;v[1]=bad;rejects(v,n,p);
            v=n;v[1]=bad;rejects(phi,v,p);rejects(phi,n,v);
        }
        auto negative=n;negative[1]=-1;rejects(phi,negative,p);rejects(phi,n,negative);
        close(op.residual_norm(phi,Vector(3,0),Vector(3,0)),0);++raw_checks;
    } else {
        for(int axis:{0,1,2})for(bool graded:{false,true})for(bool holes:{false,true})
        for(bool fd:{false,true})for(real_t eta:{TCAD_CONST(5.0),TCAD_CONST(20.0)})
        for(real_t fraction:{TCAD_CONST(.25),TCAD_CONST(1.0)})for(bool stabilized:{false,true})
        for(real_t vt:{TCAD_CONST(.01),TCAD_CONST(.1)}) {
            Grid3D grid{axis==0?3u:1u,axis==1?3u:1u,axis==2?3u:1u,
                        TCAD_CONST(1e-7),TCAD_CONST(1e-7),TCAD_CONST(1e-7)};
            const real_t left=TCAD_CONST(1e-7),right=graded?2*left:left;
            if(graded) {
                Vector coords={0,left,left+right};
                if(axis==0)grid.xx=coords;else if(axis==1)grid.yx=coords;else grid.zx=coords;
            }
            const real_t eps=11*EPS0,dos=TCAD_CONST(1e22);
            auto physical=[&](real_t e){return dos*(fd?fermi_dirac_half(e):exp_q(e));};
            const real_t majority=physical(eta),minority=physical(-TCAD_CONST(20.0));
            Vector n(3,holes?minority:majority),p(3,holes?majority:minority);
            // Nonuniform three-point finite-volume Laplacian: interior
            // diagonal = -2*eps/(left*right); endpoints have zero voltage.
            const real_t stiffness=2*eps/(left*right);
            const real_t charge=QE*fraction*(n[1]-p[1]);
            Vector phi(3,0);phi[1]=-charge/stiffness;
            PoissonSolver op(grid);op.set_permittivity(Vector(3,eps));
            op.set_charge_volume_fraction(Vector(3,fraction));op.set_dirichlet({{0,0},{2,0}});
            op.set_boltzmann_linearization(stabilized,vt);
            Vector stale(phi);stale[1]*=TCAD_CONST(.3);
            op.set_leakage_field(stale);op.assemble(n,p);
            const auto vals=op.matrix().vals(),rhs=op.rhs();
            close(op.residual_norm(phi,n,p),0);++raw_checks;
            auto wrong_n=n,wrong_p=p;
            for(auto& v:(holes?wrong_p:wrong_n))v*=2;
            const real_t changed_charge=QE*fraction*(wrong_n[1]-wrong_p[1]);
            close(op.residual_norm(phi,wrong_n,wrong_p),abs_q(charge/changed_charge-1));++raw_checks;
            ++state_checks;check(op.matrix().vals()==vals && op.rhs()==rhs);
            // A second assembly must still use the original stale cache.
            op.assemble(n,p);++state_checks;check(op.matrix().vals()==vals && op.rhs()==rhs);

            GummelOptions opt;opt.enable_quantum=false;opt.boltzmann_lin=stabilized;opt.VT=vt;
            opt.statistics_type=fd?StatisticsType::FERMI_DIRAC:StatisticsType::BOLTZMANN;
            GummelSolver solver(grid,opt);solver.set_permittivity(Vector(3,eps));
            solver.set_doping(Vector(3,0));solver.set_effective_dos(Vector(3,dos),Vector(3,dos));
            solver.set_charge_volume_fraction(Vector(3,fraction));solver.set_poisson_dirichlet({{0,0},{2,0}});
            Vector raw_n(3,dos*exp_q(holes?-TCAD_CONST(20.0):eta));
            Vector raw_p(3,dos*exp_q(holes?eta:-TCAD_CONST(20.0)));
            auto damaged_n=raw_n,damaged_p=raw_p;
            for(auto& v:(holes?damaged_p:damaged_n))v*=exp_q(TCAD_CONST(2.0));
            const real_t damage_charge=QE*fraction*(physical(holes?-TCAD_CONST(20.0):eta+2)-
                                                     physical(holes?eta+2:-TCAD_CONST(20.0)));
            const real_t expected_damage=abs_q(charge/damage_charge-1);
            for(bool isolated:{false,true}) {
                close(solver.compute_poisson_residual(phi,raw_n,raw_p,isolated,false),0);++gummel_checks;
                const real_t measured=solver.compute_poisson_residual(phi,damaged_n,damaged_p,isolated,false);
                close(measured,expected_damage);++gummel_checks;
                check(measured>TCAD_CONST(.0041));
                if(measured<=TCAD_CONST(.0041))++hidden_damage;
            }
            ++cases;
        }
    }
    std::cout<<std::setprecision(17)<<"{\"test\":\"physical_raw_residual\",\"profile\":\""<<constants_profile_name()
        <<"\",\"cases\":"<<cases<<",\"raw_checks\":"<<raw_checks<<",\"gummel_checks\":"<<gummel_checks
        <<",\"state_checks\":"<<state_checks<<",\"invalid_checks\":"<<invalid_checks
        <<",\"hidden_damage\":"<<hidden_damage<<",\"maximum_absolute_error\":"<<(double)max_error
        <<",\"failures\":"<<failures<<"}\n";
    return failures?1:0;
}
