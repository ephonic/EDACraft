#pragma once

// Positive spectral RTA face laws. FD reservoirs and the nonlinear driver
// remain outside this kernel. All quadrature and moments use real_t.
#include "math_types.h"
#include "si_transport_constants.h"
#include <algorithm>
#include <stdexcept>
#include <utility>
#include <vector>

namespace tcad {
namespace spectral_detail {
inline const std::vector<std::pair<real_t,real_t>>& quadrature() {
    static const auto rule=[] {
        constexpr int N=96;
        std::vector<std::pair<real_t,real_t>> result(N);
        for (int i=0;i<N/2;++i) {
            real_t z=cosl((long double)PI*(i+.75L)/(N+.5L));
            real_t derivative=0;
            for (int iteration=0;iteration<64;++iteration) {
                real_t p=1,previous=0;
                for (int j=1;j<=N;++j) {
                    real_t next=((2*j-1)*z*p-(j-1)*previous)/j;
                    previous=p;p=next;
                }
                derivative=N*(z*p-previous)/(z*z-1);
                real_t change=p/derivative;z-=change;
                if (abs_q(change)<TCAD_CONST(16.0)*epsilon_q()) break;
                if (iteration==63) throw std::runtime_error("spectral quadrature root did not converge");
            }
            real_t p=1,previous=0;
            for (int j=1;j<=N;++j) {
                real_t next=((2*j-1)*z*p-(j-1)*previous)/j;
                previous=p;p=next;
            }
            derivative=N*(z*p-previous)/(z*z-1);
            real_t w=2/((1-z*z)*derivative*derivative);
            result[i]={-z,w};result[N-1-i]={z,w};
        }
        return result;
    }();
    return rule;
}
inline real_t occupation(real_t x) {
    if (x>=0) return 1/(1+exp_q(-x));
    real_t value=exp_q(x);return value/(1+value);
}
inline real_t three_halves(real_t x) { return x*sqrt_q(x); }
} // namespace spectral_detail

// inputs: To,Tn,mu_o,mu_n,band_o,band_n,phi_o,phi_n,phi_f,z,
//         mobility_o,mobility_n,area,d_o,d_n,path_mode,emission.
// path_mode: 0 legacy endpoint barrier, 1 thermionic, 2 linear bulk potential.
// valleys: repeated [normal_mass/m0,DOS_mass/m0,degeneracy,offset_J].
// output: particle,total_energy,material_energy,entropy,min_f,max_f,
//         followed by particle,total_energy for each valley.
inline std::vector<double> native_spectral_face_raw(const std::vector<double>& input,
                                                   const std::vector<double>& valleys) {
    if (input.size()!=17 || valleys.empty() || valleys.size()%4)
        throw std::invalid_argument("spectral input or valley dimensions invalid");
    for (double x:input) if (!std::isfinite(x)) throw std::invalid_argument("nonfinite spectral input");
    for (double x:valleys) if (!std::isfinite(x)) throw std::invalid_argument("nonfinite valley input");
    if (input[0]<=0 || input[1]<=0 || (input[9]!=-1 && input[9]!=1) ||
        input[10]<=0 || input[11]<=0 || input[12]<=0 || input[13]<=0 || input[14]<0 ||
        (input[15]!=0 && input[15]!=1 && input[15]!=2) || input[16]<0 || (input[15]==1 && input[14]<=0))
        throw std::invalid_argument("invalid spectral temperature, geometry, mobility or interface mode");
    for (size_t v=0;v<valleys.size();v+=4)
        if (valleys[v]<=0 || valleys[v+1]<=0 || valleys[v+2]<=0)
            throw std::invalid_argument("positive valley masses and degeneracy required");
    const real_t To=input[0],Tn=input[1],z=input[9],mo=input[10],mn=input[11];
    const real_t area=input[12],do_=input[13],dn=input[14],A=input[16];
    const bool interface=input[15]==1;
    const bool linear=input[15]==2;
    const real_t muo=(real_t)input[2]+z*si_transport::elementary_charge*input[6],mun=(real_t)input[3]+z*si_transport::elementary_charge*input[7];
    const real_t bo=(real_t)input[4]+z*si_transport::elementary_charge*input[6],bn=(real_t)input[5]+z*si_transport::elementary_charge*input[7];
    const real_t bfo=(real_t)input[4]+z*si_transport::elementary_charge*input[8],bfn=(real_t)input[5]+z*si_transport::elementary_charge*input[8];
    const real_t scale=KB*std::max(To,Tn),m0=TCAD_CONST(9.1093837015e-31),h=TCAD_CONST(6.62607015e-34);
    real_t number=0,total=0,entropy=0,minimum=1,maximum=0;
    std::vector<real_t> result(6+valleys.size()/2,0);
    for (size_t index=0;index<valleys.size();index+=4) {
        const real_t offset=valleys[index+3],uo=bo+offset,un=bn+offset,fo=bfo+offset,fn=bfn+offset;
        const real_t high=interface?std::max({uo,un,fo,fn}):std::max(uo,un);
        const real_t eo=(muo-high)/scale,en=(mun-high)/scale;
        const real_t upper=std::max({TCAD_CONST(60.0),eo+60,en+60});
        std::vector<real_t> breaks={0,upper};
        if(linear) breaks.push_back(std::min(upper,abs_q(un-uo)/scale));
        for (real_t eta:{eo,en}) for (real_t shift:{TCAD_CONST(-16.0),TCAD_CONST(16.0)})
            breaks.push_back(std::min(upper,std::max(TCAD_CONST(0.0),eta+shift)));
        std::sort(breaks.begin(),breaks.end());breaks.erase(std::unique(breaks.begin(),breaks.end()),breaks.end());
        const real_t reference=KB*300,base=2*PI*valleys[index+1]*m0*reference/(h*h);
        const real_t dos=2*valleys[index+2]*spectral_detail::three_halves(base);
        const real_t D0=dos/(spectral_detail::three_halves(reference)*sqrt_q(PI)/2);
        real_t rate=0,energy=0,loss=0;
        for (size_t segment=1;segment<breaks.size();++segment) {
            real_t a=sqrt_q(breaks[segment-1]),b=sqrt_q(breaks[segment]);
            for (const auto& node:spectral_detail::quadrature()) {
                const real_t t=a+(b-a)*(node.first+1)/2,E=high+scale*t*t;
                const real_t measure=scale*(b-a)*t*node.second;
                const real_t left=spectral_detail::occupation((muo-E)/(KB*To));
                const real_t right=spectral_detail::occupation((mun-E)/(KB*Tn));
                minimum=std::min({minimum,left,right});maximum=std::max({maximum,left,right});
                real_t g=0;
                if (!interface) {
                    if(!linear) {
                        g=area/(do_/mo+dn/mn)*2/(3*si_transport::elementary_charge)*D0*spectral_detail::three_halves(E-high);
                    } else {
                        // Integral of 1/[mu(x)*(E-U(x))^(3/2)] along a
                        // linear potential, with piecewise half-cell mobility.
                        // The rationalized mean is finite in the flat limit.
                        const real_t middle=uo+(un-uo)*do_/(do_+dn);
                        auto mean=[](real_t a,real_t b) {
                            const real_t x=sqrt_q(a),y=sqrt_q(b);
                            return x*y*(x+y)/2;
                        };
                        const real_t resistance=do_/mo/mean(E-uo,E-middle)+
                            (dn>0 ? dn/mn/mean(E-middle,E-un) : real_t(0));
                        g=area*2/(3*si_transport::elementary_charge)*D0/resistance;
                    }
                } else if (A>0) {
                    real_t go=area/do_*2*mo/(3*si_transport::elementary_charge)*D0*spectral_detail::three_halves(E-std::max(uo,fo));
                    real_t gn=area/dn*2*mn/(3*si_transport::elementary_charge)*D0*spectral_detail::three_halves(E-std::max(un,fn));
                    real_t gt=A*area*dos*sqrt_q(reference/(2*PI*valleys[index]*m0))/(reference*reference)*(E-std::max(fo,fn));
                    g=1/(1/go+1/gn+1/gt);
                    real_t trace_o=left-g*(left-right)/go,trace_n=right+g*(left-right)/gn;
                    minimum=std::min({minimum,trace_o,trace_n});maximum=std::max({maximum,trace_o,trace_n});
                }
                real_t flow=measure*g*(left-right);
                rate+=flow;energy+=flow*E;loss+=flow*((muo-E)/To-(mun-E)/Tn);
            }
        }
        result[6+index/2]=rate;result[7+index/2]=energy;
        number+=rate;total+=energy;entropy+=loss;
    }
    result[0]=number;result[1]=total;result[2]=total-z*si_transport::elementary_charge*input[8]*number;
    result[3]=entropy;result[4]=minimum;result[5]=maximum;
    std::vector<double> output;output.reserve(result.size());
    for (real_t value:result) {
        double converted=(double)value;
        if (!isfinite_q(value) || !std::isfinite(converted)) throw std::invalid_argument("spectral moment dynamic range exceeded");
        output.push_back(converted);
    }
    return output;
}
} // namespace tcad
