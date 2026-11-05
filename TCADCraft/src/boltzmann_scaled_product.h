#pragma once

// Exact intermediate product of two existing binary113 expansion vectors.
// Only input parsing uses real_t. Limbs and explicit binary exponents retain
// every output bit, including bits outside the old scalar storage range.
// This does not change the existing state representation or commit a step.
#include "math_types.h"
#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace tcad { namespace mb_scaled_detail {
using Words = std::vector<uint32_t>; // base 2^16, low word first
constexpr size_t max_words = 4096; // 65536 bits; original input span < 27000
inline void trim(Words& a) { while(!a.empty() && !a.back())a.pop_back(); }
inline void check(const Words& a) {
    if(a.size()>max_words)throw std::invalid_argument("scaled integer span budget exceeded");
}
inline int compare(const Words& a,const Words& b) {
    if(a.size()!=b.size())return a.size()<b.size()?-1:1;
    for(size_t i=a.size();i--;)if(a[i]!=b[i])return a[i]<b[i]?-1:1;
    return 0;
}
inline Words add(const Words& a,const Words& b) {
    Words r(std::max(a.size(),b.size()));uint32_t carry=0;
    for(size_t i=0;i<r.size();++i) {
        const uint32_t v=(i<a.size()?a[i]:0)+(i<b.size()?b[i]:0)+carry;
        r[i]=v&65535;carry=v>>16;
    }
    if(carry)r.push_back(carry);check(r);return r;
}
inline Words subtract(const Words& a,const Words& b) { // a >= b
    Words r(a.size());int32_t borrow=0;
    for(size_t i=0;i<a.size();++i) {
        int32_t v=int32_t(a[i])-int32_t(i<b.size()?b[i]:0)-borrow;
        borrow=v<0;r[i]=uint32_t(v+borrow*65536);
    }
    if(borrow)throw std::logic_error("scaled magnitude subtraction failed");
    trim(r);return r;
}
inline Words shift(const Words& a,unsigned bits) {
    if(a.empty())return {};
    if(bits/16+a.size()+1>max_words)throw std::invalid_argument("scaled shift budget exceeded");
    Words r(bits/16,0);uint32_t carry=0;
    for(uint32_t w:a) {
        const uint32_t v=(w<<(bits%16))|carry;
        r.push_back(v&65535);carry=v>>16;
    }
    if(carry)r.push_back(carry);return r;
}
inline Words multiply(const Words& a,const Words& b) {
    if(a.empty() || b.empty())return {};
    if(a.size()+b.size()>max_words)throw std::invalid_argument("scaled product span budget exceeded");
    Words r(a.size()+b.size());
    for(size_t i=0;i<a.size();++i) {
        uint64_t carry=0;
        for(size_t j=0;j<b.size();++j) {
            const uint64_t v=uint64_t(a[i])*b[j]+r[i+j]+carry;
            r[i+j]=uint32_t(v&65535);carry=v>>16;
        }
        r[i+b.size()]=uint32_t(carry);
    }
    trim(r);return r;
}
struct Integer { Words words;int sign=0,exponent=0; };

// Reject non-decimal spellings and enforce the ORIGINAL exact decimal input
// range before rounding. In particular a just-outside value cannot round in.
inline void decimal_syntax(const std::string& s) {
    if(s.empty() || s.size()>256)throw std::invalid_argument("short decimal required");
    size_t i=(s[0]=='+' || s[0]=='-')?1:0;bool point=false,any=false;
    int before=0,first=-1,count=0;std::string digits;
    for(;i<s.size() && s[i]!='e' && s[i]!='E';++i) {
        if(s[i]=='.' && !point){point=true;continue;}
        if(s[i]<'0' || s[i]>'9')throw std::invalid_argument("decimal syntax required");
        if(!point)++before;
        if(s[i]!='0' && first<0)first=count;
        ++count;digits+=s[i];any=true;
    }
    if(!any)throw std::invalid_argument("decimal digits required");
    int exponent=0;
    if(i<s.size()) {
        ++i;int sign=1;if(i<s.size() && (s[i]=='+' || s[i]=='-')){if(s[i]=='-')sign=-1;++i;}
        if(i==s.size())throw std::invalid_argument("decimal exponent required");
        for(;i<s.size();++i) {
            if(s[i]<'0' || s[i]>'9' || exponent>100000)
                throw std::invalid_argument("bounded decimal exponent required");
            exponent=exponent*10+s[i]-'0';
        }
        exponent*=sign;
    }
    if(first<0)return;
    const int order=before-first-1+exponent;
    bool unit=digits[size_t(first)]=='1';
    for(size_t j=size_t(first)+1;j<digits.size();++j)unit=unit && digits[j]=='0';
    if(order < -4000 || order>4000 || (order==4000 && !unit))
        throw std::invalid_argument("original decimal input range exceeded");
}
inline Integer decode(const std::string& s) {
    decimal_syntax(s);char* end=nullptr;
#ifdef TCAD_USE_FLOAT128
    real_t x=strtoflt128(s.c_str(),&end);
#else
    real_t x=strtold(s.c_str(),&end);
#endif
    if(end!=s.c_str()+s.size() || !isfinite_q(x) ||
       (x!=0 && (abs_q(x)<TCAD_CONST(1e-4000) || abs_q(x)>TCAD_CONST(1e4000))))
        throw std::invalid_argument("original binary113 input range exceeded");
    if(x==0)return {};
    Integer r;r.sign=x<0?-1:1;int e=0;real_t m=0;
#ifdef TCAD_USE_FLOAT128
    m=ldexpq(frexpq(abs_q(x),&e),113);
    for(int i=0;i<8;++i) {
        const real_t q=floorq(m/65536);r.words.push_back(uint32_t(m-q*65536));m=q;
    }
#else
    throw std::invalid_argument("scaled product requires binary113");
#endif
    trim(r.words);r.exponent=e-113;return r;
}
inline Integer sum(const std::vector<std::string>& raw) {
    std::vector<Integer> values;Integer r;bool found=false;
    for(const auto& s:raw) {
        values.push_back(decode(s));const auto& v=values.back();
        if(v.sign && (!found || v.exponent<r.exponent)){r.exponent=v.exponent;found=true;}
    }
    for(const auto& v:values)if(v.sign) {
        const Words w=shift(v.words,unsigned(v.exponent-r.exponent));
        if(!r.sign){r.words=w;r.sign=v.sign;}
        else if(r.sign==v.sign)r.words=add(r.words,w);
        else {
            const int c=compare(r.words,w);
            if(c>=0)r.words=subtract(r.words,w);
            else {r.words=subtract(w,r.words);r.sign=v.sign;}
            if(r.words.empty())r.sign=0;
        }
    }
    return r;
}
inline unsigned bit(const Words& w,size_t k) {return k/16<w.size()?((w[k/16]>>(k%16))&1):0;}
inline std::string hex(const Words& a,int sign) {
    std::ostringstream s;if(sign<0)s<<'-';s<<"0x"<<std::hex<<a.back();
    for(size_t i=a.size()-1;i--;)s<<std::setw(4)<<std::setfill('0')<<a[i];
    return s.str();
}
} // namespace mb_scaled_detail

// Wire: version, precision, left count, right count, nonzero pair count,
// component count, then (signed odd coefficient_hex, exponent2) pairs.
// Components are increasing, disjoint bit intervals, at most 113 bits each.
inline std::vector<std::string> native_mb_scaled_product_raw(
    const std::vector<std::string>& left,const std::vector<std::string>& right) {
    using namespace mb_scaled_detail;
    if(real_mantissa_bits()!=113 || left.size()>4096 || right.size()>4096)
        throw std::invalid_argument("scaled product requires binary113 and original vector budgets");
    if(left.size()*right.size()>65536)throw std::invalid_argument("original product pair budget exceeded");
    const auto a=sum(left),b=sum(right);
    const auto w=multiply(a.words,b.words);const int sign=a.sign*b.sign;
    size_t na=0,nb=0;for(const auto& s:left)na+=decode(s).sign!=0;for(const auto& s:right)nb+=decode(s).sign!=0;
    std::vector<std::string> r={"mb_scaled_product_v1","113",std::to_string(left.size()),
        std::to_string(right.size()),std::to_string(na*nb),"0"};
    size_t count=0;
    // Unsigned radix chunks have no overlap or cancellation; no rounding.
    for(size_t start=0;start<w.size()*16;start+=113) {
        Words chunk(8,0);
        for(size_t j=0;j<113;++j)chunk[j/16]|=bit(w,start+j)<<(j%16);
        trim(chunk);if(chunk.empty())continue;
        size_t zeros=0;while(!bit(chunk,zeros))++zeros;
        Words odd(8,0);
        for(size_t j=zeros;j<113;++j)odd[(j-zeros)/16]|=bit(chunk,j)<<((j-zeros)%16);
        trim(odd);r.push_back(hex(odd,sign));
        r.push_back(std::to_string(a.exponent+b.exponent+int(start+zeros)));
        if(++count>4096)throw std::invalid_argument("original component evidence budget exceeded");
    }
    r[5]=std::to_string(count);return r;
}
} // namespace tcad
