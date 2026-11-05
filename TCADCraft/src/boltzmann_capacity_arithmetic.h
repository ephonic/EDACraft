#pragma once
#include "boltzmann_scaled_arithmetic.h"
namespace tcad { namespace mb_capacity_arithmetic_detail {
namespace old=mb_scaled_arithmetic_detail;
using old::Integer;using old::Words;using old::normalized;using old::bits;
using old::count;using old::bounded_decimal_integer;using old::coefficient;
using old::write;using old::sum;
using mb_scaled_detail::trim;using mb_scaled_detail::compare;using mb_scaled_detail::subtract;
constexpr size_t capacity=mb_scaled_detail::max_words;
inline Words shift(const Words& a,unsigned n) {
    if(a.empty())return {};
    if(size_t(n)+bits(a)>16*capacity)throw std::invalid_argument("scaled shift budget exceeded");
    Words r((bits(a)+n+15)/16,0);const size_t whole=n/16;const unsigned low=n%16;
    for(size_t i=0;i<a.size();++i) {
        const uint32_t v=a[i]<<low;r[i+whole]|=v&65535;
        if(v>>16)r[i+whole+1]|=v>>16;
    }
    trim(r);return r;
}
inline Words add(const Words& a,const Words& b) {
    Words r(std::max(a.size(),b.size()));uint32_t carry=0;
    for(size_t i=0;i<r.size();++i){const uint32_t v=(i<a.size()?a[i]:0)+(i<b.size()?b[i]:0)+carry;r[i]=v&65535;carry=v>>16;}
    if(carry){if(r.size()==capacity)throw std::invalid_argument("scaled integer span budget exceeded");r.push_back(carry);}
    return r;
}
inline Words multiply(const Words& a,const Words& b) {
    if(a.empty() || b.empty())return {};
    if(bits(a)+bits(b)-1>16*capacity)throw std::invalid_argument("scaled product span budget exceeded");
    Words r(std::min(capacity,a.size()+b.size()),0);
    for(size_t i=0;i<a.size();++i) {
        uint64_t carry=0;
        for(size_t j=0;j<b.size();++j) {
            const uint64_t term=uint64_t(a[i])*b[j];const size_t k=i+j;
            if(k>=r.size()){if(term || carry)throw std::invalid_argument("scaled product span budget exceeded");continue;}
            const uint64_t v=term+r[k]+carry;r[k]=uint32_t(v&65535);carry=v>>16;
        }
        if(i+b.size()<r.size())r[i+b.size()]=uint32_t(carry);
        else if(carry)throw std::invalid_argument("scaled product span budget exceeded");
    }
    trim(r);return r;
}
inline Integer plus(Integer a,Integer b,int direction=1) {
    a=normalized(a);b=normalized(b);b.sign*=direction;
    if(!a.sign)return b;
    if(!b.sign)return a;
    const int exponent=std::min(a.exponent,b.exponent);
    const Words x=shift(a.words,unsigned(a.exponent-exponent));
    const Words y=shift(b.words,unsigned(b.exponent-exponent));
    Integer r;r.exponent=exponent;r.sign=a.sign;
    if(a.sign==b.sign)r.words=add(x,y);
    else if(compare(x,y)>=0)r.words=subtract(x,y);
    else {r.words=subtract(y,x);r.sign=b.sign;}
    return normalized(r);
}
inline Integer times(Integer a,Integer b) {
    a=normalized(a);b=normalized(b);
    Integer r;r.words=multiply(a.words,b.words);
    r.sign=a.sign*b.sign;r.exponent=a.exponent+b.exponent;
    return normalized(r);
}
inline Integer read(const std::vector<std::string>& wire) {
    if(wire.size()<3 || wire.size()>8195 || wire[0]!="mb_scaled_value_v1" || wire[1]!="113")
        throw std::invalid_argument("bounded scaled value wire required");
    const size_t n=count(wire[2],4096);
    if(wire.size()!=3+2*n)throw std::invalid_argument("scaled value coverage mismatch");
    Integer r;int first=0,end=0,sign=0;
    for(size_t i=0;i<n;++i) {
        const int exponent=bounded_decimal_integer(wire[4+2*i]);
        const auto c=coefficient(wire[3+2*i],exponent);
        if(i && (exponent<end || c.sign!=sign))
            throw std::invalid_argument("scaled components overlap, unordered or inconsistent sign");
        if(!i){first=exponent;sign=c.sign;}
        end=exponent+int(bits(c.words));
        if(end-first>65536)throw std::invalid_argument("scaled integer span budget exceeded");
        r=plus(r,c);
    }
    return r;
}
inline Integer rounded_ratio(Integer a,Integer b) {
    a=normalized(a);b=normalized(b);
    if(!b.sign)throw std::invalid_argument("scaled division by zero");
    if(!a.sign)return {};
    int k=int(bits(a.words))-int(bits(b.words));
    const int comparison=k>=0?compare(a.words,shift(b.words,unsigned(k))):
        compare(shift(a.words,unsigned(-k)),b.words);
    if(comparison<0)--k;
    const int scale=112-k;
    Words numerator=a.words,denominator=b.words;
    if(scale>=0)numerator=shift(numerator,unsigned(scale));
    else denominator=shift(denominator,unsigned(-scale));
    Words q(8,0),remainder=numerator;
    const int top=int(bits(numerator))-int(bits(denominator));
    if(top>113)throw std::logic_error("scaled quotient normalization failed");
    for(int i=top;i>=0;--i) {
        const Words trial=shift(denominator,unsigned(i));
        if(compare(remainder,trial)>=0) {
            remainder=subtract(remainder,trial);q[size_t(i)/16]|=uint32_t(1)<<(i%16);
        }
    }
    const int halfway=compare(shift(remainder,1),denominator);
    if(halfway>0 || (halfway==0 && (q[0]&1)))q=add(q,Words{1});
    trim(q);
    Integer r;r.words=q;r.sign=a.sign*b.sign;
    r.exponent=a.exponent-b.exponent+k-112;
    return normalized(r);
}
} }
namespace tcad {
inline std::vector<std::string> native_mb_capacity_arithmetic_raw(
    const std::string& operation,const std::vector<std::string>& left,
    const std::vector<std::string>& right) {
    using namespace mb_capacity_arithmetic_detail;
    if(real_mantissa_bits()!=113)throw std::invalid_argument("scaled arithmetic requires binary113");
    Integer a,b,q,remainder;
    if(operation=="import") {
        if(left.size()>4096 || !right.empty())throw std::invalid_argument("original import vector budget exceeded");
        a=normalized(sum(left));q=a;
    } else {
        a=read(left);b=read(right);
        if(operation=="add")q=plus(a,b);
        else if(operation=="subtract")q=plus(a,b,-1);
        else if(operation=="multiply") {
            if(count(left[2],4096)*count(right[2],4096)>65536)
                throw std::invalid_argument("original product pair budget exceeded");
            q=times(a,b);
        } else if(operation=="divide") {
            const auto first=rounded_ratio(a,b);
            const auto residual=plus(a,times(b,first),-1);
            q=plus(first,rounded_ratio(residual,b));
            remainder=plus(a,times(b,q),-1);
        } else throw std::invalid_argument("unknown scaled arithmetic operation");
    }
    const auto value=write(q),rest=write(remainder);
    if(count(value[2],4096)+count(rest[2],4096)>4096)
        throw std::invalid_argument("original combined evidence component budget exceeded");
    std::vector<std::string> out={"mb_capacity_arithmetic_v1","113",operation,std::to_string(value.size())};
    out.insert(out.end(),value.begin(),value.end());out.push_back(std::to_string(rest.size()));
    out.insert(out.end(),rest.begin(),rest.end());return out;
}
} // namespace tcad
