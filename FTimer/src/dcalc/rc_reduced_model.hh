#pragma once

#include "rc_linear_system.hh"
#include <algorithm>
#include <cmath>
#include <vector>

namespace te {
// Passive RC reduction shared by the NLDM source fit and CCS integration.
// The physical-voltage basis preserves driving-point moments; changing
// capacitance regions updates the projected state without rebuilding it.
struct RcReducedModel {
    std::vector<double> eigen,b,weight;
    std::vector<std::vector<double>> output;
    // Physical-voltage Krylov basis, kept fixed as receiver regions change.
    std::vector<std::vector<double>> basis,projected_g,to_base,from_base;

    bool initialize_receivers(const std::vector<double>& nominal,
                              const std::vector<RcLinearSystem::Edge>& edges,
                              uint32_t driver,double seed_ground,double runtime_ground,
                              double moment_tolerance=1e-4,bool characterized_basis=false) {
        const size_t n=nominal.size();
        RcLinearSystem system;
        std::vector<double> ground(n,0.),z(n,1.);ground[driver]=seed_ground;
        if(!system.initialize(n,driver,edges) || !system.factor(ground))return false;
        for(double c:nominal)if(c<0. || !std::isfinite(c))return false;
        // CCS uses the fixed nominal-receiver voltage space. Preserve the
        // seed solve, single MGS pass and Householder normalization together:
        // weak physical modes determine both order and integration error norm.
        // The shared NLDM path retains its existing basis construction.
        std::vector<uint32_t> elimination;
        std::vector<std::vector<double>> seed_l;
        if(characterized_basis && n<=256) {
            std::vector<std::vector<uint32_t>> adjacency(n);
            for(const auto& e:edges){adjacency[e.a].push_back(e.b);adjacency[e.b].push_back(e.a);}
            std::vector<bool> seen(n,false);elimination={driver};seen[driver]=true;
            for(size_t k=0;k<elimination.size();++k)for(auto u:adjacency[elimination[k]])if(!seen[u]){seen[u]=true;elimination.push_back(u);}
            if(elimination.size()!=n)return false;
            std::reverse(elimination.begin(),elimination.end());
            std::vector<size_t> index(n);for(size_t i=0;i<n;++i)index[elimination[i]]=i;
            seed_l.assign(n,std::vector<double>(n,0.));
            for(const auto& e:edges){auto i=index[e.a],j=index[e.b];seed_l[i][i]+=e.g;seed_l[j][j]+=e.g;seed_l[i][j]-=e.g;seed_l[j][i]-=e.g;}
            seed_l[index[driver]][index[driver]]+=seed_ground;
            for(size_t j=0;j<n;++j)for(size_t i=j;i<n;++i) {
                double value=seed_l[i][j];for(size_t k=0;k<j;++k)value-=seed_l[i][k]*seed_l[j][k];
                if(i==j){if(!(value>0.))return false;seed_l[i][j]=std::sqrt(value);}
                else seed_l[i][j]=value/seed_l[j][j];
            }
        }
        auto seed_solve=[&](std::vector<double>& rhs) {
            if(seed_l.empty()) {
                if(!system.reduce(rhs))return false;
                system.back_substitute(system.driver_rhs/system.driver_diagonal,rhs);return true;
            }
            std::vector<double> values(n);
            for(size_t i=0;i<n;++i) {
                double value=rhs[elimination[i]];for(size_t j=i;j-->0;)value-=seed_l[i][j]*values[j];
                values[i]=value/seed_l[i][i];
            }
            for(size_t i=n;i-->0;) {
                double value=values[i];for(size_t j=i+1;j<n;++j)value-=seed_l[j][i]*values[j];
                values[i]=value/seed_l[i][i];
            }
            for(size_t i=0;i<n;++i)rhs[elimination[i]]=values[i];return true;
        };
        if(characterized_basis){z.assign(n,0.);z[driver]=seed_ground;if(!seed_solve(z))return false;}
        // Inspect one additional moment before accepting the maximum order.
        // A small physical-voltage residual terminates the space and, after
        // the first two moments, discards the preceding basis vector too.
        // The residual has units of time; the caller converts the 0.1 ps
        // tolerance to the library's units.
        for(unsigned k=0;k<=6;++k) {
            // Reorthogonalize in physical voltage coordinates. Building this
            // space from the current C1 instead changes the weak-mode norm
            // that controls time steps, despite a nearly equal transfer curve.
            if(characterized_basis) {
                for(const auto& q:basis) {
                    double dot=0.;for(size_t u=0;u<n;++u)dot+=q[u]*z[u];
                    for(size_t u=0;u<n;++u)z[u]-=dot*q[u];
                }
            } else for(unsigned pass=0;pass<2;++pass) {
                std::vector<double> coefficients;
                for(const auto& q:basis) {
                    double dot=0.;for(size_t u=0;u<n;++u)dot+=q[u]*z[u];
                    coefficients.push_back(dot);
                }
                for(size_t u=0;u<n;++u)for(size_t j=0;j<basis.size();++j)
                    z[u]-=coefficients[j]*basis[j][u];
            }
            double norm=0.;for(double v:z)norm+=v*v;norm=std::sqrt(norm);
            if(k>0 && norm<moment_tolerance) {
                if(k>2)basis.pop_back();
                break;
            }
            if(k==6 || norm<1e-13)break;
            const double sign=z[driver]>0.?-1.:1.;
            if(characterized_basis) {
                const double alpha=sign*norm;
                double square=0.;for(double v:z)square+=v*v;
                const double beta=1./(z[driver]*alpha-square);
                z[driver]-=alpha;
                const double factor=z[driver]*beta;
                for(size_t u=0;u<n;++u)z[u]=(u==driver?1.:0.)+factor*z[u];
            } else for(double& v:z)v*=sign/norm;
            basis.push_back(z);
            for(size_t u=0;u<n;++u)z[u]*=nominal[u];
            if(!seed_solve(z))return false;
        }
        const size_t m=basis.size();if(!m)return false;
        projected_g.assign(m,std::vector<double>(m,0.));
        for(size_t j=0;j<m;++j)for(size_t k=0;k<m;++k) {
            double value=runtime_ground*basis[j][driver]*basis[k][driver];
            for(const auto& e:edges)value+=e.g*(basis[j][e.a]-basis[j][e.b])*
                                                   (basis[k][e.a]-basis[k][e.b]);
            projected_g[j][k]=value;
        }
        return true;
    }

    bool update_receivers(const std::vector<double>& cap,uint32_t driver,
                          std::vector<double>* state=nullptr) {
        return update_receiver_modes(cap,driver,state,false);
    }

    // CCS retains modal history across receiver-capacitance changes. Its
    // implicit QL frame must keep the decomposition's order and phase; a
    // sorted Jacobi frame changes the restarted predictor's coordinates.
    // The existing NLDM/legacy update retains its original decomposition.
    bool update_receivers_ql(const std::vector<double>& cap,uint32_t driver,
                             std::vector<double>* state=nullptr) {
        return update_receiver_modes(cap,driver,state,true);
    }

    bool update_receiver_modes(const std::vector<double>& cap,uint32_t driver,
                               std::vector<double>* state,bool implicit_ql) {
        const size_t m=basis.size(),n=cap.size();
        std::vector<double> physical(m,0.);
        if(state)for(size_t j=0;j<m;++j)for(size_t k=0;k<m;++k)
            physical[j]+=to_base[j][k]*(*state)[k];
        std::vector<std::vector<double>> L(m,std::vector<double>(m,0.)),inv=L,A=L,U=L;
        for(size_t j=0;j<m;++j)for(size_t k=0;k<=j;++k) {
            double value=0.;for(size_t u=0;u<n;++u)value+=cap[u]*basis[j][u]*basis[k][u];
            for(size_t a=0;a<k;++a)value-=L[j][a]*L[k][a];
            if(j==k) {if(!(value>0.))return false;L[j][k]=std::sqrt(value);}
            else L[j][k]=value/L[k][k];
        }
        for(size_t j=0;j<m;++j)for(size_t k=0;k<=j;++k) {
            double value=j==k?1.:0.;
            for(size_t a=k;a<j;++a)value-=L[j][a]*inv[a][k];
            inv[j][k]=value/L[j][j];
        }
        for(size_t j=0;j<m;++j)for(size_t k=0;k<m;++k) {
            for(size_t a=0;a<=j;++a)for(size_t c=0;c<=k;++c)
                A[j][k]+=inv[j][a]*projected_g[a][c]*inv[k][c];
            U[j][k]=j==k?1.:0.;
        }
        if(implicit_ql) {
        // Standard symmetric Householder reduction and implicit QL iteration.
        // Preserve the solver's mode order and phase through region updates.
        std::vector<double> diagonal(m),offdiag(m);
        U=A;
        for(int i=int(m)-1;i>0;--i) {
            const int l=i-1;double h=0.,scale=0.;
            if(l>0) {
                for(int k=0;k<=l;++k)scale+=std::fabs(U[i][k]);
                if(scale==0.)offdiag[i]=U[i][l];
                else {
                    for(int k=0;k<=l;++k){U[i][k]/=scale;h+=U[i][k]*U[i][k];}
                    double f=U[i][l],g=f>=0.?-std::sqrt(h):std::sqrt(h);
                    offdiag[i]=scale*g;h-=f*g;U[i][l]=f-g;f=0.;
                    for(int j=0;j<=l;++j) {
                        U[j][i]=U[i][j]/h;g=0.;
                        for(int k=0;k<=j;++k)g+=U[j][k]*U[i][k];
                        for(int k=j+1;k<=l;++k)g+=U[k][j]*U[i][k];
                        offdiag[j]=g/h;f+=offdiag[j]*U[i][j];
                    }
                    const double hh=f/(2.*h);
                    for(int j=0;j<=l;++j) {
                        f=U[i][j];g=offdiag[j]-hh*f;offdiag[j]=g;
                        for(int k=0;k<=j;++k)U[j][k]-=f*offdiag[k]+g*U[i][k];
                    }
                }
            } else offdiag[i]=U[i][l];
            diagonal[i]=h;
        }
        diagonal[0]=offdiag[0]=0.;
        for(size_t i=0;i<m;++i) {
            if(diagonal[i]!=0.)for(size_t j=0;j<i;++j) {
                double g=0.;for(size_t k=0;k<i;++k)g+=U[i][k]*U[k][j];
                for(size_t k=0;k<i;++k)U[k][j]-=g*U[k][i];
            }
            diagonal[i]=U[i][i];U[i][i]=1.;
            for(size_t j=0;j<i;++j)U[j][i]=U[i][j]=0.;
        }
        for(size_t i=1;i<m;++i)offdiag[i-1]=offdiag[i];offdiag[m-1]=0.;
        for(size_t l=0;l<m;++l) {
            unsigned iterations=0;size_t stop;
            do {
                for(stop=l;stop+1<m;++stop) {
                    const double dd=std::fabs(diagonal[stop])+std::fabs(diagonal[stop+1]);
                    if(std::fabs(offdiag[stop])+dd==dd)break;
                }
                if(stop!=l) {
                    if(++iterations>64)return false;
                    double g=(diagonal[l+1]-diagonal[l])/(2.*offdiag[l]);
                    double r=std::hypot(g,1.);
                    g=diagonal[stop]-diagonal[l]+offdiag[l]/(g+std::copysign(r,g));
                    double si=1.,co=1.,shift=0.;int i;
                    for(i=int(stop)-1;i>=int(l);--i) {
                        const double f=si*offdiag[i],b=co*offdiag[i];r=std::hypot(f,g);offdiag[i+1]=r;
                        if(r==0.){diagonal[i+1]-=shift;offdiag[stop]=0.;break;}
                        si=f/r;co=g/r;g=diagonal[i+1]-shift;
                        r=(diagonal[i]-g)*si+2.*co*b;shift=si*r;diagonal[i+1]=g+shift;g=co*r-b;
                        for(size_t k=0;k<m;++k) {
                            const double f2=U[k][i+1];U[k][i+1]=si*U[k][i]+co*f2;U[k][i]=co*U[k][i]-si*f2;
                        }
                    }
                    if(r==0. && i>=int(l))continue;
                    diagonal[l]-=shift;offdiag[l]=g;offdiag[stop]=0.;
                }
            } while(stop!=l);
        }
        for(size_t j=0;j<m;++j)A[j][j]=diagonal[j];
        } else {
        for(unsigned iteration=0;iteration<256;++iteration) {
            size_t a=0,c=0;double largest=0.;
            for(size_t j=0;j<m;++j)for(size_t k=j+1;k<m;++k)
                if(std::fabs(A[j][k])>largest){largest=std::fabs(A[j][k]);a=j;c=k;}
            if(largest<1e-13)break;
            const double angle=.5*std::atan2(2*A[a][c],A[c][c]-A[a][a]),co=std::cos(angle),si=std::sin(angle);
            for(size_t j=0;j<m;++j){double x=A[j][a],y=A[j][c];A[j][a]=co*x-si*y;A[j][c]=si*x+co*y;}
            for(size_t j=0;j<m;++j){double x=A[a][j],y=A[c][j];A[a][j]=co*x-si*y;A[c][j]=si*x+co*y;}
            for(size_t j=0;j<m;++j){double x=U[j][a],y=U[j][c];U[j][a]=co*x-si*y;U[j][c]=si*x+co*y;}
        }
        }
        std::vector<size_t> order(m);for(size_t j=0;j<m;++j)order[j]=j;
        if(!implicit_ql)std::sort(order.begin(),order.end(),[&](size_t a,size_t c){return A[a][a]<A[c][c];});
        to_base.assign(m,std::vector<double>(m,0.));from_base=to_base;
        eigen.resize(m);b.resize(m);weight.assign(m,0.);output.assign(n,std::vector<double>(m,0.));
        for(size_t j=0;j<m;++j) {
            const size_t k=order[j];eigen[j]=std::max(0.,A[k][k]);
            for(size_t a=0;a<m;++a)for(size_t c=0;c<m;++c) {
                to_base[a][j]+=inv[c][a]*U[c][k];
                from_base[j][a]+=U[c][k]*L[a][c];
            }
            for(size_t u=0;u<n;++u) {
                for(size_t a=0;a<m;++a)output[u][j]+=basis[a][u]*to_base[a][j];
                weight[j]=std::max(weight[j],std::fabs(output[u][j]));
            }
            b[j]=output[driver][j];
        }
        if(state) {
            state->assign(m,0.);
            for(size_t j=0;j<m;++j)for(size_t a=0;a<m;++a)(*state)[j]+=from_base[j][a]*physical[a];
        }
        return true;
    }
    bool initialize(const std::vector<double>& cap,const std::vector<RcLinearSystem::Edge>& edges,uint32_t driver) {
        const size_t n=cap.size();std::vector<double> inv(n),z(n,0.);z[driver]=1.;
        for(size_t j=0;j<n;++j) {if(!(cap[j]>0.))return false;inv[j]=1/std::sqrt(cap[j]);}
        auto dot=[](const auto& a,const auto& b){double v=0.;for(size_t j=0;j<a.size();++j)v+=a[j]*b[j];return v;};
        auto mult=[&](const auto& x){std::vector<double> y(n,0.);for(const auto& e:edges){double f=e.g*(x[e.a]*inv[e.a]-x[e.b]*inv[e.b]);y[e.a]+=f*inv[e.a];y[e.b]-=f*inv[e.b];}return y;};
        std::vector<std::vector<double>> Q;
        for(unsigned k=0;k<6;++k) {
            for(unsigned pass=0;pass<2;++pass)for(const auto& q:Q){const double d=dot(q,z);for(size_t j=0;j<n;++j)z[j]-=d*q[j];}
            const double norm=std::sqrt(dot(z,z));if(norm<1e-13)break;
            for(auto& x:z)x/=norm;Q.push_back(z);z=mult(z);
        }
        const size_t m=Q.size();if(!m)return false;
        std::vector<std::vector<double>> A(m,std::vector<double>(m)),U(m,std::vector<double>(m,0.));
        for(size_t k=0;k<m;++k){const auto x=mult(Q[k]);for(size_t j=0;j<m;++j)A[j][k]=dot(Q[j],x);U[k][k]=1.;}
        for(unsigned iteration=0;iteration<256;++iteration) {
            size_t a=0,b=0;double largest=0.;
            for(size_t j=0;j<m;++j)for(size_t k=j+1;k<m;++k)if(std::fabs(A[j][k])>largest){largest=std::fabs(A[j][k]);a=j;b=k;}
            if(largest<1e-13)break;
            const double angle=.5*std::atan2(2*A[a][b],A[b][b]-A[a][a]),c=std::cos(angle),s=std::sin(angle);
            for(size_t j=0;j<m;++j){double x=A[j][a],y=A[j][b];A[j][a]=c*x-s*y;A[j][b]=s*x+c*y;}
            for(size_t j=0;j<m;++j){double x=A[a][j],y=A[b][j];A[a][j]=c*x-s*y;A[b][j]=s*x+c*y;}
            for(size_t j=0;j<m;++j){double x=U[j][a],y=U[j][b];U[j][a]=c*x-s*y;U[j][b]=s*x+c*y;}
        }
        std::vector<size_t> order(m);for(size_t j=0;j<m;++j)order[j]=j;
        std::sort(order.begin(),order.end(),[&](size_t a,size_t b){return A[a][a]<A[b][b];});
        eigen.resize(m);b.resize(m);weight.assign(m,0.);output.assign(n,std::vector<double>(m,0.));
        for(size_t j=0;j<m;++j) {
            const size_t k=order[j];eigen[j]=std::max(0.,A[k][k]);
            for(size_t u=0;u<n;++u){for(size_t a=0;a<m;++a)output[u][j]+=Q[a][u]*U[a][k];output[u][j]*=inv[u];weight[j]=std::max(weight[j],std::fabs(output[u][j]));}
            b[j]=output[driver][j];
        }
        return true;
    }
};

} // namespace te
