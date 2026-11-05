#pragma once

// Native HMM/SUSHI scalar Poisson operator, zero polarization. Geometry is
// supplied as cell/face data, never as a Python-assembled matrix or solution.
#include "fermi_local.h"
#include <array>

namespace tcad {
namespace hybrid_poisson_detail {
struct Local {
    std::vector<size_t> ids,faces;
    std::vector<int> signs;
    std::vector<real_t> matrix;
    std::vector<std::array<real_t,3>> gradient;
};
inline std::vector<real_t> cholesky(const std::vector<real_t>& matrix,
    const std::vector<real_t>& rhs) {
    const size_t n=rhs.size();
    std::vector<real_t> scale(n),L(n*n,0),y(n),x(n);
    for (size_t i=0;i<n;++i) {
        if (!isfinite_q(matrix[i*n+i]) || matrix[i*n+i]<=0)
            throw std::invalid_argument("unanchored or invalid native Poisson operator");
        scale[i]=sqrt_q(matrix[i*n+i]);
    }
    for (size_t i=0;i<n;++i) for (size_t j=0;j<=i;++j) {
        real_t value=matrix[i*n+j]/(scale[i]*scale[j]);
        for (size_t k=0;k<j;++k) value-=L[i*n+k]*L[j*n+k];
        if (i==j) {
            if (!isfinite_q(value) || value<=128*epsilon_q())
                throw std::invalid_argument("native Poisson operator is singular or too ill-conditioned");
            L[i*n+j]=sqrt_q(value);
        } else L[i*n+j]=value/L[j*n+j];
    }
    for (size_t i=0;i<n;++i) {
        real_t value=rhs[i]/scale[i];
        for (size_t k=0;k<i;++k) value-=L[i*n+k]*y[k];
        y[i]=value/L[i*n+i];
    }
    for (size_t i=n;i-->0;) {
        real_t value=y[i];
        for (size_t k=i+1;k<n;++k) value-=L[k*n+i]*x[k];
        x[i]=value/L[i*n+i];
    }
    for (size_t i=0;i<n;++i) x[i]/=scale[i];
    return x;
}
} // namespace hybrid_poisson_detail

// Cells (10): V,eps,rho_fixed,n,p,Nt,trap_fraction,centroid_x,y,z.
// Faces (10): owner,neighbor,area_vector_x,y,z,centroid_x,y,z,Dirichlet_mode,V.
// Decimal states retain the input density bits across Cython. All geometry,
// charge assembly, factorization, flux reconstruction and energy use real_t.
// Output groups: potential[nc+nf], E[3nc], flux[nf], mismatch[ni],
// algebraic residual[nfree], Gauss residual[nc], metrics[U,global,boundary,Q,valid].
inline std::vector<std::vector<double>> native_hybrid_poisson_raw(
    const std::vector<std::string>& cells,const std::vector<std::string>& faces,
    double charge_atol_C) {
    using namespace fermi_local_detail;
    using namespace hybrid_poisson_detail;
    if (cells.empty() || cells.size()%10 || faces.empty() || faces.size()%10 ||
        !std::isfinite(charge_atol_C) || charge_atol_C<0)
        throw std::invalid_argument("native Poisson dimensions or charge budget invalid");
    const size_t nc=cells.size()/10,nf=faces.size()/10,N=nc+nf;
    if (N>512) throw std::invalid_argument("native dense Poisson supports at most 512 cell+face unknowns");
    const auto c=decimals(cells),f=decimals(faces);
    std::vector<Local> locals(nc);
    std::vector<real_t> rho(nc),matrix(N*N,0),rhs(N,0),potential(N,0);
    std::vector<bool> fixed(N,false);
    std::vector<size_t> free;
    real_t reference=0;bool anchored=false;
    for (size_t i=0;i<nc;++i) {
        const size_t b=10*i;
        if (c[b]<=0 || c[b+1]<=0 || c[b+3]<0 || c[b+4]<0 || c[b+5]<0 || c[b+6]<0 || c[b+6]>1)
            throw std::invalid_argument("native Poisson requires positive volume/epsilon and valid charge state");
        rho[i]=c[b+2]+si_transport::elementary_charge*(c[b+4]-c[b+3]-c[b+5]*c[b+6]);
        rhs[i]=rho[i]*c[b];
    }
    for (size_t k=0;k<nf;++k) {
        const size_t b=10*k;
        if (f[b]<0 || f[b]>=nc || f[b+1]<-1 || f[b+1]>=nc ||
            f[b]!=(real_t)(size_t)f[b] || (f[b+1]!=-1 && f[b+1]!=(real_t)(size_t)f[b+1]) ||
            f[b]==f[b+1] || (f[b+8]!=0 && f[b+8]!=1) || (f[b+8]==1 && f[b+1]>=0))
            throw std::invalid_argument("native Poisson face index or boundary mode invalid");
        const size_t owner=(size_t)f[b];const long neighbor=(long)f[b+1];
        locals[owner].faces.push_back(k);locals[owner].signs.push_back(1);
        if (neighbor>=0) { locals[neighbor].faces.push_back(k);locals[neighbor].signs.push_back(-1); }
        if (f[b+8]==1) {
            fixed[nc+k]=true;
            if (!anchored) { reference=f[b+9];anchored=true; }
        }
    }
    if (!anchored) throw std::invalid_argument("native Poisson Dirichlet reference required");
    // Each connected component needs its own fixed-voltage boundary. Reject
    // before factorization; a tiny numerical pivot must not anchor a domain.
    std::vector<bool> seen(nc,false);
    for (size_t start=0;start<nc;++start) if (!seen[start]) {
        std::vector<size_t> queue={start};seen[start]=true;bool contact=false;
        for (size_t q=0;q<queue.size();++q) for (size_t k:locals[queue[q]].faces) {
            const size_t b=10*k;
            contact=contact || fixed[nc+k];
            if (f[b+1]<0) continue;
            const size_t other=(size_t)f[b]==queue[q] ? (size_t)f[b+1] : (size_t)f[b];
            if (!seen[other]) { seen[other]=true;queue.push_back(other); }
        }
        if (!contact) throw std::invalid_argument("unanchored native Poisson connected component");
    }
    for (size_t i=0;i<nc;++i) {
        auto& local=locals[i];const size_t m=local.faces.size(),s=m+1;
        if (m<4) throw std::invalid_argument("native 3-D cell needs at least four faces");
        local.ids.push_back(i);local.gradient.resize(s,{0,0,0});local.matrix.assign(s*s,0);
        std::vector<std::array<real_t,3>> delta(m);
        std::vector<real_t> weight(m),residual(m*s);
        for (size_t q=0;q<m;++q) {
            const size_t k=local.faces[q],b=10*k;real_t area2=0,projection=0;
            local.ids.push_back(nc+k);
            for (size_t d=0;d<3;++d) {
                const real_t av=f[b+2+d]*local.signs[q];
                area2+=av*av;delta[q][d]=f[b+5+d]-c[10*i+7+d];projection+=av*delta[q][d];
                local.gradient[q+1][d]=av/c[10*i];local.gradient[0][d]-=av/c[10*i];
            }
            if (area2<=0 || projection<=0)
                throw std::invalid_argument("native Poisson centroid must be strictly inside positive-area faces");
            weight[q]=area2/projection;
        }
        for (size_t q=0;q<m;++q) for (size_t a=0;a<s;++a) {
            real_t value=a==0 ? -1 : (a==q+1 ? 1 : 0);
            for (size_t d=0;d<3;++d) value-=delta[q][d]*local.gradient[a][d];
            residual[q*s+a]=value;
        }
        for (size_t a=0;a<s;++a) for (size_t b=0;b<=a;++b) {
            real_t value=0;
            for (size_t d=0;d<3;++d) value+=c[10*i]*local.gradient[a][d]*local.gradient[b][d];
            for (size_t q=0;q<m;++q) value+=weight[q]*residual[q*s+a]*residual[q*s+b];
            value*=c[10*i+1];local.matrix[a*s+b]=local.matrix[b*s+a]=value;
        }
        for (size_t a=0;a<s;++a) for (size_t b=0;b<s;++b)
            matrix[local.ids[a]*N+local.ids[b]]+=local.matrix[a*s+b];
    }
    for (size_t k=0;k<nf;++k) if (fixed[nc+k]) potential[nc+k]=f[10*k+9]-reference;
    for (size_t k=0;k<N;++k) if (!fixed[k]) free.push_back(k);
    const size_t nfree=free.size();
    std::vector<real_t> reduced(nfree*nfree),force(nfree);
    for (size_t a=0;a<nfree;++a) {
        const size_t i=free[a];force[a]=rhs[i];
        for (size_t j=0;j<N;++j) if (fixed[j]) force[a]-=matrix[i*N+j]*potential[j];
        for (size_t b=0;b<nfree;++b) reduced[a*nfree+b]=matrix[i*N+free[b]];
    }
    const auto answer=cholesky(reduced,force);
    for (size_t a=0;a<nfree;++a) potential[free[a]]=answer[a];
    std::vector<real_t> electric(3*nc,0),flux(nf,0),opposite(nf,0),action(N,0),gauss(nc,0),mismatch,algebraic;
    real_t energy=0;
    for (size_t i=0;i<nc;++i) {
        const auto& local=locals[i];const size_t s=local.ids.size();
        std::vector<real_t> centered(s),force_local(s,0);
        for (size_t a=0;a<s;++a) centered[a]=potential[local.ids[a]]-potential[i];
        for (size_t a=0;a<s;++a) {
            for (size_t b=0;b<s;++b) force_local[a]+=local.matrix[a*s+b]*centered[b];
            action[local.ids[a]]+=force_local[a];energy+=centered[a]*force_local[a]/2;
            for (size_t d=0;d<3;++d) electric[3*i+d]-=local.gradient[a][d]*centered[a];
        }
        for (size_t q=0;q<local.faces.size();++q) {
            if (local.signs[q]>0) flux[local.faces[q]]=-force_local[q+1];
            else opposite[local.faces[q]]=-force_local[q+1];
        }
    }
    real_t boundary=0,total=0,worst=0;
    for (size_t k=0;k<nf;++k) {
        const size_t i=(size_t)f[10*k];const long j=(long)f[10*k+1];
        gauss[i]+=flux[k];
        if (j>=0) { gauss[j]-=flux[k];mismatch.push_back(flux[k]+opposite[k]); }
        else boundary+=flux[k];
    }
    for (size_t i=0;i<nc;++i) { gauss[i]-=rhs[i];total+=rhs[i];worst=std::max(worst,abs_q(gauss[i])); }
    for (size_t i:free) { algebraic.push_back(action[i]-rhs[i]);worst=std::max(worst,abs_q(algebraic.back())); }
    for (real_t value:mismatch) worst=std::max(worst,abs_q(value));
    worst=std::max(worst,abs_q(boundary-total));
    for (size_t k=0;k<N;++k) potential[k]+=reference;
    const std::vector<real_t> metrics={energy,boundary-total,boundary,total,worst<=charge_atol_C ? (real_t)1 : (real_t)0};
    return {exported(potential),exported(electric),exported(flux),exported(mismatch),
        exported(algebraic),exported(gauss),exported(metrics)};
}
} // namespace tcad
