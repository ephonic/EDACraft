#pragma once

// Matched-valley, shared-temperature FD residual dispatch. No Python callbacks
// or precomputed fluxes/matrices cross this boundary.
#include "fermi_newton.h"
#include "hybrid_poisson.h"
#include <cstdio>

namespace tcad {
struct FermiDispatchResult {
    int density_mantissa_bits=std::numeric_limits<long double>::digits;
    std::vector<std::string> n,p;
    std::vector<double> temperature,local,fn,fp,energy_flux,old_energy,new_energy;
    std::vector<std::vector<double>> old_poisson,new_poisson,moments,newton;
};

namespace fermi_dispatch_detail {
inline std::string text(real_t value) {
    if(!isfinite_q(value)) throw std::invalid_argument("nonfinite native dispatcher scalar");
    char buffer[128];
#ifdef TCAD_USE_FLOAT128
    const int count=quadmath_snprintf(buffer,sizeof(buffer),"%.36Qe",value);
#else
    const int count=std::snprintf(buffer,sizeof(buffer),"%.36Le",value);
#endif
    if(count<0 || size_t(count)>=sizeof(buffer)) throw std::runtime_error("native decimal formatting failed");
    return std::string(buffer,size_t(count));
}
inline void pack(std::vector<std::string>& target,std::initializer_list<real_t> values) {
    for(real_t value:values) target.push_back(text(value));
}

struct Context {
    // cells: V,eps,rhofix,n0,p0,Nt,f,cx,cy,cz,T0,Cv,kappa,Ec,Eh,mn,mp.
    // faces: owner,neighbor,Ax,Ay,Az,fx,fy,fz,Vmode,V,area,do,dn,
    //        bathmode,bathT,contactmode,ncontact,pcontact,Tcontact,emissionmode,An,Ap.
    // parameters: dt,charge budget,particle budget,energy budget,Tref,mn exponent,mp exponent.
    std::vector<real_t> cells,faces;
    std::vector<double> parameters,valleys[2],old_u;
    std::vector<std::vector<double>> contact[2];
    std::vector<std::string> poisson_faces;
    size_t nc,nf;
    FermiDispatchResult result;
    real_t C(size_t i,size_t k) const {return cells[17*i+k];}
    real_t F(size_t i,size_t k) const {return faces[22*i+k];}
    bool mode(size_t i,size_t k) const {return F(i,k)==1;}

    Context(const std::vector<std::string>& raw_cells,const std::vector<std::string>& raw_faces,
            const std::vector<double>& vn,const std::vector<double>& vp,const std::vector<double>& params,
            bool allow_traps=false,bool allow_smooth_bands=false)
            :cells(fermi_local_detail::decimals(raw_cells)),faces(fermi_local_detail::decimals(raw_faces)),
             parameters(params),nc(cells.size()/17),nf(faces.size()/22) {
        if(!nc || cells.size()%17 || !nf || faces.size()%22 || nc+nf>512 || params.size()!=7)
            throw std::invalid_argument("native FD dispatcher dimensions or dense limit invalid");
        for(double value:params) if(!std::isfinite(value))
            throw std::invalid_argument("finite native FD parameters required");
        for(size_t k=0;k<5;++k) if(params[k]<=0)
            throw std::invalid_argument("positive native FD timestep, budgets and reference temperature required");
        valleys[0]=vn;valleys[1]=vp;
        for(size_t i=0;i<nc;++i) {
            for(size_t k:{0,1,3,4,10,11,12,15,16}) if(C(i,k)<=0)
                throw std::invalid_argument("positive native FD material and state required");
            if((allow_traps ? C(i,5)<0 : C(i,5)!=0) || C(i,6)<0 || C(i,6)>1 || C(i,10)<=1 || C(i,10)>=1e5)
                throw std::invalid_argument("native FD dispatcher does not support traps or out-of-bound temperatures");
            for(size_t k:{3,4}) if(!(std::log((long double)C(i,k))>-600 && std::log((long double)C(i,k))<600))
                throw std::invalid_argument("native FD density log bounds exceeded");
        }
        for(size_t f=0;f<nf;++f) {
            const real_t i=F(f,0),j=F(f,1);
            if(i<0 || i>=nc || i!=real_t(size_t(i)) || j<-1 || j>=nc ||
                    (j!=-1 && j!=real_t(size_t(j))) || i==j)
                throw std::invalid_argument("native FD face indices invalid");
            for(size_t k:{8,13,15}) if(F(f,k)!=0 && F(f,k)!=1)
                throw std::invalid_argument("native FD face mode invalid");
            if(F(f,19)!=0 && F(f,19)!=1 && F(f,19)!=2)
                throw std::invalid_argument("native FD spectral path mode invalid");
            if(F(f,10)<=0 || F(f,11)<=0 || (j>=0 ? F(f,12)<=0 : F(f,12)!=0) ||
                    (mode(f,8) && j>=0) || (mode(f,13) && (j>=0 || F(f,14)<=0)) ||
                    (mode(f,15) && (j>=0 || !mode(f,8) || F(f,16)<=0 || F(f,17)<=0 || F(f,18)<=0)) ||
                    F(f,20)<0 || F(f,21)<0 || (mode(f,19) && j<0) ||
                    (j>=0 && !mode(f,19) && !allow_smooth_bands && (C(size_t(i),13)!=C(size_t(j),13) || C(size_t(i),14)!=C(size_t(j),14))))
                throw std::invalid_argument("native FD face geometry, bath, contact or emission invalid");
            real_t area2=0,dot_owner=0,dot_neighbor=0;
            for(size_t d=0;d<3;++d) {
                area2+=F(f,2+d)*F(f,2+d);
                dot_owner+=(F(f,5+d)-C(size_t(i),7+d))*F(f,2+d);
                if(j>=0) dot_neighbor+=(C(size_t(j),7+d)-F(f,5+d))*F(f,2+d);
            }
            const real_t area=sqrt_q(area2),tol=TCAD_CONST(1e-10);
            if(!(area>0) || abs_q(F(f,10)/area-1)>tol ||
                    abs_q(dot_owner/area/F(f,11)-1)>tol ||
                    (j>=0 && abs_q(dot_neighbor/area/F(f,12)-1)>tol))
                throw std::invalid_argument("native FD inconsistent face area or half distance");
            for(size_t d=0;d<3;++d) {
                if(abs_q(F(f,5+d)-C(size_t(i),7+d)-F(f,11)*F(f,2+d)/area)>tol*F(f,11) ||
                        (j>=0 && abs_q(C(size_t(j),7+d)-F(f,5+d)-F(f,12)*F(f,2+d)/area)>tol*F(f,12)))
                    throw std::invalid_argument("native FD orthogonal half-cell geometry required");
            }
            for(size_t k=0;k<10;++k) poisson_faces.push_back(text(F(f,k)));
        }
        std::vector<real_t> n(nc),p(nc);std::vector<double> T(nc);
        for(size_t i=0;i<nc;++i) {n[i]=C(i,3);p[i]=C(i,4);T[i]=double(C(i,10));}
        result.old_poisson=poisson(n,p);
        const auto rn=reservoir(0,n,T),rp=reservoir(1,p,T);
        old_u.resize(nc);
        for(size_t i=0;i<nc;++i) old_u[i]=rn[i][1]+rp[i][1];
        result.old_energy=energies(old_u,T,result.old_poisson);
        for(size_t label=0;label<2;++label) {
            contact[label].resize(nf);
            for(size_t f=0;f<nf;++f) if(mode(f,15)) {
                const size_t i=size_t(F(f,0));std::vector<std::string> state;
                pack(state,{F(f,16+label),F(f,18),C(i,13+label)});
                contact[label][f]=native_fermi_reservoir_raw(state,valleys[label]);
            }
        }
    }

    std::vector<std::vector<double>> poisson(const std::vector<real_t>& n,const std::vector<real_t>& p,
                                            const std::vector<double>& trap={}) const {
        if(!trap.empty() && trap.size()!=nc) throw std::invalid_argument("native trap charge coverage mismatch");
        std::vector<std::string> c;
        for(size_t i=0;i<nc;++i) {
            for(size_t k=0;k<10;++k) c.push_back(text(k==3 ? n[i] : k==4 ? p[i] :
                k==6 && !trap.empty() ? real_t(trap[i]) : C(i,k)));
        }
        auto value=native_hybrid_poisson_raw(c,poisson_faces,parameters[1]);
        if(value[6][4]!=1) throw std::runtime_error("native FD Poisson budget failed");
        // Validate the actual exported D flux, not only the pre-export operator.
        std::vector<real_t> gauss(nc,0);real_t global=0;
        for(size_t f=0;f<nf;++f) {
            gauss[size_t(F(f,0))]+=value[2][f];
            if(F(f,1)>=0) gauss[size_t(F(f,1))]-=value[2][f];
        }
        for(size_t i=0;i<nc;++i) {
            const real_t occupied=C(i,5)*(trap.empty() ? C(i,6) : real_t(trap[i]));
            const real_t error=gauss[i]-C(i,0)*(C(i,2)+si_transport::elementary_charge*(p[i]-n[i]-occupied));global+=error;
            if(abs_q(error)>parameters[1]) throw std::runtime_error("native FD exported local Gauss budget failed");
        }
        if(abs_q(global)>parameters[1]) throw std::runtime_error("native FD exported global Gauss budget failed");
        return value;
    }

    std::vector<std::vector<double>> reservoir(size_t label,const std::vector<real_t>& density,
                                               const std::vector<double>& T) const {
        std::vector<std::string> states;
        for(size_t i=0;i<nc;++i) pack(states,{density[i],real_t(T[i]),C(i,13+label)});
        const auto values=native_fermi_reservoir_raw(states,valleys[label]);
        const size_t stride=3+valleys[label].size()/4;
        std::vector<std::vector<double>> rows(nc);
        for(size_t i=0;i<nc;++i) rows[i]=std::vector<double>(values.begin()+i*stride,values.begin()+(i+1)*stride);
        return rows;
    }

    std::vector<double> energies(const std::vector<double>& u,const std::vector<double>& T,
                                 const std::vector<std::vector<double>>& field) const {
        real_t carrier=0,thermal=0;
        for(size_t i=0;i<nc;++i) {carrier+=C(i,0)*u[i];thermal+=C(i,0)*C(i,11)*T[i];}
        return {double(carrier),double(thermal),field[6][0]};
    }

    void evaluate(const std::vector<double>& x,std::vector<double>& residual,double& merit) {
        std::vector<real_t> n(nc),p(nc);std::vector<double> T(nc);
        result.n.clear();result.p.clear();
        for(size_t i=0;i<nc;++i) {
            // Match the public state density arithmetic, which is platform long
            // double rather than the compiled quad scalar. Snap before ALL kernels.
            const long double factor_n=std::exp((long double)x[i]),factor_p=std::exp((long double)x[nc+i]);
            const long double nn=(long double)C(i,3)*factor_n,pp=(long double)C(i,4)*factor_p;
            n[i]=real_t(nn);p[i]=real_t(pp);T[i]=double(C(i,10))*std::exp(x[2*nc+i]);
            result.n.push_back(text(n[i]));result.p.push_back(text(p[i]));
        }
        result.temperature=T;result.new_poisson=poisson(n,p);
        const auto rn=reservoir(0,n,T),rp=reservoir(1,p,T);
        std::vector<double> u(nc);
        for(size_t i=0;i<nc;++i) u[i]=rn[i][1]+rp[i][1];
        result.fn.assign(nf,0);result.fp.assign(nf,0);result.energy_flux.assign(nf,0);
        result.moments.assign(2*nf,{});
        const auto& phi=result.new_poisson[0];
        for(size_t label=0;label<2;++label) {
            const auto& r=label==0 ? rn : rp;
            std::vector<double> mobility(nc);
            for(size_t i=0;i<nc;++i)
                mobility[i]=double(C(i,15+label))*std::pow(parameters[4]/T[i],parameters[5+label]);
            for(size_t f=0;f<nf;++f) if(F(f,1)>=0 || mode(f,15)) {
                const size_t i=size_t(F(f,0));const long j=long(F(f,1));
                const auto& two=j>=0 ? r[size_t(j)] : contact[label][f];
                const double Ttwo=j>=0 ? T[size_t(j)] : double(F(f,18));
                const double mtwo=j>=0 ? mobility[size_t(j)] :
                    double(C(i,15+label))*std::pow(parameters[4]/Ttwo,parameters[5+label]);
                std::vector<double> input={T[i],Ttwo,r[i][0],two[0],double(C(i,13+label)),
                    double(C(j>=0 ? size_t(j) : i,13+label)),phi[i],j>=0 ? phi[size_t(j)] : double(F(f,9)),
                    phi[nc+f],label==0 ? -1. : 1.,mobility[i],mtwo,double(F(f,10)),double(F(f,11)),
                    double(F(f,12)),double(F(f,19)),double(F(f,20+label))};
                const auto moments=native_spectral_face_raw(input,valleys[label]);
                (label==0 ? result.fn : result.fp)[f]=moments[0];result.energy_flux[f]+=moments[2];
                result.moments[label*nf+f]=moments;
            }
        }
        std::vector<std::string> local_cells,local_faces;
        for(size_t i=0;i<nc;++i)
            pack(local_cells,{C(i,3),C(i,4),C(i,10),n[i],p[i],real_t(T[i]),real_t(old_u[i]),real_t(u[i]),
                C(i,0),C(i,11),real_t(result.old_poisson[0][i]),real_t(phi[i]),C(i,12)});
        for(size_t f=0;f<nf;++f)
            pack(local_faces,{F(f,0),F(f,1),real_t(result.fn[f]),real_t(result.fp[f]),real_t(result.energy_flux[f]),
                real_t(result.old_poisson[0][nc+f]),real_t(phi[nc+f]),F(f,10),F(f,11),F(f,12),F(f,14),F(f,13)});
        result.local=native_fermi_local_raw(local_cells,local_faces,parameters[0]);
        result.new_energy=energies(u,T,result.new_poisson);
        residual.resize(3*nc);merit=0;real_t charge=0;
        for(size_t i=0;i<nc;++i) {
            const double scale=double(C(i,0))*(double(C(i,11))*double(C(i,10))+std::abs(old_u[i]));
            residual[i]=double(real_t(result.local[i])/(C(i,0)*C(i,3)));
            residual[nc+i]=double(real_t(result.local[nc+i])/(C(i,0)*C(i,4)));
            residual[2*nc+i]=result.local[5*nc+i]/scale;
            merit=std::max({merit,std::abs(result.local[i])/parameters[2],
                std::abs(result.local[nc+i])/parameters[2],std::abs(result.local[5*nc+i])/parameters[3]});
            charge+=real_t(result.local[nc+i])-real_t(result.local[i]);
        }
        merit=std::max(merit,double(abs_q(si_transport::elementary_charge*charge)/parameters[1]));
    }
    static int callback(void* pointer,const std::vector<double>& x,std::vector<double>& r,double* merit) {
        static_cast<Context*>(pointer)->evaluate(x,r,*merit);return 0;
    }
};
} // namespace fermi_dispatch_detail

inline FermiDispatchResult native_fermi_dispatch_raw(const std::vector<std::string>& cells,
        const std::vector<std::string>& faces,const std::vector<double>& vn,const std::vector<double>& vp,
        const std::vector<double>& parameters,int max_nfev) {
    using namespace fermi_dispatch_detail;
    if(max_nfev<1) throw std::invalid_argument("positive native FD evaluation budget required");
    Context context(cells,faces,vn,vp,parameters);const size_t nc=context.nc;
    std::vector<double> x(3*nc,0),lower(3*nc),upper(3*nc);
    for(size_t i=0;i<3*nc;++i) {
        const long double origin=std::log((long double)context.C(i%nc,i<nc ? 3 : i<2*nc ? 4 : 10));
        lower[i]=double((i<2*nc ? -600.L : 0.L)-origin);
        upper[i]=double((i<2*nc ? 600.L : std::log(1e5L))-origin);
    }
    context.result.newton=native_fermi_newton_raw(x,lower,upper,max_nfev,Context::callback,&context);
    return context.result;
}
} // namespace tcad
