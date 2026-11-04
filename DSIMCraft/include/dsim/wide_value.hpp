#pragma once
// Included inside namespace dsim, after V. Also embedded in standalone models.
inline V V::from_words(std::vector<Word> words,int width) {
    if(width<1||width>1048576)throw std::runtime_error("packed value width must be 1..1048576");
    const size_t count=size_t((width+63)/64);words.resize(count);
    words.back().a&=mask((width-1)%64+1);words.back().b&=mask((width-1)%64+1);
    V out(words[0].a,words[0].b,width);
    if(count>1&&std::any_of(words.begin()+1,words.end(),[](Word v){return v.a||v.b;}))
        out.upper=std::make_shared<const std::vector<Word>>(words.begin()+1,words.end());
    return out;
}
inline V V::filled(int width,uint64_t av,uint64_t bv) {
    if(width<1||width>1048576)throw std::runtime_error("packed value width must be 1..1048576");
    return from_words(std::vector<Word>(size_t((width+63)/64),{av,bv}),width);
}
inline V V::resized(int width) const {
    if(width==w)return *this;
    if(width<=64)return V(a,b,width);
    if(width>1048576)throw std::runtime_error("packed value width exceeds 1048576");
    std::vector<Word> words(size_t((width+63)/64));
    for(size_t i=0;i<words.size();++i)words[i]={word_a(i),word_b(i)};
    return from_words(std::move(words),width);
}
inline bool V::unknown() const {
    if(b)return true;
    if(upper)for(const auto& v:*upper)if(v.b)return true;
    return false;
}
namespace wide_detail {
using Words=std::vector<V::Word>;
inline size_t count(int width){return size_t((width+63)/64);}
inline Words words(const V& v,int width) {
    Words out(count(width));for(size_t i=0;i<out.size();++i)out[i]={v.word_a(i),v.word_b(i)};
    out.back().a&=mask((width-1)%64+1);out.back().b&=mask((width-1)%64+1);return out;
}
inline bool all(const V& v,uint64_t a,uint64_t b) {
    for(size_t i=0;i<count(v.w);++i){auto m=i+1==count(v.w)?mask((v.w-1)%64+1):~uint64_t(0);if(v.word_a(i)!=(a&m)||v.word_b(i)!=(b&m))return false;}return true;
}
inline int compare(const Words& a,const Words& b) {
    for(size_t i=a.size();i-->0;)if(a[i].a!=b[i].a)return a[i].a<b[i].a?-1:1;
    return 0;
}
inline void subtract(Words& a,const Words& b) {
    uint64_t borrow=0;
    for(size_t i=0;i<a.size();++i){auto x=a[i].a,y=b[i].a;auto first=x-y;auto next=first-borrow;a[i].a=next;borrow=uint64_t(x<y||first<borrow);}
}
inline std::string decimal(const V& v) {
    std::vector<uint32_t> limbs(count(v.w)*2);
    for(size_t i=0;i<limbs.size();++i)limbs[i]=uint32_t(v.word_a(i/2)>>(32*(i%2)));
    std::string out;
    while(std::any_of(limbs.begin(),limbs.end(),[](uint32_t n){return n!=0;})){
        uint64_t remainder=0;
        for(size_t i=limbs.size();i-->0;){auto value=(remainder<<32)|limbs[i];limbs[i]=uint32_t(value/10);remainder=value%10;}
        out+=char('0'+remainder);
    }
    if(out.empty())return "0";
    std::reverse(out.begin(),out.end());return out;
}
}
inline V wide_inv(const V& v) {
    auto out=wide_detail::words(v,v.w);for(auto& word:out)word.a=~word.a|word.b;
    return V::from_words(std::move(out),v.w);
}
inline V wide_bitop(char op,const V& a,const V& b,int width) {
    auto out=wide_detail::words(a,width),right=wide_detail::words(b,width);
    for(size_t i=0;i<out.size();++i){auto x=out[i],y=right[i];
        if(op=='^'){auto unknown=x.b|y.b;out[i]={(x.a^y.a)|unknown,unknown};continue;}
        auto x0=~(x.a|x.b),y0=~(y.a|y.b),x1=x.a&~x.b,y1=y.a&~y.b;
        auto ones=op=='&'?x1&y1:x1|y1,zeros=op=='&'?x0|y0:x0&y0;
        auto unknown=~(ones|zeros);out[i]={ones|unknown,unknown};
    }
    return V::from_words(std::move(out),width);
}
inline V wide_unary(const std::string& op,const V& value,int width) {
    auto v=value.size(width);
    if(op=="~")return wide_inv(v);
    if(op=="+")return v;
    if(op=="!"){auto t=v.truth();return t<0?V::x(1):V(t==0);}
    if(op=="|"){auto t=v.truth();return t<0?V::x(1):V(t);}
    if(op=="&"){
        for(size_t i=0;i<wide_detail::count(width);++i){auto m=i+1==wide_detail::count(width)?mask((width-1)%64+1):~uint64_t(0);if(~(v.word_a(i)|v.word_b(i))&m)return V(0);}
        return v.unknown()?V::x(1):V(1);
    }
    if(op=="^"){
        if(v.unknown())return V::x(1);
        int parity=0;for(size_t i=0;i<wide_detail::count(width);++i)for(auto n=v.word_a(i);n;n&=n-1)parity^=1;
        return V(parity);
    }
    if(op=="-"){
        if(v.unknown())return V::x(width);
        auto out=wide_detail::words(v,width);uint64_t carry=1;
        for(auto& word:out){word.a=~word.a+carry;carry=carry&&word.a==0;}
        return V::from_words(std::move(out),width);
    }
    throw std::runtime_error("invalid wide unary operator");
}
inline V wide_binary(Binary op,const V& a,const V& b,int width) {
    if(op==Binary::BitAnd||op==Binary::BitOr||op==Binary::BitXor)return wide_bitop(op==Binary::BitAnd?'&':op==Binary::BitOr?'|':'^',a,b,width);
    if(op==Binary::LogicalAnd||op==Binary::LogicalOr){
        int x=a.truth(),y=b.truth();
        if(op==Binary::LogicalAnd)return x==0||y==0?V(0):x<0||y<0?V::x(1):V(1);
        return x==1||y==1?V(1):x<0||y<0?V::x(1):V(0);
    }
    const int compare_width=std::max(a.w,b.w);
    if(op==Binary::CaseEqual||op==Binary::CaseNotEqual){bool equal=a.size(compare_width).same(b.size(compare_width));return V(op==Binary::CaseEqual?equal:!equal);}
    if(op==Binary::Equal||op==Binary::NotEqual){
        for(size_t i=0;i<wide_detail::count(compare_width);++i)if((a.word_a(i)^b.word_a(i))&~(a.word_b(i)|b.word_b(i)))return V(op==Binary::NotEqual);
        if(a.unknown()||b.unknown())return V::x(1);
        return V(op==Binary::Equal);
    }
    if(op==Binary::Less||op==Binary::Greater||op==Binary::LessEqual||op==Binary::GreaterEqual){
        if(a.unknown()||b.unknown())return V::x(1);
        auto c=wide_detail::compare(wide_detail::words(a,compare_width),wide_detail::words(b,compare_width));
        return V(op==Binary::Less?c<0:op==Binary::Greater?c>0:op==Binary::LessEqual?c<=0:c>=0);
    }
    if(op==Binary::ShiftLeft||op==Binary::ShiftRight){
        if(b.unknown())return V::x(width);
        for(size_t i=1;i<wide_detail::count(b.w);++i)if(b.word_a(i))return V(0,0,width);
        if(b.a>=uint64_t(width))return V(0,0,width);
        auto v=a.size(width);wide_detail::Words out(wide_detail::count(width));
        size_t offset=size_t(b.a/64);unsigned shift=unsigned(b.a%64);
        for(size_t i=0;i<out.size();++i){
            if(op==Binary::ShiftLeft){
                if(i<offset)continue;auto j=i-offset;
                out[i]={v.word_a(j)<<shift,v.word_b(j)<<shift};
                if(shift&&j){out[i].a|=v.word_a(j-1)>>(64-shift);out[i].b|=v.word_b(j-1)>>(64-shift);}
            }else{
                auto j=i+offset;out[i]={v.word_a(j)>>shift,v.word_b(j)>>shift};
                if(shift){out[i].a|=v.word_a(j+1)<<(64-shift);out[i].b|=v.word_b(j+1)<<(64-shift);}
            }
        }
        return V::from_words(std::move(out),width);
    }
    if(a.unknown()||b.unknown())return V::x(width);
    auto left=wide_detail::words(a,width),right=wide_detail::words(b,width);
    if(op==Binary::Add){
        uint64_t carry=0;for(size_t i=0;i<left.size();++i){auto x=left[i].a,y=right[i].a;auto first=x+y;auto next=first+carry;left[i].a=next;carry=uint64_t(first<x||next<first);}
        return V::from_words(std::move(left),width);
    }
    if(op==Binary::Subtract){wide_detail::subtract(left,right);return V::from_words(std::move(left),width);}
    if(op==Binary::Multiply){
        const size_t n=left.size()*2;std::vector<uint32_t> product(n);
        for(size_t i=0;i<n;++i){uint64_t carry=0;auto x=uint32_t(a.word_a(i/2)>>(32*(i%2)));
            for(size_t j=0;i+j<n;++j){auto y=uint32_t(b.word_a(j/2)>>(32*(j%2)));uint64_t sum=uint64_t(x)*y+product[i+j]+carry;product[i+j]=uint32_t(sum);carry=sum>>32;}}
        for(size_t i=0;i<left.size();++i)left[i].a=uint64_t(product[2*i])|(uint64_t(product[2*i+1])<<32);
        return V::from_words(std::move(left),width);
    }
    if(op==Binary::Divide||op==Binary::Modulo){
        if(!std::any_of(right.begin(),right.end(),[](V::Word word){return word.a!=0;}))return V::x(width);
        // Unsigned restoring division. Arithmetic remains word based; no gate expansion.
        // The extra carry limb is essential when the divisor's top bit is set.
        auto numerator=left;left.assign(left.size()+1,{});right.push_back({});wide_detail::Words quotient(left.size());
        for(int bit=width;bit-->0;){uint64_t carry=(numerator[size_t(bit/64)].a>>(bit%64))&1;
            for(auto& word:left){auto next=word.a>>63;word.a=(word.a<<1)|carry;carry=next;}
            if(wide_detail::compare(left,right)>=0){wide_detail::subtract(left,right);quotient[size_t(bit/64)].a|=uint64_t(1)<<(bit%64);}}
        return V::from_words(op==Binary::Divide?std::move(quotient):std::move(left),width);
    }
    throw std::runtime_error("invalid wide binary operator");
}
inline V wide_mux(const V& c,const V& a,const V& b,int width) {
    int truth=c.truth();if(truth>=0)return (truth?a:b).size(width);
    auto out=wide_detail::words(a,width),right=wide_detail::words(b,width);
    for(size_t i=0;i<out.size();++i){auto x=out[i],y=right[i];auto equal=~((x.a^y.a)|x.b|y.b);out[i]={(x.a&equal)|~equal,(x.b&equal)|~equal};}
    return V::from_words(std::move(out),width);
}
inline bool wide_case_match(const V& a,const V& b,int mode) {
    for(size_t i=0;i<wide_detail::count(std::max(a.w,b.w));++i){auto av=a.word_a(i),ax=a.word_b(i),bv=b.word_a(i),bx=b.word_b(i);auto wild=mode==2?ax|bx:mode==1?(ax&~av)|(bx&~bv):0;if(((av^bv)|(ax^bx))&~wild)return false;}return true;
}
inline V wide_slice(const V& a,int lo,int width) {
    if(lo<0||width<1||lo>a.w-width)return V::x(width);
    wide_detail::Words out(wide_detail::count(width));auto offset=size_t(lo/64);auto shift=unsigned(lo%64);
    for(size_t i=0;i<out.size();++i){out[i]={a.word_a(i+offset)>>shift,a.word_b(i+offset)>>shift};if(shift){out[i].a|=a.word_a(i+offset+1)<<(64-shift);out[i].b|=a.word_b(i+offset+1)<<(64-shift);}}
    return V::from_words(std::move(out),width);
}
inline V wide_replace(const V& base,int lo,int width,const V& value) {
    if(width<1||lo<0||lo>base.w-width)throw std::runtime_error("invalid generated wide assignment slice");
    auto out=wide_detail::words(base,base.w);auto sized=value.size(width);
    for(int done=0;done<width;){int offset=(lo+done)%64,take=std::min(64-offset,width-done);auto part=wide_slice(sized,done,take);auto selected=mask(take)<<offset;auto& word=out[size_t((lo+done)/64)];word.a=(word.a&~selected)|(part.a<<offset);word.b=(word.b&~selected)|(part.b<<offset);done+=take;}
    return V::from_words(std::move(out),base.w);
}
inline V wide_concat(const V& a,const V& b) {
    if(a.w>1048576-b.w)throw std::runtime_error("concatenation exceeds 1048576 bits");
    int width=a.w+b.w;auto out=wide_detail::words(b,width);
    for(size_t i=0;i<wide_detail::count(a.w);++i){auto j=i+size_t(b.w/64);unsigned shift=unsigned(b.w%64);out[j].a|=a.word_a(i)<<shift;out[j].b|=a.word_b(i)<<shift;if(shift&&j+1<out.size()){out[j+1].a|=a.word_a(i)>>(64-shift);out[j+1].b|=a.word_b(i)>>(64-shift);}}
    return V::from_words(std::move(out),width);
}
inline V wide_resolve(const V& a,const V& b) {
    auto out=wide_detail::words(a,a.w),right=wide_detail::words(b,a.w);
    for(size_t i=0;i<out.size();++i){auto x=out[i],y=right[i];auto az=x.b&~x.a,bz=y.b&~y.a,equal=~((x.a^y.a)|(x.b^y.b));auto conflict=~(az|bz|equal);out[i]={(x.a&bz)|(y.a&az)|(x.a&equal)|conflict,(x.b&bz)|(y.b&az)|(x.b&equal)|conflict};}
    return V::from_words(std::move(out),a.w);
}
inline std::string wide_format(const V& v,char base) {
    if(base=='d'||base=='t'){
        if(!v.unknown())return wide_detail::decimal(v);
        if(wide_detail::all(v,~uint64_t(0),~uint64_t(0)))return "x";
        if(wide_detail::all(v,0,~uint64_t(0)))return "z";
        for(size_t i=0;i<wide_detail::count(v.w);++i)if(v.word_a(i)&v.word_b(i))return "X";
        return "Z";
    }
    int step=base=='h'||base=='x'?4:base=='o'?3:1;std::string out;
    for(int i=((v.w-1)/step)*step;i>=0;i-=step){auto part=wide_slice(v,i,std::min(step,v.w-i));auto m=mask(part.w);if(part.b)out+=part.b==m?(part.a==0?'z':part.a==m?'x':'X'):(part.a&part.b?'X':'Z');else out+="0123456789abcdef"[part.a];}
    return out;
}

inline uint64_t wide_repeat_count(const V& value) {
    if(value.unknown())return 0;
    for(size_t i=1;i<wide_detail::count(value.w);++i)if(value.word_a(i))throw std::runtime_error("repeat count exceeds 64-bit runtime counter");
    return value.a;
}
