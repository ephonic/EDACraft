// Exercise the real coupled Newton caller with analytic manufactured states.
#include "newton_solver.h"
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#ifdef __linux__
#include <sys/resource.h>
#endif
using namespace tcad;
struct Capture {
    std::ostringstream stream;
    std::streambuf* previous=std::cerr.rdbuf(stream.rdbuf());
    ~Capture(){std::cerr.rdbuf(previous);}
};
int main(int argc,char** argv) {
    if(argc!=2)return 1;
    try {
#ifdef __linux__
        struct rlimit limit{128u*1024u*1024u,128u*1024u*1024u};
        if(setrlimit(RLIMIT_AS,&limit)!=0)throw std::runtime_error("memory limit unavailable");
#endif
        const std::string mode=argv[1];
        const bool carriers=mode=="carriers";
        const bool expected_banded=mode=="x"||mode=="y"||mode=="z"||carriers;
        if(!expected_banded && mode!="threshold" && mode!="quantum" && mode!="transient" && mode!="2d" && mode!="other_backend")return 1;
        Grid3D grid{2001,1,1,TCAD_CONST(2e-9),TCAD_CONST(2e-9),TCAD_CONST(2e-9)};
        if(mode=="y"){grid.nx=1;grid.ny=2001;}
        if(mode=="z"){grid.nx=1;grid.nz=2001;}
        if(mode=="threshold")grid.nx=2000;
        if(mode=="2d"){grid.nx=41;grid.ny=49;}
        const size_t count=grid.npts();
        const real_t vt=KB*TCAD_CONST(300.0)/QE;
        const real_t density=carriers ? sqrt_q(TCAD_CONST(2.8e25)*TCAD_CONST(1.04e25))*exp_q(-TCAD_CONST(1.12)/(TCAD_CONST(2.0)*vt)) : EPSILON;
        Vector phi(count,TCAD_CONST(0.0)),n(count,density),p=n,truth_phi=phi;
        std::map<size_t,real_t> bc,carrier_bc;
        for(size_t k=0;k<grid.nz;++k)for(size_t j=0;j<grid.ny;++j)for(size_t i=0;i<grid.nx;++i) {
            const size_t row=grid.index(i,j,k);
            const size_t axis_count=grid.nx>1?grid.nx:(grid.ny>1?grid.ny:grid.nz);
            const size_t axis_index=grid.nx>1?i:(grid.ny>1?j:k);
            truth_phi[row]=carriers?TCAD_CONST(0.0):TCAD_CONST(0.1)*real_t(axis_index)/real_t(axis_count-1);
            const bool boundary=(grid.nx>1&&(i==0||i+1==grid.nx))||(grid.ny>1&&(j==0||j+1==grid.ny))||(grid.nz>1&&(k==0||k+1==grid.nz));
            if(boundary){bc[row]=truth_phi[row];carrier_bc[row]=density;}
            // Short-wave perturbation forces a nontrivial Newton direction.
            // A device-wide shallow parabola can already satisfy the local
            // residual tolerance before any linear solve is attempted.
            if(carriers)n[row]=p[row]=density*(TCAD_CONST(1.0)+TCAD_CONST(0.00024975)*real_t(axis_index%2));
        }
        NewtonOptions options;options.linear_solver=mode=="other_backend"?SolverType::BICGSTAB_ILU0:SolverType::GMRES;
        options.max_iter=12;options.tol=TCAD_CONST(1e-10);options.linear_tol=TCAD_CONST(1e-20);options.use_log_space=true;
        options.enable_quantum=mode=="quantum";options.transient_enabled=mode=="transient";
        if(options.transient_enabled){options.n_prev=n;options.p_prev=p;}
        NewtonSolver solver(grid,options);solver.set_thermal_voltage(vt);
        solver.set_permittivity(Vector(count,EPS0*TCAD_CONST(11.7)));
        solver.set_mobility(Vector(count,carriers?TCAD_CONST(0.1):TCAD_CONST(0.0)),Vector(count,carriers?TCAD_CONST(0.1):TCAD_CONST(0.0)));
        solver.set_doping(Vector(count,TCAD_CONST(0.0)));
        solver.set_effective_dos(Vector(count,TCAD_CONST(2.8e25)),Vector(count,TCAD_CONST(1.04e25)));
        solver.set_bandgap(Vector(count,TCAD_CONST(1.12)));solver.set_semiconductor_mask(std::vector<char>(count,carriers?1:0));
        solver.set_phi_dirichlet(bc);solver.set_electron_bc(carrier_bc);solver.set_hole_bc(carrier_bc);
        bool solved;std::string trace;
        {Capture capture;solved=solver.solve(phi,n,p);trace=capture.stream.str();}
        std::cerr<<trace;
        const bool used_banded=trace.find("[Newton bounded banded direct n=")!=std::string::npos;
        real_t phi_error=TCAD_CONST(0.0),carrier_error=TCAD_CONST(0.0),poisson_error=TCAD_CONST(0.0);
        for(size_t k=0;k<grid.nz;++k)for(size_t j=0;j<grid.ny;++j)for(size_t i=0;i<grid.nx;++i) {
            const size_t row=grid.index(i,j,k);
            if(!isfinite_q(phi[row])||!isfinite_q(n[row])||!isfinite_q(p[row]))throw std::runtime_error("nonfinite state");
            phi_error=std::max(phi_error,abs_q(phi[row]-truth_phi[row]));
            carrier_error=std::max(carrier_error,std::max(abs_q(n[row]/density-TCAD_CONST(1.0)),abs_q(p[row]/density-TCAD_CONST(1.0))));
            if(bc.count(row))continue;
            real_t equation=carriers?QE*(p[row]-n[row]):TCAD_CONST(0.0),scale=TCAD_CONST(1.0);
            auto edge=[&](size_t neighbour,real_t h){const real_t a=EPS0*TCAD_CONST(11.7)/(h*h);equation+=a*(phi[neighbour]-phi[row]);scale+=a*(abs_q(phi[neighbour])+abs_q(phi[row]));};
            if(i)edge(row-1,grid.dx);if(i+1<grid.nx)edge(row+1,grid.dx);
            if(j)edge(row-grid.nx,grid.dy);if(j+1<grid.ny)edge(row+grid.nx,grid.dy);
            if(k)edge(row-grid.nx*grid.ny,grid.dz);if(k+1<grid.nz)edge(row+grid.nx*grid.ny,grid.dz);
            poisson_error=std::max(poisson_error,abs_q(equation)/scale);
        }
        std::cout<<"{\"mode\":\""<<mode<<"\",\"nodes\":"<<count<<",\"converged\":"<<(solved?"true":"false")<<",\"used_banded\":"<<(used_banded?"true":"false")<<",\"expected_banded\":"<<(expected_banded?"true":"false")<<",\"phi_error_V\":"<<double(phi_error)<<",\"carrier_relative\":"<<double(carrier_error)<<",\"independent_poisson_relative\":"<<double(poisson_error)<<",\"residual_samples\":"<<solver.residuals().size()<<",\"memory_limit_MiB\":128}\n";
        if(!solved||phi_error>=TCAD_CONST(1e-10)||carrier_error>=TCAD_CONST(1e-8)||poisson_error>=TCAD_CONST(1e-10)||solver.residuals().size()<2)return 2;
        if(used_banded!=expected_banded)return 3;
        return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
