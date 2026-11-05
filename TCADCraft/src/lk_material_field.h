#pragma once
#include "poisson_solver.h"
#include <algorithm>
#include <stdexcept>

namespace tcad {

// Each 1-D FV edge consists of two nodal half-materials. Interior fixed charge
// sets the jumps in edge D; its half-edge weighted nodal mean drives LK.
// No uniform-P approximation or added gradient energy.
inline real_t lk_monotone_cubic(real_t a, real_t beta, real_t b) {
    if (!isfinite_q(a) || !isfinite_q(beta) || !isfinite_q(b) || a <= 0 || beta <= 0)
        throw std::invalid_argument("material-field LK requires a finite monotone cubic");
    if (b == 0) return 0;
    const real_t target = abs_q(b);
    real_t lo = 0, hi = std::min(target/a,
        exp_q((log_q(target)-log_q(beta))/TCAD_CONST(3.0)));
    if (!isfinite_q(hi) || hi <= 0) throw std::invalid_argument("material-field LK root range");
    while ((beta*hi*hi+a)*hi < target) {
        hi *= TCAD_CONST(2.0);
        if (!isfinite_q(hi)) throw std::invalid_argument("material-field LK root overflow");
    }
    real_t value = hi;
    for (size_t iteration=0; iteration<200; ++iteration) {
        const real_t residual = (beta*value*value+a)*value-target;
        if (abs_q(residual) <= TCAD_CONST(16.0)*epsilon_q()*target)
            return b < 0 ? -value : value;
        if (residual > 0) hi=value; else lo=value;
        real_t next=value-residual/(a+TCAD_CONST(3.0)*beta*value*value);
        if (next <= lo || next >= hi || !isfinite_q(next)) next=lo+(hi-lo)/TCAD_CONST(2.0);
        if (next==value || next==lo || next==hi) return b < 0 ? -next : next;
        value=next;
    }
    throw std::runtime_error("material-field LK local root did not converge");
}

inline std::vector<real_t> lk_chain_widths(const Grid3D& g, int axis) {
    const size_t n=g.npts();
    auto edge=[&](size_t q) {return axis==0 ? g.dx_edge(q) : axis==1 ? g.dy_edge(q) : g.dz_edge(q);};
    std::vector<real_t> w(n);
    for(size_t i=0;i<n;++i) w[i]=((i ? edge(i-1):TCAD_CONST(0.0))+
        (i+1<n ? edge(i):TCAD_CONST(0.0)))/TCAD_CONST(2.0);
    if(n>1) {
        if(g.lk_zero_d_faces[2*axis]) w.front()+=edge(0)/TCAD_CONST(2.0);
        if(g.lk_zero_d_faces[2*axis+1]) w.back()+=edge(n-2)/TCAD_CONST(2.0);
    }
    return w;
}

inline std::vector<real_t> lk_material_field_1d(const Grid3D& g,
        const std::vector<real_t>& eps, const std::vector<char>& mask,
        const std::vector<real_t>& polarization, const std::vector<real_t>& phi, int axis) {
    const size_t n=g.npts();
    auto edge=[&](size_t q) {return axis==0 ? g.dx_edge(q) : axis==1 ? g.dy_edge(q) : g.dz_edge(q);};
    const auto widths=lk_chain_widths(g,axis);
    std::vector<real_t> fields(3*n,0);
    for(size_t i=0;i+1<n;++i) {
        const real_t h=edge(i), e=TCAD_CONST(2.0)*eps[i]*eps[i+1]/(eps[i]+eps[i+1]);
        const real_t pi=mask[i] ? polarization[3*i+axis] : TCAD_CONST(0.0);
        const real_t pj=mask[i+1] ? polarization[3*(i+1)+axis] : TCAD_CONST(0.0);
        const real_t d=e*((phi[i]-phi[i+1])/h+(pi/eps[i]+pj/eps[i+1])/TCAD_CONST(2.0));
        fields[3*i+axis]+=h*(d-pi)/(TCAD_CONST(2.0)*widths[i]*eps[i]);
        fields[3*(i+1)+axis]+=h*(d-pj)/(TCAD_CONST(2.0)*widths[i+1]*eps[i+1]);
    }
    if(n>1) for(int side=0;side<2;++side) if(g.lk_zero_d_faces[2*axis+side]) {
        const size_t i=side ? n-1 : 0;
        const real_t p=mask[i] ? polarization[3*i+axis] : TCAD_CONST(0.0);
        // The exterior half has D=0, hence E=-P/eps, including at t=0.
        fields[3*i+axis]-=edge(side ? n-2 : 0)*p/
            (TCAD_CONST(2.0)*widths[i]*eps[i]);
    }
    return fields;
}

// Fixed-potential material response for the transport Newton Schur complement.
// The material field is linear in phi and neighboring P, so the implicit LK
// Jacobian is tridiagonal. Non-FE rows pin P=0; no carrier equation is removed.
struct LKMaterialMatrix1D {
    std::vector<real_t> lower, diagonal, upper, source;
};

inline LKMaterialMatrix1D lk_material_matrix_1d(const Grid3D& g,
        const std::vector<real_t>& eps, const std::vector<char>& mask,
        const std::vector<real_t>& previous, const std::vector<real_t>& phi,
        real_t alpha, real_t rate, real_t imprint, real_t depol_eps,
        int polar_axis, int axis) {
    const size_t n=g.npts();
    LKMaterialMatrix1D m{std::vector<real_t>(n,0),std::vector<real_t>(n,1),
        std::vector<real_t>(n,0),std::vector<real_t>(n,0)};
    const auto w=lk_chain_widths(g,axis);
    auto edge=[&](size_t q) {return axis==0 ? g.dx_edge(q) : axis==1 ? g.dy_edge(q) : g.dz_edge(q);};
    for(size_t i=0;i<n;++i) if(mask[i]) {
        m.diagonal[i]=alpha+rate+((axis==polar_axis && depol_eps>0) ?
            TCAD_CONST(1.0)/(depol_eps*EPS0) : TCAD_CONST(0.0));
        m.source[i]=rate*previous[3*i+axis]-(axis==polar_axis ? imprint : TCAD_CONST(0.0));
        auto face=[&](size_t j, real_t h, bool right) {
            const real_t e=TCAD_CONST(2.0)*eps[i]*eps[j]/(eps[i]+eps[j]);
            const real_t weight=h/(TCAD_CONST(2.0)*w[i]);
            m.diagonal[i]+=weight*(TCAD_CONST(1.0)/eps[i]-e/(TCAD_CONST(2.0)*eps[i]*eps[i]));
            const real_t off=mask[j] ? -weight*e/(TCAD_CONST(2.0)*eps[i]*eps[j]) : TCAD_CONST(0.0);
            if(right) m.upper[i]=off; else m.lower[i]=off;
            m.source[i]+=e*(right ? phi[i]-phi[j] : phi[j]-phi[i])/
                (TCAD_CONST(2.0)*w[i]*eps[i]);
        };
        if(i) face(i-1,edge(i-1),false);
        if(i+1<n) face(i+1,edge(i),true);
        if(n>1 && i==0 && g.lk_zero_d_faces[2*axis])
            m.diagonal[i]+=edge(0)/(TCAD_CONST(2.0)*w[i]*eps[i]);
        if(n>1 && i==n-1 && g.lk_zero_d_faces[2*axis+1])
            m.diagonal[i]+=edge(n-2)/(TCAD_CONST(2.0)*w[i]*eps[i]);
    }
    return m;
}

// Thomas factorization uses native real_t throughout. This M-matrix is
// nonsingular for alpha+rate>0, positive permittivity and a 1-D chain.
inline std::vector<real_t> lk_tridiagonal_solve(const LKMaterialMatrix1D& m,
        const std::vector<real_t>& diagonal, std::vector<real_t> rhs) {
    auto d=diagonal; const size_t n=d.size();
    for(size_t i=0;i<n;++i) {
        if(!isfinite_q(d[i]) || d[i]<=0)
            throw std::runtime_error("material-field LK invalid tridiagonal pivot");
        if(i+1<n) {
            const real_t factor=m.lower[i+1]/d[i];
            d[i+1]-=factor*m.upper[i]; rhs[i+1]-=factor*rhs[i];
        }
    }
    for(size_t i=n;i-->0;) {
        if(i+1<n) rhs[i]-=m.upper[i]*rhs[i+1];
        rhs[i]/=d[i];
    }
    return rhs;
}

inline std::vector<real_t> solve_lk_material_response_1d(const Grid3D& g,
        const std::vector<real_t>& eps, const std::vector<char>& mask,
        const std::vector<real_t>& previous, const std::vector<real_t>& phi,
        real_t alpha, real_t beta, real_t rate, real_t imprint, real_t depol_eps,
        int polar_axis, int axis) {
    const size_t n=g.npts();
    const auto m=lk_material_matrix_1d(g,eps,mask,previous,phi,alpha,rate,imprint,depol_eps,polar_axis,axis);
    std::vector<real_t> p(n,0), residual(n), diagonal(n);
    // Start at zero: a common residual scale makes the line search valid even
    // when the previous history contains large, oppositely signed domains.
    real_t scale=0;
    for(real_t s:m.source) scale=std::max(scale,abs_q(s));
    auto evaluate=[&](const std::vector<real_t>& v) {
        real_t norm=0, rounding=scale;
        for(size_t i=0;i<n;++i) {
            const real_t cubic=mask[i] ? beta*v[i]*v[i]*v[i] : TCAD_CONST(0.0);
            real_t f=m.diagonal[i]*v[i]+cubic-m.source[i];
            real_t local=abs_q(m.diagonal[i]*v[i])+abs_q(cubic)+abs_q(m.source[i]);
            if(i) { f+=m.lower[i]*v[i-1]; local+=abs_q(m.lower[i]*v[i-1]); }
            if(i+1<n) { f+=m.upper[i]*v[i+1]; local+=abs_q(m.upper[i]*v[i+1]); }
            if(!isfinite_q(f)) throw std::runtime_error("material-field LK response range");
            residual[i]=f; norm=std::max(norm,abs_q(f)); rounding=std::max(rounding,local);
        }
        return std::make_pair(norm,rounding);
    };
    for(size_t iteration=0;iteration<200;++iteration) {
        const auto f=evaluate(p);
        if(f.first<=TCAD_CONST(128.0)*epsilon_q()*f.second) {
            std::vector<real_t> result(3*n,0);
            for(size_t i=0;i<n;++i) if(mask[i]) {
                result[3*i+axis]=p[i];
                for(int c=0;c<3;++c) if(c!=axis) {
                    const real_t extra=(c==polar_axis && depol_eps>0) ? TCAD_CONST(1.0)/(depol_eps*EPS0) : TCAD_CONST(0.0);
                    result[3*i+c]=lk_monotone_cubic(alpha+rate+extra,beta,
                        rate*previous[3*i+c]-(c==polar_axis ? imprint : TCAD_CONST(0.0)));
                }
            }
            return result;
        }
        for(size_t i=0;i<n;++i) {
            diagonal[i]=m.diagonal[i]+(mask[i] ? TCAD_CONST(3.0)*beta*p[i]*p[i] : TCAD_CONST(0.0));
            residual[i]=-residual[i];
        }
        const auto direction=lk_tridiagonal_solve(m,diagonal,residual);
        std::vector<real_t> trial(n);
        real_t damping=1; bool accepted=false;
        for(size_t backtrack=0;backtrack<100;++backtrack) {
            for(size_t i=0;i<n;++i) trial[i]=p[i]+damping*direction[i];
            const auto next=evaluate(trial);
            if(next.first < f.first || next.first<=TCAD_CONST(128.0)*epsilon_q()*next.second) {
                p.swap(trial); accepted=true; break;
            }
            damping/=TCAD_CONST(2.0);
        }
        if(!accepted) break;
    }
    throw std::runtime_error("material-field LK fixed-potential response did not converge");
}

inline std::vector<real_t> lk_material_susceptibility_1d(const Grid3D& g,
        const std::vector<real_t>& eps, const std::vector<char>& mask,
        const std::vector<real_t>& polarization, real_t alpha, real_t beta, real_t rate,
        real_t depol_eps, int polar_axis, int axis) {
    const size_t n=g.npts(); const auto widths=lk_chain_widths(g,axis);
    const auto m=lk_material_matrix_1d(g,eps,mask,std::vector<real_t>(3*n,0),
        std::vector<real_t>(n,0),alpha,rate,0,depol_eps,polar_axis,axis);
    std::vector<real_t> diagonal=m.diagonal, derivative(n*n,0);
    for(size_t i=0;i<n;++i) if(mask[i]) {
        const real_t p=polarization[3*i+axis]; diagonal[i]+=TCAD_CONST(3.0)*beta*p*p;
    }
    for(size_t column=0;column<n;++column) {
        std::vector<real_t> rhs(n,0);
        auto face=[&](size_t l, size_t r) {
            const real_t e=TCAD_CONST(2.0)*eps[l]*eps[r]/(eps[l]+eps[r]);
            const real_t sign=column==l ? TCAD_CONST(1.0) : -TCAD_CONST(1.0);
            if(mask[l]) rhs[l]+=sign*e/(TCAD_CONST(2.0)*widths[l]*eps[l]);
            if(mask[r]) rhs[r]+=sign*e/(TCAD_CONST(2.0)*widths[r]*eps[r]);
        };
        if(column) face(column-1,column);
        if(column+1<n) face(column,column+1);
        const auto response=lk_tridiagonal_solve(m,diagonal,rhs);
        for(size_t row=0;row<n;++row) derivative[row*n+column]=response[row];
    }
    return derivative;
}

// At fixed potential, the componentwise cubic LK law separates into Cartesian
// lines. Poisson couples these lines through the full vector divergence. This
// is the existing local LK model; no inter-component or gradient term is added.
template<class F> inline void lk_material_lines(const Grid3D& g, F visit) {
    const size_t sizes[]={g.nx,g.ny,g.nz}, strides[]={1,g.nx,g.nx*g.ny};
    for(int axis=0;axis<3;++axis) if(sizes[axis]>1) {
        Grid3D line{1,1,1,g.dx,g.dy,g.dz};
        line.lk_zero_d_faces=g.lk_zero_d_faces;
        if(axis==0) {line.nx=g.nx;line.xx=g.xx;}
        if(axis==1) {line.ny=g.ny;line.yx=g.yx;}
        if(axis==2) {line.nz=g.nz;line.zx=g.zx;}
        for(size_t base=0;base<g.npts();++base) if((base/strides[axis])%sizes[axis]==0) {
            std::vector<size_t> nodes(sizes[axis]);
            for(size_t q=0;q<nodes.size();++q) nodes[q]=base+q*strides[axis];
            visit(axis,line,nodes);
        }
    }
}

inline std::vector<real_t> lk_material_field_nd(const Grid3D& g,
        const std::vector<real_t>& eps, const std::vector<char>& mask,
        const std::vector<real_t>& p, const std::vector<real_t>& phi, int) {
    std::vector<real_t> result(3*g.npts(),0);
    lk_material_lines(g,[&](int axis,const Grid3D& line,const std::vector<size_t>& nodes) {
        const size_t m=nodes.size();std::vector<real_t> e(m),v(m),pl(3*m,0);std::vector<char> f(m);
        for(size_t q=0;q<m;++q) {const size_t i=nodes[q];e[q]=eps[i];v[q]=phi[i];f[q]=mask[i];pl[3*q+axis]=p[3*i+axis];}
        const auto field=lk_material_field_1d(line,e,f,pl,v,axis);
        for(size_t q=0;q<m;++q) result[3*nodes[q]+axis]=field[3*q+axis];
    });
    return result;
}

inline std::vector<real_t> solve_lk_material_response_nd(const Grid3D& g,
        const std::vector<real_t>& eps, const std::vector<char>& mask,
        const std::vector<real_t>& previous, const std::vector<real_t>& phi,
        real_t alpha, real_t beta, real_t rate, real_t imprint, real_t depol_eps,
        int polar_axis, int) {
    const size_t sizes[]={g.nx,g.ny,g.nz};std::vector<real_t> result(3*g.npts(),0);
    // Singleton axes still retain their local history and internal field.
    for(size_t i=0;i<g.npts();++i) if(mask[i]) for(int axis=0;axis<3;++axis) if(sizes[axis]==1) {
        const real_t extra=(axis==polar_axis && depol_eps>0) ? TCAD_CONST(1.0)/(depol_eps*EPS0) : TCAD_CONST(0.0);
        result[3*i+axis]=lk_monotone_cubic(alpha+rate+extra,beta,
            rate*previous[3*i+axis]-(axis==polar_axis ? imprint : TCAD_CONST(0.0)));
    }
    lk_material_lines(g,[&](int axis,const Grid3D& line,const std::vector<size_t>& nodes) {
        const size_t m=nodes.size();std::vector<real_t> e(m),v(m),old(3*m,0);std::vector<char> f(m);
        for(size_t q=0;q<m;++q) {const size_t i=nodes[q];e[q]=eps[i];v[q]=phi[i];f[q]=mask[i];old[3*q+axis]=previous[3*i+axis];}
        const auto p=solve_lk_material_response_1d(line,e,f,old,v,alpha,beta,rate,imprint,depol_eps,polar_axis,axis);
        for(size_t q=0;q<m;++q) result[3*nodes[q]+axis]=p[3*q+axis];
    });
    return result;
}

// Each response row has support only on its Cartesian material line. Store
// those line columns contiguously, with one N*axis_size block per active axis.
// Singleton axes have no potential response and consume no storage.
inline size_t lk_material_line_offset(const Grid3D& g, int axis) {
    const size_t sizes[]={g.nx,g.ny,g.nz};size_t offset=0;
    for(int a=0;a<axis;++a) if(sizes[a]>1) offset+=g.npts()*sizes[a];
    return offset;
}

inline std::vector<real_t> lk_material_susceptibility_lines(const Grid3D& g,
        const std::vector<real_t>& eps, const std::vector<char>& mask,
        const std::vector<real_t>& p, real_t alpha, real_t beta, real_t rate,
        real_t depol_eps, int polar_axis, int) {
    std::vector<real_t> result(lk_material_line_offset(g,3),0);
    lk_material_lines(g,[&](int axis,const Grid3D& line,const std::vector<size_t>& nodes) {
        const size_t m=nodes.size(),offset=lk_material_line_offset(g,axis);
        std::vector<real_t> e(m),pl(3*m,0);std::vector<char> f(m);
        for(size_t q=0;q<m;++q) {const size_t i=nodes[q];e[q]=eps[i];f[q]=mask[i];pl[3*q+axis]=p[3*i+axis];}
        const auto d=lk_material_susceptibility_1d(line,e,f,pl,alpha,beta,rate,depol_eps,polar_axis,axis);
        for(size_t r=0;r<m;++r) for(size_t c=0;c<m;++c)
            result[offset+nodes[r]*m+c]=d[r*m+c];
    });
    return result;
}

// Dense reference layout retained for derivative verification. Production
// Newton assembly uses the compact line storage above.
// Component-major (axis*N + row)*N + column. The exact Schur derivative
// includes every polarization response along the corresponding material line.
inline std::vector<real_t> lk_material_susceptibility_nd(const Grid3D& g,
        const std::vector<real_t>& eps, const std::vector<char>& mask,
        const std::vector<real_t>& p, real_t alpha, real_t beta, real_t rate,
        real_t depol_eps, int polar_axis, int) {
    const size_t n=g.npts();std::vector<real_t> result(3*n*n,0);
    lk_material_lines(g,[&](int axis,const Grid3D& line,const std::vector<size_t>& nodes) {
        const size_t m=nodes.size();std::vector<real_t> e(m),pl(3*m,0);std::vector<char> f(m);
        for(size_t q=0;q<m;++q) {const size_t i=nodes[q];e[q]=eps[i];f[q]=mask[i];pl[3*q+axis]=p[3*i+axis];}
        const auto d=lk_material_susceptibility_1d(line,e,f,pl,alpha,beta,rate,depol_eps,polar_axis,axis);
        for(size_t r=0;r<m;++r) for(size_t c=0;c<m;++c)
            result[(axis*n+nodes[r])*n+nodes[c]]=d[r*m+c];
    });
    return result;
}

// Returns false without changing phi/P when the caller's outer budget is
// exhausted. Samples are (voltage residual [V], dV/dD [m^2/F]). Local cubic
// roundoff is controlled at native precision; the outer root has no double cap.
inline bool solve_lk_material_chain(const Grid3D& g, const std::vector<real_t>& eps,
        const std::vector<char>& mask, const std::vector<real_t>& previous,
        real_t alpha, real_t beta, real_t viscosity, real_t imprint, real_t depol_eps,
        int polar_axis, int axis, real_t dt, real_t bottom, real_t top, size_t max_iter,
        std::vector<real_t>& phi, std::vector<real_t>& polarization,
        std::vector<std::vector<real_t>>& samples,
        const std::vector<real_t>& fixed_doping = {}) {
    const size_t n=g.npts(); const auto widths=lk_chain_widths(g,axis);
    auto edge=[&](size_t q) {return axis==0 ? g.dx_edge(q) : axis==1 ? g.dy_edge(q) : g.dz_edge(q);};
    if (!fixed_doping.empty() && (fixed_doping.size()!=n ||
            fixed_doping.front()!=0 || fixed_doping.back()!=0))
        throw std::invalid_argument("material-field LK fixed charge requires zero endpoint doping and one value per node");
    // Contact rows are Dirichlet constraints, not charged control volumes.
    // D_edge = D_left + offset_edge. E_i uses the nodal half-edge average.
    std::vector<real_t> edge_offset(n-1,0), node_offset(n,0);
    if (!fixed_doping.empty()) {
        for(size_t i=0;i<n;++i) if (!isfinite_q(fixed_doping[i]))
            throw std::invalid_argument("material-field LK fixed doping must be finite");
        for(size_t i=1;i+1<n;++i) {
            edge_offset[i]=edge_offset[i-1]+QE*fixed_doping[i]*widths[i];
            if (!isfinite_q(edge_offset[i]))
                throw std::invalid_argument("material-field LK fixed-charge displacement range");
        }
        for(size_t i=0;i<n;++i)
            node_offset[i]=((i ? edge(i-1)*edge_offset[i-1] : TCAD_CONST(0.0))+
                (i+1<n ? edge(i)*edge_offset[i] : TCAD_CONST(0.0)))/(TCAD_CONST(2.0)*widths[i]);
    }
    const real_t rate=viscosity/dt, drive=bottom-top;
    if (!isfinite_q(alpha+rate) || alpha+rate<=0)
        throw std::invalid_argument("material-field LK requires alpha+viscosity/dt > 0");
    samples.clear();
    std::vector<real_t> candidate(3*n,0);
    real_t compliance=0, source=0, pscale=0;
    for(size_t i=0;i<n;++i) {
        compliance+=widths[i]/eps[i];
        source-=widths[i]*node_offset[i]/eps[i];
        if(mask[i]) {
            source+=widths[i]*previous[3*i+axis]/eps[i];
            pscale=std::max(pscale,abs_q(previous[3*i+axis]));
            for(int c=0;c<3;++c) if(c!=axis) {
                const real_t extra=(c==polar_axis && depol_eps>0) ? TCAD_CONST(1.0)/(depol_eps*EPS0):TCAD_CONST(0.0);
                candidate[3*i+c]=lk_monotone_cubic(alpha+rate+extra,beta,
                    rate*previous[3*i+c]-(c==polar_axis ? imprint:TCAD_CONST(0.0)));
            }
        }
    }
    real_t guess=(drive+source)/compliance;
    auto evaluate=[&](real_t d) {
        real_t voltage=0, derivative=0, scale=abs_q(drive);
        for(size_t i=0;i<n;++i) {
            real_t p=0, slope=0;
            const real_t local_d=d+node_offset[i];
            if(mask[i]) {
                const real_t extra=(axis==polar_axis && depol_eps>0) ? TCAD_CONST(1.0)/(depol_eps*EPS0):TCAD_CONST(0.0);
                const real_t a=alpha+rate+extra+TCAD_CONST(1.0)/eps[i];
                p=lk_monotone_cubic(a,beta,rate*previous[3*i+axis]+local_d/eps[i]-
                    (axis==polar_axis ? imprint:TCAD_CONST(0.0)));
                slope=TCAD_CONST(1.0)/(eps[i]*(a+TCAD_CONST(3.0)*beta*p*p));
            }
            candidate[3*i+axis]=p;
            const real_t drop=widths[i]*(local_d-p)/eps[i];
            voltage+=drop; scale+=widths[i]*(abs_q(d)+abs_q(node_offset[i])+abs_q(p))/eps[i];
            derivative+=widths[i]*(TCAD_CONST(1.0)-slope)/eps[i];
        }
        if (!isfinite_q(voltage) || !isfinite_q(derivative) || derivative<=0)
            throw std::invalid_argument("material-field LK voltage equation range");
        return std::vector<real_t>{voltage-drive,derivative,scale};
    };
    real_t radius=std::max(abs_q(guess),std::max(pscale,sqrt_q(abs_q(alpha)/beta)));
    if(radius==0) radius=TCAD_CONST(1.0);
    real_t lo=guess-radius,hi=guess+radius;
    for(size_t k=0;evaluate(lo)[0]>0 || evaluate(hi)[0]<0;++k) {
        if(k==200) throw std::runtime_error("material-field LK voltage bracket");
        radius*=TCAD_CONST(2.0);lo=guess-radius;hi=guess+radius;
    }
    for(size_t iteration=0;iteration<max_iter;++iteration) {
        auto f=evaluate(guess);samples.push_back({f[0],f[1]});
        if(abs_q(f[0])<=TCAD_CONST(128.0)*epsilon_q()*f[2]) {
            std::vector<real_t> next_phi(n);next_phi[0]=bottom;
            for(size_t i=0;i+1<n;++i) {
                const real_t h=edge(i), local_d=guess+edge_offset[i];
                next_phi[i+1]=next_phi[i]-h/TCAD_CONST(2.0)*
                    ((local_d-candidate[3*i+axis])/eps[i]+(local_d-candidate[3*(i+1)+axis])/eps[i+1]);
            }
            next_phi.back()=top;
            phi=std::move(next_phi);polarization=std::move(candidate);return true;
        }
        if(f[0]>0) hi=guess;else lo=guess;
        real_t next=guess-f[0]/f[1];
        if(!isfinite_q(next) || next<=lo || next>=hi) next=lo+(hi-lo)/TCAD_CONST(2.0);
        if(next==guess) break;
        guess=next;
    }
    return false;
}
} // namespace tcad
