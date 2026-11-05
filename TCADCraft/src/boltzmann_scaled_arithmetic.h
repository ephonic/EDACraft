#pragma once
#include "boltzmann_scaled_product.h"

namespace tcad { namespace mb_scaled_arithmetic_detail {
using namespace mb_scaled_detail;

inline size_t bits(const Words& a) {
    if(a.empty())return 0;
    size_t n=16*(a.size()-1);
    for(uint32_t w=a.back();w;w>>=1)++n;
    return n;
}
inline Integer normalized(Integer a) {
    trim(a.words);
    if(a.words.empty())return {};
    size_t whole=0;
    while(!a.words[whole])++whole;
    a.words.erase(a.words.begin(),a.words.begin()+whole);
    unsigned low=0;
    for(uint32_t v=a.words[0];!(v&1);v>>=1)++low;
    if(low) {
        for(size_t i=0;i<a.words.size();++i) {
            const uint32_t next=i+1<a.words.size()?a.words[i+1]:0;
            a.words[i]=(a.words[i]>>low)|((next<<(16-low))&65535);
        }
    }
    trim(a.words);
    a.exponent+=int(16*whole+low);
    if(a.sign!=1 && a.sign!=-1)throw std::invalid_argument("scaled integer sign invalid");
    if(a.exponent < -65536 || a.exponent > 65536)
        throw std::invalid_argument("scaled explicit exponent budget exceeded");
    check(a.words);
    return a;
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
inline int bounded_decimal_integer(const std::string& s) {
    if(s.empty() || s.size()>6)throw std::invalid_argument("short canonical exponent required");
    size_t i=s[0]=='-'?1:0;
    if(i==s.size() || (s[i]=='0' && (i!=0 || s.size()!=1)))
        throw std::invalid_argument("canonical exponent required");
    int n=0;
    for(;i<s.size();++i) {
        if(s[i]<'0' || s[i]>'9')throw std::invalid_argument("decimal exponent digits required");
        n=10*n+s[i]-'0';
    }
    if(n>65536)throw std::invalid_argument("scaled explicit exponent budget exceeded");
    return s[0]=='-'?-n:n;
}
inline size_t count(const std::string& s,size_t maximum) {
    if(s.empty() || s.size()>5 || (s.size()>1 && s[0]=='0'))
        throw std::invalid_argument("canonical bounded count required");
    size_t n=0;
    for(char c:s) {
        if(c<'0' || c>'9')throw std::invalid_argument("count digits required");
        n=10*n+size_t(c-'0');
    }
    if(n>maximum)throw std::invalid_argument("scaled count budget exceeded");
    return n;
}
inline Integer coefficient(const std::string& s,int exponent) {
    Integer r;r.sign=1;r.exponent=exponent;size_t i=0;
    if(!s.empty() && s[0]=='-'){r.sign=-1;++i;}
    if(s.size()<i+3 || s.size()>i+31 || s.substr(i,2)!="0x" || s[i+2]=='0')
        throw std::invalid_argument("short canonical hex coefficient required");
    i+=2;
    for(;i<s.size();++i) {
        unsigned digit=0;
        if(s[i]>='0' && s[i]<='9')digit=unsigned(s[i]-'0');
        else if(s[i]>='a' && s[i]<='f')digit=unsigned(s[i]-'a'+10);
        else throw std::invalid_argument("lowercase hex digits required");
        r.words=shift(r.words,4);
        r.words=add(r.words,Words{digit});
        trim(r.words);
    }
    if(r.words.empty() || !(r.words[0]&1) || bits(r.words)>113)
        throw std::invalid_argument("odd binary113 coefficient required");
    return r;
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
inline std::vector<std::string> write(Integer a) {
    a=normalized(a);
    std::vector<std::string> r={"mb_scaled_value_v1","113","0"};
    size_t n=0;
    for(size_t start=0;start<bits(a.words);start+=113) {
        Words w(8,0);
        for(size_t j=0;j<113;++j)w[j/16]|=bit(a.words,start+j)<<(j%16);
        trim(w);
        if(w.empty())continue;
        Integer part;part.words=w;part.sign=a.sign;part.exponent=a.exponent+int(start);
        part=normalized(part);
        r.push_back(hex(part.words,part.sign));r.push_back(std::to_string(part.exponent));
        if(++n>4096)throw std::invalid_argument("original component budget exceeded");
    }
    r[2]=std::to_string(n);return r;
}

// Round the arbitrary dyadic ratio to nearest-even binary113 using only
// integer shifts, subtraction and an exact half-way comparison.
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
} // namespace mb_scaled_arithmetic_detail

// Result: version, precision, operation, result-wire token count, result wire,
// remainder-wire token count, remainder wire. Division uses two rounded
// binary113 quotient terms and saves the exact a-b*q remainder. Other
// operations are exact and have a zero remainder. No state is submitted.
inline std::vector<std::string> native_mb_scaled_arithmetic_raw(
    const std::string& operation,const std::vector<std::string>& left,
    const std::vector<std::string>& right) {
    using namespace mb_scaled_arithmetic_detail;
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
    std::vector<std::string> out={"mb_scaled_arithmetic_v1","113",operation,std::to_string(value.size())};
    out.insert(out.end(),value.begin(),value.end());out.push_back(std::to_string(rest.size()));
    out.insert(out.end(),rest.begin(),rest.end());return out;
}
} // namespace tcad
