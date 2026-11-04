#pragma once
// dsim portable generated-code runtime. No parser or AST dependency.
#include <algorithm>
#ifdef DSIM_TIME_WHEEL_ENABLED
#include <array>
#endif
#include <cstdint>
#ifdef DSIM_REAL_ENABLED
#include <cmath>
#include <cstring>
#include <iomanip>
#endif
#include <functional>
#if defined(DSIM_MEMORY_IO_ENABLED) || defined(DSIM_FILE_IO_ENABLED)
#include <fstream>
#ifdef DSIM_FILE_IO_ENABLED
#include <filesystem>
#endif
#include <iterator>
#include <cctype>
#endif
#include <iostream>
#include <initializer_list>
#include <limits>
#include <map>
#include <memory>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#if defined(DSIM_COMB_REGION_ENABLED) || defined(DSIM_IPC_ENABLED)
#include <deque>
#endif
#ifdef DSIM_COMB_REGION_ENABLED
#if defined(DSIM_TIMING_ENABLED) || defined(DSIM_COMPACT_GATES) || defined(DSIM_PROCESS_CONTROL_ENABLED) || defined(DSIM_DYNAMIC_FORK_ENABLED) || defined(DSIM_EXPRESSION_EVENTS_ENABLED) || defined(DSIM_NAMED_EVENTS_ENABLED) || defined(DSIM_PROPERTY_ENABLED)
#error compiled combinational regions require ordinary static RTL scheduling
#endif
#endif
#ifdef DSIM_DYNAMIC_FORK_ENABLED
#include <deque>
#if !defined(DSIM_PROCESS_CONTROL_ENABLED) || !defined(DSIM_FORK_JOIN_ENABLED)
#error DSIM_DYNAMIC_FORK_ENABLED requires fork join and process control
#endif
#endif
#if defined(DSIM_EVENT_NBA_ENABLED) && !defined(DSIM_EXPRESSION_EVENTS_ENABLED)
#error DSIM_EVENT_NBA_ENABLED requires DSIM_EXPRESSION_EVENTS_ENABLED
#endif
#if defined(DSIM_SCALAR_TIMING_ENABLED) && !defined(DSIM_TIMING_ENABLED)
#error DSIM_SCALAR_TIMING_ENABLED requires DSIM_TIMING_ENABLED
#endif
#if defined(DSIM_SDF_JOBS_ENABLED) && !defined(DSIM_SCALAR_TIMING_ENABLED)
#error DSIM_SDF_JOBS_ENABLED requires DSIM_SCALAR_TIMING_ENABLED
#endif
#if defined(DSIM_CONTINUOUS_DELAY_ENABLED) && !defined(DSIM_TIMING_ENABLED)
#error DSIM_CONTINUOUS_DELAY_ENABLED requires DSIM_TIMING_ENABLED
#endif
// Stable d-ary candidates retain time/order semantics. Binary remains the
// default until larger paired measurements establish a reproducible benefit.
#ifndef DSIM_TIMER_HEAP_ARITY
#define DSIM_TIMER_HEAP_ARITY 2
#endif
namespace dsim {
#ifdef DSIM_TIME_WHEEL_ENABLED
// Development candidate. Event has uint64_t time/order; callers assign increasing
// order and never insert before now. All state is owned and copyable for rollback.
template<class Event>
class NearTimerQueue {
    static constexpr uint32_t none=UINT32_MAX;
    static constexpr unsigned width=256;
    struct Later {
        bool operator()(const Event& a,const Event& b) const {
            return a.time!=b.time?a.time>b.time:a.order>b.order;
        }
    };
    struct Node {Event event;uint32_t next=none;};
    std::array<uint32_t,width> head{},tail{};
    std::array<uint64_t,width/64> occupied{};
    std::vector<Node> nodes;
    std::vector<Event> far;
    uint32_t free=none,first=none;
    uint64_t base=0;
    size_t count=0;

    static unsigned trailing(uint64_t value) {
        // The argument is nonzero. GCC and Clang implement this without a loop.
        return unsigned(__builtin_ctzll(value));
    }
    void find_first() {
        const unsigned start=unsigned(base%width),word=start/64,bit=start%64;
        uint64_t bits=occupied[word]&(~uint64_t(0)<<bit);
        if(bits){first=word*64+trailing(bits);return;}
        for(unsigned i=word+1;i<width/64;++i)
            if(occupied[i]){first=i*64+trailing(occupied[i]);return;}
        for(unsigned i=0;i<word;++i)
            if(occupied[i]){first=i*64+trailing(occupied[i]);return;}
        bits=occupied[word]&((uint64_t(1)<<bit)-1);
        first=bits?word*64+trailing(bits):none;
    }
    void push_near(Event event) {
        uint32_t slot;
        if(free!=none){slot=free;free=nodes[slot].next;nodes[slot]={event,none};}
        else {
            if(nodes.size()>=none)throw std::runtime_error("too many near timer slots");
            slot=uint32_t(nodes.size());nodes.push_back({event,none});
        }
        const unsigned bucket=unsigned(event.time%width);
        if(head[bucket]==none) {
            head[bucket]=slot;occupied[bucket/64]|=uint64_t(1)<<(bucket%64);
            if(first==none||event.time<nodes[head[first]].event.time)first=bucket;
        } else nodes[tail[bucket]].next=slot;
        tail[bucket]=slot;
    }
public:
    NearTimerQueue(){head.fill(none);tail.fill(none);}
    bool empty() const {return count==0;}
    size_t size() const {return count;}
    const Event& front() const {
        if(first!=none)return nodes[head[first]].event;
        if(far.empty())throw std::runtime_error("empty timer queue");
        return far.front();
    }
    // Advance only at actual simulator time, never when purging a future stale
    // event. Old near and promoted far timestamps are disjoint, so promotion
    // preserves insertion order within each timestamp before any new insertion.
    void advance(uint64_t now) {
        if(now<base)throw std::runtime_error("timer queue time reversal");
        if(!empty()&&front().time<now)throw std::runtime_error("timer queue skipped event");
        base=now;
        while(!far.empty()&&far.front().time-base<width) {
            std::pop_heap(far.begin(),far.end(),Later{});
            auto event=far.back();far.pop_back();push_near(event);
        }
    }
    void push(Event event,uint64_t now) {
        if(event.time<now)throw std::runtime_error("timer scheduled in the past");
        if(now!=base)advance(now);
        if(event.time-base<width)push_near(event);
        else {far.push_back(event);std::push_heap(far.begin(),far.end(),Later{});}
        ++count;
    }
    Event pop() {
        if(empty())throw std::runtime_error("empty timer queue");
        Event event;
        if(first!=none) {
            const unsigned bucket=first;const auto slot=head[bucket];
            event=nodes[slot].event;head[bucket]=nodes[slot].next;
            nodes[slot].next=free;free=slot;
            if(head[bucket]==none) {
                tail[bucket]=none;occupied[bucket/64]&=~(uint64_t(1)<<(bucket%64));
                find_first();
            }
        } else {
            std::pop_heap(far.begin(),far.end(),Later{});event=far.back();far.pop_back();
        }
        --count;return event;
    }
};

#endif
#ifdef DSIM_DPI_ENABLED
struct ForeignCallBarrier {}; // A prediction must retry external effects on the committed path.
#endif
inline uint64_t mask(int w) { return w >= 64 ? ~uint64_t(0) : (uint64_t(1) << w) - 1; }
enum class Binary { BitAnd, BitOr, BitXor, LogicalAnd, LogicalOr, CaseEqual, CaseNotEqual, Equal, NotEqual, Less, Greater, LessEqual, GreaterEqual, ShiftLeft, ShiftRight, Add, Subtract, Multiply, Divide, Modulo };
// b=0: a stores 0/1; b=1: a=1 means X, a=0 means Z.
struct V {
    uint64_t a=0, b=0; int w=1;
#ifdef DSIM_REAL_ENABLED
    int real_width=0;
    static V real(double value,int width=64) {
        V out(0,0,width);out.real_width=width;
        if(width==32){float rounded=float(value);uint32_t bits;std::memcpy(&bits,&rounded,4);out.a=bits;}
        else std::memcpy(&out.a,&value,8);
        return out;
    }
    double real_value() const {
        if(real_width==32){uint32_t bits=uint32_t(a);float value;std::memcpy(&value,&bits,4);return value;}
        if(real_width==64){double value;std::memcpy(&value,&a,8);return value;}
        throw std::runtime_error("expected real value");
    }
#endif
#ifdef DSIM_STRING_ENABLED
    // Immutable ownership keeps signal/event/activation/checkpoint copies independent.
    std::shared_ptr<const std::string> text_data;
    static V text(std::string value) {V result;result.text_data=std::make_shared<const std::string>(std::move(value));return result;}
    const std::string& text_value() const {if(!text_data)throw std::runtime_error("expected string value");return *text_data;}
    bool same_text(const V& other) const {return text_data==other.text_data||(text_data&&other.text_data&&*text_data==*other.text_data);}
#endif
#ifdef DSIM_WIDE_VALUES
    struct Word { uint64_t a=0,b=0; };
    // Immutable tail ownership makes copied values, events and checkpoints safe.
    std::shared_ptr<const std::vector<Word>> upper;
    uint64_t word_a(size_t i) const {return i==0?a:upper&&i<=upper->size()?(*upper)[i-1].a:0;}
    uint64_t word_b(size_t i) const {return i==0?b:upper&&i<=upper->size()?(*upper)[i-1].b:0;}
    static V from_words(std::vector<Word> words,int width);
    static V filled(int width,uint64_t av,uint64_t bv);
    static V ones(int width) {return filled(width,~uint64_t(0),0);}
    V resized(int width) const;
    bool unknown() const;
#endif
#ifdef DSIM_STRUCT_STRING_ENABLED
    // String fields occupy address slots, never numeric encodings. Immutable
    // ownership gives queued assignments and checkpoints ordinary value copies.
    using StructStrings=std::map<int,std::string>;
    std::shared_ptr<const StructStrings> struct_strings;
    static V string_field(const V& text) {
        V result;result.struct_strings=std::make_shared<const StructStrings>(StructStrings{{0,text.text_value()}});return result;
    }
    V read_string_field(int offset) const {
        if(!struct_strings||!struct_strings->count(offset))return V::text(""); // Invalid fixed-array reads have default string fields.
        return V::text(struct_strings->at(offset));
    }
    bool same_struct_strings(const V& other) const {
        return struct_strings==other.struct_strings||(struct_strings&&other.struct_strings&&*struct_strings==*other.struct_strings);
    }
#endif
    V(uint64_t av=0,uint64_t bv=0,int width=1):a(av&mask(width)),b(bv&mask(width)),w(width) {}
    static V x(int w) {
#ifdef DSIM_WIDE_VALUES
        if(w>64)return filled(w,~uint64_t(0),~uint64_t(0));
#endif
        return V(mask(w),mask(w),w);
    }
    static V z(int w) {
#ifdef DSIM_WIDE_VALUES
        if(w>64)return filled(w,0,~uint64_t(0));
#endif
        return V(0,mask(w),w);
    }
    V size(int width) const {
#ifdef DSIM_STRUCT_STRING_ENABLED
        if(struct_strings){if(width!=w)throw std::runtime_error("struct storage width mismatch");return *this;}
#endif
#ifdef DSIM_REAL_ENABLED
        if(real_width)return *this;
#endif
#ifdef DSIM_STRING_ENABLED
        if(text_data)return *this;
#endif
#ifdef DSIM_WIDE_VALUES
        if(width>64||w>64)return resized(width);
#endif
        return V(a,b,width);
    }
    int truth() const {
#ifdef DSIM_STRUCT_STRING_ENABLED
        if(struct_strings)throw std::runtime_error("unpacked struct is not a boolean expression");
#endif
#ifdef DSIM_REAL_ENABLED
        if(real_width)return real_value()!=0;
#endif
#ifdef DSIM_STRING_ENABLED
        if(text_data)throw std::runtime_error("string cannot be used as a boolean expression");
#endif
#ifdef DSIM_WIDE_VALUES
        if(w>64) {bool x=false;for(size_t i=0;i<size_t((w+63)/64);++i){if(word_a(i)&~word_b(i))return 1;x=x||word_b(i)!=0;}return x?-1:0;}
#endif
        return (a&~b) ? 1 : b ? -1 : 0;
    }
    int bit(int i) const {
#ifdef DSIM_WIDE_VALUES
        if(w>64){if(i<0||i>=w)return 2;auto av=word_a(size_t(i/64)),bv=word_b(size_t(i/64));i%=64;return (bv>>i&1)?(av>>i&1?2:3):int(av>>i&1);}
#endif
        return i<0 || i>=w ? 2 : (b>>i&1) ? (a>>i&1 ? 2:3) : int(a>>i&1);
    }
#ifdef DSIM_WIDE_VALUES
    bool same(const V& v) const {
#ifdef DSIM_REAL_ENABLED
        if(real_width!=v.real_width)return false;
#endif
#ifdef DSIM_STRING_ENABLED
        if(!same_text(v))return false;
#endif
#ifdef DSIM_STRUCT_STRING_ENABLED
        if(!same_struct_strings(v))return false;
#endif
        if(w!=v.w||a!=v.a||b!=v.b)return false;
        if(upper!=v.upper)for(size_t i=1;i<size_t((w+63)/64);++i)if(word_a(i)!=v.word_a(i)||word_b(i)!=v.word_b(i))return false;
        return true;
    }
#else
    bool same(const V& v) const {
#ifdef DSIM_REAL_ENABLED
        if(real_width!=v.real_width)return false;
#endif
#ifdef DSIM_STRING_ENABLED
        if(!same_text(v))return false;
#endif
#ifdef DSIM_STRUCT_STRING_ENABLED
        if(!same_struct_strings(v))return false;
#endif
        return w==v.w && a==v.a && b==v.b;
    }
#endif
};
#ifdef DSIM_WIDE_VALUES
#include "wide_value.hpp"
#endif
#ifdef DSIM_REAL_ENABLED
inline double real_numeric(const V& v,bool sign=false) {
    if(v.real_width)return v.real_value();
    const bool negative=sign&&v.bit(v.w-1)==1;double value=negative?-1:0;
    // Start a signed Horner expansion at -1 to avoid cancellation near -1.
    for(int i=v.w-int(negative);i-->0;)value=value*2+(v.bit(i)==1);
    return value;
}
inline V real_integral(double value,int width,bool truncate=false) {
    value=truncate?std::trunc(value):std::round(value);
    if(!std::isfinite(value))return V::x(width);
    double remaining=std::fabs(value);
#ifdef DSIM_WIDE_VALUES
    std::vector<V::Word> words(size_t((width+63)/64));
    for(int bit=0;bit<width&&remaining>=1;++bit){if(std::fmod(remaining,2)>=1)words[size_t(bit/64)].a|=uint64_t(1)<<(bit%64);remaining=std::floor(remaining/2);}
    if(value<0){uint64_t carry=1;for(auto& word:words){word.a=~word.a+carry;carry=carry&&word.a==0;}}
    return V::from_words(std::move(words),width);
#else
    uint64_t bits=0;for(int bit=0;bit<width&&remaining>=1;++bit){if(std::fmod(remaining,2)>=1)bits|=uint64_t(1)<<bit;remaining=std::floor(remaining/2);}
    return V(value<0?uint64_t(0)-bits:bits,0,width);
#endif
}
inline V real_convert(V value,int real_width,int width,bool sign=false) {
    if(real_width)return V::real(real_numeric(value,sign),real_width);
    return value.real_width?real_integral(value.real_value(),width):value.size(width);
}
inline V real_from_bits(V value,int width) {V out(value.a&~value.b,0,width);out.real_width=width;return out;}
inline V real_from_bits64(V value) {return real_from_bits(value,64);}
inline V real_from_bits32(V value) {return real_from_bits(value,32);}
inline V real_to_bits64(V value) {return V(V::real(real_numeric(value),64).a,0,64);}
inline V real_to_bits32(V value) {return V(V::real(real_numeric(value),32).a,0,32);}
inline V real_itor(V value) {return V::real(real_numeric(value.size(32),true));}
inline V real_rtoi(V value) {return real_integral(real_numeric(value),32,true);}
inline V real_operation(const std::string& op,V a,bool sign_a,V b,bool sign_b) {
    const int width=std::max(a.real_width,b.real_width);
    double x=real_numeric(a,sign_a),y=real_numeric(b,sign_b);
    if(width==32){x=static_cast<float>(x);y=static_cast<float>(y);}
    if(op=="+")return V::real(x+y,width);if(op=="-")return V::real(x-y,width);
    if(op=="*")return V::real(x*y,width);if(op=="/")return V::real(x/y,width);
    if(op=="**")return V::real(std::pow(x,y),width);
    if(op=="==")return V(x==y);if(op=="!=")return V(x!=y);
    if(op=="<")return V(x<y);if(op==">")return V(x>y);
    if(op=="<=")return V(x<=y);if(op==">=")return V(x>=y);
    if(op=="&&"||op=="||"){const int ax=a.truth(),by=b.truth();if(op=="&&")return ax==0||by==0?V(0):ax<0||by<0?V::x(1):V(1);return ax==1||by==1?V(1):ax<0||by<0?V::x(1):V(0);}
    throw std::runtime_error("operator requires integral operands");
}
inline std::string real_format(double value,char format='g',int precision=17) {
    std::ostringstream out;out.imbue(std::locale::classic());
    if(format=='f'||format=='F')out<<std::fixed;
    else if(format=='e'||format=='E')out<<std::scientific;
    if(format=='E'||format=='F'||format=='G')out<<std::uppercase;
    out<<std::setprecision(precision)<<value;return out.str();
}
#endif
#ifdef DSIM_TWO_STATE_ENABLED
inline V two_state_value(V value) {
#ifdef DSIM_STRUCT_STRING_ENABLED
    if(value.struct_strings){auto fields=value.struct_strings;value.struct_strings.reset();auto result=two_state_value(std::move(value));result.struct_strings=std::move(fields);return result;}
#endif
#ifdef DSIM_WIDE_VALUES
    if(value.w>64&&value.unknown()) {
        std::vector<V::Word> words(size_t((value.w+63)/64));
        for(size_t i=0;i<words.size();++i)words[i]={value.word_a(i)&~value.word_b(i),0};
        return V::from_words(std::move(words),value.w);
    }
#endif
    if(value.b)return V(value.a&~value.b,0,value.w);
    return value;
}
#endif
#ifdef DSIM_ARRAY_STREAM_ENABLED
// MSB-first four-state stream. Each byte stores 0, 1, X(2) or Z(3);
// runtime lengths never masquerade as a statically sized packed expression.
using StreamBits=std::vector<uint8_t>;
inline void stream_extend(StreamBits& target,const StreamBits& source) {
    if(source.size()>1048576-target.size())throw std::runtime_error("bit stream exceeds 1048576 bits");
    target.insert(target.end(),source.begin(),source.end());
}
inline void stream_append(StreamBits& target,const V& value) {
    if(size_t(value.w)>1048576-target.size())throw std::runtime_error("bit stream exceeds 1048576 bits");
    for(int bit=value.w-1;bit>=0;--bit)target.push_back(uint8_t(value.bit(bit)));
}
inline StreamBits stream_scalar(const V& value) {StreamBits bits;stream_append(bits,value);return bits;}
inline StreamBits stream_array(const std::vector<V>& values) {
    StreamBits bits;for(const auto& value:values)stream_append(bits,value);return bits;
}
inline StreamBits stream_reverse(StreamBits bits,int slice) {
    if(slice<1||slice>1048576)throw std::runtime_error("invalid stream slice size");
    StreamBits reversed;reversed.reserve(bits.size());
    for(size_t end=bits.size();end;) {
        const size_t begin=end-std::min(size_t(slice),end);
        reversed.insert(reversed.end(),bits.begin()+begin,bits.begin()+end);end=begin;
    }
    return reversed;
}
inline V stream_piece(const StreamBits& bits,size_t offset,int width,bool two_state) {
    if(width<1||width>1048576)throw std::runtime_error("invalid bit stream element width");
    if(width<=64) {
        uint64_t a=0,b=0;
        for(int i=0;i<width;++i) {
            const int code=offset+size_t(i)<bits.size()?bits[offset+size_t(i)]:0;
            if(two_state&&code>1)continue;
            const uint64_t selected=uint64_t(1)<<(width-i-1);
            if(code==1||code==2)a|=selected;if(code>1)b|=selected;
        }
        return V(a,b,width);
    }
#ifdef DSIM_WIDE_VALUES
    std::vector<V::Word> words(size_t((width+63)/64));
    for(int i=0;i<width;++i) {
        const int code=offset+size_t(i)<bits.size()?bits[offset+size_t(i)]:0;
        if(two_state&&code>1)continue;
        const size_t bit=size_t(width-i-1);const uint64_t selected=uint64_t(1)<<(bit%64);
        if(code==1||code==2)words[bit/64].a|=selected;if(code>1)words[bit/64].b|=selected;
    }
    return V::from_words(std::move(words),width);
#else
    throw std::runtime_error("wide bit stream destination requires multiword values");
#endif
}
inline V stream_pack(const StreamBits& bits,int width,bool two_state,bool strict) {
    if(bits.size()>size_t(width)||(strict&&bits.size()!=size_t(width)))
        throw std::runtime_error(strict?"bit-stream cast size mismatch":"stream destination is smaller than source");
    return stream_piece(bits,0,width,two_state);
}
inline std::vector<V> stream_unpack(const StreamBits& bits,int width,bool two_state,int count,bool strict,int bound=-1) {
    if(width<1||width>1048576)throw std::runtime_error("invalid bit stream element width");
    const size_t length=count<0?(bits.size()+size_t(width)-1)/size_t(width):size_t(count);
    if(length>1048576/size_t(width)||bits.size()>length*size_t(width)||(strict&&bits.size()!=length*size_t(width)))
        throw std::runtime_error(strict?"bit-stream cast size mismatch":"stream destination is smaller than source");
    const size_t retained=bound<0?length:std::min(length,size_t(bound)+1);
    std::vector<V> values;values.reserve(retained);
    for(size_t i=0;i<retained;++i)values.push_back(stream_piece(bits,i*size_t(width),width,two_state));
    return values;
}
#endif
#ifdef DSIM_MIXED_STATE_ENABLED
// Only the two-state members of an unpacked aggregate discard unknowns.
// Packed aggregates keep their shared four-state representation.
inline V masked_two_state_value(V value,const V& selected) {
#ifdef DSIM_STRUCT_STRING_ENABLED
    if(value.struct_strings){auto fields=value.struct_strings;value.struct_strings.reset();auto result=masked_two_state_value(std::move(value),selected);result.struct_strings=std::move(fields);return result;}
#endif
#ifdef DSIM_WIDE_VALUES
    if(value.w>64) {
        if(!value.unknown())return value;
        std::vector<V::Word> words(size_t((value.w+63)/64));
        for(size_t i=0;i<words.size();++i) {
            const auto clear=value.word_b(i)&selected.word_a(i);
            words[i]={value.word_a(i)&~clear,value.word_b(i)&~clear};
        }
        return V::from_words(std::move(words),value.w);
    }
#endif
    const auto clear=value.b&selected.a;
    return clear?V(value.a&~clear,value.b&~clear,value.w):value;
}
#endif
#ifdef DSIM_VECTOR_SYSTEM_FUNCTIONS
// Selected four-state values are represented by a four-bit mask (0,1,X,Z).
inline V count_bits(const V& value,unsigned selected) {
    unsigned count=0;
    for(int i=0;i<(value.w+63)/64;++i) {
#ifdef DSIM_WIDE_VALUES
        uint64_t a=value.word_a(size_t(i)),b=value.word_b(size_t(i));
#else
        uint64_t a=value.a,b=value.b;
#endif
        uint64_t matches=0;
        if(selected&1)matches|=~a&~b;
        if(selected&2)matches|=a&~b;
        if(selected&4)matches|=a&b;
        if(selected&8)matches|=~a&b;
        count+=unsigned(__builtin_popcountll(matches&mask(std::min(64,value.w-i*64))));
    }
    return V(count,0,32);
}
// 0=clog2, 1=isunknown, 2=countones, 3=onehot, 4=onehot0.
// Operands are already self-sized. Masked word pairs preserve X/Z semantics.
template<int Mode> inline V vector_system(const V& value) {
    unsigned ones=0;int highest=-1;
    for(int i=0;i<(value.w+63)/64;++i) {
#ifdef DSIM_WIDE_VALUES
        uint64_t a=value.word_a(size_t(i)),b=value.word_b(size_t(i));
#else
        uint64_t a=value.a,b=value.b;
#endif
        const uint64_t keep=mask(std::min(64,value.w-i*64));a&=keep;b&=keep;
        if constexpr(Mode==0) {if(b)return V::x(32);}
        if constexpr(Mode==1) {if(b)return V(1,0,1);}
        if constexpr(Mode!=1) {
            const uint64_t known=a&~b;ones+=unsigned(__builtin_popcountll(known));
            if constexpr(Mode==0) {if(known)highest=i*64+63-__builtin_clzll(known);}
            if constexpr(Mode==3||Mode==4) {if(ones>1)return V(0,0,1);}
        }
    }
    if constexpr(Mode==0)return V(highest<0?0:highest+(ones>1),0,32);
    if constexpr(Mode==1)return V(0,0,1);
    if constexpr(Mode==2)return V(ones,0,32);
    if constexpr(Mode==3)return V(ones==1,0,1);
    return V(ones<=1,0,1);
}
#endif
inline V signed_size(V value,int width) {
    if(width<=value.w)return value.size(width);
    int sign=value.bit(value.w-1);
    uint64_t fill_a=(sign==1||sign==2)?~uint64_t(0):0;
    uint64_t fill_b=sign>=2?~uint64_t(0):0;
#ifdef DSIM_WIDE_VALUES
    if(width>64) {
        std::vector<V::Word> words(size_t((width+63)/64));
        for(size_t i=0;i<words.size();++i) {
            int remaining=value.w-int(i*64);uint64_t keep=remaining>=64?~uint64_t(0):remaining>0?mask(remaining):0;
            words[i]={(value.word_a(i)&keep)|(fill_a&~keep),(value.word_b(i)&keep)|(fill_b&~keep)};
        }
        return V::from_words(std::move(words),width);
    }
#endif
    uint64_t extra=mask(width)^mask(value.w);
    return V(value.a|(fill_a&extra),value.b|(fill_b&extra),width);
}
inline uint64_t repeat_count(const V& value,bool is_signed=false) {
    if(is_signed&&value.bit(value.w-1)==1)return 0;
#ifdef DSIM_WIDE_VALUES
    return wide_repeat_count(value);
#else
    return value.b?0:value.a;
#endif
}

#ifdef DSIM_DYNAMIC_DELAY_ENABLED
inline uint64_t procedural_delay_ticks(const V& value,uint64_t scale,uint64_t quantum=1) {
#ifdef DSIM_REAL_ENABLED
    if(value.real_width) {
        const long double ticks=std::round(static_cast<long double>(value.real_value())*scale);
        if(!std::isfinite(ticks)||ticks<0||ticks>=std::ldexp(1.0L,64))throw std::runtime_error("real delay is negative, nonfinite or exceeds simulation time range");
        if(uint64_t(ticks)>std::numeric_limits<uint64_t>::max()/quantum)
            throw std::runtime_error("real delay exceeds simulation time range");
        return uint64_t(ticks)*quantum;
    }
#endif
    // Procedural integral delays convert to an unsigned 64-bit time value.
    // Any unknown input bit denotes zero delay (Inactive / current NBA).
#ifdef DSIM_WIDE_VALUES
    if(value.unknown())return 0;
#else
    if(value.b)return 0;
#endif
    if(value.a>std::numeric_limits<uint64_t>::max()/scale)
        throw std::runtime_error("procedural delay exceeds simulation time range");
    const auto ticks=value.a*scale;
    if(ticks>std::numeric_limits<uint64_t>::max()/quantum)
        throw std::runtime_error("procedural delay exceeds simulation time range");
    return ticks*quantum;
}
#endif
inline V inv(V v) {
#ifdef DSIM_WIDE_VALUES
    if(v.w>64)return wide_inv(v);
#endif
    return V(~v.a|v.b,v.b,v.w);
}
inline V bitop(char op,V a,V b,int w) {
#ifdef DSIM_WIDE_VALUES
    if(a.w>64||b.w>64||w>64)return wide_bitop(op,a,b,w);
#endif
    a=a.size(w); b=b.size(w);
    auto a0=~(a.a|a.b)&mask(w), b0=~(b.a|b.b)&mask(w);
    auto a1=a.a&~a.b, b1=b.a&~b.b;
    uint64_t ones=0,zeros=0;
    if(op=='&') { ones=a1&b1; zeros=a0|b0; }
    else if(op=='|') { ones=a1|b1; zeros=a0&b0; }
    else { auto unknown=a.b|b.b; return V((a.a^b.a)|unknown,unknown,w); }
    auto unknown=~(ones|zeros)&mask(w); return V(ones|unknown,unknown,w);
}
enum class Unary {BitNot,LogicalNot,Plus,Minus,ReduceAnd,ReduceOr,ReduceXor};
template<Unary op> inline V unary_op(V v,int w) {
#ifdef DSIM_WIDE_VALUES
    if(v.w>64||w>64) {
        constexpr const char* name=op==Unary::BitNot?"~":op==Unary::LogicalNot?"!":op==Unary::Plus?"+":op==Unary::Minus?"-":op==Unary::ReduceAnd?"&":op==Unary::ReduceOr?"|":"^";
        return wide_unary(name,v,w);
    }
#endif
    v=v.size(w);
    if constexpr(op==Unary::BitNot)return inv(v);
    else if constexpr(op==Unary::LogicalNot){int t=v.truth();return t<0?V::x(1):V(!t,0,1);}
    else if constexpr(op==Unary::Plus)return v;
    else if constexpr(op==Unary::Minus)return v.b?V::x(w):V(0-v.a,0,w);
    else if constexpr(op==Unary::ReduceAnd)return ((~v.a&~v.b)&mask(w))?V(0):v.b?V::x(1):V(1);
    else if constexpr(op==Unary::ReduceOr){int t=v.truth();return t<0?V::x(1):V(t);}
    else {if(v.b)return V::x(1);return V(unsigned(__builtin_parityll(v.a)));}
}
inline V unary(const std::string& op,V v,int w) {
    if(op=="~")return unary_op<Unary::BitNot>(v,w);
    if(op=="!")return unary_op<Unary::LogicalNot>(v,w);
    if(op=="+")return unary_op<Unary::Plus>(v,w);
    if(op=="-")return unary_op<Unary::Minus>(v,w);
    if(op=="&")return unary_op<Unary::ReduceAnd>(v,w);
    if(op=="|")return unary_op<Unary::ReduceOr>(v,w);
    if(op=="^")return unary_op<Unary::ReduceXor>(v,w);
    throw std::runtime_error("invalid generated unary operator");
}
// Operator identity is fixed by code generation, allowing native inlining.
template<Binary op> inline V binary_op(V a,V b,int w) {
#ifdef DSIM_STRUCT_STRING_ENABLED
    if(a.struct_strings||b.struct_strings) {
        if constexpr(op==Binary::Equal||op==Binary::NotEqual||op==Binary::CaseEqual||op==Binary::CaseNotEqual) {
            if(!a.same_struct_strings(b))return V(op==Binary::NotEqual||op==Binary::CaseNotEqual);
            a.struct_strings.reset();b.struct_strings.reset();return binary_op<op>(std::move(a),std::move(b),w);
        } else throw std::runtime_error("non-equality operation on unpacked struct");
    }
#endif
#ifdef DSIM_WIDE_VALUES
    if(a.w>64||b.w>64||w>64)return wide_binary(op,a,b,w);
#endif
    int n=std::max(a.w,b.w);
    if(op==Binary::BitAnd || op==Binary::BitOr || op==Binary::BitXor) return bitop(op==Binary::BitAnd?'&':op==Binary::BitOr?'|':'^',a,b,w);
    if(op==Binary::LogicalAnd || op==Binary::LogicalOr) {
        int x=a.truth(),y=b.truth();
        if(op==Binary::LogicalAnd) return x==0||y==0?V(0):x<0||y<0?V::x(1):V(1);
        return x==1||y==1?V(1):x<0||y<0?V::x(1):V(0);
    }
    if(op==Binary::CaseEqual || op==Binary::CaseNotEqual) {
        bool eq=a.size(n).same(b.size(n)); return V(op==Binary::CaseEqual?eq:!eq);
    }
    if(op==Binary::Equal || op==Binary::NotEqual) {
        // Known mismatching bits decide equality even if another bit is X/Z.
        uint64_t mismatch=(a.a^b.a)&~(a.b|b.b);
        if(mismatch) return V(op==Binary::NotEqual);
        if(a.b||b.b) return V::x(1);
        return V(op==Binary::Equal);
    }
    if(op==Binary::Less || op==Binary::Greater || op==Binary::LessEqual || op==Binary::GreaterEqual) {
        if(a.b||b.b) return V::x(1);
        return V(op==Binary::Less?a.a<b.a:op==Binary::Greater?a.a>b.a:op==Binary::LessEqual?a.a<=b.a:a.a>=b.a);
    }
    if(op==Binary::ShiftLeft || op==Binary::ShiftRight) {
        if(b.b) return V::x(w);
        if(b.a>=uint64_t(w)) return V(0,0,w);
        return op==Binary::ShiftLeft?V(a.a<<b.a,a.b<<b.a,w):V(a.a>>b.a,a.b>>b.a,w);
    }
    if(a.b||b.b) return V::x(w);
    if(op==Binary::Add) return V(a.a+b.a,0,w);
    if(op==Binary::Subtract) return V(a.a-b.a,0,w);
    if(op==Binary::Multiply) return V(a.a*b.a,0,w);
    if(op==Binary::Divide) return b.a?V(a.a/b.a,0,w):V::x(w);
    if(op==Binary::Modulo) return b.a?V(a.a%b.a,0,w):V::x(w);
    throw std::runtime_error("invalid generated binary operator");
}
// Operands are already extended to their common expression type by lowering.
template<Binary op> inline V signed_binary_op(V a,V b,int width) {
    if constexpr(op!=Binary::Divide&&op!=Binary::Modulo&&op!=Binary::Less&&op!=Binary::Greater&&op!=Binary::LessEqual&&op!=Binary::GreaterEqual)
        return binary_op<op>(a,b,width);
    bool unknown;
#ifdef DSIM_WIDE_VALUES
    unknown=a.unknown()||b.unknown();
#else
    unknown=a.b||b.b;
#endif
    if(unknown)return V::x(op==Binary::Divide||op==Binary::Modulo?width:1);
    bool an=a.bit(a.w-1)==1,bn=b.bit(b.w-1)==1;
    if constexpr(op==Binary::Divide||op==Binary::Modulo) {
        if(an)a=unary("-",a,width);
        if(bn)b=unary("-",b,width);
        auto result=binary_op<op>(a,b,width);
        return (op==Binary::Divide?an!=bn:an)?unary("-",result,width):result;
    } else {
        if(an==bn)return binary_op<op>(a,b,width);
        return V(op==Binary::Less||op==Binary::LessEqual?an:bn);
    }
}
// Merge indices instead of using std::sort: four-state comparisons can be
// unknown and therefore do not satisfy a C++ strict weak ordering. This merge
// remains bounded and deterministic even in that case, without moving keys or
// evaluating a SystemVerilog with expression more than once per element.
template<class Before> inline void array_order_values(std::vector<V>& values,const std::vector<V>& keys,Before before) {
    if(values.size()!=keys.size())throw std::runtime_error("array ordering key count mismatch");
    const auto count=values.size();if(count<2)return;
    std::vector<size_t> order(count),scratch(count);
    for(size_t i=0;i<count;++i)order[i]=i;
    for(size_t span=1;span<count;span=span>count/2?count:span*2) {
        for(size_t begin=0;begin<count;) {
            const auto middle=begin+std::min(span,count-begin),end=middle+std::min(span,count-middle);
            size_t left=begin,right=middle,out=begin;
            while(left<middle&&right<end)
                scratch[out++]=before(keys[order[right]],keys[order[left]])?order[right++]:order[left++];
            while(left<middle)scratch[out++]=order[left++];
            while(right<end)scratch[out++]=order[right++];
            begin=end;
        }
        order.swap(scratch);
    }
    std::vector<V> sorted;sorted.reserve(count);
    for(auto index:order)sorted.push_back(std::move(values[index]));
    values=std::move(sorted);
}
inline V signed_shift_right(V a,V b,int width) {
#ifdef DSIM_WIDE_VALUES
    if(b.unknown())return V::x(width);
    bool huge=false;for(size_t i=1;i<size_t((b.w+63)/64);++i)huge|=b.word_a(i)!=0;
#else
    if(b.b)return V::x(width);
    bool huge=false;
#endif
    a=a.size(width);
    if(huge||b.a>=uint64_t(width)) {
        int sign=a.bit(width-1);return signed_size(V(sign==1||sign==2,sign>=2,1),width);
    }
    if(!b.a)return a;
    auto shifted=binary_op<Binary::ShiftRight>(a,b,width);
    return signed_size(shifted.size(width-int(b.a)),width);
}
// RHS X/Z bits are wildcards; known mismatches dominate uncovered LHS X/Z.
inline V wildcard_equal(V left,V right,bool negate=false) {
    const int width=std::max(left.w,right.w);left=left.size(width);right=right.size(width);
    bool unknown=false;
    for(int word=0;word<(width+63)/64;++word) {
#ifdef DSIM_WIDE_VALUES
        uint64_t a=left.word_a(size_t(word)),b=left.word_b(size_t(word));
        uint64_t c=right.word_a(size_t(word)),d=right.word_b(size_t(word));
#else
        uint64_t a=left.a,b=left.b,c=right.a,d=right.b;
#endif
        const uint64_t care=~d&mask(std::min(64,width-word*64));
        if((a^c)&~b&care)return V(negate);
        unknown=unknown||(b&care)!=0;
    }
    return unknown?V::x(1):V(!negate);
}
inline V membership_range(V value,V low,V high,bool sign) {
    auto lower=sign?signed_binary_op<Binary::GreaterEqual>(value,low,1):binary_op<Binary::GreaterEqual>(value,low,1);
    auto upper=sign?signed_binary_op<Binary::LessEqual>(value,high,1):binary_op<Binary::LessEqual>(value,high,1);
    return binary_op<Binary::LogicalAnd>(lower,upper,1);
}
// Dynamic dispatch remains available for runtime API users and truth-table tests.
inline V binary(const std::string& op,V a,V b,int w) {
    if(op=="&") return binary_op<Binary::BitAnd>(a,b,w);
    if(op=="|") return binary_op<Binary::BitOr>(a,b,w);
    if(op=="^") return binary_op<Binary::BitXor>(a,b,w);
    if(op=="&&") return binary_op<Binary::LogicalAnd>(a,b,w);
    if(op=="||") return binary_op<Binary::LogicalOr>(a,b,w);
    if(op=="==?")return wildcard_equal(a,b);
    if(op=="!=?")return wildcard_equal(a,b,true);
    if(op=="===") return binary_op<Binary::CaseEqual>(a,b,w);
    if(op=="!==") return binary_op<Binary::CaseNotEqual>(a,b,w);
    if(op=="==") return binary_op<Binary::Equal>(a,b,w);
    if(op=="!=") return binary_op<Binary::NotEqual>(a,b,w);
    if(op=="<") return binary_op<Binary::Less>(a,b,w);
    if(op==">") return binary_op<Binary::Greater>(a,b,w);
    if(op=="<=") return binary_op<Binary::LessEqual>(a,b,w);
    if(op==">=") return binary_op<Binary::GreaterEqual>(a,b,w);
    if(op=="<<") return binary_op<Binary::ShiftLeft>(a,b,w);
    if(op==">>") return binary_op<Binary::ShiftRight>(a,b,w);
    if(op=="+") return binary_op<Binary::Add>(a,b,w);
    if(op=="-") return binary_op<Binary::Subtract>(a,b,w);
    if(op=="*") return binary_op<Binary::Multiply>(a,b,w);
    if(op=="/") return binary_op<Binary::Divide>(a,b,w);
    if(op=="%") return binary_op<Binary::Modulo>(a,b,w);
    throw std::runtime_error("invalid binary operator");
}
inline V mux(V c,V a,V b,int w) {
#ifdef DSIM_WIDE_VALUES
    if(c.w>64||a.w>64||b.w>64||w>64)return wide_mux(c,a,b,w);
#endif
    if(c.truth()>=0) return (c.truth()?a:b).size(w);
    a=a.size(w); b=b.size(w);
    // With an ambiguous condition only equal known bits survive. In
    // particular Z/Z combines to X; a known condition still passes Z through.
    auto equal=~((a.a^b.a)|a.b|b.b)&mask(w);
    return V((a.a&equal)|~equal,(a.b&equal)|~equal,w);
}
// mode 0: exact case; 1: casez (Z wildcards); 2: casex (X/Z wildcards).
inline bool case_match(V selector,V item,int mode) {
#ifdef DSIM_WIDE_VALUES
    if(selector.w>64||item.w>64)return wide_case_match(selector,item,mode);
#endif
    int width=std::max(selector.w,item.w);
    selector=selector.size(width); item=item.size(width);
    uint64_t wild=mode==2?(selector.b|item.b):mode==1?((selector.b&~selector.a)|(item.b&~item.a)):0;
    return (((selector.a^item.a)|(selector.b^item.b))&~wild&mask(width))==0;
}
inline V concat(V a,V b) {
#ifdef DSIM_STRUCT_STRING_ENABLED
    if(a.struct_strings||b.struct_strings) {
        V::StructStrings fields;if(b.struct_strings)fields=*b.struct_strings;
        if(a.struct_strings)for(const auto& item:*a.struct_strings)fields.emplace(item.first+b.w,item.second);
        a.struct_strings.reset();b.struct_strings.reset();auto result=concat(std::move(a),std::move(b));
        result.struct_strings=std::make_shared<const V::StructStrings>(std::move(fields));return result;
    }
#endif
#ifdef DSIM_WIDE_VALUES
    if(a.w>64-b.w)return wide_concat(a,b);
#endif
    if(a.w+b.w>64) throw std::runtime_error("concatenation exceeds 64 bits");
    return V((a.a<<b.w)|b.a,(a.b<<b.w)|b.b,a.w+b.w);
}
#ifdef DSIM_REPLICATION_ENABLED
inline V replicate(V value,unsigned count) {
    if(!count||count>1048576U/unsigned(value.w))throw std::runtime_error("invalid replication width");
    // Sign-extension and CRC masks commonly repeat a single four-state bit.
    // Expand each bit plane directly, preserving both X and Z.
    if(value.w==1&&count<=64)return V(value.a?mask(int(count)):0,value.b?mask(int(count)):0,int(count));
    V result;bool have=false;
    for(unsigned n=count;n;n>>=1) {
        if(n&1){result=have?concat(value,result):value;have=true;}
        if(n>1)value=concat(value,value);
    }
    return result;
}
#endif
inline V slice(V a,int lo,int width) {
#ifdef DSIM_STRUCT_STRING_ENABLED
    if(a.struct_strings) {
        V::StructStrings fields;for(const auto& item:*a.struct_strings)if(item.first>=lo&&item.first-lo<width)fields.emplace(item.first-lo,item.second);
        a.struct_strings.reset();auto result=slice(std::move(a),lo,width);
        if(!fields.empty())result.struct_strings=std::make_shared<const V::StructStrings>(std::move(fields));return result;
    }
#endif
#ifdef DSIM_REAL_ENABLED
    if(a.real_width&&lo==0&&width==a.w)return a;
#endif
#ifdef DSIM_WIDE_VALUES
    if(a.w>64||width>64)return wide_slice(a,lo,width);
#endif
    if(lo<0||lo+width>a.w) return V::x(width);
    return V(a.a>>lo,a.b>>lo,width);
}
inline V replace(V base,int lo,int width,V value) {
#ifdef DSIM_STRUCT_STRING_ENABLED
    if(base.struct_strings||value.struct_strings) {
        V::StructStrings fields;if(base.struct_strings)for(const auto& item:*base.struct_strings)if(item.first<lo||item.first-lo>=width)fields.insert(item);
        if(value.struct_strings)for(const auto& item:*value.struct_strings)if(item.first<width)fields.emplace(item.first+lo,item.second);
        base.struct_strings.reset();value.struct_strings.reset();auto result=replace(std::move(base),lo,width,std::move(value));
        if(!fields.empty())result.struct_strings=std::make_shared<const V::StructStrings>(std::move(fields));return result;
    }
#endif
#ifdef DSIM_REAL_ENABLED
    if(value.real_width&&lo==0&&width==base.w)return value;
#endif
#ifdef DSIM_WIDE_VALUES
    if(base.w>64||value.w>64||width>64)return wide_replace(base,lo,width,value);
#endif
    if(width<1 || width>64 || lo<0 || lo>base.w-width)
        throw std::runtime_error("invalid generated assignment slice");
    value=value.size(width); auto selected=mask(width)<<lo;
    return V((base.a&~selected)|(value.a<<lo),(base.b&~selected)|(value.b<<lo),base.w);
}
// Pieces are ordered from the rightmost concatenation item to the leftmost.
// VCS applies overlapping variable pieces left-to-right, so the rightmost wins.
struct Part { int signal,lo,width,rhs_lo,driver=-1;
#ifdef DSIM_DYNAMIC_ARRAYS_ENABLED
    uint64_t dynamic_generation=0;
    int dynamic_index=-1;
    bool dynamic_event=false;
#endif
};
#ifdef DSIM_INDEXED_SELECT_ENABLED
// Validate a packed dimension before flattening; VCS treats a partially
// out-of-range multidimensional selection as entirely invalid.
inline Part packed_dimension(int total,V index,int base,int width,bool descending,bool signed_index) {
    Part empty{0,0,0,0};
#ifdef DSIM_WIDE_VALUES
    if(index.unknown())return empty;
    const bool negative=signed_index&&index.bit(index.w-1)==1;
    for(int bit=64;bit<index.w;++bit)if(index.bit(bit)!=(negative?1:0))return empty;
    if(negative&&index.w>64&&!(index.a>>63))return empty;
#else
    if(index.b)return empty;
#endif
    if(!signed_index&&index.a>uint64_t(INT64_MAX))return empty;
    const int64_t value=int64_t(index.a);
    const int64_t delta=descending?width-1:0;
    // Reject extreme values before subtracting the signed declaration bound.
    if(value<int64_t(base)+delta-width+1||value>=int64_t(base)+delta+total)return empty;
    const int64_t lo=value-base-delta;
    if(lo<0||lo>int64_t(total)-width)return empty;
    return {0,int(lo),width,0};
}
inline Part indexed_part(int signal,int total,V index,int base,int width,bool descending,int rhs_lo,bool signed_index=false) {
    Part empty{signal,0,0,rhs_lo};
    if(signal<0)return empty;
#ifdef DSIM_WIDE_VALUES
    if(index.unknown())return empty;
    const bool negative=signed_index&&index.bit(index.w-1)==1;
    for(int bit=64;bit<index.w;++bit)if(index.bit(bit)!=(negative?1:0))return empty;
    if(index.w>64&&bool(index.a>>63)!=negative)return empty;
#else
    if(index.b)return empty;
    const bool negative=signed_index&&bool(index.a&(UINT64_C(1)<<(index.w-1)));
#endif
    if(!signed_index&&index.a>uint64_t(INT64_MAX))return empty;
    const int64_t value=int64_t(negative&&index.w<64?index.a|~mask(index.w):index.a);
    const int64_t delta=descending?width-1:0;
    const int64_t end=int64_t(base)+delta+total;
    const int64_t start=int64_t(base)+delta-width+1;
    // Bound before subtraction, including signed negative indices whose
    // in-range portion must be written/read rather than discarded entirely.
    if(value<start||value>=end)return empty;
    const int64_t lo=value-base-delta;
    const int clipped=int(std::max(int64_t(0),lo));
    const int count=int(std::min(int64_t(total),lo+width))-clipped;
    return {signal,clipped,count,rhs_lo+int(clipped-lo)};
}
inline Part view_indexed_part(int signal,int view_lo,int view_width,V index,int base,int width,bool descending,int rhs_lo,bool signed_index=false) {
    auto part=indexed_part(signal,view_width,index,base,width,descending,rhs_lo,signed_index);
    part.lo+=view_lo;return part;
}
inline V indexed_slice(V value,V index,int base,int width,bool descending,bool signed_index=false) {
    auto part=indexed_part(0,value.w,index,base,width,descending,0,signed_index);
    if(!part.width)return V::x(width);
    if(part.width==width)return slice(value,part.lo,width);
    return replace(V::x(width),part.rhs_lo,part.width,slice(value,part.lo,part.width));
}
// Tables contain logical signal IDs; partitioned models map only the selected
// word. Lookup is O(1), with no per-access allocation or array scan.
inline int memory_signal(const int* words,int count,int base,V index,const int* mapping=nullptr) {
#ifdef DSIM_WIDE_VALUES
    if(index.unknown())return -1;
    for(int i=1;i<(index.w+63)/64;++i)if(index.word_a(size_t(i)))return -1;
#else
    if(index.b)return -1;
#endif
    if(index.a<uint64_t(base)||index.a-uint64_t(base)>=uint64_t(count))return -1;
    int id=words[size_t(index.a-uint64_t(base))];
    return mapping?mapping[id]:id;
}
inline Part memory_part(int signal,int lo,int width,int rhs_lo) {
    return {signal,lo,signal<0?0:width,rhs_lo};
}
template<class Kernel>
inline V memory_read(Kernel& s,const int* words,int count,int base,V index,int width,const int* mapping=nullptr) {
    int id=memory_signal(words,count,base,index,mapping);
    return id<0?V::x(width):s.get(id);
}
#ifdef DSIM_STRING_ENABLED
template<class Kernel>
inline V text_memory_read(Kernel& s,const int* words,int count,int base,V index,int width,const int* mapping=nullptr) {
    int id=memory_signal(words,count,base,index,mapping);
    return id<0?V::text(""):s.get(id);
}
#endif

#endif
#ifdef DSIM_MEMORY_IO_ENABLED
inline int memory_bound(V value) {
#ifdef DSIM_WIDE_VALUES
    if(value.unknown())throw std::runtime_error("unknown memory file bound");
    for(int i=1;i<(value.w+63)/64;++i)if(value.word_a(size_t(i)))throw std::runtime_error("memory file bound overflow");
#else
    if(value.b)throw std::runtime_error("unknown memory file bound");
#endif
    if(value.a>INT32_MAX)throw std::runtime_error("memory file bound overflow");
    return int(value.a);
}
inline int memory_digit(char c) {
    if(c>='0'&&c<='9')return c-'0';
    if(c>='a'&&c<='f')return c-'a'+10;
    if(c>='A'&&c<='F')return c-'A'+10;
    return -1;
}
inline V memory_value(const std::string& token,int radix,int width) {
    const int bits=radix==16?4:1;
    std::string digits;for(char c:token)if(c!='_')digits+=c;
    if(digits.empty())throw std::runtime_error("empty memory data token");
    bool x=digits.front()=='x'||digits.front()=='X';
    bool z=digits.front()=='z'||digits.front()=='Z';
    #ifdef DSIM_WIDE_VALUES
    using MemoryWord=V::Word;
#else
    struct MemoryWord {uint64_t a,b;};
#endif
    std::vector<MemoryWord> words(size_t((width+63)/64),{x?~uint64_t(0):0,(x||z)?~uint64_t(0):0});
    size_t offset=0;
    for(auto it=digits.rbegin();it!=digits.rend();++it) {
        const char c=*it;int digit=memory_digit(c);
        bool dx=c=='x'||c=='X',dz=c=='z'||c=='Z';
        if(!dx&&!dz&&(digit<0||digit>=radix))throw std::runtime_error("invalid memory data token: "+token);
        for(int b=0;b<bits;++b,++offset)if(offset<size_t(width)) {
            auto& word=words[offset/64];uint64_t mask=uint64_t(1)<<(offset%64);
            word.a&=~mask;word.b&=~mask;
            if(dx||(!dz&&((digit>>b)&1)))word.a|=mask;
            if(dx||dz)word.b|=mask;
        }
    }
#ifdef DSIM_WIDE_VALUES
    return V::from_words(words,width);
#else
    return V(words[0].a,words[0].b,width);
#endif
}
template<class Kernel>
inline void read_memory(Kernel& s,const int* words,int count,int base,const std::string& filename,int radix,int width,int start,int finish,const int* mapping=nullptr) {
    auto error=[&](const std::string& text){throw std::runtime_error(filename+": "+text);};
    if(start<base||finish<base||int64_t(start)>=int64_t(base)+count||int64_t(finish)>=int64_t(base)+count)error("memory file range is out of bounds");
    std::string text=s.read_memory_file(filename);
    std::vector<std::pair<int,V>> updates;
    int64_t address=start;int direction=start<=finish?1:-1;
    for(size_t pos=0;pos<text.size();) {
        if(std::isspace(static_cast<unsigned char>(text[pos]))){++pos;continue;}
        if(text[pos]=='/'&&pos+1<text.size()) {
            if(text[pos+1]=='/') {pos=text.find('\n',pos+2);if(pos==std::string::npos)break;continue;}
            if(text[pos+1]=='*') {auto end=text.find("*/",pos+2);if(end==std::string::npos)error("unterminated memory file comment");pos=end+2;continue;}
        }
        size_t begin=pos;
        while(pos<text.size()&&!std::isspace(static_cast<unsigned char>(text[pos]))&&text[pos]!='/')++pos;
        if(begin==pos)error("invalid memory file character");
        std::string token=text.substr(begin,pos-begin);
        if(token[0]=='@') {
            uint64_t value=0;bool seen=false;
            for(size_t i=1;i<token.size();++i)if(token[i]!='_') {
                int digit=memory_digit(token[i]);if(digit<0||value>(uint64_t(INT32_MAX)-uint64_t(digit))/16)error("invalid memory file address");
                value=value*16+uint64_t(digit);seen=true;
            }
            if(!seen)error("empty memory file address");address=int64_t(value);
        } else {
            if(address<std::min(start,finish)||address>std::max(start,finish))error("memory data exceeds selected range");
            int id=words?words[size_t(address-base)]:int(address-base);
            V value;
            try {value=memory_value(token,radix,width);}
            catch(const std::runtime_error& failure){error(failure.what());}
            updates.emplace_back(mapping?mapping[id]:id,std::move(value));
            address+=direction;
        }
    }
    // Reject malformed input before publishing any memory changes.
    for(auto& update:updates)s.set(update.first,std::move(update.second));
}
template<class Kernel>
inline void write_memory(Kernel& s,const int* words,int count,int base,const std::string& filename,int radix,int width,int start,int finish,const int* mapping=nullptr) {
    auto error=[&](const std::string& text){throw std::runtime_error(filename+": "+text);};
    if(start<base||finish<base||int64_t(start)>=int64_t(base)+count||int64_t(finish)>=int64_t(base)+count)error("memory file range is out of bounds");
    std::ostringstream output;
    // Explicit addresses preserve partial ranges when the file is read back.
    output<<'@'<<std::hex<<start<<'\n';
    const int step=radix==16?4:1,direction=start<=finish?1:-1;
    for(int64_t address=start;;address+=direction) {
        int id=words?words[size_t(address-base)]:int(address-base);const V value=s.get(mapping?mapping[id]:id);
        for(int bit=((width-1)/step)*step;bit>=0;bit-=step) {
            unsigned digit=0;bool unknown=false,all_x=true,all_z=true;
            for(int b=0;b<std::min(step,width-bit);++b) {
                const int v=value.bit(bit+b);unknown|=v>=2;all_x&=v==2;all_z&=v==3;
                if(v==1)digit|=1u<<b;
            }
            output<<(unknown?(all_z?'z':all_x?'x':'X'):"0123456789abcdef"[digit]);
        }
        output<<'\n';if(address==finish)break;
    }
    s.write_memory_file(filename,output.str());
}
// Reuse the same atomic file parser and formatter for compact fixed storage.
// The adapter interprets IDs as offsets, without materializing a word-ID table.
template<class Kernel> struct FixedMemoryIO {
    Kernel& kernel;int owner,width;bool two_state;
    std::string read_memory_file(const std::string& file){return kernel.read_memory_file(file);}
    void write_memory_file(const std::string& file,std::string text){kernel.write_memory_file(file,std::move(text));}
    V get(int offset){return kernel.dynamic_read(owner,V(uint64_t(offset),0,64),width,two_state);}
    void set(int offset,V value){kernel.dynamic_write(owner,V(uint64_t(offset),0,64),std::move(value),width,two_state);}
};
template<class Kernel>
inline void read_fixed_memory(Kernel& s,int owner,int count,int base,const std::string& filename,int radix,int width,int start,int finish,bool two_state) {
    FixedMemoryIO<Kernel> adapter{s,owner,width,two_state};
    read_memory(adapter,nullptr,count,base,filename,radix,width,start,finish);
}
template<class Kernel>
inline void write_fixed_memory(Kernel& s,int owner,int count,int base,const std::string& filename,int radix,int width,int start,int finish,bool two_state) {
    FixedMemoryIO<Kernel> adapter{s,owner,width,two_state};
    write_memory(adapter,nullptr,count,base,filename,radix,width,start,finish);
}
#endif

inline V resolve(V a,V b) {
#ifdef DSIM_WIDE_VALUES
    if(a.w>64||b.w>64)return wide_resolve(a,b);
#endif
    uint64_t az=a.b&~a.a,bz=b.b&~b.a;
    uint64_t eq=~((a.a^b.a)|(a.b^b.b));
    uint64_t conflict=~(az|bz|eq)&mask(a.w);
    return V((a.a&bz)|(b.a&az)|(a.a&eq)|conflict,
             (a.b&bz)|(b.b&az)|(a.b&eq)|conflict,a.w);
}
inline std::string format(V v,char base) {
#ifdef DSIM_STRING_ENABLED
    if(v.text_data){if(base!='s')throw std::runtime_error("string format requires %s");return v.text_value();}
#endif
    if(base=='c')return std::string(1,char(v.a&~v.b&255));
    if(base=='s') {
        std::string text;
        for(int i=(v.w+7)/8;i-->0;){unsigned byte=0;for(int bit=0;bit<8;++bit)if(v.bit(i*8+bit)==1)byte|=1u<<bit;if(byte)text+=char(byte);}
        return text;
    }
#ifdef DSIM_WIDE_VALUES
    if(v.w>64)return wide_format(v,base);
#endif
    if(base=='d' || base=='t') {
        if(!v.b) return std::to_string(v.a);
        if(v.b==mask(v.w) && v.a==mask(v.w)) return "x";
        if(v.b==mask(v.w) && v.a==0) return "z";
        return (v.a&v.b)?"X":"Z";
    }
    int step=base=='h'||base=='x'?4:base=='o'?3:1;
    std::string s;
    for(int i=((v.w-1)/step)*step;i>=0;i-=step) {
        auto m=mask(std::min(step,v.w-i)); auto a=v.a>>i&m,b=v.b>>i&m;
        if(b) s+=b==m?(a==0?'z':a==m?'x':'X'):(a&b?'X':'Z');
        else s+="0123456789abcdef"[a];
    }
    return s;
}
#if defined(DSIM_STRING_ENABLED) || defined(DSIM_PLUSARGS_ENABLED)
inline V packed_text(const std::string& text,int width) {
#ifdef DSIM_WIDE_VALUES
    using Word=V::Word;
#else
    struct Word {uint64_t a,b;};
#endif
    std::vector<Word> words(size_t((width+63)/64),{0,0});
    for(size_t i=0;i<text.size()&&i<size_t((width+7)/8);++i)
        words[i/8].a|=uint64_t(static_cast<unsigned char>(text[text.size()-1-i]))<<((i%8)*8);
#ifdef DSIM_WIDE_VALUES
    return V::from_words(words,width);
#else
    return V(words[0].a,0,width);
#endif
}
#endif
#ifdef DSIM_SCAN_ENABLED
// Owned scan plans/results are local to the call. File cursors themselves live
// in Sim's checkpointed handle table; no libc FILE* escapes into generated code.
struct ScanTarget {int width;bool text;};
struct ScanValue {bool matched=false;V value;};
struct ScanResult {int32_t count=0;std::vector<ScanValue> values;};
struct ScanField {char kind;size_t limit;bool suppress;int target;};
inline bool scan_space(int c) {return c==' '||c=='\t'||c=='\n'||c=='\r'||c=='\f'||c=='\v';}
inline std::string scan_source(const V& value) {
    if(value.text_data){auto text=value.text_value();return text.substr(0,text.find('\0'));}
    std::string text;bool started=false;
    for(int byte=(value.w+7)/8;byte-->0;) {
        unsigned c=0;for(int bit=0;bit<8;++bit)if(value.bit(byte*8+bit)==1)c|=1u<<bit;
        if(!started&&!c)continue;
        started=true;if(!c)break;text+=char(c);
    }
    return text;
}
inline std::vector<ScanField> scan_plan(const std::string& fmt,const std::vector<ScanTarget>& targets) {
    if(fmt.empty())throw std::runtime_error("scan requires a nonempty format string");
    std::vector<ScanField> fields;int target=0;
    for(size_t i=0;i<fmt.size();++i) {
        char c=fmt[i];
        if(scan_space(static_cast<unsigned char>(c))){fields.push_back({' ',0,false,-1});continue;}
        if(c!='%'){fields.push_back({c,0,false,-2});continue;}
        if(++i==fmt.size())throw std::runtime_error("incomplete scan format");
        if(fmt[i]=='%'){fields.push_back({'%',0,false,-2});continue;}
        bool suppress=fmt[i]=='*';if(suppress&&++i==fmt.size())throw std::runtime_error("incomplete scan format");
        size_t width=0;bool bounded=false;
        while(i<fmt.size()&&fmt[i]>='0'&&fmt[i]<='9') {
            bounded=true;width=width*10+size_t(fmt[i++]-'0');
            if(width>1048576)throw std::runtime_error("scan field width exceeds 1048576");
        }
        if(i==fmt.size()||(bounded&&!width))throw std::runtime_error("invalid scan field width");
        c=fmt[i];if(c>='A'&&c<='Z')c=char(c-'A'+'a');
        if(std::string("dhxobsc").find(c)==std::string::npos)
            throw std::runtime_error("unsupported scan format; supported: %d %h %x %o %b %s %c and suppression");
        const int index=suppress?-1:target++;
        if(index>=0) {
            if(size_t(index)>=targets.size())throw std::runtime_error("scan format/target count mismatch");
            if(targets[size_t(index)].text&&c!='s'&&c!='c')throw std::runtime_error("numeric scan conversion requires an integral target");
        }
        // VCS ignores a field width on %c: it always reads one raw byte.
        fields.push_back({c,c=='c'?1:width,suppress,index});
    }
    if(size_t(target)!=targets.size())throw std::runtime_error("scan format/target count mismatch");
    return fields;
}
template<class Get,class Put>
inline ScanResult scan_input(const std::string& fmt,const std::vector<ScanTarget>& targets,Get get,Put put) {
    const auto fields=scan_plan(fmt,targets); // Validate before changing a cursor.
    ScanResult result;result.values.resize(targets.size());
    int look=-2;
    auto peek=[&](){if(look==-2)look=get();return look;};
    auto take=[&](){int c=peek();look=-2;return c;};
    bool input_failure=false;
    for(const auto& field:fields) {
        if(field.target==-2) {
            if(peek()<0){input_failure=true;break;}
            if(peek()!=static_cast<unsigned char>(field.kind))break;
            take();continue;
        }
        if(field.kind==' ') {if(peek()<0){input_failure=true;break;}while(scan_space(peek()))take();continue;}
        if(field.kind!='c')while(scan_space(peek()))take();
        if(peek()<0){input_failure=true;break;}
        size_t remaining=field.limit?field.limit:std::numeric_limits<size_t>::max();
        const auto target=field.suppress?ScanTarget{32,false}:targets[size_t(field.target)];
        V value(0,0,target.width);bool matched=false;
        if(field.kind=='s'||field.kind=='c') {
            std::string bytes;
            while(remaining&&peek()>=0&&(field.kind=='c'||!scan_space(peek()))) {bytes+=char(take());--remaining;}
            matched=!bytes.empty();
            if(matched)value=target.text?V::text(bytes.substr(0,bytes.find('\0'))):packed_text(bytes,target.width);
        } else {
            const int radix=field.kind=='d'?10:field.kind=='b'?2:field.kind=='o'?8:16;
            bool negative=false;
            if(radix==10&&(peek()=='+'||peek()=='-')){negative=take()=='-';--remaining;}
            bool underscores=false;
            while(remaining&&peek()=='_'){take();--remaining;underscores=true;}
            if(remaining&&peek()<0&&!underscores){input_failure=true;break;}
            while(remaining&&peek()>=0) {
                int c=peek();
                if(c=='_'){take();--remaining;continue;}
                const bool x=c=='x'||c=='X',z=c=='z'||c=='Z'||c=='?';
                const int digit=c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:c>='A'&&c<='F'?c-'A'+10:-1;
                if(radix==10&&(x||z)) {
                    if(matched)break;
                    value=x?V::x(target.width):V::z(target.width);matched=true;take();--remaining;break;
                }
                if(!x&&!z&&(digit<0||digit>=radix))break;
                if(!matched&&(x||z))value=x?V::x(target.width):V::z(target.width);
                matched=true;take();--remaining;
                if(radix==10)value=binary_op<Binary::Add>(binary_op<Binary::Multiply>(value,V(10,0,32),target.width),V(uint64_t(digit),0,32),target.width);
                else {
                    const int bits=radix==16?4:radix==8?3:1;
                    auto chunk=x?V::x(bits):z?V::z(bits):V(uint64_t(digit),0,bits);
                    value=replace(binary_op<Binary::ShiftLeft>(value,V(bits,0,32),target.width),0,std::min(bits,target.width),chunk);
                }
            }
            if(negative)value=unary("-",value,target.width);
        }
        if(!matched)break;
        if(!field.suppress){result.values[size_t(field.target)]={true,std::move(value)};++result.count;}
    }
    if(look>=0)put(look);
    if(input_failure&&!result.count)result.count=-1;
    return result;
}
#endif

struct TimeFormat {
    uint64_t unit_fs=1;
    int digits=0,width=20;
    std::string suffix;
};
inline int time_exponent(uint64_t fs) {
    int exponent=0;
    while(fs>1 && fs%10==0){fs/=10;++exponent;}
    if(fs!=1)throw std::runtime_error("time unit must be a positive power of ten femtoseconds");
    return exponent;
}
inline std::string format_time(V value,uint64_t caller_unit_fs,const TimeFormat& config) {
    // VCS converts an unknown %t operand to a bare zero.
#ifdef DSIM_WIDE_VALUES
    if(value.unknown())return "0";
    auto text=format(value,'d');
#else
    if(value.b)return "0";
    auto text=std::to_string(value.a);
#endif
    int shift=time_exponent(caller_unit_fs)-time_exponent(config.unit_fs)+config.digits;
    if(shift>=0)text.append(size_t(shift),'0');
    else {
        size_t removed=size_t(-shift);
        if(removed>text.size())text="0";
        else {
            size_t cut=text.size()-removed;
            char first_removed=text[cut];
            bool round=first_removed>'5' || (first_removed=='5' &&
                (text.find_first_not_of('0',cut+1)!=std::string::npos || (cut && (text[cut-1]-'0')%2)));
            text.resize(cut);
            if(text.empty())text="0";
            if(round) {
                size_t i=text.size();while(i && text[i-1]=='9')text[--i]='0';
                if(i)++text[i-1];else text.insert(text.begin(),'1');
            }
        }
    }
    auto first=text.find_first_not_of('0');text=first==std::string::npos?"0":text.substr(first);
    if(config.digits) {
        if(text.size()<=size_t(config.digits))text.insert(0,size_t(config.digits)+1-text.size(),'0');
        text.insert(text.size()-size_t(config.digits),1,'.');
    }
    return text+config.suffix;
}
#ifdef DSIM_STRING_ENABLED
#ifdef DSIM_STRING_REPLICATION_ENABLED
inline V text_repeat(const V& count,const V& value,bool sign) {
    const auto& text=value.text_value();
    if(text.empty()||(sign&&count.bit(count.w-1)==1))return V::text("");
    bool high=false,unknown=false;
    for(int i=0;i<count.w;++i){const int bit=count.bit(i);unknown|=bit>1;high|=i>=64&&bit==1;}
    if(unknown||(!high&&!count.a))return V::text("");
    constexpr size_t limit=1048576;
    if(high||count.a>limit/text.size())throw std::runtime_error("string replication result exceeds 1048576 bytes");
    const size_t total=size_t(count.a)*text.size();std::string result(total,'\0');
    std::copy_n(text.data(),text.size(),result.data());
    for(size_t filled=text.size();filled<total;) {
        const size_t chunk=std::min(filled,total-filled);
        std::copy_n(result.data(),chunk,result.data()+filled);filled+=chunk;
    }
    return V::text(std::move(result));
}
#endif
inline int64_t text_index(const V& value) {
    // Arguments arrive as signed int values. getc clears X/Z bits; substr rejects them below.
    uint32_t bits=0;for(int i=0;i<32;++i)if(value.bit(i)==1)bits|=uint32_t(1)<<i;
    return bits&0x80000000u?int64_t(bits)-0x100000000ll:int64_t(bits);
}
inline V text_len(const V& value) {return V(value.text_value().size(),0,32);}
inline V text_getc(const V& value,const V& index) {
    const auto& text=value.text_value();const auto i=text_index(index);
    return V(i<0||uint64_t(i)>=text.size()?0:static_cast<unsigned char>(text[size_t(i)]),0,8);
}
inline V text_putc(const V& value,const V& index,const V& character) {
    for(int bit=0;bit<32;++bit)if(index.bit(bit)>=2)return value;
    for(int bit=0;bit<8;++bit)if(character.bit(bit)>=2)return value;
    const auto position=text_index(index);const auto byte=character.a&255;
    if(!byte||position<0||uint64_t(position)>=value.text_value().size())return value;
    auto text=value.text_value();text[size_t(position)]=char(byte);return V::text(std::move(text));
}
inline V text_substr(const V& value,const V& first,const V& last) {
    const auto& text=value.text_value();const auto i=text_index(first),j=text_index(last);
    for(const auto* index:{&first,&last})for(int bit=0;bit<std::min(index->w,32);++bit)if(index->bit(bit)>=2)return V::text("");
    return V::text(i<0||j<i||uint64_t(j)>=text.size()?std::string():text.substr(size_t(i),size_t(j-i+1)));
}
inline unsigned char text_lower(unsigned char byte) {return byte>='A'&&byte<='Z'?byte+('a'-'A'):byte;}
inline V text_tolower(const V& value) {auto text=value.text_value();for(char& c:text)c=char(text_lower(static_cast<unsigned char>(c)));return V::text(std::move(text));}
inline V text_toupper(const V& value) {auto text=value.text_value();for(char& c:text)if(c>='a'&&c<='z')c-=('a'-'A');return V::text(std::move(text));}
inline int text_order(const std::string& left,const std::string& right) {
    const size_t common=std::min(left.size(),right.size());
    for(size_t i=0;i<common;++i){const int delta=int(static_cast<unsigned char>(left[i]))-int(static_cast<unsigned char>(right[i]));if(delta)return delta;}
    return left.size()<right.size()?-1:left.size()>right.size()?1:0;
}
inline V text_compare(const V& left,const V& right) {return V(uint32_t(text_order(left.text_value(),right.text_value())),0,32);}
inline int text_packed_compare(const V& left,const V& right) {
    const auto& a=left.text_value();const auto& b=right.text_value();
    const auto ai=a.find_first_not_of(char(0)),bi=b.find_first_not_of(char(0));
    const size_t an=ai==std::string::npos?0:a.size()-ai,bn=bi==std::string::npos?0:b.size()-bi;
    if(an!=bn)return an<bn?-1:1;
    return an?text_order(a.substr(ai),b.substr(bi)):0;
}
inline V text_icompare(const V& left,const V& right) {return text_compare(text_tolower(left),text_tolower(right));}
inline V text_parse_integer(const V& value,unsigned radix) {
    // VCS accepts underscores anywhere, a leading sign, and the lowercase
    // radix prefix. Whitespace and the first non-digit terminate conversion.
    std::string text;for(char c:value.text_value())if(c!='_')text+=c;
    size_t at=0;bool negative=false;
    if(at<text.size()&&(text[at]=='+'||text[at]=='-'))negative=text[at++]=='-';
    const char prefix=radix==16?'x':radix==8?'o':radix==2?'b':'\0';
    if(prefix&&at+1<text.size()&&text[at]=='0'&&text[at+1]==prefix)at+=2;
    uint32_t result=0;
    for(;at<text.size();++at) {
        const unsigned char c=text[at];unsigned digit=c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:c>='A'&&c<='F'?c-'A'+10:radix;
        if(digit>=radix)break;
        result=result*radix+digit;
    }
    return V(negative?uint32_t(0)-result:result,0,32);
}
inline V text_atoi(const V& value) {return text_parse_integer(value,10);}
inline V text_atohex(const V& value) {return text_parse_integer(value,16);}
inline V text_atooct(const V& value) {return text_parse_integer(value,8);}
inline V text_atobin(const V& value) {return text_parse_integer(value,2);}
inline V text_format_integer(const V& value,unsigned radix) {
    if(radix==2) {
        std::string text;for(int bit=31;bit>=0;--bit)text+="01xz"[value.bit(bit)];
        const auto first=text.find_first_not_of('0');return V::text(first==std::string::npos?"0":text.substr(first));
    }
    for(int bit=0;bit<32;++bit)if(value.bit(bit)>=2)return V::text("?");
    uint32_t bits=uint32_t(value.a);
    if(radix==10)return V::text(std::to_string(bits&0x80000000u?int64_t(bits)-0x100000000ll:int64_t(bits)));
    std::string text;
    do{text+="0123456789abcdef"[bits%radix];bits/=radix;}while(bits);
    std::reverse(text.begin(),text.end());return V::text(std::move(text));
}
inline V text_itoa(const V& value) {return text_format_integer(value,10);}
inline V text_hextoa(const V& value) {return text_format_integer(value,16);}
inline V text_octtoa(const V& value) {return text_format_integer(value,8);}
inline V text_bintoa(const V& value) {return text_format_integer(value,2);}
#endif
inline void display(const std::string& fmt,const std::vector<V>& args,bool newline=true,std::ostream& output=std::cout,uint64_t caller_unit_fs=1,const TimeFormat& time_format={},const std::vector<bool>& signs={}) {
    size_t arg=0;
    for(size_t i=0;i<fmt.size();++i) {
        if(fmt[i]!='%') { output<<fmt[i]; continue; }
        if(++i==fmt.size()) throw std::runtime_error("incomplete display format");
        if(fmt[i]=='%') { output<<'%'; continue; }
        bool zero=fmt[i]=='0'; size_t start=i;
        while(i<fmt.size() && fmt[i]>='0' && fmt[i]<='9') ++i;
        if(i==fmt.size() || arg==args.size()) throw std::runtime_error("invalid display arguments");
        int width=i>start?std::stoi(fmt.substr(start,i-start)):0;
        int precision=6;
        if(i<fmt.size()&&fmt[i]=='.') {
            const auto begin=++i;while(i<fmt.size()&&fmt[i]>='0'&&fmt[i]<='9')++i;
            if(begin==i||i==fmt.size())throw std::runtime_error("invalid real format precision");
            precision=std::stoi(fmt.substr(begin,i-begin));
            if(precision>1048576)throw std::runtime_error("real format precision exceeds limit");
        }
        bool is_signed=arg<signs.size()&&signs[arg];
        V value=args[arg++];
#ifdef DSIM_REAL_ENABLED
        if(std::string("fFeEgG").find(fmt[i])!=std::string::npos) {
            auto result=real_format(real_numeric(value,is_signed),fmt[i],precision);
            if(width>int(result.size()))output<<std::string(size_t(width)-result.size(),' ');
            output<<result;continue;
        }
        if(value.real_width)value=real_integral(value.real_value(),32);
#endif
        auto result=fmt[i]=='t'?format_time(value,caller_unit_fs,time_format):format(value,fmt[i]);
        if(fmt[i]=='s'
#ifdef DSIM_STRING_ENABLED
           &&!value.text_data
#endif
        ) {
            result.clear();
            for(int byte=(value.w+7)/8;byte-->0;) {
                unsigned character=0;bool unknown=false;
                for(int bit=0;bit<8&&byte*8+bit<value.w;++bit) {
                    const int state=value.bit(byte*8+bit);unknown|=state>=2;
                    if(state==1)character|=1u<<bit;
                }
                if(!unknown&&character)result+=char(character);
                else if(!zero)result+=' ';
            }
        }
        if(fmt[i]=='d'&&is_signed&&value.bit(value.w-1)==1) {
#ifdef DSIM_WIDE_VALUES
            if(!value.unknown())
#else
            if(!value.b)
#endif
                result="-"+format(unary("-",value,value.w),'d');
        }
        if(fmt[i]=='t') {if(i==start)width=time_format.width;}
        else if(zero&&fmt[i]!='s') { auto p=result.find_first_not_of('0'); result=p==std::string::npos?"0":result.substr(p); }
        else if(!width && fmt[i]=='d') {
#ifdef DSIM_WIDE_VALUES
            if(value.w>64)width=int(format(V::ones(value.w),'d').size());else
#endif
            width=int(std::to_string(mask(value.w)).size());
            if(is_signed) {
                int field_bits=std::max(32,value.w);
                auto minimum=binary_op<Binary::ShiftLeft>(V(1,0,field_bits),V(uint64_t(field_bits-1),0,32),field_bits);
                width=1+int(format(minimum,'d').size());
            }
        }
        if(width>int(result.size())) output<<std::string(width-result.size(),' ');
        output<<result;
    }
    if(newline) output<<'\n';
}
#ifdef DSIM_EXPRESSION_EVENTS_ENABLED
class Sim;
struct EventExpression {
    std::function<V(Sim&)> evaluate;
    std::vector<int> dependencies;
    int edge=0; // 0 change, 1 posedge, 2 negedge, 3 named occurrence.
    bool sample_on_arm=false;
    std::function<V(Sim&)> condition;
    // Heap dereferences are valid only after execution has supplied a receiver.
    bool defer_until_armed=false;
    // Resolve an instance event once on entry, rather than watching the
    // receiver variable. Edges 3/4/5/6 mean occurrence/query change/rise/fall.
    std::function<int(Sim&)> named_source;
    // A container comparison can change and return to the same value during
    // one process activation. Sample its pure operand at each notification;
    // the awakened process still runs through the ordinary Active queue.
    bool sample_on_change=false;
};
#endif
struct Watch { int process,edges; uint64_t generation; };
// VCS-compatible ideal Liberty tristate driver: an unknown disable condition
// drives X even when the data happens to be Z. This is deliberately distinct
// from an expression mux's bitwise merge of two equal Z operands.
inline V tristate(V disabled,V value,int width) {
    int state=disabled.truth();
    return state==1?V::z(width):state==0?value.size(width):V::x(width);
}
// Most nets have one driver. Keep it inline; retain ordered overflow storage
// for multi-driver nets and deep-copy that storage for simulation checkpoints.
class DriverValues {
    bool assigned=false;
    int first_id=0;
    V first;
    std::unique_ptr<std::map<int,V>> extra;
public:
    DriverValues()=default;
    DriverValues(const DriverValues& other):assigned(other.assigned),first_id(other.first_id),first(other.first),
        extra(other.extra?std::make_unique<std::map<int,V>>(*other.extra):nullptr) {}
    DriverValues& operator=(const DriverValues& other) {
        if(this!=&other) {DriverValues copy(other);*this=std::move(copy);}return *this;
    }
    DriverValues(DriverValues&&) noexcept=default;
    DriverValues& operator=(DriverValues&&) noexcept=default;
    V& operator[](int id) {
        if(!assigned) {assigned=true;first_id=id;return first;}
        if(id==first_id)return first;
        if(!extra)extra=std::make_unique<std::map<int,V>>();
        return (*extra)[id];
    }
    // Preserve the stored driver for force/release and later multi-driver
    // promotion, but let an isolated single driver publish its value directly.
    bool assign_single(int id,const V& value) {
        if(extra||(assigned&&id!=first_id))return false;
        assigned=true;first_id=id;first=value;return true;
    }
    V resolved(int width) const {
        if(!assigned)return V::z(width);
        V result=first;
        if(extra)for(const auto& driver:*extra)result=resolve(result,driver.second);
        return result;
    }
};
struct Signal { V value; bool net; bool aliased=false; DriverValues drivers; std::vector<Watch> watches;
#ifdef DSIM_REAL_ENABLED
    int real_width=0;
#endif
#ifdef DSIM_TWO_STATE_ENABLED
    bool two_state=false;
#endif
#ifdef DSIM_MIXED_STATE_ENABLED
    int state_mask=-1;
#endif
};
#ifdef DSIM_COMPACT_GATES
// Internal one-bit gate nets use native V bit planes: 0/1/Z/X=0/1/2/3.
// IDs occupy a separate negative range. A new driver or alias promotes only
// this slot to full resolution; watches retain their original insertion order.
struct CompactSignal {
    std::vector<Watch> watches;
    std::unique_ptr<Signal> fallback;
    uint64_t order=0;
    int driver=0;
    uint8_t value=2,driven_value=2;
    bool driven=false;
    CompactSignal()=default;
    CompactSignal(const CompactSignal& other):watches(other.watches),
        fallback(other.fallback?std::make_unique<Signal>(*other.fallback):nullptr),
        order(other.order),driver(other.driver),value(other.value),driven_value(other.driven_value),driven(other.driven) {}
    CompactSignal& operator=(const CompactSignal& other) {
        if(this!=&other){CompactSignal copy(other);*this=std::move(copy);}return *this;
    }
    CompactSignal(CompactSignal&&) noexcept=default;
    CompactSignal& operator=(CompactSignal&&) noexcept=default;
};
#endif
// Each Liberty storage element owns both state variables: simultaneous clear /
// preset may deliberately make them noncomplementary. Z is not a stored value.
struct GateState {
    uint8_t q=2,qn=2,pending_q=2,pending_qn=2,clock=2,clear=2,preset=2,data=2;
    bool initialized=false;
    int commit=-1,sample=-1;
    V value(bool inverse=false) const { auto bit=inverse?qn:q; return bit<2?V(bit):V::x(1); }
    bool pending() const { return q!=pending_q || qn!=pending_qn; }
    static uint8_t logic(V value) { return value.b ? 2 : uint8_t(value.a&1); }
    static uint8_t invert(uint8_t old) { return old<2?uint8_t(old^1):2; }
    static uint8_t merge(uint8_t a,uint8_t b) { return a==b?a:2; }
    static uint8_t conflict(char action,uint8_t old) {
        return action=='L'?0:action=='H'?1:action=='N'?old:
               action=='T'?invert(old):2;
    }
    void capture(bool latch,V control,V next,V reset,V set,char both1,char both2) {
        auto c=logic(control),d=logic(next),r=logic(reset),s=logic(set);
        bool changed=!initialized || clock!=c || clear!=r || preset!=s || (latch && data!=d);
        int old=clock;
        int mode=latch ? (c==1?1:c==0?0:2) :
                 old==0 && c==1 ? 1 : ((old==0 && c==2)||(old==2 && c==1)) ? 2 : 0;
        clock=c; clear=r; preset=s; data=d; initialized=true;
        if(!changed) return;
        // A hold/no-change must preserve an earlier pending capture/reset,
        // including a falling edge reached via #0 before NBA is applied.
        const auto hold_q=pending_q,hold_qn=pending_qn;
        uint8_t normal_q=mode==1?d:mode==2?merge(hold_q,d):hold_q;
        uint8_t normal_qn=mode==1?invert(d):mode==2?merge(hold_qn,invert(d)):hold_qn;
        bool first=true;
        for(int a=0;a<=1;++a) for(int b=0;b<=1;++b) {
            if(r<2 && r!=a) continue;
            if(s<2 && s!=b) continue;
            uint8_t v=a && b?(both1=='N'?hold_q:conflict(both1,q)):a?0:b?1:normal_q;
            uint8_t n=a && b?(both2=='N'?hold_qn:conflict(both2,qn)):a?1:b?0:normal_qn;
            pending_q=first?v:merge(pending_q,v);
            pending_qn=first?n:merge(pending_qn,n); first=false;
        }
    }
    bool apply() { bool changed=pending(); q=pending_q; qn=pending_qn; return changed; }
};

// Generic RTL closures live in a separate owned table. Compiled gate processes
// share a handler and carry only a cell index, rather than a heap closure each.
enum class WaitKind : uint8_t { Unbound,Dynamic,Fixed };
#ifdef DSIM_DYNAMIC_FORK_ENABLED
struct ForkFrame {
    std::map<int,int> processes,groups,waits,targets;
};
// Metadata is immutable once published. Values and watches belong to Sim,
// so ordinary checkpoint copies preserve values without breaking sharing.
struct ActivationFrame {
    std::shared_ptr<const ActivationFrame> parent;
    std::map<int,int> signals;
};
#endif
#ifdef DSIM_SHARED_TASKS_ENABLED
struct TaskContinuation {
    uint32_t payload;
    std::shared_ptr<const ForkFrame> fork_frame;
    std::shared_ptr<const ActivationFrame> activation;
    size_t activation_level;
    int location;
};
#endif
struct Process {
    uint64_t generation=0; uint32_t handler=UINT32_MAX,payload=0;
    bool queued=false,waiting=false; WaitKind wait_kind=WaitKind::Unbound;
    // Fits the existing process padding; checkpoint copies own the cache.
    int32_t last_wait_site=-1;
#ifdef DSIM_RANDOM_ENABLED
    uint64_t random_state=1;
#endif
#ifdef DSIM_PROCESS_HANDLES_ENABLED
    int handle_object=-1;
#ifdef DSIM_PROCESS_LIFETIME_ENABLED
    int lifecycle=1,handle_dependency=-1;
#endif
#endif
#ifdef DSIM_PROCESS_CONTROL_ENABLED
    uint64_t control_epoch=0;
    int transfer=-1,location=-1;
#endif
#ifdef DSIM_DYNAMIC_FORK_ENABLED
    std::shared_ptr<const ForkFrame> fork_frame=nullptr;
    std::shared_ptr<const ActivationFrame> activation=nullptr;
    size_t activation_level=0;
#endif
#ifdef DSIM_SHARED_TASKS_ENABLED
    std::vector<TaskContinuation> task_calls;
    bool task_transfer=false;
#endif
};
// A bounded-backlog FIFO keeps storage across delta cycles and ring wraparound.
// Only a generated process PC may claim that a failed step precedes all
// effects of its next instruction. An arbitrary callback/function cannot.
struct InstructionBudgetExhausted : std::runtime_error {
    InstructionBudgetExhausted():std::runtime_error("event/instruction limit exceeded (execution budget exhausted; a zero-delay loop is one possible cause)") {}
};
#ifdef DSIM_PROCESS_LIFETIME_ENABLED
struct ProcessTermination {};
#endif
#ifdef DSIM_TERMINATION_UNWIND_ENABLED
// Simulation control crosses function/lambda boundaries while preserving RAII.
struct SimulationTermination {};
#ifdef DSIM_STOP_ENABLED
struct SimulationStopBarrier {};
#endif
#endif
struct Ready { int process; bool wake;
#ifdef DSIM_MASKED_COMB_REGION_ENABLED
    uint8_t comb_members=0;
    uint16_t comb_mask=0;
#endif
#ifdef DSIM_SDF_JOBS_ENABLED
    bool sdf_job=false;
#endif
#ifdef DSIM_EVENT_NBA_ENABLED
    bool event_nba=false;
#endif
#ifdef DSIM_EXPRESSION_EVENTS_ENABLED
    bool expression=false;
#endif
#ifdef DSIM_PROCESS_CONTROL_ENABLED
    uint64_t control_epoch=0;
#endif
    bool resume=false; // Dispatch was already charged before the interruption.
};
class ReadyQueue {
    std::vector<Ready> storage;
    size_t first=0,count=0;
public:
    bool empty() const { return count==0; }
#ifdef DSIM_SCHEDULING_STATS
    uint64_t pushes=0,pops=0;
#endif
    Ready front() const {return storage[first];}
    void push(Ready event) {
#ifdef DSIM_SCHEDULING_STATS
        ++pushes;
#endif
        if(count==storage.size())grow();
        storage[(first+count)&(storage.size()-1)]=event; ++count;
    }
private:
    // Allocation and ring linearization are rare; keep them out of the hot
    // enqueue path so the compiler can inline the ordinary append.
    __attribute__((noinline)) void grow() {
        std::vector<Ready> grown(storage.empty()?16:storage.size()*2);
        for(size_t i=0;i<count;++i)grown[i]=storage[(first+i)&(storage.size()-1)];
        storage.swap(grown);first=0;
    }
public:
    Ready pop() {
#ifdef DSIM_SCHEDULING_STATS
        ++pops;
#endif
        Ready event=storage[first]; first=(first+1)&(storage.size()-1); --count; return event;
    }
    void prepend(Ready event) {
#ifdef DSIM_SCHEDULING_STATS
        ++pushes;
#endif
        if(count==storage.size())grow();
        first=(first+storage.size()-1)&(storage.size()-1);storage[first]=event;++count;
    }
    void swap(ReadyQueue& other) {
        storage.swap(other.storage); std::swap(first,other.first); std::swap(count,other.count);
    }
};
#ifdef DSIM_PATH_ENABLED
#ifndef DSIM_TIMING_ENABLED
#error DSIM_PATH_ENABLED requires DSIM_TIMING_ENABLED
#endif
struct PathStamp {
    uint64_t time=0;
    uint8_t before=2,after=2;
    bool valid=false;
};
#endif
class Sim {
#ifdef DSIM_FILE_IO_ENABLED
    struct FileHandle {
        std::string path;
        int64_t position=0;
        bool readable=false,writable=false,append=false,eof=false;
        std::vector<unsigned char> pushed;
    };
    std::map<std::string,std::shared_ptr<std::string>> file_images;
    std::map<uint32_t,FileHandle> file_fd,file_mcd;
#endif
#ifdef DSIM_MEMORY_IO_ENABLED
    std::map<std::string,std::string> memory_file_overlay;
#endif
#ifdef DSIM_FORCE_ENABLED
    struct ForcedValue {int owner;V value;};
    std::map<int,ForcedValue> forced_values;
    bool updating_force=false;
#endif
#ifdef DSIM_PROPERTY_ENABLED
    // Lazily retain the value before the first write in a time slot. This is
    // preponed sampling, independent of Active/NBA evaluation order.
    std::map<int,V> property_samples;
    std::set<int> property_sampled_signals;
    std::map<int,std::vector<int>> property_disables;
    std::vector<int> property_observed_sites;
    ReadyQueue property_reactive;
    bool property_reacting=false;
    struct PropertySample {
        int kind,depth;
        std::function<V(Sim&)> value;
        std::function<bool(Sim&)> gate;
        V initial,result;
        std::vector<V> history;
        size_t cursor=0;
    };
    struct PropertyStage {int delay;std::function<bool(Sim&)> value;};
    struct PropertyAttempt {size_t stage;int remaining;};
    struct PropertySite {
        int clock,edges,process,delay,kind;
        std::function<bool(Sim&)> antecedent,consequent,disable;
        bool pending=false,clock_pending=false;
        std::vector<bool> results;
        std::vector<PropertySample> samples;
        std::vector<PropertyStage> stages;
        std::vector<PropertyAttempt> attempts;
#ifdef DSIM_PROPERTY_ANTECEDENT_ENABLED
        size_t antecedent_stages=0;
#endif
    };
    std::vector<PropertySite> property_sites;
    std::map<int,std::vector<int>> property_clocks;
#ifdef DSIM_CLOCKING_ENABLED
    struct ClockingInput {int signal;std::function<V(Sim&)> sample;};
    struct ClockingWait {int process;uint64_t generation,remaining;};
    struct ClockingDrive {std::vector<Part> parts;V value;uint64_t skew;};
    struct ClockingSite {
        int clock,edges;bool pending=false;uint64_t tick=UINT64_MAX;
        std::vector<ClockingInput> inputs;
        std::vector<ClockingWait> waiters;
        std::vector<ClockingDrive> drives;
    };
    std::vector<ClockingSite> clocking_sites;
    std::map<int,std::vector<int>> clocking_clocks;
    void schedule_clocking_drive(ClockingDrive drive) {
        if(!drive.skew)property_nba.push_back({0,Nba::Parts,std::move(drive.value),std::move(drive.parts)});
        else schedule_nba({0,Nba::Parts,std::move(drive.value),std::move(drive.parts)},drive.skew,true);
    }
    void observe_clockings() {
        for(auto& site:clocking_sites)if(site.pending) {
            site.pending=false;site.tick=now;
            for(auto& input:site.inputs)set(input.signal,input.sample(*this));
            auto drives=std::move(site.drives);site.drives.clear();
            for(auto& drive:drives)schedule_clocking_drive(std::move(drive));
            std::vector<ClockingWait> waiting;
            for(auto wait:site.waiters) {
                auto& process=processes.at(size_t(wait.process));
                if(!process.waiting||process.generation!=wait.generation)continue;
                if(--wait.remaining)waiting.push_back(wait);
                else {process.waiting=false;enqueue_property(wait.process);}
            }
            site.waiters=std::move(waiting);
        }
    }
#endif
    void property_changed(int id,const V& old,const V& value) {
        if(property_sampled_signals.count(id))property_samples.emplace(id,old);
        const int a=old.bit(0),b=value.bit(0);
        const int edges=4|(((a==0&&b!=0)||(a>=2&&b==1))?1:0)|(((a==1&&b!=1)||(a>=2&&b==0))?2:0);
#ifdef DSIM_CLOCKING_ENABLED
        auto clocking=clocking_clocks.find(id);
        if(clocking!=clocking_clocks.end())for(int index:clocking->second) {
            auto& site=clocking_sites[size_t(index)];if(site.edges&edges) {
                if(site.pending||site.tick==now)throw std::runtime_error("multiple clocking edges in one time slot are not supported yet");
                site.pending=true;
            }
        }
#endif
        // Unsampled disable iff is asynchronous: even a pulse entirely between
        // clock ticks cancels an outstanding nonoverlapped attempt.
        auto disabling=property_disables.find(id);
        if(disabling!=property_disables.end())for(int index:disabling->second) {
            auto& site=property_sites[size_t(index)];
            if(site.disable(*this)){site.pending=false;site.attempts.clear();}
        }
        auto clocks=property_clocks.find(id);
        if(clocks!=property_clocks.end())for(int index:clocks->second) {
            auto& site=property_sites[size_t(index)];
            if((site.edges&edges)&&!site.clock_pending) {
                site.clock_pending=true;property_observed_sites.push_back(index);
            }
        }
    }
    bool properties_pending() const {
#ifdef DSIM_CLOCKING_ENABLED
        for(const auto& site:clocking_sites)if(site.pending)return true;
#endif
        return !property_observed_sites.empty();
    }
    void prepare_property_samples(PropertySite& site) {
        // Every occurrence advances on its clock, even when an antecedent
        // short-circuits or disable iff aborts the current attempt.
        for(auto& sample:site.samples) {
            const V current=sample.value(*this);
            const V previous=sample.history.size()<size_t(sample.depth)?sample.initial:sample.history[sample.cursor];
            if(sample.kind==0)sample.result=current;
            else if(sample.kind==1)sample.result=previous;
            else if(sample.kind==2)sample.result=V(current.bit(0)==1&&previous.bit(0)!=1);
            else if(sample.kind==3)sample.result=V(current.bit(0)==0&&previous.bit(0)!=0);
            else sample.result=V(sample.kind==4?current.same(previous):!current.same(previous));
            if(sample.kind&&sample.gate(*this)) {
                if(sample.history.size()<size_t(sample.depth))sample.history.push_back(current);
                else {sample.history[sample.cursor]=current;sample.cursor=(sample.cursor+1)%size_t(sample.depth);}
            }
        }
    }
    void observe_properties() {
#ifdef DSIM_CLOCKING_ENABLED
        observe_clockings();
#endif
        auto sites=std::move(property_observed_sites);property_observed_sites.clear();
        for(int index:sites) {
            auto& site=property_sites[size_t(index)];
            if(!site.clock_pending)continue;
            site.clock_pending=false;
            prepare_property_samples(site);
            if(site.kind==0)continue;
            if(site.disable(*this)){site.pending=false;site.attempts.clear();continue;}
            const bool antecedent=site.antecedent(*this);
            auto result=[&](bool pass,bool vacuous=false) {
                // Match the VCS default: vacuous successes do not run a
                // pass/cover action. Coverage also ignores failed attempts.
                if(vacuous||(site.kind==3&&!pass))return;
                site.results.push_back(pass);enqueue_property(site.process);
            };
            if(!site.stages.empty()) {
                // One independent attempt per matching antecedent. Advance old
                // attempts before starting this clock's attempt. ##0 checks
                // every following stage in the same sampled time slot.
                auto advance=[&](PropertyAttempt& attempt) {
                    while(!attempt.remaining) {
                        if(!site.stages[attempt.stage].value(*this)){
#ifdef DSIM_PROPERTY_ANTECEDENT_ENABLED
                            // A failed premise is vacuous. Once the complete
                            // antecedent matched, failures belong to the consequent.
                            if(attempt.stage>=site.antecedent_stages)
#endif
                                result(false);
                            return false;
                        }
                        if(++attempt.stage==site.stages.size()){result(true);return false;}
                        attempt.remaining=site.stages[attempt.stage].delay;
                    }
                    return true;
                };
                size_t kept=0;
                for(auto attempt:site.attempts) {
                    if(attempt.remaining)--attempt.remaining;
                    if(advance(attempt))site.attempts[kept++]=attempt;
                }
                site.attempts.resize(kept);
                if(antecedent) {
                    PropertyAttempt attempt{0,site.stages.front().delay};
                    if(advance(attempt))site.attempts.push_back(attempt);
                }
                continue;
            }
            const bool consequent=site.consequent(*this);
            if(site.pending){result(consequent);site.pending=false;}
            if(!antecedent)result(true,true);
            else if(site.delay)site.pending=true;
            else result(consequent);
        }
    }
#endif
#ifdef DSIM_ASSOCIATIVE_ARRAYS_ENABLED
    struct AssociativeKey {
        // Integral inputs have already been converted to the declared key type.
        // Preserve every limb and the sign, including in checkpoint copies.
        V integral;bool negative=false;
        bool object_key=false;uint64_t object_identity=0;
#ifdef DSIM_STRING_ENABLED
        std::shared_ptr<const std::string> text;
#endif
        bool operator<(const AssociativeKey& other) const {
#ifdef DSIM_STRING_ENABLED
            if(bool(text)!=bool(other.text))return bool(text)<bool(other.text);
            if(text)return text_order(*text,*other.text)<0;
#endif
            if(object_key!=other.object_key)return object_key<other.object_key;
            if(object_key)return object_identity<other.object_identity;
            if(negative!=other.negative)return negative;
#ifdef DSIM_WIDE_VALUES
            if(integral.w>64||other.integral.w>64) {
                auto word=[](const AssociativeKey& key,size_t i) {
                    const size_t words=size_t((key.integral.w+63)/64);
                    if(i>=words)return key.negative?~uint64_t(0):uint64_t(0);
                    auto bits=key.integral.word_a(i);
                    if(key.negative&&i==words-1)bits|=~mask((key.integral.w-1)%64+1);
                    return bits;
                };
                for(size_t i=size_t((std::max(integral.w,other.integral.w)+63)/64);i--;) {
                    const auto a=word(*this,i),b=word(other,i);if(a!=b)return a<b;
                }
                return false;
            }
#endif
            const auto a=integral.a|(negative?~mask(integral.w):0);
            const auto b=other.integral.a|(other.negative?~mask(other.integral.w):0);
            return a<b;
        }
    };
    // Each map owns its subarrays. Empty branches remain existing outer
    // elements until the parent key is deleted, and checkpoint copies are deep.
    struct AssociativeArray:std::map<AssociativeKey,V> {
        std::map<AssociativeKey,AssociativeArray> children;
#ifdef DSIM_QUEUES_ENABLED
        std::vector<V> queue;
#endif
    };
    struct AssociativeRef {
        int signal,dependency,object=-1,width=0;size_t field=0;bool unsigned_key=false,class_key=false,explicit_key_type=false;
        std::vector<AssociativeKey> path;
        AssociativeRef(int id):signal(id),dependency(id) {}
    };
#endif
#ifdef DSIM_OBJECTS_ENABLED
#ifdef DSIM_OBJECT_SCALAR_REFS_ENABLED
    struct ObjectScalarRef {size_t object,field;int type,dependency;};
    std::map<std::pair<size_t,size_t>,int> object_scalar_signals;
    std::map<int,ObjectScalarRef> object_scalar_references;
#endif
  #ifdef DSIM_QUEUES_ENABLED
    struct ObjectQueueRef {size_t object,field;int dependency;};
#ifdef DSIM_OBJECT_ARRAY_REFS_ENABLED
    std::map<std::pair<size_t,size_t>,int> object_array_signals;
    std::map<int,ObjectQueueRef> object_array_references;
    const ObjectQueueRef* object_array_reference_view(int logical) const {
        auto found=object_array_references.find(dynamic_signal(logical));
        return found==object_array_references.end()?nullptr:&found->second;
    }

#endif
  #endif
  #ifdef DSIM_CONSTRAINT_ENABLED
    struct RandomCycle {std::string constraints;std::vector<V> used;};
  #endif
    // Handles are stable indices, so copying a Sim for checkpoint/rollback also
    // copies the heap while preserving aliases inside that simulation state.
    struct Object {int type;std::vector<V> fields;std::vector<int> bases;
#ifdef DSIM_PROCESS_HANDLES_ENABLED
        int process=-2; // -2: ordinary object; -1: completed incarnation detached on slot reuse.
        uint64_t process_random=1;
#ifdef DSIM_PROCESS_LIFETIME_ENABLED
        int process_state=0;
#endif
#endif
        std::set<size_t> assigned_constants;
#ifdef DSIM_QUEUES_ENABLED
        std::map<size_t,std::vector<V>> queues;
#endif
#ifdef DSIM_CONSTRAINT_ENABLED
        uint64_t random_state=1;
        bool random_enabled=true;
        std::map<size_t,bool> random_modes;
        std::map<size_t,RandomCycle> random_cycles;
        bool constraints_enabled=true;
        std::map<std::string,bool> constraint_modes;
#endif
#ifdef DSIM_ASSOCIATIVE_ARRAYS_ENABLED
        std::map<size_t,AssociativeArray> associative;
#endif
    };
    std::vector<Object> objects;
#ifdef DSIM_OBJECT_FORMAT_ENABLED
    struct ObjectPrintField {
        std::string name;size_t field;int signal;char kind;bool is_signed;
        std::vector<int> axes;std::vector<std::pair<V,std::string>> enumerators;
    };
    struct ObjectPrintType {std::string name;std::vector<ObjectPrintField> fields;};
    std::map<int,std::shared_ptr<const ObjectPrintType>> object_print_types;
#endif
#if defined(DSIM_ASSOCIATIVE_ARRAYS_ENABLED) && defined(DSIM_STRING_ENABLED)
    std::set<std::pair<int,size_t>> object_string_associatives;
#endif
#ifdef DSIM_COVERAGE_ENABLED
    struct CoverageBin {
        std::string name;int kind;bool expand,is_default;
        std::vector<std::pair<int64_t,int64_t>> ranges;
    };
    struct CoveragePoint {
        int width;bool sign;int weight,goal,least,automatic;
        std::vector<CoverageBin> bins;
        std::vector<int> cross;
    };
    struct CoverageType {
        bool per_instance,merge;int goal;std::vector<CoveragePoint> points;
        std::function<void(Sim&,V,V)> sample;
    };
    struct CoverageObject {
        int type;V owner;bool enabled=true;std::string name;
        std::vector<std::vector<uint64_t>> hits;
    };
    std::map<int,CoverageType> coverage_types;
    std::map<size_t,CoverageObject> coverage_objects;
#endif
#endif
#ifdef DSIM_IPC_ENABLED
    struct IpcMessage {V value;std::string type;};
    struct IpcTicket {int process;uint64_t generation;};
    struct IpcObject {
        int kind;int64_t count;size_t bound;
        std::deque<IpcMessage> messages;
        std::deque<IpcTicket> readers,writers;
    };
    struct IpcRequest {
        size_t object;int operation;uint64_t generation;V value;std::string type;
        std::vector<V> captures;bool ready=false;
    };
    std::map<size_t,IpcObject> ipc_objects;
    std::map<int,IpcRequest> ipc_requests;
    size_t ipc_cancellation_depth=0;
    std::set<size_t> ipc_cancelled_objects;
    bool ipc_live(const IpcTicket& ticket) const {
        auto found=ipc_requests.find(ticket.process);
        return found!=ipc_requests.end()&&!found->second.ready&&found->second.generation==ticket.generation&&
            processes.at(size_t(ticket.process)).generation==ticket.generation;
    }
    void ipc_complete(int id,V value=V()) {
        auto& request=ipc_requests.at(id);request.value=std::move(value);request.ready=true;
        auto& process=processes.at(size_t(id));
        if(process.waiting){process.waiting=false;enqueue(id);}
    }
    void ipc_drain(IpcObject& object) {
        for(;;) {
            while(!object.readers.empty()&&!ipc_live(object.readers.front()))object.readers.pop_front();
            while(!object.writers.empty()&&!ipc_live(object.writers.front()))object.writers.pop_front();
            if(object.kind==2) {
                // An unsatisfied large request must not prevent a later get
                // from obtaining available keys. Preserve arrival order among
                // requests that can currently complete (including get(0)).
                bool completed=false;
                for(auto it=object.readers.begin();it!=object.readers.end();) {
                    if(!ipc_live(*it)){it=object.readers.erase(it);continue;}
                    const int id=it->process;const int64_t count=int32_t(ipc_requests.at(id).value.a);
                    if(count>object.count){++it;continue;}
                    object.count-=count;it=object.readers.erase(it);ipc_complete(id);completed=true;
                }
                if(!completed)return;
                continue;
            }
            if(!object.readers.empty()&&!object.messages.empty()) {
                int id=object.readers.front().process;auto& request=ipc_requests.at(id);
                if(request.type!=object.messages.front().type)throw std::runtime_error("mailbox get/peek message type mismatch");
                V value=object.messages.front().value;
                if(request.operation==1)object.messages.pop_front();
                object.readers.pop_front();ipc_complete(id,std::move(value));continue;
            }
            if(!object.writers.empty()&&(!object.bound||object.messages.size()<object.bound)) {
                int id=object.writers.front().process;auto& request=ipc_requests.at(id);
                object.messages.push_back({request.value,request.type});object.writers.pop_front();ipc_complete(id);continue;
            }
            return;
        }
    }
    void ipc_cancel(int id) {
        auto found=ipc_requests.find(id);if(found==ipc_requests.end())return;
        size_t index=found->second.object;ipc_requests.erase(found);auto& object=ipc_objects.at(index);
        const auto cancelled=[&](const IpcTicket& ticket){return ticket.process==id;};
        object.readers.erase(std::remove_if(object.readers.begin(),object.readers.end(),cancelled),object.readers.end());
        object.writers.erase(std::remove_if(object.writers.begin(),object.writers.end(),cancelled),object.writers.end());
        if(ipc_cancellation_depth)ipc_cancelled_objects.insert(index);else ipc_drain(object);
    }
    void ipc_cancel_end() {
        if(--ipc_cancellation_depth)return;
        auto changed=std::move(ipc_cancelled_objects);ipc_cancelled_objects.clear();
        for(size_t index:changed)ipc_drain(ipc_objects.at(index));
    }
#endif
#ifdef DSIM_AGGREGATE_STORAGE_ENABLED
    struct AggregateType {V initial,mask;};
    std::map<int,AggregateType> dynamic_aggregate_types;
    std::map<std::pair<int,size_t>,AggregateType> object_aggregate_types;
    static V aggregate_element(V value,const AggregateType& type) {
#ifdef DSIM_MIXED_STATE_ENABLED
        return masked_two_state_value(std::move(value),type.mask);
#else
        return value;
#endif
    }
#endif
#ifdef DSIM_DYNAMIC_ARRAYS_ENABLED
    std::map<int,std::vector<V>> dynamic_arrays;
#ifdef DSIM_QUEUE_REF_LIMITS_ENABLED
    // A ref formal may be unbounded while its actual queue remains bounded.
    std::map<int,int> queue_reference_limits;
#endif
    std::set<int> fixed_array_signals;
#ifdef DSIM_ASSOCIATIVE_ARRAYS_ENABLED
    std::map<int,AssociativeArray> associative_arrays;
    std::set<int> unsigned_associative_signals,class_associative_signals;
#ifdef DSIM_ASSOCIATIVE_REFS_ENABLED
    std::map<std::pair<size_t,size_t>,int> object_associative_signals;
    std::map<int,AssociativeRef> associative_reference_views;
#endif
#endif
    std::map<int,uint64_t> dynamic_generations;
    uint64_t dynamic_generation=0;
    std::map<int,uint64_t> dynamic_instances;
    uint64_t dynamic_owner(int physical) {
        auto found=dynamic_instances.find(physical);
        if(found!=dynamic_instances.end())return found->second;
        if(dynamic_generation==UINT64_MAX)throw std::runtime_error("dynamic array generation overflow");
        return dynamic_instances.emplace(physical,++dynamic_generation).first->second;
    }
    int dynamic_signal(int id) const {
#ifdef DSIM_DYNAMIC_FORK_ENABLED
        return activation_signal(id);
#else
        return id;
#endif
    }
#endif
    using Action=std::function<void()>;
    using CompiledAction=void(*)(Sim&,void*,uint32_t);
    struct Handler { CompiledAction run; uint32_t context; };
#ifdef DSIM_SDF_JOBS_ENABLED
    // Dedicated lifetime-sensitive SDF jobs have no PC, dynamic wait generation
    // or suspension site. Their initial positions are interleaved with ordinary
    // processes in registration order; subsequent wakes use the same Active FIFO.
    struct SdfJob {
        uint32_t handler,payload,before_process;
        bool queued=false,waiting=false;
    };
    std::vector<SdfJob> sdf_jobs;
    void enqueue_sdf_job(uint32_t id) {
        auto& job=sdf_jobs[id];
        if(job.queued)return;
        job.queued=true;active.push({int(id),false,true});
    }
    void wake_sdf_job(int encoded) {
        auto id=uint32_t(-int64_t(encoded)-1);
        auto& job=sdf_jobs[id];
        if(!job.waiting)return;
        job.waiting=false;enqueue_sdf_job(id);
    }
#endif
#ifdef DSIM_PATH_ENABLED
    std::vector<PathStamp> path_stamps;
#ifdef DSIM_COMPACT_GATES
    std::vector<PathStamp> compact_path_stamps;
#endif
    void record_path_change(int id,V before,V after) {
#ifdef DSIM_COMPACT_GATES
        auto& stamp=id<0?compact_path_stamps.at(size_t(-int64_t(id)-1)):path_stamps.at(size_t(id));
#else
        auto& stamp=path_stamps.at(size_t(id));
#endif
        stamp={now,uint8_t(before.bit(0)),uint8_t(after.bit(0)),true};
    }
#endif
#ifdef DSIM_COMPACT_GATES
    std::vector<CompactSignal> compact_signals;
    std::vector<uint64_t> signal_orders;
    uint64_t next_signal_order=0;
    static size_t compact_index(int id) {return size_t(-int64_t(id)-1);}
    static V unpack_scalar(uint8_t bits) {return V(bits&1,bits>>1,1);}
    static uint8_t pack_scalar(V value) {return uint8_t((value.a&1)|((value.b&1)<<1));}
    Signal& signal_record(int id) {
        if(id>=0)return signals.at(id);
        auto& c=compact_signals.at(compact_index(id));
        if(!c.fallback) {
            auto record=std::make_unique<Signal>(Signal{unpack_scalar(c.value),true,false,{}, {}});
            if(c.driven)record->drivers[c.driver]=unpack_scalar(c.driven_value);
            c.fallback=std::move(record);
        }
        return *c.fallback;
    }
    std::vector<Watch>& signal_watches(int id) {
        return id<0?compact_signals.at(compact_index(id)).watches:signals.at(id).watches;
    }
    uint64_t signal_order(int id) const {
        return id<0?compact_signals.at(compact_index(id)).order:signal_orders.at(size_t(id));
    }
    void publish(const std::map<int,V>& pending) {
        std::vector<std::pair<int,V>> ordered(pending.begin(),pending.end());
        std::sort(ordered.begin(),ordered.end(),[&](const auto& a,const auto& b){return signal_order(a.first)<signal_order(b.first);});
        for(const auto& update:ordered)set(update.first,update.second);
    }
    void store_driver(int id,int driver,V value) {
        if(id>=0) {auto& s=signals.at(id);s.drivers[driver]=value.size(s.value.w);return;}
        auto& c=compact_signals.at(compact_index(id));
        if(!c.fallback&&(!c.driven||c.driver==driver)) {
            c.driver=driver;c.driven_value=pack_scalar(value);c.driven=true;
        } else signal_record(id).drivers[driver]=value.size(1);
    }
    void publish_compact(int id,CompactSignal& c,uint8_t bits) {
        const uint8_t previous=c.fallback?pack_scalar(c.fallback->value):c.value;
        if(previous==bits)return;
        if(c.fallback)c.fallback->value=unpack_scalar(bits);else c.value=bits;
#ifdef DSIM_CHECKS_ENABLED
        record_check_change(id,unpack_scalar(previous).bit(0),unpack_scalar(bits).bit(0));
#endif
#ifdef DSIM_PATH_ENABLED
        record_path_change(id,unpack_scalar(previous),unpack_scalar(bits));
#endif
#if defined(DSIM_WAVE_ENABLED) || defined(DSIM_PARALLEL_ENABLED)
        const V value=unpack_scalar(bits);
#endif
#ifdef DSIM_WAVE_ENABLED
        record_wave_change(id,value);
#endif
#ifdef DSIM_PARALLEL_ENABLED
        if(resolved_observer) {
            if(speculating)speculative_effects.push_back([observer=resolved_observer,time=now,id,value]{observer(time,id,value);});
            else resolved_observer(now,id,value);
        }
#endif
        if(c.watches.empty())return;
        int a=previous,b=bits;
        bool pos=(a==0&&b!=0)||(a>=2&&b==1);
        bool neg=(a==1&&b!=1)||(a>=2&&b==0);
        int edges=4|(pos?1:0)|(neg?2:0);
        for(const auto& w:c.watches) {
#ifdef DSIM_SDF_JOBS_ENABLED
            if(w.process<0){if(w.edges&edges)wake_sdf_job(w.process);continue;}
#endif
#ifdef DSIM_EVENT_NBA_ENABLED
            if(w.edges==-1){notify_event_nba(w.process,edges);continue;}
#endif
#ifdef DSIM_EXPRESSION_EVENTS_ENABLED
            if(w.edges>=64){queue_expression_wait((w.edges>>6)-1,w.generation);continue;}
#endif
            auto& p=processes[w.process];
            if(!p.waiting||p.generation!=w.generation)continue;
            if(w.edges&edges){
#ifdef DSIM_SELECTION_CHECKS_ENABLED
                flush_selection_reports(w.process);
#endif
                p.waiting=false;enqueue(w.process);}
        }
    }
    void set_compact(int id,V value) {
        auto& c=compact_signals.at(compact_index(id));
        publish_compact(id,c,pack_scalar(value));
    }
#endif
#ifdef DSIM_DYNAMIC_FORK_ENABLED
    // Appending a spawned closure must not move the currently executing one.
    std::deque<Action> actions;
#else
    std::vector<Action> actions;
#endif
    std::vector<std::shared_ptr<void>> contexts;
#ifdef DSIM_COMB_REGION_ENABLED
    // One FIFO token owns an ordered subset of adjacent independent continuous
    // assignments. Each input's immutable subscriber mask is stored in its
    // negative watcher. Separate pending masks preserve notification order.
    struct CombRegion {
        std::vector<int> members;
        Action run;
        uint64_t armed=0;
        std::deque<uint64_t> pending;
        bool expanded=false;
#ifdef DSIM_MASKED_COMB_REGION_ENABLED
        std::function<void(uint64_t)> masked_run;
#endif
    };
    std::vector<CombRegion> comb_regions;
    void issue_comb_region(int id,uint64_t mask) {
        if(!mask)return;
        auto& region=comb_regions[size_t(id)];region.armed&=~mask;
#ifdef DSIM_MASKED_COMB_REGION_ENABLED
        unsigned count=0;
        for(uint64_t remaining=mask;remaining;remaining&=remaining-1) {
            const unsigned bit=unsigned(__builtin_ctzll(remaining));
            ++count;
#else
        for(size_t bit=0;bit<region.members.size();++bit)if(mask&(UINT64_C(1)<<bit)) {
#endif
            auto& p=processes[size_t(region.members[bit])];p.waiting=false;p.queued=true;
        }
#ifdef DSIM_MASKED_COMB_REGION_ENABLED
        Ready event{-1-id,false};event.comb_members=uint8_t(count);event.comb_mask=uint16_t(mask);
        active.push(event);
#else
        region.pending.push_back(mask);
        active.push({-1-id,false});
#endif
    }
    void notify_comb_region(int id) {issue_comb_region(id,comb_regions[size_t(id)].armed);}
#ifdef DSIM_MASKED_COMB_REGION_ENABLED
    void notify_masked_comb_region(int id,uint64_t subscribers) {issue_comb_region(id,comb_regions[size_t(id)].armed&subscribers);}
#endif
    void run_comb_region(int id) {
        auto& region=comb_regions[size_t(id)];
#ifdef DSIM_MASKED_COMB_REGION_ENABLED
        const auto event=active.front();const uint64_t mask=event.comb_mask;
#else
        const auto mask=region.pending.front();
#endif
        const auto full=(UINT64_C(1)<<region.members.size())-1;
#ifdef DSIM_MASKED_COMB_REGION_ENABLED
        const unsigned count=region.masked_run?event.comb_members:unsigned(region.members.size());
        const uint64_t cost=4*count;
        if(!region.expanded&&(region.masked_run||mask==full)&&steps<=limit&&cost<=limit-steps) {
#else
        const uint64_t cost=4*region.members.size();
        if(!region.expanded&&mask==full&&steps<=limit&&cost<=limit-steps) {
#endif
            // Original events each charge one dispatch and three instructions.
            // A near-limit batch takes the original PC path instead.
            active.pop();
#ifndef DSIM_MASKED_COMB_REGION_ENABLED
            region.pending.pop_front();
#endif
            steps+=cost;
#ifdef DSIM_SCHEDULING_STATS
            ++comb_region_runs;
#ifdef DSIM_MASKED_COMB_REGION_ENABLED
            comb_member_runs+=count;
#else
            comb_member_runs+=region.members.size();
#endif
#endif
#ifdef DSIM_MASKED_COMB_REGION_ENABLED
            if(region.masked_run)region.masked_run(mask);else region.run();
#else
            region.run();
#endif
        } else {
            // A budget interruption can leave a member's original PC inside
            // its body. Keep using those closures after any expansion, even
            // when all members later become ready together.
            region.expanded=true;
            active.pop();
#ifndef DSIM_MASKED_COMB_REGION_ENABLED
            region.pending.pop_front();
#endif
            for(size_t bit=region.members.size();bit-->0;)if(mask&(UINT64_C(1)<<bit))
                active.prepend({region.members[bit],false});
#ifdef DSIM_SCHEDULING_STATS
            ++comb_region_expansions;
#endif
        }
    }
#endif
    std::vector<Handler> handlers;
#ifdef DSIM_CHECKS_ENABLED
    using TimingAction=void(*)(Sim&,void*,uint32_t,int,int);
    struct TimingWatch {uint32_t context,payload;TimingAction action;};
    // Signal IDs are dense inside each storage class. Index only watched
    // signals into sparse observer groups; an unwatched change takes O(1).
    std::vector<int32_t> timing_watch_ids;
#ifdef DSIM_COMPACT_GATES
    std::vector<int32_t> compact_timing_watch_ids;
#endif
    std::vector<std::vector<TimingWatch>> timing_watches;
    void record_check_change(int id,int before,int after) {
#ifdef DSIM_COMPACT_GATES
        const auto& ids=id<0?compact_timing_watch_ids:timing_watch_ids;
        const auto index=id<0?compact_index(id):size_t(id);
#else
        const auto& ids=timing_watch_ids;const auto index=size_t(id);
#endif
        if(index>=ids.size()||ids[index]<0)return;
        for(const auto& w:timing_watches[size_t(ids[index])])w.action(*this,contexts.at(w.context).get(),w.payload,before,after);
    }
#endif
#if defined(DSIM_COMPACT_NBA_STORAGE) && !defined(DSIM_WIDE_VALUES) && !defined(DSIM_STRING_ENABLED) && !defined(DSIM_REFERENCE_NBA_STORAGE)
    // Scalar whole-variable NBA payloads need only the bit planes. Parts are
    // uncommon and own separate storage; their width uses the unused target ID.
    struct Nba {
        enum Kind : uint32_t { Assign,Parts,Wake
#ifdef DSIM_NAMED_EVENTS_ENABLED
            ,NamedEvent
#endif
        };
        int signal;Kind kind;uint64_t a,b;
        std::unique_ptr<std::vector<Part>> selected;
        Nba(int id,Kind k,V value,std::vector<Part> parts)
            :signal(k==Parts?value.w:id),kind(k),a(value.a),b(value.b),
             selected(parts.empty()?nullptr:std::make_unique<std::vector<Part>>(std::move(parts))) {}
        Nba(int id,Kind k,uint64_t av,uint64_t bv):signal(id),kind(k),a(av),b(bv) {}
        Nba(const Nba& other):signal(other.signal),kind(other.kind),a(other.a),b(other.b),
            selected(other.selected?std::make_unique<std::vector<Part>>(*other.selected):nullptr) {}
        Nba& operator=(const Nba& other) {if(this!=&other){Nba copy(other);*this=std::move(copy);}return *this;}
        Nba(Nba&&) noexcept=default;
        Nba& operator=(Nba&&) noexcept=default;
        V value() const {return V(a,b,kind==Parts?signal:64);}
        const std::vector<Part>& parts() const {static const std::vector<Part> empty;return selected?*selected:empty;}
    };
#else
    struct Nba { enum Kind : uint8_t { Assign,Parts,Wake
#ifdef DSIM_NAMED_EVENTS_ENABLED
        ,NamedEvent
#endif
    }; int signal; Kind kind; V value; std::vector<Part> parts; };
#endif
#ifdef DSIM_DELAYED_NBA_ENABLED
    struct Timer {
        uint64_t time,order;
        int process;
        bool delayed_nba=false;
#ifdef DSIM_PROCESS_CONTROL_ENABLED
        uint64_t control_epoch=0;
#endif
#ifdef DSIM_CLOCKING_ENABLED
        bool clocking_drive=false;
#endif
    };
#else
    struct Timer { uint64_t time,order; int process;
#ifdef DSIM_PROCESS_CONTROL_ENABLED
        uint64_t control_epoch=0;
#endif
    };
#endif
    struct TimerLater {
        bool operator()(const Timer& a,const Timer& b) const {
            return a.time!=b.time?a.time>b.time:a.order>b.order;
        }
    };
#ifdef DSIM_FORK_JOIN_ENABLED
    struct ForkGroup {
        int parent;
        std::vector<int> children;
        std::vector<bool> completed;
        size_t remaining=0;
        int kind=1;bool released=true;
#ifdef DSIM_DYNAMIC_FORK_ENABLED
        int source=-1;
#endif
#ifdef DSIM_SHARED_TASKS_ENABLED
        uint32_t owner_payload=UINT32_MAX;
#endif
    };
    std::vector<ForkGroup> fork_groups;
#ifdef DSIM_SHARED_TASKS_ENABLED
    struct TaskInvocation {uint32_t parent;int location;};
    std::map<uint32_t,TaskInvocation> task_invocations;
#endif
    std::set<int> fork_waiters;
#ifdef DSIM_DYNAMIC_FORK_ENABLED
    int fork_current_process=-1;
    // Static declaration initializers can call automatic constructors/functions
    // before any simulation process is executing. They own a temporary chain.
    std::shared_ptr<const ActivationFrame> startup_activation;
    size_t startup_activation_level=0;
    std::vector<ForkGroup> fork_templates;
    std::map<int,Action> fork_actions;
    size_t fork_template_waits=0,fork_template_targets=0;
    struct ActivationSlot {
        std::weak_ptr<const ActivationFrame> owner;
        std::map<int,int> signals;
    };
    std::vector<ActivationSlot> activation_slots;
    size_t activation_first_signal=SIZE_MAX;
    std::map<std::pair<size_t,int>,int> activation_watches;
    int activation_signal(int id) const {
        const auto& activation=fork_current_process<0?startup_activation:processes[size_t(fork_current_process)].activation;
        for(auto* frame=activation.get();frame;frame=frame->parent.get()) {
            auto found=frame->signals.find(id);if(found!=frame->signals.end())return found->second;
        }
        return id;
    }
    int fork_reference(int id,std::map<int,int> ForkFrame::*member) const {
        if(fork_current_process<0)return id;
        const auto& frame=processes[size_t(fork_current_process)].fork_frame;
        if(!frame)return id;
        const auto& mapping=frame.get()->*member;auto found=mapping.find(id);
        return found==mapping.end()?id:found->second;
    }
#endif
#endif
#ifdef DSIM_PROCESS_CONTROL_ENABLED
    struct DisableTarget {int process,continuation;std::vector<int> groups;int identity,begin;
#ifdef DSIM_SHARED_TASKS_ENABLED
        uint32_t payload=UINT32_MAX;
#endif
    };
    std::vector<DisableTarget> disable_targets;
    bool stale_process_ready(const Ready& event) const {
#ifdef DSIM_EXPRESSION_EVENTS_ENABLED
        if(event.expression)return false;
#endif
#ifdef DSIM_EVENT_NBA_ENABLED
        if(event.event_nba)return false;
#endif
#ifdef DSIM_SDF_JOBS_ENABLED
        if(event.sdf_job)return false;
#endif
        return event.process>=0&&event.control_epoch!=processes[size_t(event.process)].control_epoch;
    }
    void discard_stale_process_timers() {
        while(!timed.empty()) {
            const auto& event=timed.front();
#ifdef DSIM_DELAYED_NBA_ENABLED
            if(event.delayed_nba)break;
#endif
            if(event.process<0) {
#ifdef DSIM_TIMING_ENABLED
                if(stale_delivery(event.process)){discard_stale_deliveries();continue;}
#endif
                break;
            }
            if(event.control_epoch==processes[size_t(event.process)].control_epoch)break;
            (void)pop_timer();
        }
    }
    void invalidate_process(int id,int continuation=0) {
#ifdef DSIM_PROCESS_LIFETIME_ENABLED
        if(!continuation)complete_process(id,4);
#endif
        auto& process=processes.at(size_t(id));
        if(process.control_epoch==UINT64_MAX||process.generation==UINT64_MAX)throw std::runtime_error("process cancellation epoch overflow");
        ++process.control_epoch;++process.generation;
        process.queued=false;process.waiting=false;process.transfer=continuation;process.location=-1;
        if(!continuation) {
#ifdef DSIM_SHARED_TASKS_ENABLED
            if(!process.task_calls.empty()) {
                process.payload=process.task_calls.front().payload;
                process.fork_frame=process.task_calls.front().fork_frame;
            }
            process.task_calls.clear();process.task_transfer=false;
#endif
#ifdef DSIM_DYNAMIC_FORK_ENABLED
            process.activation.reset();process.activation_level=0;
#endif
        }
        fork_waiters.erase(id);
#ifdef DSIM_IPC_ENABLED
        ipc_cancel(id);
#endif
    }
#endif
    struct WaitRef { int signal,slot; };
    struct WaitSite { int process; size_t first,count; };
    ReadyQueue active,inactive;
    std::vector<Nba> nba,nba_batch;
#ifdef DSIM_PROPERTY_ENABLED
    std::vector<Nba> property_nba;
    void enqueue_property(int id) {
        auto& process=processes.at(size_t(id));if(process.queued)return;
        process.queued=true;Ready ready{id,false};
#ifdef DSIM_PROCESS_CONTROL_ENABLED
        ready.control_epoch=process.control_epoch;
#endif
        property_reactive.push(ready);
    }
#endif
    void queue_nba(Nba event) {
#ifdef DSIM_PROPERTY_ENABLED
        if(property_reacting){property_nba.push_back(std::move(event));return;}
#endif
        nba.push_back(std::move(event));
    }

#ifdef DSIM_EXPRESSION_EVENTS_ENABLED
    struct ExpressionWait {
        EventExpression expression;
        V before;
        int process;
        uint64_t generation=0;
#ifdef DSIM_NAMED_EVENTS_ENABLED
        uint64_t queued_generation=0;
        int named_event=-1;
        std::map<int,int> named_slots;
#endif
        bool queued=false;
    };
    std::vector<ExpressionWait> expression_waits;
    std::map<int,std::vector<int>> expression_sites;
    void queue_expression_wait(int id,uint64_t source_generation=0) {
        auto& wait=expression_waits.at(size_t(id));
#ifdef DSIM_NAMED_EVENTS_ENABLED
        if(wait.expression.named_source&&source_generation!=wait.generation)return;
#endif
        if(wait.expression.defer_until_armed) {
            const auto& process=processes[size_t(wait.process)];
            if(!process.waiting||process.generation!=wait.generation)return;
        }
#ifdef DSIM_NAMED_EVENTS_ENABLED
        if(wait.expression.edge==3||wait.expression.named_source) {
            const auto& process=processes[size_t(wait.process)];
            if(!process.waiting||process.generation!=wait.generation)return;
            // An occurrence belongs to the currently armed wait. A delayed
            // Active job must not deliver an earlier occurrence to a new arm.
            wait.queued_generation=wait.generation;
        }
#endif
        if(wait.expression.sample_on_change){evaluate_expression_wait(id);return;}
        if(wait.queued)return;
        wait.queued=true;
        Ready job{id,false};job.expression=true;active.push(job);
    }
    void evaluate_expression_wait(int id) {
        auto& wait=expression_waits.at(size_t(id));
        wait.queued=false;
        auto& process=processes[size_t(wait.process)];
        if(wait.expression.defer_until_armed&&(!process.waiting||process.generation!=wait.generation))return;
#ifdef DSIM_DYNAMIC_FORK_ENABLED
        const int previous=fork_current_process;fork_current_process=wait.process;
        struct ContextGuard {int& current;int previous;~ContextGuard(){current=previous;}} guard{fork_current_process,previous};
#endif
#ifdef DSIM_NAMED_EVENTS_ENABLED
        if((wait.expression.edge==3||wait.expression.named_source)&&wait.queued_generation!=wait.generation)return;
#endif
        V after;
#ifdef DSIM_NAMED_EVENTS_ENABLED
        if(wait.expression.named_source)after=V(event_triggered(wait.named_event)?1:0,0,1);
        else
#endif
        after=wait.expression.evaluate(*this);
        const int a=wait.before.bit(0),b=after.bit(0);
        const bool changed=!wait.before.same(after);
        const int kind=wait.expression.edge>=4?wait.expression.edge-4:wait.expression.edge;
        bool edge=kind==0?changed:kind==1?
            (a==0&&b!=0)||(a>=2&&b==1):(a==1&&b!=1)||(a>=2&&b==0);
#ifdef DSIM_NAMED_EVENTS_ENABLED
        if(wait.expression.edge==3)edge=true;
#endif
        wait.before=std::move(after);
        if(!edge||!process.waiting||process.generation!=wait.generation)return;
        // Only the event operand is watched. Read the iff condition after an
        // actual edge/value change or occurrence, using four-state truth.
        if(wait.expression.condition&&wait.expression.condition(*this).truth()!=1)return;
#ifdef DSIM_SELECTION_CHECKS_ENABLED
        flush_selection_reports(wait.process);
#endif
        process.waiting=false;enqueue(wait.process);
    }
#endif
#ifdef DSIM_EVENT_NBA_ENABLED
    // Immutable subscriptions are registered before execution. Each issue owns
    // its value, destination addresses, repetition count and source baselines.
    // No process topology or callback referring to a task frame is created here.
    struct EventNbaPending {
        uint64_t remaining;
        V value;
        std::vector<Part> parts;
        std::vector<V> before;
        std::vector<bool> notified;
    };
    struct EventNbaSource {
        EventExpression expression;
        V before;
        int site,offset,mask=0;
        bool dirty=false;
    };
    struct EventNbaSite {
        std::vector<int> sources;
        std::vector<EventNbaPending> pending;
        bool queued=false;
    };
    std::vector<EventNbaSite> event_nba_sites;
    std::vector<EventNbaSource> event_nba_sources;
    void notify_event_nba(int id,int edges) {
        auto& source=event_nba_sources.at(size_t(id));
        if(source.mask&&!(source.mask&edges))return;
        auto& site=event_nba_sites[size_t(source.site)];
        if(source.expression.defer_until_armed&&site.pending.empty())return;
        if(source.mask&&site.pending.empty())return;
        source.dirty=true;
        // A queued occurrence can only belong to issues already present.
        for(auto& issue:site.pending)issue.notified[size_t(source.offset)]=true;
        if(site.queued)return;
        site.queued=true;Ready job{source.site,false};job.event_nba=true;active.push(job);
    }
    void evaluate_event_nba(int id) {
        auto& site=event_nba_sites.at(size_t(id));site.queued=false;
        std::vector<bool> hit(site.pending.size(),false);
        for(int source_id:site.sources) {
            auto& source=event_nba_sources[size_t(source_id)];
            if(!source.dirty)continue;
            source.dirty=false;
            auto& expression=source.expression;
            if(expression.defer_until_armed&&site.pending.empty())continue;
            V after=source.mask?V():expression.evaluate(*this);
            for(size_t i=0;i<site.pending.size();++i) {
                auto& issue=site.pending[i];const auto offset=size_t(source.offset);
                if(!issue.notified[offset])continue;
                issue.notified[offset]=false;
                const auto& before=issue.before[offset];
                const int a=before.bit(0),b=after.bit(0);
                bool edge=source.mask||expression.edge==3||(expression.edge==0?!before.same(after):expression.edge==1?
                    (a==0&&b!=0)||(a>=2&&b==1):(a==1&&b!=1)||(a>=2&&b==0));
                issue.before[offset]=after;
                if(edge&&(!expression.condition||expression.condition(*this).truth()==1))hit[i]=true;
            }
            source.before=std::move(after);
        }
        // Stable issue order also determines same-site NBA insertion order.
        for(size_t i=0;i<site.pending.size();++i)if(hit[i]) {
            auto& issue=site.pending[i];
            if(!--issue.remaining)queue_nba({0,Nba::Parts,std::move(issue.value),std::move(issue.parts)});
            else for(int source_id:site.sources) {
                const auto& source=event_nba_sources[size_t(source_id)];
                if(!source.mask&&source.expression.sample_on_arm)
                    issue.before[size_t(source.offset)]=source.expression.evaluate(*this);
            }
        }
        site.pending.erase(std::remove_if(site.pending.begin(),site.pending.end(),
            [](const EventNbaPending& issue){return !issue.remaining;}),site.pending.end());
    }
#endif
#ifdef DSIM_NAMED_EVENTS_ENABLED
    struct NamedEventState { uint64_t time=0;bool triggered=false; };
    std::map<int,NamedEventState> named_events;
    std::map<int,int> named_event_dependencies;
#ifdef DSIM_EVENT_ALIASES_ENABLED
    std::map<int,std::set<int>> event_alias_dependencies;
#endif
#ifdef DSIM_WAIT_ORDER_ENABLED
    struct OrderedWait {
        std::vector<int> events;
        size_t next=0;
        uint64_t generation=0;
        bool succeeded=false;
    };
    std::map<int,OrderedWait> ordered_waits;
    std::map<int,std::vector<int>> ordered_subscriptions;
    void subscribe_ordered_wait(int site,const std::vector<int>& events) {
        // Subscribe once: a single occurrence cannot consume consecutive
        // duplicate names in the sequence.
        for(int event:std::set<int>(events.begin(),events.end()))
            ordered_subscriptions[event].push_back(site);
        ordered_waits.emplace(site,OrderedWait{events});
    }
    void notify_ordered_waits(int event) {
        auto found=ordered_subscriptions.find(event);
        if(found==ordered_subscriptions.end())return;
        for(int site:found->second) {
            auto& wait=ordered_waits.at(site);
            auto& process=processes[size_t(wait_sites[size_t(site)].process)];
            if(!process.waiting||process.generation!=wait.generation)continue;
            if(wait.events[wait.next]==event) {
                if(++wait.next<wait.events.size())continue;
                wait.succeeded=true;
            } else {
                // Ignore already consumed events. A future event arriving
                // before the next expected event fails the statement.
                if(std::find(wait.events.begin()+wait.next,wait.events.end(),event)==wait.events.end())continue;
                wait.succeeded=false;
            }
#ifdef DSIM_SELECTION_CHECKS_ENABLED
            flush_selection_reports(wait_sites[size_t(site)].process);
#endif
            process.waiting=false;enqueue(wait_sites[size_t(site)].process);
        }
    }
#endif
#endif
#ifdef DSIM_DELAYED_NBA_ENABLED
    std::vector<Nba> delayed_nba;
    std::vector<int> free_delayed_nba;
    void schedule_nba(Nba event,uint64_t dt
#ifdef DSIM_CLOCKING_ENABLED
                      ,bool clocking_drive=false
#endif
                      ) {
        if(!dt){queue_nba(std::move(event));return;}
        if(dt>UINT64_MAX-now)throw std::runtime_error("simulation time overflow");
        if(timer_order==UINT64_MAX)throw std::runtime_error("timer sequence overflow");
        if(free_delayed_nba.empty()&&delayed_nba.size()>=size_t(INT32_MAX))
            throw std::runtime_error("too many pending delayed NBA updates");
        int slot;
        if(free_delayed_nba.empty()){slot=int(delayed_nba.size());delayed_nba.push_back(std::move(event));}
        else {slot=free_delayed_nba.back();free_delayed_nba.pop_back();delayed_nba[size_t(slot)]=std::move(event);}
        Timer timer{now+dt,timer_order++,slot,true};
#ifdef DSIM_CLOCKING_ENABLED
        timer.clocking_drive=clocking_drive;
#endif
        push_timer(timer);
    }
#endif
#ifdef DSIM_TIME_WHEEL_ENABLED
    NearTimerQueue<Timer> timed;
#else
    std::vector<Timer> timed;
#endif
    void push_timer(Timer event) {
#ifdef DSIM_TIME_WHEEL_ENABLED
        timed.push(event,now);
#else
        timed.push_back(event);
#if !defined(DSIM_TIMER_HEAP_ARITY) || DSIM_TIMER_HEAP_ARITY == 2
        std::push_heap(timed.begin(),timed.end(),TimerLater{});
#else
        static_assert(DSIM_TIMER_HEAP_ARITY==4||DSIM_TIMER_HEAP_ARITY==8,"timer heap arity must be 2, 4 or 8");
        size_t hole=timed.size()-1;
        while(hole) {
            const auto parent=(hole-1)/DSIM_TIMER_HEAP_ARITY;
            if(!TimerLater{}(timed[parent],event))break;
            timed[hole]=timed[parent];hole=parent;
        }
        timed[hole]=event;
#endif
#endif
    }
    Timer pop_timer() {
#ifdef DSIM_TIME_WHEEL_ENABLED
        return timed.pop();
#elif !defined(DSIM_TIMER_HEAP_ARITY) || DSIM_TIMER_HEAP_ARITY == 2
        std::pop_heap(timed.begin(),timed.end(),TimerLater{});
        const auto event=timed.back();timed.pop_back();return event;
#else
        const auto event=timed.front(),last=timed.back();timed.pop_back();
        if(timed.empty())return event;
        size_t hole=0;
        while(hole<=(timed.size()-1)/DSIM_TIMER_HEAP_ARITY) {
            const auto first=hole*DSIM_TIMER_HEAP_ARITY+1;
            if(first>=timed.size())break;
            auto best=first;
            const auto end=std::min(first+DSIM_TIMER_HEAP_ARITY,timed.size());
            for(auto child=first+1;child<end;++child)
                if(TimerLater{}(timed[best],timed[child]))best=child;
            if(!TimerLater{}(last,timed[best]))break;
            timed[hole]=timed[best];hole=best;
        }
        timed[hole]=last;return event;
#endif
    }
    uint64_t timer_order=0;
#ifdef DSIM_TIMING_ENABLED
public:
    // Kernel policies, not names of Verilog/VCS path-delay options. A timing
    // annotator must select delays and pulse policy before issuing a request.
    enum class DelayPolicy : uint8_t { ReplacePending, PreserveTransitions };
private:
#ifdef DSIM_SCALAR_TIMING_ENABLED
    // Scalar channels store V::bit(0) codes: 0/1/X/Z = 0/1/2/3.
    // Vector state and payloads are allocated only for wider channels.
    struct DelayedDriver {
        int signal,driver;
        uint64_t generation=0;
        uint32_t wide=UINT32_MAX;
        DelayPolicy policy;
        uint8_t input=2,output=3;
        bool initialized=false;
#ifdef DSIM_CONTINUOUS_DELAY_ENABLED
        uint32_t parts=UINT32_MAX;
#endif
    };
    struct VectorDriver {V input,output;};
    struct Delivery {uint64_t generation;uint32_t channel,payload;};
    std::vector<VectorDriver> vector_drivers;
    std::vector<V> delivery_values;
    std::vector<uint32_t> free_delivery_values;
#else
    struct DelayedDriver {
        int signal,driver;
        DelayPolicy policy;
        V input,output;
        uint64_t generation=0;
        bool initialized=false;
#ifdef DSIM_CONTINUOUS_DELAY_ENABLED
        uint32_t parts=UINT32_MAX;
#endif
    };
    struct Delivery {uint32_t channel;uint64_t generation;V value;};
#endif
    std::vector<DelayedDriver> delayed_drivers;
#ifdef DSIM_PATH_ENABLED
    std::vector<uint32_t> initial_path_drivers;
#endif
    std::map<std::pair<int,int>,uint32_t> delayed_bindings;
    std::vector<Delivery> deliveries;
    std::vector<int> free_deliveries;
#ifdef DSIM_CONTINUOUS_DELAY_ENABLED
    std::vector<std::vector<Part>> continuous_parts;
#ifdef DSIM_CONTINUOUS_VARIABLE_ENABLED
    // Split once at binding time, not on every delayed delivery. Variable
    // destinations have no driver IDs and use ordinary assignment conversion.
    std::vector<std::vector<Part>> continuous_variable_parts;
#endif
    void commit_continuous_or_drive(uint32_t id,V value) {
        const auto& channel=delayed_drivers[id];
        if(channel.parts!=UINT32_MAX) {
#ifdef DSIM_CONTINUOUS_VARIABLE_ENABLED
            if(!continuous_parts[channel.parts].empty())drive_parts(continuous_parts[channel.parts],value);
            if(!continuous_variable_parts[channel.parts].empty())commit_parts(continuous_variable_parts[channel.parts],value);
#else
            drive_parts(continuous_parts[channel.parts],value);
#endif
        }
        else drive(channel.signal,channel.driver,value);
    }
#endif
#ifdef DSIM_SCALAR_TIMING_ENABLED
    static V timing_scalar_value(uint8_t code) {
        return code<2?V(code,0,1):code==2?V::x(1):V::z(1);
    }
    void release_delivery(int slot) {
        const auto& event=deliveries[size_t(slot)];
        if(delayed_drivers[event.channel].wide!=UINT32_MAX) {
            delivery_values[event.payload]=V();
            free_delivery_values.push_back(event.payload);
        }
        free_deliveries.push_back(slot);
    }
    void queue_delivery(uint32_t id,uint32_t payload,uint64_t dt) {
        int slot;Delivery event{delayed_drivers[id].generation,id,payload};
        if(free_deliveries.empty()){slot=int(deliveries.size());deliveries.push_back(event);}
        else {slot=free_deliveries.back();free_deliveries.pop_back();deliveries[size_t(slot)]=event;}
        if(!dt)active.push({-slot-1,false});
        else push_timer({now+dt,timer_order++,-slot-1});
    }
    void check_delivery(const DelayedDriver& channel,uint64_t dt,bool issue) const {
        if(dt>UINT64_MAX-now)throw std::runtime_error("simulation time overflow");
        if(channel.policy==DelayPolicy::ReplacePending&&channel.generation==UINT64_MAX)
            throw std::runtime_error("delayed driver generation overflow");
        if(issue&&dt&&timer_order==UINT64_MAX)throw std::runtime_error("timer sequence overflow");
        if(issue&&free_deliveries.empty()&&deliveries.size()>=size_t(INT32_MAX))
            throw std::runtime_error("too many pending delayed drives");
    }
    void drive_timing_scalar(int id,int driver,uint8_t code) {
#ifdef DSIM_COMPACT_GATES
        if(id<0) {
            auto& slot=compact_signals.at(compact_index(id));
            if(connections_ready&&!slot.fallback&&(!slot.driven||slot.driver==driver)) {
                const uint8_t bits=code<2?code:uint8_t(code^1);
                slot.driver=driver;slot.driven_value=bits;slot.driven=true;
                publish_compact(id,slot,bits);return;
            }
        }
#endif
        drive(id,driver,timing_scalar_value(code));
    }
#endif
    // Negative Ready/Timer process IDs identify delivery slots; ordinary
    // process IDs remain nonnegative. Slots stay owned until consumed/purged.
    bool stale_delivery(int process) const {
        const auto& event=deliveries[size_t(-int64_t(process)-1)];
        return event.generation!=delayed_drivers[event.channel].generation;
    }
    void discard_stale_deliveries() {
        while(!timed.empty()&&timed.front().process<0&&stale_delivery(timed.front().process)) {
            const auto event=pop_timer();
#ifdef DSIM_SCALAR_TIMING_ENABLED
            release_delivery(int(-int64_t(event.process)-1));
#else
            free_deliveries.push_back(int(-int64_t(event.process)-1));
#endif
        }
    }
    void apply_delivery(int process) {
#ifdef DSIM_SCALAR_TIMING_ENABLED
        int slot=int(-int64_t(process)-1);auto event=deliveries[size_t(slot)];
        auto& channel=delayed_drivers[event.channel];
        if(event.generation!=channel.generation){release_delivery(slot);return;}
        if(channel.wide==UINT32_MAX) {
            release_delivery(slot);channel.output=uint8_t(event.payload);
#ifdef DSIM_CONTINUOUS_DELAY_ENABLED
            if(channel.parts!=UINT32_MAX)commit_continuous_or_drive(event.channel,timing_scalar_value(channel.output));
            else
#endif
            drive_timing_scalar(channel.signal,channel.driver,channel.output);
        } else {
            V value=delivery_values[event.payload];release_delivery(slot);
            vector_drivers[channel.wide].output=value;
#ifdef DSIM_CONTINUOUS_DELAY_ENABLED
            commit_continuous_or_drive(event.channel,value);
#else
            drive(channel.signal,channel.driver,value);
#endif
        }
#else
        int slot=int(-int64_t(process)-1);
        auto event=deliveries[size_t(slot)];free_deliveries.push_back(slot);
        auto& channel=delayed_drivers[event.channel];
        if(event.generation!=channel.generation)return;
        channel.output=event.value;
#ifdef DSIM_CONTINUOUS_DELAY_ENABLED
        commit_continuous_or_drive(event.channel,event.value);
#else
        drive(channel.signal,channel.driver,event.value);
#endif
#endif
    }
#endif
    std::vector<WaitSite> wait_sites;
    std::vector<WaitRef> wait_refs;
    std::map<std::pair<int,int>,int> dynamic_watches;
    uint64_t steps=0;
    using Bit=std::pair<int,int>;
    std::map<Bit,int> connection_nodes;
    std::vector<int> connection_parent;
    std::vector<std::vector<Bit>> bit_groups;
    std::map<int,std::vector<std::pair<int,int>>> signal_groups; // signal -> (group, bit)
    bool connections_ready=false;
#ifdef DSIM_PARALLEL_ENABLED
    uint64_t transaction_serial=0,transaction_active=0;
    struct Arrival {uint64_t time,order;int signal,driver;V value;};
    struct ArrivalLater {bool operator()(const Arrival& a,const Arrival& b) const {return a.time!=b.time?a.time>b.time:a.order>b.order;}};
    std::vector<Arrival> arrivals;
    uint64_t arrival_order=0;
    std::function<void(uint64_t,int,V)> resolved_observer;
    std::function<void(uint64_t,const std::string&)> output_sink;
    void receive_inputs() {
        while(!arrivals.empty()&&arrivals.front().time==now) {
            std::pop_heap(arrivals.begin(),arrivals.end(),ArrivalLater{});
            auto event=arrivals.back();arrivals.pop_back();
            if(event.driver<0)set(event.signal,event.value);else drive(event.signal,event.driver,event.value);
        }
    }
#endif
#ifdef DSIM_RANDOM_ENABLED
    // Owned by Sim/Process: ordinary snapshots and parallel transactions copy
    // both streams. Never use a host-global generator or thread_local storage.
    uint32_t legacy_random_state=0;
    uint64_t root_random_state=1;
    int random_process=-1;
    static uint32_t random_next(uint64_t& state) {
        // SplitMix64, with a fixed 32-bit output convention for reproducibility.
        uint64_t value=(state+=UINT64_C(0x9e3779b97f4a7c15));
        value=(value^(value>>30))*UINT64_C(0xbf58476d1ce4e5b9);
        value=(value^(value>>27))*UINT64_C(0x94d049bb133111eb);
        return uint32_t((value^(value>>31))>>32);
    }
    uint64_t& thread_random_state() {
        return random_process<0?root_random_state:processes.at(size_t(random_process)).random_state;
    }
#endif
#ifdef DSIM_PLUSARGS_ENABLED
    std::shared_ptr<const std::vector<std::string>> runtime_plusargs;
#endif
    bool running=false,topology_locked=false,speculating=false;
#ifdef DSIM_PROCESS_LIFETIME_ENABLED
    struct ProcessAwaiter {int process;uint64_t generation,epoch;};
    std::map<int,std::vector<ProcessAwaiter>> process_awaiters;
#endif
#ifdef DSIM_FINAL_ENABLED
    std::vector<int> final_processes;
    bool finalized=false;
#endif
    // A participant captures an owned value and returns a reusable restore
    // action. Shared storage behind process closures must register here.
    std::vector<std::function<Action()>> state_capture;
    std::vector<Action> speculative_effects;
#ifdef DSIM_SELECTION_CHECKS_ENABLED
    struct SelectionReport {int process;std::string message;};
    std::vector<SelectionReport> selection_reports;
    int selection_process=-1;
    void flush_selection_reports(int process) {
        if(selection_reports.empty())return;
#ifndef DSIM_REFERENCE_SELECTION_FLUSH
        erase_selection_reports(process);
    }
    // Most notifications have no deferred diagnostic. Keep the string/vector
    // cleanup out of their register allocation and instruction working set.
    __attribute__((noinline,cold)) void erase_selection_reports(int process) {
#endif
        selection_reports.erase(std::remove_if(selection_reports.begin(),selection_reports.end(),
            [process](const SelectionReport& report){return report.process==process;}),selection_reports.end());
    }
#endif
    Sim(const Sim&)=default;
    Sim& operator=(const Sim&)=default;
    Sim& operator=(Sim&&)=default;
    void structural_change() const {
        if(topology_locked||running)throw std::runtime_error("simulation topology is frozen after checkpoint/start");
    }
#ifdef DSIM_WAVE_ENABLED
    void* wave_context=nullptr;
    void(*wave_change)(void*,uint64_t,int,V)=nullptr;
    void(*wave_tick)(void*,uint64_t)=nullptr;
    void record_wave_change(int id,V value) {
#ifdef DSIM_NAMED_EVENTS_ENABLED
        // Event identities are scheduler state, never declared wave lanes.
        if(named_events.count(id))return;
#endif
#ifdef DSIM_DYNAMIC_FORK_ENABLED
        if(id>=0&&size_t(id)>=activation_first_signal)return;
#endif
        if(!wave_change)return;
        if(!speculating)wave_change(wave_context,now,id,value);
        else speculative_effects.push_back([fn=wave_change,ctx=wave_context,time=now,id,value]{fn(ctx,time,id,value);});
    }
    void record_wave_tick() {
        if(!wave_tick)return;
        if(!speculating)wave_tick(wave_context,now);
        else speculative_effects.push_back([fn=wave_tick,ctx=wave_context,time=now]{fn(ctx,time);});
    }
#endif
    int connection_root(int id) {
        while(connection_parent[id]!=id) {
            connection_parent[id]=connection_parent[connection_parent[id]];
            id=connection_parent[id];
        }
        return id;
    }
    V local_value(int id) const {
#ifdef DSIM_COMPACT_GATES
        if(id<0) {
            const auto& c=compact_signals.at(compact_index(id));
            return c.fallback?c.fallback->drivers.resolved(1):c.driven?unpack_scalar(c.driven_value):V::z(1);
        }
#endif
        const auto& signal=signals.at(id);
        return signal.drivers.resolved(signal.value.w);
    }
    void settle(const std::set<int>& changed) {
        if(!connections_ready) finish_connections();
        std::map<int,V> local,pending;
        auto get_local=[&](int id) {
            auto it=local.find(id);
            if(it==local.end()) it=local.emplace(id,local_value(id)).first;
            return it->second;
        };
        std::set<int> touched;
        for(int id:changed) {
            pending[id]=get_local(id);
            auto it=signal_groups.find(id);
            if(it!=signal_groups.end()) for(auto link:it->second) touched.insert(link.first);
        }
        for(int group:touched) {
            V value=V::z(1);
            for(auto bit:bit_groups[group]) value=resolve(value,slice(get_local(bit.first),bit.second,1));
            for(auto bit:bit_groups[group]) {
                auto it=pending.find(bit.first);
                if(it==pending.end()) it=pending.emplace(bit.first,get(bit.first)).first;
                it->second=replace(it->second,bit.second,1,value);
            }
        }
        // Every driver and aliased bit is resolved before any watcher can run.
#ifdef DSIM_COMPACT_GATES
        publish(pending);
#else
        for(auto& update:pending) set(update.first,update.second);
#endif
    }
    void commit_parts(const std::vector<Part>& parts,V value) {
        std::map<int,V> pending;
        for(auto it_part=parts.rbegin();it_part!=parts.rend();++it_part) {
            auto part=*it_part;
            if(!part.width)continue; // Invalid/unknown selected destination.
#ifdef DSIM_DYNAMIC_ARRAYS_ENABLED
            if(part.dynamic_index>=0||part.dynamic_event) {
                const auto& generations=part.dynamic_event?dynamic_instances:dynamic_generations;
                auto found=generations.find(part.signal);
                if(found!=generations.end()&&found->second==part.dynamic_generation) {
                    if(part.dynamic_event) {
                        if(part.dynamic_index<0) {
                            if(fixed_array_signals.count(part.signal))continue;
                            throw std::runtime_error("nonblocking dynamic array index is unknown or out of range");
                        }
                        (void)dynamic_part(part.signal,V(uint64_t(part.dynamic_index),0,32),part.width);
                    }
                    bool two_state=false;
#ifdef DSIM_TWO_STATE_ENABLED
                    two_state=signals.at(size_t(part.signal)).two_state;
#endif
                    dynamic_write_slice(part.signal,V(uint64_t(part.dynamic_index),0,32),part,value,two_state);
                }
                continue;
            }
#endif
#ifdef DSIM_DYNAMIC_FORK_ENABLED
            part.signal=activation_signal(part.signal);
#endif
            auto it=pending.find(part.signal);
            if(it==pending.end()) it=pending.emplace(part.signal,get(part.signal)).first;
            it->second=replace(it->second,part.lo,part.width,slice(value,part.rhs_lo,part.width));
        }
#ifdef DSIM_COMPACT_GATES
        publish(pending);
#else
        for(auto& update:pending) set(update.first,update.second);
#endif
    }
    template<class Events> void wait_dynamic(int p,const Events& events) {
        auto& proc=processes.at(p);
        if(proc.wait_kind==WaitKind::Fixed)throw std::runtime_error("fixed-sensitive process cannot use dynamic waiting");
        proc.last_wait_site=-1;
        proc.wait_kind=WaitKind::Dynamic;proc.waiting=true; ++proc.generation;
        for(auto [id,edge]:events) {
#ifdef DSIM_COMPACT_GATES
            auto& list=signal_watches(id);
#else
            auto& list=signals.at(id).watches;
#endif
            auto found=dynamic_watches.find({p,id});
            if(found==dynamic_watches.end()) {
                found=dynamic_watches.emplace(std::make_pair(p,id),int(list.size())).first;
                list.push_back({p,0,0});
            }
            auto& watch=list[found->second];
            int mask=edge==0?4:edge==1?1:2;
            watch.edges=watch.generation==proc.generation?watch.edges|mask:mask;
            watch.generation=proc.generation;
        }
    }

public:
#ifdef DSIM_AGGREGATE_STORAGE_ENABLED
    void dynamic_aggregate_type(int id,V initial,V mask){dynamic_aggregate_types[id]={std::move(initial),std::move(mask)};}
    void object_aggregate_type(int type,size_t field,V initial,V mask){object_aggregate_types[{type,field}]={std::move(initial),std::move(mask)};}
#endif
    Sim()=default;
#ifdef DSIM_RANDOM_ENABLED
    void seed_random_process(int id,uint64_t identity) {
        structural_change();
        // Use the compiler's logical process identity, independent of the local
        // worker registration order. Fork creation reseeds from its real parent.
        processes.at(size_t(id)).random_state=UINT64_C(0x9e3779b97f4a7c15)*(identity+1);
    }
    V random_legacy(uint32_t& seed) {
        if(!seed)seed=259341593u;
        seed=seed*69069u+1u;legacy_random_state=seed;
        // Integer form of the IEEE legacy uniform conversion: use the top 23
        // state bits and the correction term. The legacy negative conversion
        // subtracts one at exact integer boundaries; saturate the upper tail
        // before mapping the signed result, avoiding floating overflow/UB.
        const uint32_t top=seed>>9;
        uint64_t scaled=((uint64_t(top)+1)<<9)+(top>>14);
        if(scaled<UINT64_C(0x80000000)&&!(top&16383u))--scaled;
        if(scaled>UINT32_MAX)scaled=UINT32_MAX;
        return V(uint32_t(scaled)^UINT32_C(0x80000000),0,32);
    }
    V random_legacy() {return random_legacy(legacy_random_state);}
    V random_unsigned() {return V(random_next(thread_random_state()),0,32);}
    V random_unsigned(V seed) {
        // The optional seed is an input value; it does not write the actual.
        thread_random_state()=uint32_t(seed.a&~seed.b);
        return random_unsigned();
    }
    V random_range(V maximum,V minimum=V(0,0,32)) {
        uint32_t hi=uint32_t(maximum.a&~maximum.b),lo=uint32_t(minimum.a&~minimum.b);
        if(hi<lo)std::swap(hi,lo);
        const uint64_t span=uint64_t(hi)-lo+1;
        // Rejection avoids modulo bias, including the entire unsigned range.
        const uint64_t limit=(UINT64_C(1)<<32)/span*span;
        uint32_t value;
        do{value=random_next(thread_random_state());}while(uint64_t(value)>=limit);
        return V(lo+uint64_t(value)%span,0,32);
    }
#endif

    uint64_t time_precision_fs=1;
    TimeFormat time_format;
    void set_time_precision(uint64_t fs) {
        if(running||topology_locked||steps||now)throw std::runtime_error("cannot change simulation precision after execution or checkpoint");
        time_exponent(fs);time_precision_fs=fs;time_format.unit_fs=fs;
    }
    uint64_t local_time(uint64_t unit_fs) const {
        if(unit_fs<time_precision_fs||unit_fs%time_precision_fs)throw std::runtime_error("invalid module time unit");
        auto factor=unit_fs/time_precision_fs;
        return now/factor+(now%factor>=factor/2+factor%2);
    }
    void timeformat(int units,int digits,std::string suffix,int width) {
        if(units < -15 || units>0 || digits<0 || digits>15 || width<0 || width>1000)throw std::runtime_error("invalid $timeformat arguments");
        uint64_t fs=1;for(int i=-15;i<units;++i)fs*=10;
        time_format={fs,digits,width,std::move(suffix)};
    }
#ifdef DSIM_PARALLEL_ENABLED
    // Coordinator-only configuration / delivery between worker barriers.
    bool next_event_time(uint64_t& time) {
        if(running||speculating)throw std::runtime_error("event query requires a committed scheduler boundary");
        if(finished)return false;
#ifdef DSIM_TIMING_ENABLED
        discard_stale_deliveries();
#endif
#ifdef DSIM_PROCESS_CONTROL_ENABLED
        discard_stale_process_timers();
#endif
        if(!active.empty()||!inactive.empty()||!nba.empty()){time=now;return true;}
        bool found=false;
        if(!timed.empty()){time=timed.front().time;found=true;}
        if(!arrivals.empty()&&(!found||arrivals.front().time<time)){time=arrivals.front().time;found=true;}
        return found;
    }
    void observe_resolved(std::function<void(uint64_t,int,V)> observer) {
        if(running||speculating)throw std::runtime_error("observer change during execution");
        resolved_observer=std::move(observer);
    }
    void redirect_output(std::function<void(uint64_t,const std::string&)> sink) {
        if(running||speculating)throw std::runtime_error("output sink change during execution");
        output_sink=std::move(sink);
    }
    void deliver_at(uint64_t time,int signal,int driver,V value) {
        if(running||time<now||arrival_order==UINT64_MAX)throw std::runtime_error("invalid parallel input delivery");
#ifdef DSIM_COMPACT_GATES
        (void)get(signal);
#else
        (void)signals.at(signal);
#endif
        arrivals.push_back({time,arrival_order++,signal,driver,value});
        std::push_heap(arrivals.begin(),arrivals.end(),ArrivalLater{});
    }
#endif
    struct PredictionStats { uint64_t attempts=0,commits=0,rollbacks=0,speculative_steps=0,replayed_steps=0; } prediction_stats;
    class Checkpoint {
        friend class Sim;
        const Sim* owner=nullptr;
        std::shared_ptr<const Sim> saved;
        std::vector<Action> participants;
#ifdef DSIM_PARALLEL_ENABLED
        uint64_t transaction_id=0;
#endif
    };
    template<class T> void register_state(std::shared_ptr<T> state) {
        structural_change();
        if(!state)throw std::runtime_error("cannot checkpoint null model state");
        state_capture.push_back([state]{auto saved=*state;return [state,saved]{*state=saved;};});
    }
private:
    Checkpoint save_checkpoint(bool transaction) {
        if(running||speculating)throw std::runtime_error("checkpoint requires a scheduler boundary outside prediction");
#ifdef DSIM_WAVE_ENABLED
        if(wave_context&&!transaction)throw std::runtime_error("waveform checkpoints require predict_until transaction");
#else
        (void)transaction;
#endif
        finish_connections();topology_locked=true;
        Checkpoint cp;cp.owner=this;cp.saved=std::shared_ptr<const Sim>(new Sim(*this));
        for(const auto& capture:state_capture)cp.participants.push_back(capture());
        return cp;
    }
    void load_checkpoint(const Checkpoint& cp) {
        if(running||cp.owner!=this||!cp.saved)throw std::runtime_error("invalid checkpoint owner or scheduler boundary");
        auto stats=prediction_stats;
#ifdef DSIM_PARALLEL_ENABLED
        auto serial=transaction_serial;
#endif
        // Copy before modifying the live kernel, including the mutable lambda
        // captures holding RTL PCs/repeat counters and every pending queue.
        Sim restored(*cp.saved);
        *this=std::move(restored);prediction_stats=stats;
#ifdef DSIM_PARALLEL_ENABLED
        // Tokens stay unique even after restoring an older checkpoint.
        transaction_serial=serial;transaction_active=0;
#endif
        for(const auto& restore:cp.participants)restore();
    }
public:
    Checkpoint checkpoint() {return save_checkpoint(false);}
#ifdef DSIM_OBJECTS_ENABLED
#ifdef DSIM_COVERAGE_ENABLED
    static int64_t coverage_integer(V value,int width,bool sign) {
        const uint64_t raw=value.a&mask(width);
        return sign&&(raw&(uint64_t(1)<<(width-1)))?int64_t(raw)-int64_t(uint64_t(1)<<width):int64_t(raw);
    }
    void add_coverage_type(int type,bool per_instance,bool merge,int goal,std::vector<CoveragePoint> points,std::function<void(Sim&,V,V)> sample) {
        for(size_t p=0;p<points.size();++p) {
            auto& point=points[p];
            if(!point.cross.empty()) {
                size_t count=1;
                for(int source:point.cross) {
                    if(source<0||size_t(source)>=p||!points[size_t(source)].cross.empty())throw std::runtime_error("invalid coverage cross source");
                    size_t bins=0;for(const auto& bin:points[size_t(source)].bins)if(!bin.kind&&!bin.is_default)++bins;
                    if(bins&&count>65536/bins)throw std::runtime_error("automatic coverage cross exceeds 65536 bins");
                    count*=bins;
                }
                point.bins.resize(count,CoverageBin{"cross",0,false,false,{}});continue;
            }
            bool explicit_bins=false;
            for(const auto& bin:point.bins)if(bin.kind==0)explicit_bins=true;
            if(!explicit_bins) {
                const uint64_t domain=uint64_t(1)<<point.width;
                const int64_t first=point.sign?-int64_t(domain/2):0;
                const uint64_t count=std::min(domain,uint64_t(point.automatic));
                for(uint64_t i=0;i<count;++i)point.bins.push_back({"auto["+std::to_string(i)+"]",0,false,false,{{first+int64_t(i*domain/count),first+int64_t((i+1)*domain/count)-1}}});
            }
            std::vector<CoverageBin> bins;
            for(auto bin:point.bins) {
                for(auto range:bin.ranges)if(range.first>range.second)throw std::runtime_error("coverage bin has a descending range: "+bin.name);
                if(!bin.kind&&!bin.is_default)for(const auto& excluded:point.bins)if(excluded.kind)for(auto remove:excluded.ranges) {
                    std::vector<std::pair<int64_t,int64_t>> remaining;
                    for(auto range:bin.ranges) {
                        if(remove.second<range.first||remove.first>range.second)remaining.push_back(range);
                        else {if(range.first<remove.first)remaining.push_back({range.first,remove.first-1});if(range.second>remove.second)remaining.push_back({remove.second+1,range.second});}
                    }
                    bin.ranges=std::move(remaining);
                }
                if(!bin.is_default&&bin.ranges.empty())continue;
                if(bin.expand) {
                    for(auto range:bin.ranges) {
                        if(uint64_t(range.second-range.first)+1>65536||bins.size()+uint64_t(range.second-range.first)+1>65536)throw std::runtime_error("expanded coverage bins exceed 65536");
                        for(int64_t value=range.first;value<=range.second;++value)bins.push_back({bin.name+"["+std::to_string(value)+"]",bin.kind,false,false,{{value,value}}});
                    }
                } else bins.push_back(std::move(bin));
            }
            point.bins=std::move(bins);
        }
        if(!coverage_types.emplace(type,CoverageType{per_instance,merge,goal,std::move(points),std::move(sample)}).second)throw std::runtime_error("duplicate coverage type");
    }
    V coverage_new(int type,V owner,int dependency) {
        const auto& definition=coverage_types.at(type);auto handle=object_new(type,{},dependency);
        CoverageObject object{type,owner};
        for(const auto& point:definition.points)object.hits.emplace_back(point.bins.size(),0);
        coverage_objects.emplace(size_t(handle.a-1),std::move(object));return handle;
    }
    CoverageObject& coverage_object(V handle,int type) {return coverage_objects.at(object_index(handle,type));}
    void coverage_sample(V handle,int type,const std::vector<V>& values,const std::vector<bool>& gates) {
        auto& object=coverage_object(handle,type);if(!object.enabled)return;
        const auto& definition=coverage_types.at(type);
        std::vector<std::vector<size_t>> matched(definition.points.size());
        for(size_t p=0;p<definition.points.size();++p) {
            const auto& point=definition.points[p];
            if(!point.cross.empty()) {
                if(!gates.at(p))continue;
                std::vector<size_t> indices{0};
                for(int source:point.cross) {
                    size_t count=0;for(const auto& bin:definition.points[size_t(source)].bins)if(!bin.kind&&!bin.is_default)++count;
                    std::vector<size_t> next;
                    for(auto prefix:indices)for(auto bin:matched[size_t(source)])next.push_back(prefix*count+bin);
                    indices=std::move(next);
                }
                for(auto index:indices)if(object.hits[p][index]!=UINT64_MAX)++object.hits[p][index];
                continue;
            }
            if(!gates.at(p)||values.at(p).b)continue;
            const auto value=coverage_integer(values[p],point.width,point.sign);
            auto matches=[&](const CoverageBin& bin){for(auto range:bin.ranges)if(value>=range.first&&value<=range.second)return true;return false;};
            bool ignored=false;
            for(const auto& bin:point.bins)if(bin.kind&&matches(bin)) {
                if(bin.kind==2)throw std::runtime_error("illegal coverage bin hit: "+bin.name);
                ignored=true;
            }
            if(ignored)continue;
            size_t regular=0;
            for(size_t b=0;b<point.bins.size();++b)if(!point.bins[b].kind&&!point.bins[b].is_default) {
                if(matches(point.bins[b])){matched[p].push_back(regular);if(object.hits[p][b]!=UINT64_MAX)++object.hits[p][b];}
                ++regular;
            }
        }
    }
    void coverage_invoke(V handle,int type) {
        auto& object=coverage_object(handle,type);if(object.enabled)coverage_types.at(type).sample(*this,handle,object.owner);
    }
    void coverage_event(int type) {
        for(const auto& item:coverage_objects)if(item.second.type==type&&item.second.enabled)coverage_invoke(V(item.first+1,0,64),type);
    }
    void coverage_enable(V handle,int type,bool enabled) {coverage_object(handle,type).enabled=enabled;}
    void coverage_name(V handle,int type,const std::string& name) {coverage_object(handle,type).name=name;}
    static double coverage_score(const CoverageType& type,const std::vector<std::vector<uint64_t>>& hits,int selected=-1) {
        double sum=0,weights=0;
        for(size_t p=0;p<type.points.size();++p) {
            if(selected>=0&&size_t(selected)!=p)continue;
            const auto& point=type.points[p];size_t total=0,covered=0;
            for(size_t b=0;b<point.bins.size();++b)if(!point.bins[b].kind&&!point.bins[b].is_default) {++total;if(hits[p][b]>=uint64_t(point.least))++covered;}
            const double raw=total?100.0*double(covered)/double(total):100.0;
            sum+=(selected>=0?1:point.weight)*raw;weights+=selected>=0?1:point.weight;
        }
        return weights?sum/weights:100.0;
    }
    double coverage_query(V handle,int type,bool instance,int selected=-1) {
        const auto& object=coverage_object(handle,type);const auto& definition=coverage_types.at(type);
        // VCS queries aggregate type hit counts independently of report goals
        // and merge_instances. Without per_instance it exposes no instance data.
        if(instance)return definition.per_instance?coverage_score(definition,object.hits,selected):0.0;
        {
            auto hits=object.hits;for(auto& point:hits)std::fill(point.begin(),point.end(),0);
            for(const auto& item:coverage_objects)if(item.second.type==type)for(size_t p=0;p<hits.size();++p)for(size_t b=0;b<hits[p].size();++b) {
                auto value=item.second.hits[p][b];hits[p][b]=UINT64_MAX-hits[p][b]<value?UINT64_MAX:hits[p][b]+value;
            }
            return coverage_score(definition,hits,selected);
        }

    }
#endif
    V object_new(int type,std::vector<V> fields,int dependency,std::vector<int> bases={}) {
        if(type<0||objects.size()>=1048576)throw std::runtime_error("class object allocation limit exceeded");
        objects.push_back({type,std::move(fields),std::move(bases)});
#ifdef DSIM_CONSTRAINT_ENABLED
        auto high=random_next(thread_random_state());auto low=random_next(thread_random_state());
        objects.back().random_state=(uint64_t(high)<<32)|low;
#endif
        set(dependency,V(get(dependency).a+1,0,64));
        return V(uint64_t(objects.size()),0,64);
    }
#ifdef DSIM_IPC_ENABLED
    static int32_t ipc_count(V value) {
        value=value.size(32);if(value.b)throw std::runtime_error("IPC count contains X/Z");return int32_t(value.a);
    }
    V ipc_new(int type,int kind,V count,int dependency) {
        const int32_t number=ipc_count(count);
        if(kind==1&&number<0)throw std::runtime_error("mailbox bound must not be negative");
        V handle=object_new(type,{},dependency);
        ipc_objects.emplace(size_t(handle.a-1),IpcObject{kind,kind==2?number:0,kind==1?size_t(number):0,{},{},{}});
        return handle;
    }
    IpcObject& ipc_object(V handle,int type) {
        auto found=ipc_objects.find(object_index(handle,type));
        if(found==ipc_objects.end())throw std::runtime_error("invalid IPC object");return found->second;
    }
    struct IpcResult {int status;V value;};
    IpcResult ipc_try(V handle,int type,int operation,V value,const std::string& message_type) {
        auto& object=ipc_object(handle,type);ipc_drain(object);
        if(object.kind==2) {
            int32_t count=ipc_count(value);if(count<0)throw std::runtime_error("semaphore key count must not be negative");
            if(operation==0) {
                if(object.count>INT64_MAX-count)throw std::runtime_error("semaphore key count overflow");
                object.count+=count;ipc_drain(object);return {1,V()};
            }
            if(count>object.count)return {0,V()};object.count-=count;return {1,V()};
        }
        if(operation==3)return {int(object.messages.size()),V()};
        if(operation==0) {
            if(object.bound&&object.messages.size()>=object.bound)return {0,V()};
            object.messages.push_back({std::move(value),message_type});ipc_drain(object);return {1,V()};
        }
        if(object.messages.empty())return {0,V()};
        if(object.messages.front().type!=message_type)return {-1,V()};
        V message=object.messages.front().value;if(operation==1)object.messages.pop_front();
        ipc_drain(object);return {1,std::move(message)};
    }
    // Capture receiver, input and ref selectors exactly once before suspension.
    // All queues/results belong to Sim and are included in checkpoints.
    bool ipc_wait(int id,V handle,int type,int operation,V value,std::string message_type,std::vector<V> captures) {
        auto& object=ipc_object(handle,type);
        if(object.kind==2&&ipc_count(value)<0)throw std::runtime_error("semaphore key count must not be negative");
        auto& process=processes.at(size_t(id));
        if(ipc_requests.count(id))throw std::runtime_error("process already has a pending IPC request");
        if(process.generation==UINT64_MAX)throw std::runtime_error("IPC wait generation overflow");
        ++process.generation;process.wait_kind=WaitKind::Dynamic;process.last_wait_site=-1;
        ipc_requests.emplace(id,IpcRequest{size_t(handle.a-1),operation,process.generation,std::move(value),std::move(message_type),std::move(captures),false});
        (operation==0?object.writers:object.readers).push_back({id,process.generation});ipc_drain(object);
        if(ipc_requests.at(id).ready)return false;
        process.waiting=true;return true;
    }
    V ipc_result(int id) const {
        const auto& request=ipc_requests.at(id);if(!request.ready)throw std::runtime_error("IPC request has not completed");return request.value;
    }
    V ipc_capture(int id,size_t index) const {return ipc_requests.at(id).captures.at(index);}
    void ipc_finish(int id) {ipc_requests.erase(id);}
#endif
    size_t object_index(V handle,int type) const {
        if(handle.w!=64||handle.b||!handle.a||handle.a>objects.size())throw std::runtime_error("null or invalid class object access");
        const size_t index=size_t(handle.a-1);
        if(objects[index].type!=type&&std::find(objects[index].bases.begin(),objects[index].bases.end(),type)==objects[index].bases.end())throw std::runtime_error("class object type mismatch");
        return index;
    }
    int object_type(V handle) const {
        if(handle.w!=64||handle.b||!handle.a||handle.a>objects.size())throw std::runtime_error("null or invalid class object access");
        return objects[size_t(handle.a-1)].type;
    }
    bool object_can_cast(V handle,int type) const {
        if(handle.w!=64||handle.b||handle.a>objects.size())throw std::runtime_error("invalid class handle in $cast");
        if(!handle.a)return true;
        const auto& object=objects[size_t(handle.a-1)];
        return object.type==type||std::find(object.bases.begin(),object.bases.end(),type)!=object.bases.end();
    }
#ifdef DSIM_PROCESS_HANDLES_ENABLED
    V process_self(int type,int dependency) {
        if(random_process<0)throw std::runtime_error("process::self requires an executing process");
        auto& process=processes.at(size_t(random_process));
        if(process.handle_object<0) {
            if(objects.size()>=1048576)throw std::runtime_error("process handle allocation limit exceeded");
            // Acquiring self must not consume the executing process's PRNG stream.
            process.handle_object=int(objects.size());objects.push_back({type,{},{}});
            objects.back().process=random_process;
#ifdef DSIM_PROCESS_LIFETIME_ENABLED
            process.handle_dependency=dependency;
#endif
            set(dependency,V(get(dependency).a+1,0,64));
        }
        return V(uint64_t(process.handle_object)+1,0,64);
    }
    uint64_t& process_random_state(V handle,int type) {
        auto& object=objects.at(object_index(handle,type));
        if(object.process==-2)throw std::runtime_error("invalid native process handle");
        return object.process<0?object.process_random:processes.at(size_t(object.process)).random_state;
    }
    void process_srandom(V handle,int type,V seed) {process_random_state(handle,type)=uint32_t(seed.a&~seed.b);}
#ifdef DSIM_STRING_ENABLED
    V process_get_randstate(V handle,int type) {
        auto state=process_random_state(handle,type);std::string text="DSIM-RNG1:";
        for(int shift=60;shift>=0;shift-=4)text+="0123456789abcdef"[(state>>shift)&15];
        return V::text(text);
    }
    void process_set_randstate(V handle,int type,const V& value) {
        auto& target=process_random_state(handle,type);const auto& text=value.text_value();
        if(text.size()!=26||text.compare(0,10,"DSIM-RNG1:"))throw std::runtime_error("invalid process random state");
        uint64_t state=0;
        for(size_t i=10;i<text.size();++i) {
            const auto c=text[i];unsigned digit=c>='0'&&c<='9'?unsigned(c-'0'):c>='a'&&c<='f'?unsigned(c-'a'+10):16;
            if(digit==16)throw std::runtime_error("invalid process random state");state=(state<<4)|digit;
        }
        target=state;
    }
#endif
    void detach_process_handle(int id) {
        auto& process=processes.at(size_t(id));if(process.handle_object<0)return;
        auto& object=objects.at(size_t(process.handle_object));object.process_random=process.random_state;object.process=-1;
#ifdef DSIM_PROCESS_LIFETIME_ENABLED
        object.process_state=process.lifecycle;
#endif
        process.handle_object=-1;
    }
#ifdef DSIM_PROCESS_LIFETIME_ENABLED
    int process_status(V handle,int type) const {
        const auto& object=objects.at(object_index(handle,type));
        if(object.process==-2)throw std::runtime_error("invalid native process handle");
        if(object.process<0)return object.process_state;
        const auto& state=processes.at(size_t(object.process));
        if(state.lifecycle==0||state.lifecycle==4)return state.lifecycle;
        if(object.process==random_process||state.queued)return 1;
        return state.waiting?2:state.lifecycle;
    }
    void complete_process(int id,int status=0) {
        auto& state=processes.at(size_t(id));
        if(state.lifecycle==0||state.lifecycle==4)return;
        state.lifecycle=status;
        for(auto it=process_awaiters.begin();it!=process_awaiters.end();) {
            auto& list=it->second;list.erase(std::remove_if(list.begin(),list.end(),[&](const ProcessAwaiter& item){return item.process==id;}),list.end());
            if(list.empty())it=process_awaiters.erase(it);else ++it;
        }
        if(state.handle_object<0)return;
        objects.at(size_t(state.handle_object)).process_state=status;
        if(state.handle_dependency>=0)set(state.handle_dependency,V(get(state.handle_dependency).a+1,0,64));
        auto found=process_awaiters.find(state.handle_object);if(found==process_awaiters.end())return;
        auto waiters=std::move(found->second);process_awaiters.erase(found);
        for(const auto& item:waiters) {
            auto& waiter=processes.at(size_t(item.process));
            if(waiter.waiting&&waiter.generation==item.generation&&waiter.control_epoch==item.epoch) {
                waiter.waiting=false;enqueue(item.process);
            }
        }
    }
    bool process_await(V handle,int type,int caller) {
        const int status=process_status(handle,type);if(status==0||status==4)return false;
        auto& waiter=processes.at(size_t(caller));waiter.last_wait_site=-1;waiter.wait_kind=WaitKind::Dynamic;
        waiter.waiting=true;++waiter.generation;
        process_awaiters[int(handle.a-1)].push_back({caller,waiter.generation,waiter.control_epoch});return true;
    }
    void process_kill(V handle,int type) {
        const int status=process_status(handle,type);if(status==0||status==4)return;
        const int target=objects.at(object_index(handle,type)).process;
        disable_fork(target);invalidate_process(target);
        for(size_t group=0;group<fork_groups.size();++group) {
            auto& item=fork_groups[group];
            for(size_t branch=0;branch<item.children.size();++branch)
                if(item.children[branch]==target&&item.remaining&&!item.completed[branch])finish_fork(int(group),branch);
        }
        if(random_process>=0&&processes.at(size_t(random_process)).lifecycle==4)throw ProcessTermination{};
    }
#endif
#endif
    V object_get(V handle,int type,size_t field) const {
        return objects.at(object_index(handle,type)).fields.at(field);
    }
#ifdef DSIM_OBJECT_SCALAR_REFS_ENABLED
    int object_scalar_reference(V handle,int type,size_t field,int dependency,bool two_state,int real_width=0) {
        const auto object=object_index(handle,type);const auto key=std::make_pair(object,field);
        if(auto found=object_scalar_signals.find(key);found!=object_scalar_signals.end())return found->second;
        const auto value=objects.at(object).fields.at(field);
        if(signals.size()>=size_t(INT32_MAX))throw std::runtime_error("too many class scalar references");
        if(activation_first_signal==SIZE_MAX)activation_first_signal=signals.size();
        const int id=int(signals.size());signals.push_back({value,false,false,{},{}});
#ifdef DSIM_TWO_STATE_ENABLED
        signals.back().two_state=two_state;
#else
        (void)two_state;
#endif
#ifdef DSIM_REAL_ENABLED
        signals.back().real_width=real_width;
#else
        (void)real_width;
#endif
#ifdef DSIM_COMPACT_GATES
        if(next_signal_order==UINT64_MAX)throw std::runtime_error("signal order overflow");
        signal_orders.push_back(next_signal_order++);
#endif
#ifdef DSIM_PATH_ENABLED
        path_stamps.emplace_back();
#endif
        object_scalar_signals.emplace(key,id);object_scalar_references.emplace(id,ObjectScalarRef{object,field,type,dependency});return id;
    }
#endif
#ifdef DSIM_OBJECT_FORMAT_ENABLED
    void object_print_type(int type,std::string name,std::vector<ObjectPrintField> fields) {
        structural_change();object_print_types[type]=std::make_shared<const ObjectPrintType>(ObjectPrintType{std::move(name),std::move(fields)});
    }
    const ObjectPrintType& object_print_type(int type) const {
        auto found=object_print_types.find(type);
        if(found==object_print_types.end())throw std::runtime_error("class output type metadata is unavailable");
        return *found->second;
    }
    std::string object_reference_text(V value) const {
        if(!value.a&&!value.b)return "null";
        const auto& name=object_print_type(object_type(value)).name;
        if(name.empty())throw std::runtime_error("class reference type name is not supported yet");
        return "{ ref to class "+name+"}";
    }
    std::string object_field_text(V value,const ObjectPrintField& field) const {
        if(field.kind=='s')return "\""+value.text_value()+"\"";
        if(field.kind=='o')return object_reference_text(value);
#ifdef DSIM_NAMED_EVENTS_ENABLED
        if(field.kind=='e') {
#ifdef DSIM_EVENT_ALIASES_ENABLED
            if(field.signal<0&&!value.a&&!value.b)return "null";
#endif
            return event_triggered(field.signal>=0?field.signal:event_id(value))?"ON":"OFF";
        }
#endif
#ifdef DSIM_REAL_ENABLED
        if(field.kind=='r')return real_format(value.real_value(),'g',6);
#endif
        if(field.kind=='n')for(const auto& enumerator:field.enumerators)
            if(binary_op<Binary::CaseEqual>(value,enumerator.first,1).truth()==1)return enumerator.second;
        if(field.kind=='h') {
            auto text=format(value,'h');auto start=text.find_first_not_of('0');
            return "'h"+(start==std::string::npos?std::string("0"):text.substr(start));
        }
        if(field.kind=='d'||field.kind=='n') {
            std::ostringstream out;display("%0d",{value},false,out,1,{}, {field.is_signed});return out.str();
        }
        throw std::runtime_error("class output field type is not supported yet: "+field.name);
    }
#ifdef DSIM_QUEUES_ENABLED
    std::string object_queue_text(const std::vector<V>* values,const ObjectPrintField& field) const {
        std::string text="'{";
        if(values)for(size_t i=0;i<values->size();++i){if(i)text+=", ";text+=object_field_text((*values)[i],field);}
        return text+(values&&!values->empty()?"} ":"}");
    }
#endif
#ifdef DSIM_ASSOCIATIVE_ARRAYS_ENABLED
    std::string object_map_key_text(const AssociativeKey& key) const {
#ifdef DSIM_STRING_ENABLED
        if(key.text)return "\""+*key.text+"\"";
#endif
        if(key.object_key)return object_reference_text(V(key.object_identity,0,64));
        auto text=format(key.integral,'h');auto start=text.find_first_not_of('0');return "0x"+(start==std::string::npos?std::string("0"):text.substr(start));
    }
    std::string object_map_text(const AssociativeArray* values,const ObjectPrintField& field,size_t axis=0) const {
        std::string text="'{";bool first=true;
        auto append=[&](const AssociativeKey& key,const std::string& value){if(!first)text+=", ";first=false;text+=object_map_key_text(key)+":"+value;};
        if(values) {
            if(axis+1==field.axes.size())for(const auto& item:*values)append(item.first,object_field_text(item.second,field));
            else for(const auto& item:values->children) {
#ifdef DSIM_QUEUES_ENABLED
                if(field.axes[axis+1]==1)append(item.first,object_queue_text(&item.second.queue,field));else
#endif
                append(item.first,object_map_text(&item.second,field,axis+1));
            }
        }
        return text+(values&&(!values->empty()||!values->children.empty())?"} ":"}");
    }
#endif
    V object_text(V handle) const {
        if(!handle.a&&!handle.b)return V::text("null");
        const auto& object=objects.at(object_index(handle,object_type(handle)));
        const auto& type=object_print_type(object.type);std::string text="'{";bool first=true;
        for(const auto& field:type.fields) {
            if(field.kind=='?')throw std::runtime_error("class output field type is not supported yet: "+field.name);
            if(!first)text+=", ";first=false;text+=field.name+":";
            if(field.axes.empty())text+=object_field_text(field.signal>=0?(field.kind=='e'?V():get(field.signal)):object.fields.at(field.field),field);
#ifdef DSIM_QUEUES_ENABLED
            else if(field.axes.front()==1) {
                if(field.signal>=0){auto values=dynamic_values(field.signal);text+=object_queue_text(&values,field);}
                else {auto found=object.queues.find(field.field);text+=object_queue_text(found==object.queues.end()?nullptr:&found->second,field);}
            }
#endif
#ifdef DSIM_ASSOCIATIVE_ARRAYS_ENABLED
            else if(field.axes.front()==2) {
                if(field.signal>=0)text+=object_map_text(associative_find(AssociativeRef(field.signal)),field);
                else {auto found=object.associative.find(field.field);text+=object_map_text(found==object.associative.end()?nullptr:&found->second,field);}
            }
#endif
            else throw std::runtime_error("class output array dimension is not supported yet: "+field.name);
        }
        return V::text(text+"}");
    }
#endif
#ifdef DSIM_CONSTRAINT_ENABLED
    uint32_t object_random(V handle) {return random_next(objects.at(object_index(handle,object_type(handle))).random_state);}
    RandomCycle& object_random_cycle(V handle,size_t field) {return objects.at(object_index(handle,object_type(handle))).random_cycles[field];}
    void object_srandom(V handle,V seed) {objects.at(object_index(handle,object_type(handle))).random_state=uint32_t(seed.a&~seed.b);}
    bool object_rand_mode_enabled(V handle,size_t field) const {
        const auto& object=objects.at(object_index(handle,object_type(handle)));auto found=object.random_modes.find(field);
        return found==object.random_modes.end()?object.random_enabled:found->second;
    }
    void object_rand_mode(V handle,V enabled) {auto& object=objects.at(object_index(handle,object_type(handle)));object.random_enabled=enabled.truth()==1;object.random_modes.clear();}
    void object_rand_mode(V handle,size_t field,V enabled) {objects.at(object_index(handle,object_type(handle))).random_modes[field]=enabled.truth()==1;}
    bool object_constraint_mode(V handle,const std::string& name) const {
        const auto& object=objects.at(object_index(handle,object_type(handle)));auto found=object.constraint_modes.find(name);
        return found==object.constraint_modes.end()?object.constraints_enabled:found->second;
    }
    void object_constraint_mode(V handle,V enabled) {auto& object=objects.at(object_index(handle,object_type(handle)));object.constraints_enabled=enabled.truth()==1;object.constraint_modes.clear();}
    void object_constraint_mode(V handle,const std::string& name,V enabled) {objects.at(object_index(handle,object_type(handle))).constraint_modes[name]=enabled.truth()==1;}
#endif
    void object_set(V handle,int type,size_t field,V value,int dependency) {
#ifdef DSIM_AGGREGATE_STORAGE_ENABLED
        if(auto meta=object_aggregate_types.find({type,field});meta!=object_aggregate_types.end())value=aggregate_element(std::move(value),meta->second);
#endif
        auto& old=objects.at(object_index(handle,type)).fields.at(field);
        if(old.same(value))return;
        old=std::move(value);
#ifdef DSIM_OBJECT_SCALAR_REFS_ENABLED
        if(auto found=object_scalar_signals.find({object_index(handle,type),field});found!=object_scalar_signals.end())
            set(found->second,old,true);
#endif
        set(dependency,V(get(dependency).a+1,0,64));
    }
    void object_set_const(V handle,int type,size_t field,V value,int dependency) {
        auto& object=objects.at(object_index(handle,type));
        (void)object.fields.at(field);
        if(!object.assigned_constants.insert(field).second)
            throw std::runtime_error("instance const class property assigned more than once");
        object_set(handle,type,field,std::move(value),dependency);
    }
#endif
#ifdef DSIM_SCHEDULING_STATS
    uint64_t comb_region_runs=0,comb_member_runs=0,comb_region_expansions=0;
    uint64_t wake_dispatch_runs=0;
#ifdef DSIM_COMB_LEAF_ENABLED
    uint64_t comb_leaf_runs=0;
#endif
#ifdef DSIM_COMB_LEAF_BATCH_ENABLED
    uint64_t comb_leaf_batch_entries=0,comb_leaf_batch_events=0;
#endif
    uint64_t ready_pushes() const {return active.pushes+inactive.pushes;}
    uint64_t ready_pops() const {return active.pops+inactive.pops;}
#endif
#ifdef DSIM_COMB_REGION_ENABLED
#ifdef DSIM_MASKED_COMB_REGION_ENABLED
    int add_masked_comb_region(std::vector<int> members,const std::vector<std::pair<int,uint64_t>>& inputs,std::function<void(uint64_t)> run) {
        structural_change();
        if(members.size()<2||members.size()>16||inputs.empty()||!run||comb_regions.size()>=size_t(INT32_MAX))
            throw std::runtime_error("invalid compiled combinational region");
        for(size_t i=0;i<members.size();++i) {
            (void)processes.at(size_t(members[i]));
            if(i&&members[i]!=members[i-1]+1)throw std::runtime_error("nonadjacent combinational region members");
        }
        const auto full=(UINT64_C(1)<<members.size())-1;
        for(auto input:inputs) {
            (void)signals.at(size_t(input.first));
            if(!input.second||(input.second&~full))throw std::runtime_error("invalid combinational subscriber mask");
        }
        const int id=int(comb_regions.size());comb_regions.push_back({std::move(members),{},0,{},false,std::move(run)});
        for(auto input:inputs)signals[size_t(input.first)].watches.push_back({-1-id,4,input.second});
        return id;
    }
    int add_comb_region(std::vector<int> members,const std::vector<int>& inputs,Action run) {
        if(members.size()<2||members.size()>16||!run)throw std::runtime_error("invalid compiled combinational region");
        const auto full=(UINT64_C(1)<<members.size())-1;
        std::vector<std::pair<int,uint64_t>> masks;
        for(int input:inputs)masks.push_back({input,full});
        const int id=add_masked_comb_region(std::move(members),masks,[](uint64_t){});
        comb_regions[size_t(id)].run=std::move(run);comb_regions[size_t(id)].masked_run={};return id;
    }
#else
    int add_comb_region(std::vector<int> members,const std::vector<int>& inputs,Action run) {
        structural_change();
        if(members.size()<2||members.size()>16||inputs.empty()||!run||comb_regions.size()>=size_t(INT32_MAX))
            throw std::runtime_error("invalid compiled combinational region");
        for(size_t i=0;i<members.size();++i) {
            (void)processes.at(size_t(members[i]));
            if(i&&members[i]!=members[i-1]+1)throw std::runtime_error("nonadjacent combinational region members");
        }
        for(int input:inputs)(void)signals.at(size_t(input));
        const int id=int(comb_regions.size());comb_regions.push_back({std::move(members),std::move(run),0,{}});
        for(int input:inputs)signals[size_t(input)].watches.push_back({-1-id,4,0});
        return id;
    }
#endif
    void enqueue_comb_region(int id) {
        const auto count=comb_regions.at(size_t(id)).members.size();
        issue_comb_region(id,(UINT64_C(1)<<count)-1);
    }
    void arm_comb_member(int region,int bit,int process,int site) {
        comb_regions[size_t(region)].armed|=UINT64_C(1)<<bit;
        auto& p=processes[size_t(process)];p.queued=false;p.waiting=true;p.generation=1;p.last_wait_site=site;
    }
#endif
#ifdef DSIM_SELECTION_CHECKS_ENABLED
    // Reports belong to the calling process, including nested functions/tasks.
    // Sim snapshots own this queue, so speculative reports roll back with it.
    void selection_report(const std::string& message) {
        if(selection_process<0)throw std::runtime_error("selection check outside a running process");
        selection_reports.push_back({selection_process,message});
    }
#endif
    void freeze_topology() {structural_change();finish_connections();topology_locked=true;}
    void restore(const Checkpoint& cp) {
        if(speculating)throw std::runtime_error("cannot restore manually inside prediction");
#ifdef DSIM_WAVE_ENABLED
        if(wave_context)throw std::runtime_error("cannot rewind an attached waveform outside a transaction");
#endif
        load_checkpoint(cp);
    }
#ifdef DSIM_PARALLEL_ENABLED
    // Coordinator-owned transactions buffer output, resolved notifications and
    // waveform callbacks until every partition has agreed on a window end.
    Checkpoint begin_transaction() {
        if(transaction_serial==UINT64_MAX)throw std::runtime_error("transaction sequence overflow");
        auto cp=save_checkpoint(true);
        cp.transaction_id=++transaction_serial;
        transaction_active=cp.transaction_id;speculating=true;
#ifdef DSIM_MEMORY_IO_ENABLED
        memory_file_overlay.clear();
#endif
        return cp;
    }
    bool transaction_pending(const Checkpoint& cp) const {
        return speculating&&cp.owner==this&&cp.saved&&cp.transaction_id
            &&cp.transaction_id==transaction_active;
    }
    void rollback_transaction(const Checkpoint& cp) {
        if(running||!transaction_pending(cp))throw std::runtime_error("invalid transaction rollback");
        load_checkpoint(cp);
    }
    void commit_transaction(const Checkpoint& cp) {
        if(running||!transaction_pending(cp))throw std::runtime_error("invalid transaction commit");
        // An external sink may fail after a partial commit; never replay it.
        speculating=false;transaction_active=0;
        auto effects=std::move(speculative_effects);speculative_effects.clear();
        for(auto& effect:effects)effect();
    }
#endif
#ifdef DSIM_STRING_ENABLED
    int signal_text() {int id=signal(1,false);signals.at(size_t(id)).value=V::text("");return id;}
#endif
    void print(const std::string& fmt,const std::vector<V>& args,bool newline=true,uint64_t caller_unit_fs=0,const std::vector<bool>& signs={}) {
        if(!caller_unit_fs)caller_unit_fs=time_precision_fs;
#ifdef DSIM_PARALLEL_ENABLED
        if(output_sink) {
            std::ostringstream text;display(fmt,args,newline,text,caller_unit_fs,time_format,signs);
            if(speculating)speculative_effects.push_back([sink=output_sink,time=now,text=text.str()]{sink(time,text);});
            else output_sink(now,text.str());
            return;
        }
#endif
        if(!speculating){display(fmt,args,newline,std::cout,caller_unit_fs,time_format,signs);return;}
        std::ostringstream text;display(fmt,args,newline,text,caller_unit_fs,time_format,signs);
        speculative_effects.push_back([text=text.str()]{std::cout<<text;});
    }
#ifdef DSIM_DPI_ENABLED
    bool prediction_active() const {return speculating;}
#endif
    template<class Predict,class Validate,class Correct>
    bool predict_until(uint64_t horizon,Predict predict,Validate validate,Correct correct) {
        if(horizon<now)throw std::runtime_error("prediction horizon precedes current time");
        auto cp=save_checkpoint(true);auto before=steps;
        ++prediction_stats.attempts;speculating=true;
#ifdef DSIM_MEMORY_IO_ENABLED
        memory_file_overlay.clear();
#endif
        bool accepted=false;
        try {
            predict(*this);run_until(horizon);accepted=validate(static_cast<const Sim&>(*this));
            prediction_stats.speculative_steps+=steps-before;
            if(accepted) {
                ++prediction_stats.commits;speculating=false;
                auto effects=std::move(speculative_effects);speculative_effects.clear();
                // Once external effects start, a sink failure must propagate;
                // replaying a partly committed output would duplicate it.
                for(auto& effect:effects)effect();
            } else {
                ++prediction_stats.rollbacks;load_checkpoint(cp);
                correct(*this);run_until(horizon);
                prediction_stats.replayed_steps+=steps-before;
            }
#ifdef DSIM_DPI_ENABLED
        } catch(const ForeignCallBarrier&) {
            prediction_stats.speculative_steps+=steps-before;
            ++prediction_stats.rollbacks;load_checkpoint(cp);
            correct(*this);run_until(horizon);
            prediction_stats.replayed_steps+=steps-before;return false;
#endif
#ifdef DSIM_STOP_ENABLED
        } catch(const SimulationStopBarrier&) {
            prediction_stats.speculative_steps+=steps-before;
            ++prediction_stats.rollbacks;load_checkpoint(cp);
            correct(*this);run_until(horizon);
            prediction_stats.replayed_steps+=steps-before;return false;
#endif
        } catch(...) {
            if(speculating){++prediction_stats.rollbacks;load_checkpoint(cp);}
            throw;
        }
        return accepted;
    }
#ifdef DSIM_WAVE_ENABLED
    void attach_wave(void* context,void(*change)(void*,uint64_t,int,V),void(*tick)(void*,uint64_t)) {
        if(running||speculating)throw std::runtime_error("cannot change waveform sink during simulation/prediction");
        wave_context=context;wave_change=change;wave_tick=tick;
    }
#endif
#ifdef DSIM_DUMP_TASKS_ENABLED
    // File/selection/control requests share the same transaction order as
    // value and tick callbacks. Callers capture owned arguments and time.
    void wave_effect(Action effect) {
        if(speculating)speculative_effects.push_back(std::move(effect));
        else effect();
    }
#endif
#ifdef DSIM_FILE_IO_ENABLED
    // Sim checkpoints copy cursors and share immutable byte images. Writes use
    // COW, so speculative branches never mutate either their parent or the OS.
    void file_effect(Action effect) {
        if(speculating)speculative_effects.push_back(std::move(effect));else effect();
    }
    static void store_file_bytes(const std::string& path,const std::string& bytes,int64_t position,bool truncate) {
        if(truncate) {
            std::ofstream out(path,std::ios::binary|std::ios::trunc);
            if(!out)throw std::runtime_error(path+": cannot open output file");
            out.write(bytes.data(),std::streamsize(bytes.size()));out.close();
            if(!out)throw std::runtime_error(path+": cannot write output file");
        } else {
            std::fstream out(path,std::ios::binary|std::ios::in|std::ios::out);
            if(!out)throw std::runtime_error(path+": cannot reopen output file");
            out.seekp(position);out.write(bytes.data(),std::streamsize(bytes.size()));out.close();
            if(!out)throw std::runtime_error(path+": cannot write output file");
        }
    }
    static std::string file_path(const std::string& filename) {
        if(filename.empty()||filename.find('\0')!=std::string::npos)return {};
        return std::filesystem::absolute(filename).lexically_normal().string();
    }
    uint32_t file_open(const std::string& filename,std::string mode,bool mcd=false) {
        const std::string path=file_path(filename);if(path.empty())return 0;
        if(mcd)mode="w";
        // Binary mode is a spelling variant on the supported POSIX platforms.
        if(mode=="rb"||mode=="wb"||mode=="ab")mode.erase(1,1);
        else if(mode=="rb+"||mode=="wb+"||mode=="ab+"||mode=="r+b"||mode=="w+b"||mode=="a+b")mode=mode.substr(0,1)+"+";
        if(mode!="r"&&mode!="w"&&mode!="a"&&mode!="r+"&&mode!="w+"&&mode!="a+")
            throw std::runtime_error("unsupported $fopen mode: "+mode);
        uint32_t slot=mcd?1:3;
        auto& handles=mcd?file_mcd:file_fd;
        while(handles.count(slot)&&slot<(mcd?31u:0x7fffffffu))++slot;
        if(slot==(mcd?31u:0x7fffffffu))return 0;
        bool exists=false;std::error_code ec;
        auto status=std::filesystem::status(path,ec);
        exists=!ec&&std::filesystem::exists(status);
        if(exists&&!std::filesystem::is_regular_file(status))return 0;
        auto found=file_images.find(path);
        std::shared_ptr<std::string> image;
        if(mode[0]!='w') {
            if(found!=file_images.end())image=found->second;
            else if(exists) {
                std::ifstream in(path,std::ios::binary);if(!in)return 0;
                image=std::make_shared<std::string>(std::istreambuf_iterator<char>(in),std::istreambuf_iterator<char>());
                if(in.bad())return 0;
            } else if(mode[0]=='r')return 0;
        }
        const bool writing=mode[0]!='r'||mode.size()==2;
        if(writing) {
            const auto writable=std::filesystem::perms::owner_write|std::filesystem::perms::group_write|std::filesystem::perms::others_write;
            if(exists&&(status.permissions()&writable)==std::filesystem::perms::none)return 0;
            if(!exists) {
                auto parent=std::filesystem::status(std::filesystem::path(path).parent_path(),ec);
                if(ec||!std::filesystem::is_directory(parent)||(parent.permissions()&writable)==std::filesystem::perms::none)return 0;
            }
        }
        if(!image)image=std::make_shared<std::string>();
        if(mode[0]=='w'||(!exists&&found==file_images.end()&&writing)) {
            if(speculating)file_effect([path]{store_file_bytes(path,"",0,true);});
            else {
                std::ofstream out(path,std::ios::binary|std::ios::trunc);if(!out)return 0;
                out.close();if(!out)return 0;
            }
        }
        file_images[path]=std::move(image);
        FileHandle handle;handle.path=path;handle.readable=mode[0]=='r'||mode.size()==2;
        handle.writable=writing;handle.append=mode[0]=='a';
        // a+ reads initially at the start; plain a initially reports the end.
        if(mode=="a")handle.position=int64_t(file_images.at(path)->size());
        handles.emplace(slot,std::move(handle));
        return mcd?(1u<<slot):(0x80000000u|slot);
    }
    static uint32_t file_integer(V value) {
        value=value.size(32);if(value.b)throw std::runtime_error("file descriptor/offset contains X/Z");return uint32_t(value.a);
    }
    FileHandle& file_handle(uint32_t fd) {
        auto found=file_fd.find(fd&0x7fffffffu);
        if(!(fd&0x80000000u)||found==file_fd.end())throw std::runtime_error("invalid file descriptor");
        return found->second;
    }
    int file_getc(uint32_t fd) {
        auto& h=file_handle(fd);if(!h.readable)return -1;
        if(!h.pushed.empty()){int c=h.pushed.back();h.pushed.pop_back();++h.position;return c;}
        const auto& bytes=*file_images.at(h.path);
        if(h.position<0||uint64_t(h.position)>=bytes.size()){h.eof=true;return -1;}
        return static_cast<unsigned char>(bytes[size_t(h.position++)]);
    }
    int file_ungetc(uint32_t character,uint32_t fd) {
        auto& h=file_handle(fd);if(!h.readable||int32_t(character)==-1)return -1;
        h.pushed.push_back(static_cast<unsigned char>(character));--h.position;h.eof=false;return 0;
    }
    int file_eof(uint32_t fd) {return file_handle(fd).eof?1:0;}
    int32_t file_tell(uint32_t fd) {auto position=file_handle(fd).position;return position<0?-1:int32_t(position);}
    int file_seek(uint32_t fd,uint32_t offset,uint32_t origin) {
        auto& h=file_handle(fd);if(origin>2)return -1;
        int64_t base=origin==0?0:origin==1?h.position:int64_t(file_images.at(h.path)->size());
        const int64_t position=base+int32_t(offset);if(position<0)return -1;
        h.position=position;h.eof=false;h.pushed.clear();return 0;
    }
    int file_rewind(uint32_t fd) {return file_seek(fd,0,0);}
    struct FileWord {int32_t count;V value;};
    FileWord file_read_word(uint32_t fd,int width) {
        if(width<=0)throw std::runtime_error("invalid binary read width");
        file_handle(fd);
        FileWord word{0,V(0,0,width)};
        const int bytes=(width-1)/8+1;
        // File bytes run from the most significant byte to the least. Missing
        // low bytes stay zero; callers decide whether a short word is stored.
        for(int i=0;i<bytes;++i) {
            const int c=file_getc(fd);if(c<0)break;
            const int lo=(bytes-1-i)*8;
            word.value=replace(word.value,lo,std::min(8,width-lo),V(uint32_t(c),0,8));
            ++word.count;
        }
        return word;
    }
    struct FileLine {int32_t count;std::string text;};
    FileLine file_gets(uint32_t fd,size_t capacity=0) {
        auto& h=file_handle(fd);if(!h.readable)return {-1,{}};
        FileLine line{0,{}};
        while(!capacity||line.text.size()<capacity) {
            int c=file_getc(fd);if(c<0)break;
            line.text+=char(c);if(c=='\n')break;
        }
        line.count=int32_t(line.text.size());return line;
    }
#ifdef DSIM_SCAN_ENABLED
    ScanResult scan_file(uint32_t fd,const std::string& fmt,const std::vector<ScanTarget>& targets) {
        file_handle(fd);
        return scan_input(fmt,targets,[&]{return file_getc(fd);},[&](int c){file_ungetc(uint32_t(c),fd);});
    }
#endif
    void file_write_handle(FileHandle& h,const std::string& bytes) {
        if(!h.writable)throw std::runtime_error("file descriptor is not writable");
        auto& image=file_images.at(h.path);
        int64_t position=h.append?int64_t(image->size()):h.position;
        if(position<0)throw std::runtime_error("negative output file position");
        const auto path=h.path;
        file_effect([path,bytes,position]{store_file_bytes(path,bytes,position,false);});
        if(image.use_count()!=1)image=std::make_shared<std::string>(*image);
        if(size_t(position)>image->size())image->resize(size_t(position),'\0');
        image->replace(size_t(position),bytes.size(),bytes);
        h.position=position+int64_t(bytes.size());h.pushed.clear();
    }
    void file_write(uint32_t fd,const std::string& bytes) {
        if(fd==0x80000001u){print("%s",{V::text(bytes)},false);return;}
        if(fd==0x80000002u){file_effect([bytes]{std::cerr<<bytes;});return;}
        if(fd&0x80000000u){file_write_handle(file_handle(fd),bytes);return;}
        if(fd&1u)print("%s",{V::text(bytes)},false);
        for(unsigned bit=1;bit<31;++bit)if(fd&(1u<<bit)) {
            auto found=file_mcd.find(bit);
            if(found==file_mcd.end())throw std::runtime_error("invalid multichannel descriptor");
            file_write_handle(found->second,bytes);
        }
    }
    void file_close(uint32_t fd) {
        if(fd&0x80000000u){file_handle(fd);file_fd.erase(fd&0x7fffffffu);return;}
        for(unsigned bit=1;bit<31;++bit)if(fd&(1u<<bit))file_mcd.erase(bit);
    }
    void file_flush(uint32_t fd=0) {
        // Every committed write owns and closes its OS stream. Never flush
        // speculative data to the OS; queued effects preserve program order.
        if((fd&0x80000000u)&&fd!=0x80000001u&&fd!=0x80000002u)file_handle(fd);
        if(!fd||fd==0x80000001u||(!(fd&0x80000000u)&&(fd&1)))file_effect([]{std::cout.flush();});
        if(!fd||fd==0x80000002u)file_effect([]{std::cerr.flush();});
    }
#endif
#ifdef DSIM_MEMORY_IO_ENABLED
    std::string read_memory_file(const std::string& filename) const {
#ifdef DSIM_FILE_IO_ENABLED
        auto image=file_images.find(file_path(filename));if(image!=file_images.end())return *image->second;
#endif
        if(speculating) {
            auto found=memory_file_overlay.find(filename);if(found!=memory_file_overlay.end())return found->second;
        }
        std::ifstream input(filename,std::ios::binary);
        if(!input)throw std::runtime_error(filename+": cannot open memory file");
        std::string text((std::istreambuf_iterator<char>(input)),std::istreambuf_iterator<char>());
        if(input.bad())throw std::runtime_error(filename+": cannot read memory file");return text;
    }
    void write_memory_file(const std::string& filename,std::string text) {
#ifdef DSIM_FILE_IO_ENABLED
        file_images[file_path(filename)]=std::make_shared<std::string>(text);
#endif
        auto write=[filename,text] {
            std::ofstream output(filename,std::ios::binary|std::ios::trunc);
            if(!output)throw std::runtime_error(filename+": cannot open memory file for writing");
            output.write(text.data(),std::streamsize(text.size()));output.close();
            if(!output)throw std::runtime_error(filename+": cannot write memory file");
        };
        if(speculating){memory_file_overlay[filename]=std::move(text);speculative_effects.push_back(std::move(write));}
        else write();
    }
#endif
#ifdef DSIM_SCAN_ENABLED
    ScanResult scan_string(const std::string& text,const std::string& fmt,const std::vector<ScanTarget>& targets,bool packed=false) const {
        // VCS distinguishes empty packed data (including a string literal)
        // from an empty string when the format has no conversions.
        if(text.empty()&&packed) {
            const auto fields=scan_plan(fmt,targets);
            if(std::none_of(fields.begin(),fields.end(),[](const ScanField& f){return f.target>=0||f.suppress;}))return {};
        }
        size_t at=0;
        return scan_input(fmt,targets,[&]{return at<text.size()?int(static_cast<unsigned char>(text[at++])):-1;},[&](int){--at;});
    }
#endif
#ifdef DSIM_STRING_ENABLED
    struct StringFormat {std::string text;size_t arguments;std::string conversions;std::vector<size_t> positions;};
    static StringFormat string_format(const V& format_value,const std::string& scope) {
        std::string fmt=format(format_value,'s'),expanded,conversions;size_t count=0;std::vector<size_t> positions;
        for(size_t i=0;i<fmt.size();++i) {
            if(fmt[i]!='%'){expanded+=fmt[i];continue;}
            size_t begin=i;
            if(++i==fmt.size())throw std::runtime_error("incomplete string format");
            if(fmt[i]=='%'){expanded+="%%";continue;}
            if(fmt[i]=='m'||fmt[i]=='M'){for(char c:scope){expanded+=c;if(c=='%')expanded+='%';}continue;}
            unsigned width=0;
            while(i<fmt.size()&&fmt[i]>='0'&&fmt[i]<='9') {
                width=width*10+unsigned(fmt[i++]-'0');
                if(width>1048576)throw std::runtime_error("string format field width exceeds 1048576");
            }
            if(i<fmt.size()&&fmt[i]=='.'){++i;while(i<fmt.size()&&fmt[i]>='0'&&fmt[i]<='9')++i;}
            if(i==fmt.size()||std::string("bdhxotscfFeEgGp").find(fmt[i])==std::string::npos)
                throw std::runtime_error("unsupported string format; supported: %b %d %h %x %o %t %s %c %m");
            ++count;conversions+=fmt[i];expanded+=fmt.substr(begin,i-begin+1);positions.push_back(expanded.size()-1);
        }
        return {std::move(expanded),count,std::move(conversions),std::move(positions)};
    }
    void print_string_format(const StringFormat& plan,const std::vector<V>& args,const std::vector<bool>& signs,
                             const std::vector<bool>& objects,std::ostream& result,uint64_t unit) const {
        if(plan.conversions.find('p')==std::string::npos) {
            if(std::find(objects.begin(),objects.end(),true)!=objects.end())throw std::runtime_error("class formatting currently requires %p");
            display(plan.text,args,false,result,unit,time_format,signs);return;
        }
        auto values=args;auto format=plan.text;
        for(size_t i=0;i<plan.conversions.size();++i) {
            const bool object=i<objects.size()&&objects[i];
            if(plan.conversions[i]!='p') {
                if(object)throw std::runtime_error("class formatting currently requires %p");
                continue;
            }
            if(!object)throw std::runtime_error("%p output currently requires a class value");
#ifdef DSIM_OBJECT_FORMAT_ENABLED
            format[plan.positions[i]]='s';
#else
            throw std::runtime_error("class output support is not enabled");
#endif
        }
        display(format,values,false,result,unit,time_format,signs);
    }
    V format_text(const V& format_value,const std::vector<V>& args,const std::vector<bool>& signs,
                  const std::string& scope,uint64_t unit,const std::vector<bool>& objects={}) const {
        auto plan=string_format(format_value,scope);
        if(plan.arguments!=args.size())throw std::runtime_error("string format/argument count mismatch");
        std::ostringstream result;print_string_format(plan,args,signs,objects,result,unit);
        return V::text(result.str());
    }
    V write_text(const std::vector<V>& values,const std::vector<bool>& signs,const std::vector<int>& packed_widths,
                 const std::string& scope,uint64_t unit,char radix='d',const std::vector<bool>& objects={}) const {
        std::ostringstream result;
        for(size_t i=0;i<values.size();++i) {
#ifdef DSIM_OBJECT_FORMAT_ENABLED
            if(i<objects.size()&&objects[i]){result<<values[i].text_value();continue;}
#endif
            if(values[i].text_data) {
                const auto plan=string_format(values[i],scope);
                if(plan.arguments>values.size()-i-1)throw std::runtime_error("$swrite format/argument count mismatch");
                std::vector<V> args;std::vector<bool> arg_signs,arg_objects;
                for(size_t n=0;n<plan.arguments;++n) {
                    ++i;auto value=values[i];
                    if(plan.conversions[n]!='s'&&i<packed_widths.size()&&packed_widths[i])value=packed_text(value.text_value(),packed_widths[i]);
                    args.push_back(value);arg_signs.push_back(i<signs.size()&&signs[i]);arg_objects.push_back(i<objects.size()&&objects[i]);
                }
                print_string_format(plan,args,arg_signs,arg_objects,result,unit);
            } else {
                char base=radix;
#ifdef DSIM_REAL_ENABLED
                if(values[i].real_width)base='g';
#endif
                display(std::string("%")+base,{values[i]},false,result,unit,time_format,{i<signs.size()&&signs[i]});
            }
        }
        return V::text(result.str());
    }
#endif
#ifdef DSIM_PLUSARGS_ENABLED
    void set_plusargs(const std::vector<std::string>& args) {structural_change();runtime_plusargs=std::make_shared<const std::vector<std::string>>(args);}
    bool test_plusarg(const std::string& prefix) const {
        if(prefix.empty()||!runtime_plusargs)return false;
        for(const auto& arg:*runtime_plusargs)if(arg.compare(0,prefix.size(),prefix)==0)return true;
        return false;
    }
    struct PlusargValue {bool matched;V value;};
    PlusargValue value_plusarg(const std::string& fmt,int width,bool text) const {
        const auto percent=fmt.find('%');
        if(percent==std::string::npos||percent+2!=fmt.size()||std::string("dhxobs").find(fmt.back())==std::string::npos)
            throw std::runtime_error("$value$plusargs requires one trailing %d %h %x %o %b or %s conversion");
        if(text&&fmt.back()!='s')throw std::runtime_error("numeric plusarg conversion requires an integral target");
        const std::string prefix=fmt.substr(0,percent);
        if(runtime_plusargs)for(const auto& arg:*runtime_plusargs)if(arg.compare(0,prefix.size(),prefix)==0) {
            const auto input=arg.substr(prefix.size());
            if(fmt.back()=='s') {
#ifdef DSIM_STRING_ENABLED
                if(text)return {true,V::text(input)};
#endif
                return {true,packed_text(input.empty()?"0":input,width)};
            }
            int radix=fmt.back()=='d'?10:fmt.back()=='b'?2:fmt.back()=='o'?8:16;
            size_t i=0;bool negative=false;
            if(radix==10&&i<input.size()&&(input[i]=='+'||input[i]=='-'))negative=input[i++]=='-';
            // VCS rejects the complete numeric suffix when any character is
            // invalid. The variable's ordinary store applies two-state coercion.
            for(size_t at=i;at<input.size();++at) {
                const char c=input[at];if(c=='_')continue;
                const int digit=c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:c>='A'&&c<='F'?c-'A'+10:-1;
                const bool special=radix!=10&&(c=='x'||c=='X'||c=='z'||c=='Z'||c=='?');
                if(!special&&(digit<0||digit>=radix))return {true,V::x(width)};
            }
            V value(0,0,width);bool first=true;
            for(;i<input.size();++i) {
                char c=input[i];if(c=='_')continue;
                const bool x=c=='x'||c=='X',z=c=='z'||c=='Z'||c=='?';int digit=c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:c>='A'&&c<='F'?c-'A'+10:-1;
                if(radix==10&&(x||z))break;
                if(!x&&!z&&(digit<0||digit>=radix))break;
                if(first&&(x||z))value=x?V::x(width):V::z(width);
                first=false;
                auto chunk=x?V::x(radix==16?4:radix==8?3:1):z?V::z(radix==16?4:radix==8?3:1):V(uint64_t(digit),0,32);
                if(radix==10)value=binary_op<Binary::Add>(binary_op<Binary::Multiply>(value,V(10,0,32),width),chunk,width);
                else {
                    const int bits=radix==16?4:radix==8?3:1;
                    value=replace(binary_op<Binary::ShiftLeft>(value,V(bits,0,32),width),0,std::min(bits,width),chunk);
                }
            }
            if(negative)value=unary("-",value,width);
            return {true,value};
        }
        return {false,V(0,0,width)};
    }
#endif
    uint64_t now=0,limit=std::numeric_limits<uint64_t>::max(); bool finished=false;
#ifdef DSIM_TERMINATION_UNWIND_ENABLED
    void suppress_finalization() {
#ifdef DSIM_FINAL_ENABLED
        finalized=true;
#endif
    }
    void terminate_simulation() {
#ifdef DSIM_FINAL_ENABLED
        if(finalized)return;
#endif
        finished=true;throw SimulationTermination{};
    }
#ifdef DSIM_STOP_ENABLED
    void stop_simulation() {
        // Reading a command is external I/O. Replay at the committed boundary.
        if(speculating)throw SimulationStopBarrier{};
        std::cerr<<"dsim: $stop at time "<<now<<'\n';
        for(std::string command;;) {
            std::cerr<<"dsim> ";
            if(!std::getline(std::cin,command)) {
                suppress_finalization();finished=true;throw SimulationTermination{};
            }
            const auto first=command.find_first_not_of(" \t\r");
            const auto last=command.find_last_not_of(" \t\r");
            command=first==std::string::npos?"":command.substr(first,last-first+1);
            if(command=="run"||command=="continue")return;
            if(command=="quit"||command=="exit") {
                finished=true;throw SimulationTermination{};
            }
            std::cerr<<"commands: run, quit\n";
        }
    }
#endif
#endif
#ifdef DSIM_FINAL_ENABLED
    bool defer_finalization=false;
    void add_final_process(int id) {
        structural_change();
        if(id<0||size_t(id)>=processes.size())throw std::runtime_error("invalid final process");
        final_processes.push_back(id);
    }
    void finalize() {
        if(finalized)return;
        if(running)throw std::runtime_error("finalization requires a scheduler boundary");
        finalized=true;running=true;
        struct Guard {bool& flag;~Guard(){flag=false;}} guard{running};
#ifdef DSIM_TERMINATION_UNWIND_ENABLED
        try {
#endif
        for(int id:final_processes) {
#ifdef DSIM_RANDOM_ENABLED
            const int old_random=random_process;random_process=id;
            struct RandomGuard {int& value;int old;~RandomGuard(){value=old;}} random_guard{random_process,old_random};
#endif
#ifdef DSIM_DYNAMIC_FORK_ENABLED
            const int old_process=fork_current_process;fork_current_process=id;
            struct ForkGuard {int& value;int old;~ForkGuard(){value=old;}} fork_guard{fork_current_process,old_process};
#endif
#ifdef DSIM_SELECTION_CHECKS_ENABLED
            const int old_selection=selection_process;selection_process=id;
            struct SelectionGuard {int& value;int old;~SelectionGuard(){value=old;}} selection_guard{selection_process,old_selection};
#endif
            const auto& process=processes[size_t(id)];
#ifdef DSIM_PROCESS_LIFETIME_ENABLED
            try {
#endif
            if(process.handler==UINT32_MAX)
#ifdef DSIM_SHARED_TASKS_ENABLED
                dispatch_task_action(id);
#else
                actions[process.payload]();
#endif
            else {const auto& handler=handlers[process.handler];handler.run(*this,contexts[handler.context].get(),process.payload);}
#ifdef DSIM_PROCESS_LIFETIME_ENABLED
            } catch(const ProcessTermination&) {}
#endif
        }
#ifdef DSIM_TERMINATION_UNWIND_ENABLED
        } catch(const SimulationTermination&) {}
#endif
#ifdef DSIM_SELECTION_CHECKS_ENABLED
        auto reports=std::move(selection_reports);selection_reports.clear();
        for(const auto& report:reports)print(report.message+" time=%0d",{V(now,0,64)});
#endif
        finished=true;
#ifdef DSIM_WAVE_ENABLED
        record_wave_tick();
#endif
    }
#endif
    std::vector<Signal> signals; std::vector<Process> processes;
#ifdef DSIM_MIXED_STATE_ENABLED
    std::vector<V> state_masks;
    void set_state_mask(int id,V selected) {
        structural_change();
        auto& signal=signals.at(size_t(id));
        if(signal.net||selected.w!=signal.value.w||signal.state_mask>=0)
            throw std::runtime_error("invalid generated aggregate state mask");
        signal.state_mask=int(state_masks.size());state_masks.push_back(std::move(selected));
        signal.value=masked_two_state_value(std::move(signal.value),state_masks.back());
    }
#endif
#ifdef DSIM_COMPACT_GATES
    int compact_net() {
        structural_change();
        if(compact_signals.size()>=size_t(INT32_MAX)||next_signal_order==UINT64_MAX)throw std::runtime_error("too many simulation signals");
        compact_signals.emplace_back();compact_signals.back().order=next_signal_order++;
#ifdef DSIM_PATH_ENABLED
        compact_path_stamps.emplace_back();
#endif
        return -int(compact_signals.size());
    }
    size_t compact_signal_count() const {return compact_signals.size();}
    bool is_net(int id) const {if(id<0){(void)compact_signals.at(compact_index(id));return true;}return signals.at(id).net;}
    int signal(int w,bool net) {
        structural_change();
        if(signals.size()>=size_t(INT32_MAX)||next_signal_order==UINT64_MAX)throw std::runtime_error("too many simulation signals");
        signals.push_back({net?V::z(w):V::x(w),net,false,{}, {}});signal_orders.push_back(next_signal_order++);
#ifdef DSIM_PATH_ENABLED
        path_stamps.emplace_back();
#endif
        return int(signals.size())-1;
    }
    V get(int id) const {
#ifdef DSIM_DYNAMIC_FORK_ENABLED
        id=activation_signal(id);
#endif
        if(id<0){const auto& c=compact_signals.at(compact_index(id));return c.fallback?c.fallback->value:unpack_scalar(c.value);}
        return signals.at(id).value;
    }
#else
    int signal(int w,bool net) { structural_change();signals.push_back({net?V::z(w):V::x(w),net,false,{}, {}});
#ifdef DSIM_PATH_ENABLED
        path_stamps.emplace_back();
#endif
        return int(signals.size())-1; }
    V get(int id) const {
#ifdef DSIM_DYNAMIC_FORK_ENABLED
        id=activation_signal(id);
#endif
        return signals.at(id).value;
    }
#endif
#ifdef DSIM_TWO_STATE_ENABLED
    int signal_two_state(int width) {
        int id=signal(width,false);
        signals[id].two_state=true;signals[id].value=V(0,0,width);
        return id;
    }
#endif
#ifdef DSIM_REAL_ENABLED
    int signal_real(int width) {
        int id=signal(width,false);signals[size_t(id)].real_width=width;signals[size_t(id)].value=V::real(0,width);return id;
    }
#endif
#ifdef DSIM_NAMED_EVENTS_ENABLED
    int named_event(int dependency=-1) {
        if(dependency>=0)(void)get(dependency);
        int id;
        if(dependency<0)id=signal(1,false);
        else {
            // Instance identities are checkpointed execution state, like
            // automatic storage. Static design topology remains frozen.
            if(signals.size()>=size_t(INT32_MAX))throw std::runtime_error("too many named events");
            id=int(signals.size());signals.push_back({V(0,0,1),false,false,{},{}});
#ifdef DSIM_COMPACT_GATES
            if(next_signal_order==UINT64_MAX)throw std::runtime_error("signal order overflow");
            signal_orders.push_back(next_signal_order++);
#endif
#ifdef DSIM_PATH_ENABLED
            path_stamps.emplace_back();
#endif
        }
        signals[size_t(id)].value=V(0,0,1);
        if(dependency>=0)named_event_dependencies.emplace(id,dependency);
        named_events.emplace(id,NamedEventState{});return id;
    }
    int event_id(V handle) const {
        if(handle.b||!handle.a||handle.a>uint64_t(INT32_MAX)||!named_events.count(int(handle.a-1)))
            throw std::runtime_error("null or invalid named event handle");
        return int(handle.a-1);
    }
    int event_wait_id(V handle) const {
#ifdef DSIM_EVENT_ALIASES_ENABLED
        if(!handle.b&&!handle.a)return -1;
#endif
        return event_id(handle);
    }
#ifdef DSIM_EVENT_ALIASES_ENABLED
    V event_alias(V handle,int dependency) {
        const int id=event_wait_id(handle);(void)get(dependency);
        if(id>=0) {
            auto primary=named_event_dependencies.find(id);
            if(primary==named_event_dependencies.end()||primary->second!=dependency)event_alias_dependencies[id].insert(dependency);
        }
        return handle;
    }
#endif
    bool event_triggered(int id) const {
        const auto& state=named_events.at(id);return state.triggered&&state.time==now;
    }
    void trigger_event(int id) {
#ifdef DSIM_EVENT_ALIASES_ENABLED
        if(id<0)return;
#endif
        auto& state=named_events.at(id);state={now,true};
        // Hidden signal changes represent occurrences, including two triggers
        // in one time step. The persistent query reads the timestamp instead.
#ifdef DSIM_WAIT_ORDER_ENABLED
        // Preserve trigger order even before the waiting Active process runs.
        notify_ordered_waits(id);
#endif
        set(id,V(get(id).a^1,0,1));
        if(auto found=named_event_dependencies.find(id);found!=named_event_dependencies.end()) {
            const int dependency=found->second;
            set(dependency,V(get(dependency).a+1,0,64));
        }
#ifdef DSIM_EVENT_ALIASES_ENABLED
        if(auto found=event_alias_dependencies.find(id);found!=event_alias_dependencies.end())
            for(int dependency:found->second)set(dependency,V(get(dependency).a+1,0,64));
#endif
        // A query expression is reevaluated only on an occurrence. It reads
        // true then; a query armed while already true cannot see a transition.
        // The implicit fall on advancing time does not update that baseline.
        for(const auto& watch:signals[size_t(id)].watches)if(watch.edges>=0&&(watch.edges&8)) {
            auto& process=processes[size_t(watch.process)];
            if(!process.waiting||process.generation!=watch.generation)continue;
#ifdef DSIM_SELECTION_CHECKS_ENABLED
            flush_selection_reports(watch.process);
#endif
            process.waiting=false;enqueue(watch.process);
        }
    }
    void trigger_event_nba(int id) {
#ifdef DSIM_EVENT_ALIASES_ENABLED
        if(id<0)return;
#endif
        (void)named_events.at(id);queue_nba({id,Nba::NamedEvent,V(),{}});
    }
#ifdef DSIM_DELAYED_NBA_ENABLED
    void trigger_event_after(int id,uint64_t ticks) {
#ifdef DSIM_EVENT_ALIASES_ENABLED
        if(id<0)return;
#endif
        (void)named_events.at(id);schedule_nba({id,Nba::NamedEvent,V(),{}},ticks);
    }
#endif
#endif
    int fork_process_id(int id) const {
#ifdef DSIM_DYNAMIC_FORK_ENABLED
        return fork_reference(id,&ForkFrame::processes);
#else
        return id;
#endif
    }
    // Depths are compiled relative to the process's inherited fork frame.
    // Every PC checks its expected depth, including return/break/disable paths.
    void activation_depth(size_t depth) {
#ifdef DSIM_DYNAMIC_FORK_ENABLED
        auto& activation=fork_current_process<0?startup_activation:processes.at(size_t(fork_current_process)).activation;
        auto& level=fork_current_process<0?startup_activation_level:processes[size_t(fork_current_process)].activation_level;
        if(depth>level)throw std::runtime_error("invalid automatic activation depth");
        while(level>depth){activation=activation->parent;--level;}
#else
        (void)depth;
#endif
    }
    void push_activation(std::initializer_list<int> ids,std::initializer_list<std::pair<int,int>> aliases={}) {
#ifdef DSIM_DYNAMIC_FORK_ENABLED
        // Gate installation can add static signals after fork configuration.
        // Freeze the private-storage boundary only when execution allocates.
        if(activation_first_signal==SIZE_MAX)activation_first_signal=signals.size();
        auto frame=std::make_shared<ActivationFrame>();
        auto& activation=fork_current_process<0?startup_activation:processes.at(size_t(fork_current_process)).activation;
        auto& level=fork_current_process<0?startup_activation_level:processes[size_t(fork_current_process)].activation_level;
        frame->parent=activation;
        ActivationSlot* available=nullptr;
        for(auto& slot:activation_slots)if(slot.owner.expired()&&slot.signals.size()==ids.size()) {
            bool match=true;for(int id:ids)if(!slot.signals.count(id)){match=false;break;}
            if(match){available=&slot;break;}
        }
        if(available)frame->signals=available->signals;
        else {
            for(int id:ids) {
                if(signals.size()>=size_t(INT32_MAX))throw std::runtime_error("too many automatic activation variables");
                auto signal=signals.at(size_t(id));signal.watches.clear();signal.drivers={};
                frame->signals[id]=int(signals.size());signals.push_back(std::move(signal));
#ifdef DSIM_AGGREGATE_STORAGE_ENABLED
                // Container descriptors follow automatic storage, including
                // aliases passed through a ref formal in a later activation.
                if(auto meta=dynamic_aggregate_types.find(id);meta!=dynamic_aggregate_types.end())
                    dynamic_aggregate_types[frame->signals[id]]=meta->second;
#endif
#ifdef DSIM_COMPACT_GATES
                if(next_signal_order==UINT64_MAX)throw std::runtime_error("signal order overflow");
                signal_orders.push_back(next_signal_order++);
#endif
#ifdef DSIM_PATH_ENABLED
                path_stamps.emplace_back();
#endif
            }
            activation_slots.push_back({{},frame->signals});available=&activation_slots.back();
        }
#ifdef DSIM_DYNAMIC_ARRAYS_ENABLED
        for(auto [logical,physical]:frame->signals){dynamic_arrays.erase(physical);dynamic_generations.erase(physical);dynamic_instances.erase(physical);
#ifdef DSIM_QUEUE_REF_LIMITS_ENABLED
            queue_reference_limits.erase(physical);
#endif
        }
#ifdef DSIM_ASSOCIATIVE_ARRAYS_ENABLED
        for(auto [logical,physical]:frame->signals)associative_arrays.erase(physical);
#endif
#endif
        // Alias targets are physical IDs captured in the caller before this
        // frame is entered. The slot pool owns only newly allocated variables.
        for(auto [logical,physical]:aliases) {
            if(frame->signals.count(logical)||signals.at(size_t(physical)).net||
               signals.at(size_t(logical)).value.w!=signals[size_t(physical)].value.w)
                throw std::runtime_error("invalid reference argument binding");
            frame->signals.emplace(logical,physical);
        }
        available->owner=frame;activation=std::move(frame);++level;
#else
        (void)ids;(void)aliases;
#endif
    }
#ifdef DSIM_DYNAMIC_FORK_ENABLED
    int reference_signal(int logical) const {return activation_signal(logical);}
#ifdef DSIM_QUEUE_REF_LIMITS_ENABLED
    int reference_queue_signal(int logical,int actual_bound) {
        const int physical=activation_signal(logical);
        queue_reference_limits.emplace(physical,actual_bound);return physical;
    }
#endif
    struct ReferenceActivation {
        Sim& sim;int process;std::shared_ptr<const ActivationFrame> previous;size_t depth;
        ReferenceActivation(const ReferenceActivation&)=delete;
        ReferenceActivation(Sim& s,int p,std::shared_ptr<const ActivationFrame> frame,size_t level)
            :sim(s),process(p),previous(std::move(frame)),depth(level) {}
        ~ReferenceActivation() {
            if(process<0){sim.startup_activation=std::move(previous);sim.startup_activation_level=depth;}
            else {auto& state=sim.processes[size_t(process)];
#ifdef DSIM_PROCESS_LIFETIME_ENABLED
                if(state.lifecycle==4){state.activation.reset();state.activation_level=0;return;}
#endif
                state.activation=std::move(previous);state.activation_level=depth;}
        }
    };
    ReferenceActivation reference_activation(std::initializer_list<int> ids,
                                             std::initializer_list<std::pair<int,int>> aliases) {
        const int p=fork_current_process;
        auto previous=p<0?startup_activation:processes.at(size_t(p)).activation;
        const auto level=p<0?startup_activation_level:processes[size_t(p)].activation_level;
        push_activation(ids,aliases);
        return ReferenceActivation(*this,p,std::move(previous),level);
    }
#endif
    int fork_wait_id(int id) const {
#ifdef DSIM_DYNAMIC_FORK_ENABLED
        return fork_reference(id,&ForkFrame::waits);
#else
        return id;
#endif
    }
    int fork_group_id(int id) const {
#ifdef DSIM_DYNAMIC_FORK_ENABLED
        return fork_reference(id,&ForkFrame::groups);
#else
        return id;
#endif
    }
    int fork_target_id(int id) const {
#ifdef DSIM_DYNAMIC_FORK_ENABLED
        return fork_reference(id,&ForkFrame::targets);
#else
        return id;
#endif
    }
    int process(Action fn) {
        structural_change();
        if(processes.size()>=size_t(INT32_MAX)||actions.size()>=UINT32_MAX)throw std::runtime_error("too many simulation processes");
        actions.push_back(std::move(fn));
        processes.push_back({0,UINT32_MAX,uint32_t(actions.size()-1),false,false});
        return int(processes.size())-1;
    }
#ifdef DSIM_SHARED_FUNCTIONS_ENABLED
    // Native calls finish before the scheduler can checkpoint. Keep depth on
    // the owning Sim, and remove every entry while unwinding, including errors.
    std::map<unsigned,unsigned> function_depths;
    struct FunctionDepth {
        Sim& sim;unsigned id;
        FunctionDepth(Sim& owner,unsigned key):sim(owner),id(key) {
            auto& count=sim.function_depths[id];
            if(count>=1024)throw std::runtime_error("recursive function depth exceeds 1024");
            ++count;
        }
        FunctionDepth(const FunctionDepth&)=delete;
        ~FunctionDepth(){auto it=sim.function_depths.find(id);if(!--it->second)sim.function_depths.erase(it);}
    };
    FunctionDepth function_depth(unsigned id){return FunctionDepth(*this,id);}
#endif
    // Register each model once: the kernel owns its lifetime and captures its
    // mutable state for checkpoints. All its handlers refer to the same context.
    template<class T> uint32_t compiled_context(std::shared_ptr<T> state) {
        structural_change();
        if(!state||contexts.size()>=UINT32_MAX)throw std::runtime_error("invalid compiled model context");
        register_state(state);contexts.push_back(std::move(state));
        return uint32_t(contexts.size()-1);
    }
    uint32_t compiled_handler(uint32_t context,CompiledAction fn) {
        structural_change();
        if(context>=contexts.size()||!fn||handlers.size()>=UINT32_MAX)throw std::runtime_error("invalid compiled model handler");
        handlers.push_back({fn,context});return uint32_t(handlers.size()-1);
    }
#ifdef DSIM_CHECKS_ENABLED
    void timing_watch(int signal,uint32_t context,TimingAction action,uint32_t payload) {
        structural_change();
        if(context>=contexts.size()||!action)throw std::runtime_error("invalid timing-check observer");
        (void)get(signal);
#ifdef DSIM_COMPACT_GATES
        auto& ids=signal<0?compact_timing_watch_ids:timing_watch_ids;
        const auto index=signal<0?compact_index(signal):size_t(signal);
#else
        auto& ids=timing_watch_ids;const auto index=size_t(signal);
#endif
        if(index>=ids.size())ids.resize(index+1,-1);
        if(ids[index]<0) {
            if(timing_watches.size()>=size_t(INT32_MAX))throw std::runtime_error("too many timing-check observer groups");
            ids[index]=int32_t(timing_watches.size());timing_watches.emplace_back();
        }
        timing_watches[size_t(ids[index])].push_back({context,payload,action});
    }
#endif
    int compiled_process(uint32_t handler,uint32_t payload) {
        structural_change();
        if(handler>=handlers.size()||processes.size()>=size_t(INT32_MAX))throw std::runtime_error("invalid compiled model process");
        processes.push_back({0,handler,payload,false,false});return int(processes.size())-1;
    }
#ifdef DSIM_SDF_JOBS_ENABLED
    uint32_t compiled_sdf_job(uint32_t handler,uint32_t payload,int source) {
        structural_change();
        if(handler>=handlers.size()||sdf_jobs.size()>=size_t(INT32_MAX)||processes.size()>UINT32_MAX)
            throw std::runtime_error("invalid compiled SDF job");
        if(get(source).w!=1)throw std::runtime_error("compiled SDF job requires a scalar source");
        uint32_t id=uint32_t(sdf_jobs.size());
        sdf_jobs.push_back({handler,payload,uint32_t(processes.size()),false,false});
#ifdef DSIM_COMPACT_GATES
        signal_watches(source).push_back({-int(id)-1,4,0});
#else
        signals[source].watches.push_back({-int(id)-1,4,0});
#endif
        return id;
    }
    void initialize_sdf_jobs_and_processes(std::initializer_list<int> dormant={}) {
        // Registration anchors preserve the previous all-process initialization
        // order, including multiple gate scopes and intervening RTL processes.
        size_t job=0;
        for(size_t process=0;process<=processes.size();++process) {
            while(job<sdf_jobs.size()&&sdf_jobs[job].before_process==process)
                enqueue_sdf_job(uint32_t(job++));
            if(process<processes.size()&&std::find(dormant.begin(),dormant.end(),int(process))==dormant.end())enqueue(int(process));
        }
    }
#endif
    uint64_t executed_steps() const {return steps;}
#ifdef DSIM_BATCH_ENABLED
#ifdef DSIM_BATCH_PROFILE
    struct BatchStats {uint64_t entries=0,events=0;} batch_stats;
#endif
    // Called by a compiled handler for its already-popped first event. Consume
    // only the consecutive FIFO prefix for that SAME handler/context. Never
    // skip a delivery, wake, behavioral process or another model handler.
    template<class Evaluate> void compiled_batch(uint32_t handler,uint32_t payload,Evaluate evaluate) {
        if(!running)throw std::runtime_error("compiled batch requires a running handler");
#ifdef DSIM_BATCH_PROFILE
        ++batch_stats.entries;
#endif
        for(;;) {
#ifdef DSIM_BATCH_PROFILE
            ++batch_stats.events;
#endif
            evaluate(payload);
            if(finished)return;
            if(active.empty())return;
            auto event=active.front();
#ifdef DSIM_PROCESS_CONTROL_ENABLED
            if(stale_process_ready(event))return;
#endif
#ifdef DSIM_EVENT_NBA_ENABLED
            if(event.event_nba)return;
#endif
#ifdef DSIM_EXPRESSION_EVENTS_ENABLED
            if(event.expression)return;
#endif
#ifdef DSIM_SDF_JOBS_ENABLED
            if(event.sdf_job)return;
#endif
            if(event.process<0||event.wake||event.resume)return;
            auto& next=processes[size_t(event.process)];
            if(next.handler!=handler)return;
#ifdef DSIM_TIMING_ENABLED
            discard_stale_deliveries();
#endif
#ifdef DSIM_PROCESS_CONTROL_ENABLED
            discard_stale_process_timers();
#endif
#ifdef DSIM_PARALLEL_ENABLED
            receive_inputs();
#endif
            // Match run_to: budget failure precedes popping the event, and
            // queued is cleared before rearming/evaluating the next cell.
            step();active.pop();next.queued=false;payload=next.payload;
        }
    }
#endif
    void enqueue(int p) {
        if(processes[p].queued) return;
        processes[p].queued=true;
        Ready event{p,false};
#ifdef DSIM_PROCESS_CONTROL_ENABLED
        event.control_epoch=processes[size_t(p)].control_epoch;
#endif
        active.push(event);
    }
#ifdef DSIM_DYNAMIC_ARRAYS_ENABLED
    static bool dynamic_index(V value,size_t limit,size_t& index) {
        for(int bit=0;bit<value.w;++bit)if(value.bit(bit)>1||(bit>=32&&value.bit(bit)))return false;
        index=size_t(value.a);return index<limit;
    }
    size_t dynamic_size(int id) const {
#ifdef DSIM_OBJECT_ARRAY_REFS_ENABLED
        if(auto* ref=object_array_reference_view(id))return object_queue_size(*ref);
#endif
        auto found=dynamic_arrays.find(dynamic_signal(id));
        return found==dynamic_arrays.end()?0:found->second.size();
    }
    std::vector<V> dynamic_values(int id) const {
#ifdef DSIM_OBJECT_ARRAY_REFS_ENABLED
        if(auto* ref=object_array_reference_view(id))return object_queue_values(*ref);
#endif
        auto found=dynamic_arrays.find(dynamic_signal(id));
        return found==dynamic_arrays.end()?std::vector<V>{}:found->second;
    }
    static V container_default(int width,bool two_state,bool text=false) {
#ifdef DSIM_STRING_ENABLED
        if(text)return V::text("");
#endif
        return two_state?V(0,0,width):V::x(width);
    }
    V dynamic_element_default(int id,int width,bool two_state,bool text=false) const {
#ifdef DSIM_OBJECT_ARRAY_REFS_ENABLED
        if(auto* ref=object_array_reference_view(id))return object_queue_element_default(*ref,width,two_state,text);
#endif
#ifdef DSIM_AGGREGATE_STORAGE_ENABLED
        if(auto meta=dynamic_aggregate_types.find(dynamic_signal(id));meta!=dynamic_aggregate_types.end())return meta->second.initial;
#endif
        return container_default(width,two_state,text);
    }
    V dynamic_element_value(int id,V value,int width,bool two_state) const {
#ifdef DSIM_OBJECT_ARRAY_REFS_ENABLED
        if(auto* ref=object_array_reference_view(id))return object_queue_element_value(*ref,std::move(value),width,two_state);
#endif
        value=value.size(width);
#ifdef DSIM_TWO_STATE_ENABLED
        if(two_state)value=two_state_value(std::move(value));
#endif
#ifdef DSIM_AGGREGATE_STORAGE_ENABLED
        if(auto meta=dynamic_aggregate_types.find(dynamic_signal(id));meta!=dynamic_aggregate_types.end())value=aggregate_element(std::move(value),meta->second);
#endif
        return value;
    }
    V dynamic_read(int id,V index,int width,bool two_state,bool text=false) const {
#ifdef DSIM_OBJECT_ARRAY_REFS_ENABLED
        if(auto* ref=object_array_reference_view(id))return object_queue_read(*ref,index,width,two_state,text);
#endif
        const auto found=dynamic_arrays.find(dynamic_signal(id));
        size_t offset;
        if(found==dynamic_arrays.end()||!dynamic_index(index,found->second.size(),offset))
            return dynamic_element_default(id,width,two_state,text);
        return found->second[offset];
    }
    void dynamic_replace(int id,std::vector<V> values,int width,bool two_state,bool preserve_storage=false) {
#ifdef DSIM_OBJECT_ARRAY_REFS_ENABLED
        if(auto* ref=object_array_reference_view(id)){object_queue_replace(*ref,std::move(values),width,two_state,-1);return;}
#endif
        const int physical=dynamic_signal(id);(void)dynamic_owner(physical);
        if(!preserve_storage) {
            if(dynamic_generation==UINT64_MAX)throw std::runtime_error("dynamic array generation overflow");
            dynamic_generations[physical]=++dynamic_generation;
        }
        for(auto& value:values) {
            value=dynamic_element_value(id,std::move(value),width,two_state);
        }
        dynamic_arrays[physical]=std::move(values);
        set(id,V(get(id).a^1,0,width));
    }
    void dynamic_new(int id,V size,int width,bool two_state,const std::vector<V>& source={},int initializer=-1) {
        size_t length;
        if(!dynamic_index(size,1048577,length))
            throw std::runtime_error("dynamic array size must be known, nonnegative and <=1048576");
        std::vector<V> values(length,dynamic_element_default(id,width,two_state));
        std::copy_n(source.begin(),std::min(source.size(),values.size()),values.begin());
        // VCS retains element identity for a same-length new[n](self),
        // while ordinary whole-array assignment replaces the allocation.
        const bool preserve=initializer>=0&&dynamic_signal(initializer)==dynamic_signal(id)&&length==dynamic_size(id);
        dynamic_replace(id,std::move(values),width,two_state,preserve);
    }
    void fixed_array(int id,int count,int width,bool two_state) {
        if(count<1)throw std::runtime_error("invalid fixed array size");
        dynamic_replace(id,std::vector<V>(size_t(count),container_default(width,two_state)),width,two_state);
        fixed_array_signals.insert(dynamic_signal(id));
    }
#ifdef DSIM_QUEUES_ENABLED
    void queue_replace(int id,std::vector<V> values,int width,bool two_state,int bound) {
#ifdef DSIM_QUEUE_REF_LIMITS_ENABLED
        if(auto limit=queue_reference_limits.find(dynamic_signal(id));limit!=queue_reference_limits.end())bound=limit->second;
#endif
        if(bound>=0&&values.size()>size_t(bound)+1)values.resize(size_t(bound)+1);
        if(values.size()>1048576)throw std::runtime_error("queue size exceeds 1048576 elements");
        dynamic_replace(id,std::move(values),width,two_state);
    }
    void queue_notify(int id,int width) {set(id,V(get(id).a^1,0,width));}
    V queue_method(int id,int operation,V index,V value,int width,bool two_state,int bound,bool text=false) {
#ifdef DSIM_QUEUE_REF_LIMITS_ENABLED
        if(auto limit=queue_reference_limits.find(dynamic_signal(id));limit!=queue_reference_limits.end())bound=limit->second;
#endif
#ifdef DSIM_OBJECT_ARRAY_REFS_ENABLED
        if(auto* ref=object_array_reference_view(id))return object_queue_method(*ref,operation,index,std::move(value),width,two_state,bound,text);
#endif
        const int physical=dynamic_signal(id);(void)dynamic_owner(physical);
        if((operation==2||operation==3)&&dynamic_arrays[physical].empty())return dynamic_element_default(id,width,two_state,text);
        value=dynamic_element_value(id,std::move(value),width,two_state);
        bool changed=false;auto result=queue_change(dynamic_arrays[physical],operation,index,value,width,two_state,bound,changed,text);
        if(changed)queue_notify(id,width);return result;
    }
    static V queue_change(std::vector<V>& values,int operation,V index,V value,int width,bool two_state,int bound,bool& changed,bool text=false) {
        V result=container_default(width,two_state,text);size_t offset=0;
        value=value.size(width);
#ifdef DSIM_TWO_STATE_ENABLED
        if(two_state)value=two_state_value(value);
#endif
        // 0/1 push back/front, 2/3 pop back/front, 4 insert, 5 delete(index), 6 delete all.
        if(operation<=1) {
            if(operation==0&&bound>=0&&values.size()>size_t(bound))return result;
            values.insert(operation==0?values.end():values.begin(),value);
        } else if(operation<=3) {
            if(values.empty())return result;
            auto it=operation==2?values.end()-1:values.begin();result=*it;values.erase(it);
        } else if(operation==4) {
            if(!dynamic_index(index,values.size()+1,offset))return result;
            values.insert(values.begin()+offset,value);
        } else if(operation==5) {
            if(!dynamic_index(index,values.size(),offset))return result;
            values.erase(values.begin()+offset);
        } else values.clear();
        if(bound>=0&&values.size()>size_t(bound)+1)values.resize(size_t(bound)+1);
        if(values.size()>1048576)throw std::runtime_error("queue size exceeds 1048576 elements");
        changed=true;return result;
    }
    void queue_write(int id,V index,V value,int width,bool two_state,int bound) {
        size_t offset;const auto length=dynamic_size(id);
        if(dynamic_index(index,length+1,offset)&&offset==length) {
            (void)queue_method(id,0,V(0),value,width,two_state,bound);return;
        }
        dynamic_write(id,index,value,width,two_state);
    }
    void queue_write_slice(int id,V index,Part part,V value,bool two_state,int bound) {
        if(!part.width)return;
        size_t offset;const auto length=dynamic_size(id);
        const int width=signals[size_t(dynamic_signal(id))].value.w;
        if(dynamic_index(index,length+1,offset)&&offset==length) {
            auto previous=two_state?V(0,0,width):V::x(width);
            auto next=replace(previous,part.lo,part.width,slice(value,part.rhs_lo,part.width));
            queue_write(id,index,std::move(next),width,two_state,bound);return;
        }
        dynamic_write_slice(id,index,part,value,two_state);
    }

#ifdef DSIM_OBJECTS_ENABLED
#ifdef DSIM_OBJECT_ARRAY_REFS_ENABLED
    int object_array_reference(ObjectQueueRef ref,int width,int bound) {
        const auto key=std::make_pair(ref.object,ref.field);
        if(auto found=object_array_signals.find(key);found!=object_array_signals.end())return found->second;
        if(signals.size()>=size_t(INT32_MAX))throw std::runtime_error("too many class array references");
        if(activation_first_signal==SIZE_MAX)activation_first_signal=signals.size();
        const int id=int(signals.size());signals.push_back({V(0,0,width),false,false,{},{}});
#ifdef DSIM_COMPACT_GATES
        if(next_signal_order==UINT64_MAX)throw std::runtime_error("signal order overflow");
        signal_orders.push_back(next_signal_order++);
#endif
#ifdef DSIM_PATH_ENABLED
        path_stamps.emplace_back();
#endif
        object_array_signals.emplace(key,id);object_array_references.emplace(id,ref);
#ifdef DSIM_QUEUE_REF_LIMITS_ENABLED
        if(bound>=-1)queue_reference_limits.emplace(id,bound);
#else
        (void)bound;
#endif
        return id;
    }
#endif
    ObjectQueueRef object_queue(V handle,int type,size_t field,int dependency) const {
        const auto object=object_index(handle,type);(void)objects.at(object).fields.at(field);
        return {object,field,dependency};
    }
    const std::vector<V>& object_queue_values(ObjectQueueRef ref) const {
        const auto& queues=objects.at(ref.object).queues;auto found=queues.find(ref.field);
        static const std::vector<V> empty;return found==queues.end()?empty:found->second;
    }
    size_t object_queue_size(ObjectQueueRef ref) const {return object_queue_values(ref).size();}
    V object_queue_element_default(ObjectQueueRef ref,int width,bool two_state,bool text=false) const {
#ifdef DSIM_AGGREGATE_STORAGE_ENABLED
        if(auto meta=object_aggregate_types.find({objects.at(ref.object).type,ref.field});meta!=object_aggregate_types.end())return meta->second.initial;
#endif
        return container_default(width,two_state,text);
    }
    V object_queue_element_value(ObjectQueueRef ref,V value,int width,bool two_state) const {
        value=value.size(width);
#ifdef DSIM_TWO_STATE_ENABLED
        if(two_state)value=two_state_value(std::move(value));
#endif
#ifdef DSIM_AGGREGATE_STORAGE_ENABLED
        if(auto meta=object_aggregate_types.find({objects.at(ref.object).type,ref.field});meta!=object_aggregate_types.end())value=aggregate_element(std::move(value),meta->second);
#endif
        return value;
    }
    V object_queue_read(ObjectQueueRef ref,V index,int width,bool two_state,bool text=false) const {
        const auto& values=object_queue_values(ref);size_t offset;
        if(!dynamic_index(index,values.size(),offset))return object_queue_element_default(ref,width,two_state,text);
        return values[offset];
    }
    void object_queue_notify(ObjectQueueRef ref) {
        set(ref.dependency,V(get(ref.dependency).a+1,0,64));
#ifdef DSIM_OBJECT_ARRAY_REFS_ENABLED
        if(auto found=object_array_signals.find({ref.object,ref.field});found!=object_array_signals.end()) {
            const int id=found->second;set(id,V(get(id).a^1,0,signals.at(size_t(id)).value.w));
        }
#endif
    }
    void object_queue_replace(ObjectQueueRef ref,std::vector<V> values,int width,bool two_state,int bound) {
        if(bound>=0&&values.size()>size_t(bound)+1)values.resize(size_t(bound)+1);
        if(values.size()>1048576)throw std::runtime_error("queue size exceeds 1048576 elements");
        for(auto& value:values) {
            value=object_queue_element_value(ref,std::move(value),width,two_state);
        }
        objects.at(ref.object).queues[ref.field]=std::move(values);object_queue_notify(ref);
    }
    void object_dynamic_new(ObjectQueueRef ref,V size,int width,bool two_state,const std::vector<V>& source={},bool text=false) {
        size_t length;
        if(!dynamic_index(size,1048577,length))throw std::runtime_error("dynamic array size must be known, nonnegative and <=1048576");
        std::vector<V> values(length,object_queue_element_default(ref,width,two_state,text));
        std::copy_n(source.begin(),std::min(source.size(),length),values.begin());
        object_queue_replace(ref,std::move(values),width,two_state,-1);
    }
    V object_queue_method(ObjectQueueRef ref,int operation,V index,V value,int width,bool two_state,int bound,bool text=false) {
        if((operation==2||operation==3)&&object_queue_values(ref).empty())return object_queue_element_default(ref,width,two_state,text);
        value=object_queue_element_value(ref,std::move(value),width,two_state);
        bool changed=false;auto result=queue_change(objects.at(ref.object).queues[ref.field],operation,index,value,width,two_state,bound,changed,text);
        if(changed)object_queue_notify(ref);return result;
    }
    void object_queue_write(ObjectQueueRef ref,V index,V value,int width,bool two_state,int bound) {
        size_t offset;const auto length=object_queue_size(ref);
        if(!dynamic_index(index,length+1,offset))return;
        if(offset==length){if(bound!=-2)(void)object_queue_method(ref,0,V(0),value,width,two_state,bound);return;}
        value=object_queue_element_value(ref,std::move(value),width,two_state);
        auto& previous=objects.at(ref.object).queues.at(ref.field).at(offset);
        if(previous.same(value))return;previous=std::move(value);object_queue_notify(ref);
    }
    void object_queue_write_slice(ObjectQueueRef ref,V index,Part part,V value,bool two_state,int width,int bound) {
        if(!part.width)return;
        auto previous=object_queue_read(ref,index,width,two_state);
        object_queue_write(ref,index,replace(previous,part.lo,part.width,slice(value,part.rhs_lo,part.width)),width,two_state,bound);
    }
#endif

#endif
#ifdef DSIM_ASSOCIATIVE_ARRAYS_ENABLED
#ifdef DSIM_ASSOCIATIVE_REFS_ENABLED
    AssociativeRef resolve_associative_reference(AssociativeRef ref) const {
        if(ref.object<0)if(auto found=associative_reference_views.find(dynamic_signal(ref.signal));found!=associative_reference_views.end()) {
            auto actual=found->second;
            actual.path.insert(actual.path.end(),ref.path.begin(),ref.path.end());
            if(ref.explicit_key_type) {
                actual.unsigned_key=ref.unsigned_key;actual.class_key=ref.class_key;actual.explicit_key_type=true;
            }
            return actual;
        }
        return ref;
    }
#endif
    AssociativeRef associative_ref(int id) const {return AssociativeRef(id);}
    void associative_set_unsigned(int id) {unsigned_associative_signals.insert(id);}
    void associative_set_class(int id) {class_associative_signals.insert(id);}
    bool associative_key(AssociativeRef ref,V value,AssociativeKey& key) const {
#ifdef DSIM_ASSOCIATIVE_REFS_ENABLED
        ref=resolve_associative_reference(std::move(ref));
#endif
#ifdef DSIM_STRING_ENABLED
        if(value.text_data){key.text=value.text_data;return true;}
        key.text.reset();
#endif
        key.object_key=ref.class_key||(!ref.explicit_key_type&&class_associative_signals.count(ref.signal));
        if(key.object_key) {value=value.size(64);if(value.b)return false;key.object_identity=value.a;return true;}
#ifdef DSIM_WIDE_VALUES
        if(value.unknown())return false;
#else
        if(value.b)return false;
#endif
        key.negative=!(ref.unsigned_key||(!ref.explicit_key_type&&unsigned_associative_signals.count(ref.signal)))&&value.bit(value.w-1)==1;
        key.integral=std::move(value);return true;
    }
    AssociativeRef associative_subarray(AssociativeRef ref,V index,bool unsigned_key=false,bool class_key=false) const {
#ifdef DSIM_ASSOCIATIVE_REFS_ENABLED
        ref=resolve_associative_reference(std::move(ref));
#endif
        AssociativeKey key;
        if(!associative_key(ref,index,key))throw std::runtime_error("associative array index contains X/Z");
        ref.path.push_back(std::move(key));ref.unsigned_key=unsigned_key;ref.class_key=class_key;ref.explicit_key_type=true;
        return ref;
    }
    const AssociativeArray* associative_find(AssociativeRef ref) const {
#ifdef DSIM_ASSOCIATIVE_REFS_ENABLED
        ref=resolve_associative_reference(std::move(ref));
#endif
        const AssociativeArray* array=nullptr;
#ifdef DSIM_OBJECTS_ENABLED
        if(ref.object>=0) {
            const auto& maps=objects.at(size_t(ref.object)).associative;
            auto it=maps.find(ref.field);if(it!=maps.end())array=&it->second;
        } else
#endif
        {
            auto it=associative_arrays.find(dynamic_signal(ref.signal));if(it!=associative_arrays.end())array=&it->second;
        }
        for(const auto& key:ref.path) {
            if(!array)return nullptr;
            auto it=array->children.find(key);array=it==array->children.end()?nullptr:&it->second;
        }
        return array;
    }
    AssociativeArray& associative_storage(AssociativeRef ref) {
#ifdef DSIM_ASSOCIATIVE_REFS_ENABLED
        ref=resolve_associative_reference(std::move(ref));
#endif
        AssociativeArray* array=nullptr;
#ifdef DSIM_OBJECTS_ENABLED
        if(ref.object>=0)array=&objects.at(size_t(ref.object)).associative[ref.field];
        else
#endif
        {
            const int physical=dynamic_signal(ref.signal);(void)dynamic_owner(physical);
            array=&associative_arrays[physical];
        }
        for(const auto& key:ref.path) {
            if(!array->count(key)&&array->size()>=1048576)throw std::runtime_error("associative array exceeds 1048576 elements");
            array->emplace(key,V(0));array=&array->children[key];
        }
        return *array;
    }
    size_t associative_size(AssociativeRef ref) const {
        const auto* array=associative_find(ref);return array?array->size():0;
    }
    bool associative_exists(AssociativeRef ref,V index) const {
        AssociativeKey key;const auto* array=associative_find(ref);
        return associative_key(ref,index,key)&&array&&array->count(key);
    }
#ifdef DSIM_AGGREGATE_STORAGE_ENABLED
    const AggregateType* associative_element_type(AssociativeRef ref) const {
#ifdef DSIM_ASSOCIATIVE_REFS_ENABLED
        ref=resolve_associative_reference(std::move(ref));
#endif
#ifdef DSIM_OBJECTS_ENABLED
        if(ref.object>=0) {
            auto meta=object_aggregate_types.find({objects.at(size_t(ref.object)).type,ref.field});
            return meta==object_aggregate_types.end()?nullptr:&meta->second;
        }
#endif
        auto meta=dynamic_aggregate_types.find(dynamic_signal(ref.signal));
        return meta==dynamic_aggregate_types.end()?nullptr:&meta->second;
    }
#endif
    V associative_element_default(AssociativeRef ref,int width,bool two_state) const {
#ifdef DSIM_ASSOCIATIVE_REFS_ENABLED
        ref=resolve_associative_reference(std::move(ref));
#endif
#if defined(DSIM_OBJECTS_ENABLED) && defined(DSIM_STRING_ENABLED)
        if(ref.object>=0&&object_string_associatives.count({objects.at(size_t(ref.object)).type,ref.field}))return V::text("");
#endif
#ifdef DSIM_AGGREGATE_STORAGE_ENABLED
        if(auto* type=associative_element_type(ref))return type->initial;
#endif
        return container_default(width,two_state);
    }
    V associative_element_value(AssociativeRef ref,V value,int width,bool two_state) const {
        value=value.size(width);
#ifdef DSIM_TWO_STATE_ENABLED
        if(two_state)value=two_state_value(std::move(value));
#endif
#ifdef DSIM_AGGREGATE_STORAGE_ENABLED
        if(auto* type=associative_element_type(ref))value=aggregate_element(std::move(value),*type);
#endif
        return value;
    }
    V associative_read(AssociativeRef ref,V index,int width,bool two_state) const {
        AssociativeKey key;if(!associative_key(ref,index,key))throw std::runtime_error("associative array read index contains X/Z");
        const auto* array=associative_find(ref);
        if(array) {
            auto element=array->find(key);if(element!=array->end())return element->second;
        }
        return associative_element_default(ref,width,two_state);
    }
    std::vector<V> associative_values(AssociativeRef ref) const {
        std::vector<V> result;const auto* array=associative_find(ref);
        if(array)for(const auto& pair:*array)result.push_back(pair.second);
        return result;
    }
    void associative_notify(AssociativeRef ref,int width) {
#ifdef DSIM_ASSOCIATIVE_REFS_ENABLED
        ref=resolve_associative_reference(std::move(ref));
#endif
        if(ref.object>=0)set(ref.dependency,V(get(ref.dependency).a+1,0,64));
        else set(ref.signal,V(get(ref.signal).a^1,0,width));
#ifdef DSIM_ASSOCIATIVE_REFS_ENABLED
        if(ref.object>=0)if(auto found=object_associative_signals.find({size_t(ref.object),ref.field});found!=object_associative_signals.end()) {
            const int id=found->second;set(id,V(get(id).a^1,0,signals.at(size_t(id)).value.w));
        }
#endif
    }
#ifdef DSIM_QUEUES_ENABLED
    const std::vector<V>& associative_queue_values(AssociativeRef ref) const {
        const auto* array=associative_find(ref);static const std::vector<V> empty;
        return array?array->queue:empty;
    }
    size_t associative_queue_size(AssociativeRef ref) const {return associative_queue_values(ref).size();}
    V associative_queue_read(AssociativeRef ref,V index,int width,bool two_state,bool text=false) const {
        const auto& values=associative_queue_values(ref);size_t offset;
        return dynamic_index(index,values.size(),offset)?values[offset]:container_default(width,two_state,text);
    }
    void associative_queue_replace(AssociativeRef ref,std::vector<V> values,int width,bool two_state,int bound) {
        if(bound>=0&&values.size()>size_t(bound)+1)values.resize(size_t(bound)+1);
        if(values.size()>1048576)throw std::runtime_error("queue size exceeds 1048576 elements");
        for(auto& value:values) {
            value=value.size(width);
#ifdef DSIM_TWO_STATE_ENABLED
            if(two_state)value=two_state_value(value);
#endif
        }
        associative_storage(ref).queue=std::move(values);associative_notify(ref,width);
    }
    V associative_queue_method(AssociativeRef ref,int operation,V index,V value,int width,bool two_state,int bound,bool text=false) {
        const bool existed=associative_find(ref)!=nullptr;bool changed=false;
        auto result=queue_change(associative_storage(ref).queue,operation,index,value,width,two_state,bound,changed,text);
        if(changed||!existed)associative_notify(ref,width);return result;
    }
    void associative_queue_write(AssociativeRef ref,V index,V value,int width,bool two_state,int bound) {
        // Selecting an associative element as an lvalue creates its queue even
        // when the following queue index cannot be written.
        if(!associative_find(ref)){(void)associative_storage(ref);associative_notify(ref,width);}
        size_t offset;const auto length=associative_queue_size(ref);
        if(!dynamic_index(index,length+1,offset))return;
        if(offset==length){(void)associative_queue_method(ref,0,V(0),value,width,two_state,bound);return;}
        value=value.size(width);
#ifdef DSIM_TWO_STATE_ENABLED
        if(two_state)value=two_state_value(value);
#endif
        auto& previous=associative_storage(ref).queue.at(offset);
        if(previous.same(value))return;previous=std::move(value);associative_notify(ref,width);
    }
    void associative_queue_write_slice(AssociativeRef ref,V index,Part part,V value,bool two_state,int width,int bound) {
        if(!part.width)return;
        auto previous=associative_queue_read(ref,index,width,two_state);
        associative_queue_write(ref,index,replace(previous,part.lo,part.width,slice(value,part.rhs_lo,part.width)),width,two_state,bound);
    }
#endif
    AssociativeArray associative_snapshot(AssociativeRef source) const {
        const auto* old=associative_find(source);return old?*old:AssociativeArray{};
    }
    void associative_restore(AssociativeRef ref,AssociativeArray values,int width,bool two_state=false) {
        bool normalize=two_state;
#ifdef DSIM_AGGREGATE_STORAGE_ENABLED
        normalize=normalize||associative_element_type(ref)!=nullptr;
#endif
        if(normalize) {
            std::function<void(AssociativeArray&)> convert=[&](AssociativeArray& array) {
                for(auto& pair:array)if(!array.children.count(pair.first))
                    pair.second=associative_element_value(ref,std::move(pair.second),width,two_state);
#ifdef DSIM_QUEUES_ENABLED
                for(auto& value:array.queue)value=associative_element_value(ref,std::move(value),width,two_state);
#endif
                for(auto& pair:array.children)convert(pair.second);
            };convert(values);
        }
        associative_storage(ref)=std::move(values);associative_notify(ref,width);
    }
    void associative_replace(AssociativeRef ref,AssociativeRef source,int width,bool two_state=false) {
        associative_restore(ref,associative_snapshot(source),width,two_state);
    }
    void associative_write(AssociativeRef ref,V index,V value,int width,bool two_state) {
        AssociativeKey key;if(!associative_key(ref,index,key))throw std::runtime_error("associative array write index contains X/Z");
        value=associative_element_value(ref,std::move(value),width,two_state);
        auto& array=associative_storage(ref);auto found=array.find(key);
        if(found!=array.end()&&found->second.same(value))return;
        if(found==array.end()&&array.size()>=1048576)throw std::runtime_error("associative array exceeds 1048576 elements");
        array[std::move(key)]=std::move(value);associative_notify(ref,width);
    }
    void associative_write_slice(AssociativeRef ref,V index,Part part,V value,bool two_state) {
        if(!part.width)return;
        const int width=ref.object>=0?ref.width:signals[size_t(dynamic_signal(ref.signal))].value.w;
        auto previous=associative_read(ref,index,width,two_state);
        auto next=replace(previous,part.lo,part.width,slice(value,part.rhs_lo,part.width));
        associative_write(ref,index,std::move(next),previous.w,two_state);
    }
    void associative_delete(AssociativeRef ref,V index,bool all,int width) {
        const auto* previous=associative_find(ref);if(!previous||previous->empty())return;
        auto& array=associative_storage(ref);
        if(all){array.clear();array.children.clear();}
        else {AssociativeKey key;if(!associative_key(ref,index,key)||!array.erase(key))return;array.children.erase(key);}
        associative_notify(ref,width);
    }
    bool associative_cursor(AssociativeRef ref,V& index,int operation) const {
        const auto* found=associative_find(ref);if(!found||found->empty())return false;
        const auto& array=*found;auto it=array.begin();AssociativeKey key;
        if(operation==1)it=std::prev(array.end());
        else if(operation>=2) {
            if(!associative_key(ref,index,key))return false;
            if(operation==2)it=array.upper_bound(key);
            else {it=array.lower_bound(key);if(it==array.begin())return false;--it;}
        }
        if(it==array.end())return false;
#ifdef DSIM_STRING_ENABLED
        if(it->first.text){index=V::text(*it->first.text);return true;}
#endif
        index=it->first.object_key?V(it->first.object_identity,0,64):it->first.integral;return true;
    }
#ifdef DSIM_OBJECTS_ENABLED
#ifdef DSIM_ASSOCIATIVE_REFS_ENABLED
    int object_associative_reference(AssociativeRef ref,int width) {
        const auto key=std::make_pair(size_t(ref.object),ref.field);
        if(ref.object<0||!ref.path.empty())throw std::runtime_error("associative ref requires a whole class member");
        if(auto found=object_associative_signals.find(key);found!=object_associative_signals.end())return found->second;
        if(signals.size()>=size_t(INT32_MAX))throw std::runtime_error("too many associative references");
        if(activation_first_signal==SIZE_MAX)activation_first_signal=signals.size();
        const int id=int(signals.size());signals.push_back({V(0,0,width),false,false,{},{}});
#ifdef DSIM_COMPACT_GATES
        if(next_signal_order==UINT64_MAX)throw std::runtime_error("signal order overflow");
        signal_orders.push_back(next_signal_order++);
#endif
#ifdef DSIM_PATH_ENABLED
        path_stamps.emplace_back();
#endif
        object_associative_signals.emplace(key,id);associative_reference_views.emplace(id,std::move(ref));return id;
    }
#endif
#ifdef DSIM_STRING_ENABLED
    void object_associative_string(int type,size_t field) {object_string_associatives.emplace(type,field);}
#endif
    AssociativeRef object_associative(V handle,int type,size_t field,int width,int dependency,bool unsigned_key=false,bool class_key=false) const {
        AssociativeRef ref(dependency);ref.object=int(object_index(handle,type));ref.field=field;ref.width=width;ref.unsigned_key=unsigned_key;ref.class_key=class_key;
        (void)objects.at(size_t(ref.object)).fields.at(field);return ref;
    }
#endif

#endif
    Part dynamic_part(int id,V index,int width,bool event=false,bool ignore_invalid=false) {
#ifdef DSIM_OBJECT_ARRAY_REFS_ENABLED
        if(object_array_reference_view(id))throw std::runtime_error("nonblocking assignment through a class array ref is not supported yet");
#endif
        const int physical=dynamic_signal(id);size_t offset;
        Part part{physical,0,width,0};
        if(event) {
            // Event-controlled NBA snapshots the index but resolves storage
            // when the event matures. Keep the descriptor invocation, so a
            // reused automatic slot cannot receive an older call's update.
            part.dynamic_generation=dynamic_owner(physical);part.dynamic_event=true;
            const size_t limit=fixed_array_signals.count(physical)?dynamic_size(id):1048576;
            part.dynamic_index=dynamic_index(index,limit,offset)?int(offset):-2;
        } else {
            auto found=dynamic_arrays.find(physical);
            if(found==dynamic_arrays.end()||!dynamic_index(index,found->second.size(),offset)) {
                if(ignore_invalid||fixed_array_signals.count(physical))return {physical,0,0,0};
                throw std::runtime_error("nonblocking dynamic array index is unknown or out of range");
            }
            part.dynamic_generation=dynamic_generations.at(physical);part.dynamic_index=int(offset);
        }
        return part;
    }
    void dynamic_write(int id,V index,V value,int width,bool two_state) {
#ifdef DSIM_OBJECT_ARRAY_REFS_ENABLED
        if(auto* ref=object_array_reference_view(id)){object_queue_write(*ref,index,std::move(value),width,two_state,-2);return;}
#endif
        auto found=dynamic_arrays.find(dynamic_signal(id));
        size_t offset;
        if(found==dynamic_arrays.end()||!dynamic_index(index,found->second.size(),offset))return;
        value=dynamic_element_value(id,std::move(value),width,two_state);
        if(found->second[offset].same(value))return;
        found->second[offset]=std::move(value);
        set(id,V(get(id).a^1,0,width));
    }
    void dynamic_write_slice(int id,V index,Part part,V value,bool two_state) {
#ifdef DSIM_OBJECT_ARRAY_REFS_ENABLED
        if(auto* ref=object_array_reference_view(id)){const int width=signals.at(size_t(dynamic_signal(id))).value.w;object_queue_write_slice(*ref,index,part,std::move(value),two_state,width,-2);return;}
#endif
        if(!part.width)return;
        auto found=dynamic_arrays.find(dynamic_signal(id));size_t offset;
        if(found==dynamic_arrays.end()||!dynamic_index(index,found->second.size(),offset))return;
        // Merge when the update commits, so another assignment to disjoint bits
        // of this element is preserved, including queued NBA updates.
        const auto& previous=found->second[offset];
        auto selected=slice(value,part.rhs_lo,part.width);
        auto next=!part.lo&&part.width==previous.w?std::move(selected):replace(previous,part.lo,part.width,std::move(selected));
        const int width=previous.w;
        next=dynamic_element_value(id,std::move(next),width,two_state);
        if(previous.same(next))return;
        found->second[offset]=std::move(next);
        set(id,V(get(id).a^1,0,width));
    }
#endif
    // A generated, non-suspending scalar loop may borrow these values only
    // after this guard. No writes may bypass an event, observer or force.
    template<bool Known> bool scalar_storage_ready(std::initializer_list<int> ids) const {
#if defined(DSIM_DYNAMIC_FORK_ENABLED) || defined(DSIM_PROPERTY_ENABLED) || defined(DSIM_CHECKS_ENABLED) || defined(DSIM_PATH_ENABLED) || defined(DSIM_WAVE_ENABLED)
        (void)ids;return false;
#else
#ifdef DSIM_PARALLEL_ENABLED
        if(resolved_observer)return false;
#endif
        for(int id:ids) {
            if(id<0||size_t(id)>=signals.size())return false;
            const auto& signal=signals[size_t(id)];
            if(signal.net||signal.aliased||!signal.watches.empty()||signal.value.w>64||(Known&&signal.value.b))return false;
#ifdef DSIM_FORCE_ENABLED
            if(forced_values.count(id))return false;
#endif
#ifdef DSIM_MIXED_STATE_ENABLED
            if(signal.state_mask>=0)return false;
#endif
        }
        return true;
#endif
    }
    bool function_locals_ready(std::initializer_list<int> ids) const {return scalar_storage_ready<false>(ids);}
    bool integral_loop_ready(std::initializer_list<int> ids) const {return scalar_storage_ready<true>(ids);}
    V& integral_loop_value(int id) {return signals[size_t(id)].value;}
    // Reserve a complete, nonthrowing iteration. Near the limit generated
    // code resumes the original PC path, preserving the exact failing step.
    bool integral_loop_steps(uint64_t count) {
        if(steps>limit||count>limit-steps)return false;
        steps+=count;return true;
    }
#ifdef DSIM_COMB_LEAF_ENABLED
    // Dispatch is charged by run_to. The exact wait/store/return body has no
    // internal suspension or budgeted expression; otherwise use its old PC.
    bool begin_comb_leaf() {
        if(!integral_loop_steps(3))return false;
#ifdef DSIM_SCHEDULING_STATS
        ++comb_leaf_runs;
#endif
        return true;
    }
#endif
#ifdef DSIM_COMB_LEAF_BATCH_ENABLED
    // Only generated, pure, three-instruction RTL leaves may use this handler.
    // Retain the owning action (and its PC) for partial-budget execution.
    void bind_comb_leaf(int process,uint32_t handler) {
        structural_change();
        auto& p=processes.at(size_t(process));
        if(handler>=handlers.size()||p.handler!=UINT32_MAX||p.payload!=uint32_t(process))
            throw std::runtime_error("invalid combinational leaf binding");
        p.handler=handler;
    }
    template<class Evaluate> void compiled_leaf_batch(uint32_t handler,uint32_t payload,Evaluate evaluate) {
#ifdef DSIM_SCHEDULING_STATS
        ++comb_leaf_batch_entries;
#endif
        if(!begin_comb_leaf()) {
            // The original action may stop with a nonzero PC. Keep all later
            // activations on that action, including checkpoint/replay.
            processes[payload].handler=UINT32_MAX;
            actions[payload]();return;
        }
        for(;;) {
#ifdef DSIM_SCHEDULING_STATS
            ++comb_leaf_batch_events;
#endif
            evaluate(payload);
            if(finished||active.empty())return;
            const auto event=active.front();
            if(event.process<0||event.wake||event.resume)return;
            auto& next=processes[size_t(event.process)];
            if(next.handler!=handler)return;
            // Leave an incomplete activation to run_to and the owning PC.
            // Reserve one dispatch plus wait/store/return before popping.
            if(!integral_loop_steps(4))return;
            active.pop();next.queued=false;payload=next.payload;
#ifdef DSIM_SELECTION_CHECKS_ENABLED
            selection_process=event.process;
#endif
#ifdef DSIM_RANDOM_ENABLED
            random_process=event.process;
#endif
#ifdef DSIM_SCHEDULING_STATS
            ++comb_leaf_runs;
#endif
        }
    }
#endif
#if !defined(DSIM_WIDE_VALUES) && !defined(DSIM_STRING_ENABLED) && !defined(DSIM_REAL_ENABLED) && !defined(DSIM_REFERENCE_SCALAR_STORES)
#ifdef DSIM_TYPED_STORES_ENABLED
    // Generated whole-program stores supply a valid signal ID and its fixed
    // width. Normalize at the caller, then share the complete publication path.
    // No notification, observer or queue boundary is bypassed.
    template<int Width> void set_sized(int id,V value) {
        static_assert(Width>0&&Width<=64,"invalid generated scalar width");
        const auto av=value.a&mask(Width),bv=value.b&mask(Width);
        const auto& previous=signals[size_t(id)].value;
        if(previous.a==av&&previous.b==bv)return;
        set_planes<true>(id,av,bv);
    }
#endif
    // Pass scalar bit planes in registers across the out-of-line store. The
    // public V API and the complete change/notification path stay shared.
    void set(int id,V value
#ifdef DSIM_OBJECT_SCALAR_REFS_ENABLED
        ,bool reference_update=false
#endif
    ) {set_planes(id,value.a,value.b
#ifdef DSIM_OBJECT_SCALAR_REFS_ENABLED
        ,reference_update
#endif
    );}
#ifdef DSIM_TYPED_STORES_ENABLED
    // Instantiate both entry contracts from one notification implementation.
    // Generic stores retain their normalization and comparison in this call;
    // prepared stores have already performed those operations at the caller.
    template<bool Prepared=false>
#endif
    void set_planes(int id,uint64_t av,uint64_t bv
#ifdef DSIM_OBJECT_SCALAR_REFS_ENABLED
        ,bool reference_update=false
#endif
    ) {
        V value(av,bv,64);
#else
    void set(int id,V value
#ifdef DSIM_OBJECT_SCALAR_REFS_ENABLED
        ,bool reference_update=false
#endif
    ) {
#endif
#ifdef DSIM_DYNAMIC_FORK_ENABLED
        id=activation_signal(id);
#endif
#ifdef DSIM_COMPACT_GATES
        if(id<0){set_compact(id,value);return;}
#endif
#ifdef DSIM_FORCE_ENABLED
        if(!updating_force&&forced_values.count(id))return;
#endif
#ifdef DSIM_TYPED_STORES_ENABLED
        auto& s=[&]() -> Signal& {if constexpr(Prepared)return signals[size_t(id)];else return signals.at(id);}();
        if constexpr(!Prepared) {
#else
        auto& s=signals.at(id);
#endif
        value=value.size(s.value.w);
#ifdef DSIM_REAL_ENABLED
        value=real_convert(value,s.real_width,s.value.w);
#endif
#ifdef DSIM_TWO_STATE_ENABLED
        if(s.two_state)value=two_state_value(std::move(value));
#endif
#ifdef DSIM_MIXED_STATE_ENABLED
        if(s.state_mask>=0)value=masked_two_state_value(std::move(value),state_masks[size_t(s.state_mask)]);
#endif
#ifdef DSIM_TYPED_STORES_ENABLED
        }
#endif
#ifdef DSIM_OBJECT_SCALAR_REFS_ENABLED
        if(!reference_update)if(auto found=object_scalar_references.find(id);found!=object_scalar_references.end()) {
            const auto ref=found->second;
            object_set(V(uint64_t(ref.object)+1,0,64),ref.type,ref.field,std::move(value),ref.dependency);return;
        }
#endif
        V old=s.value;
#ifdef DSIM_TYPED_STORES_ENABLED
        if constexpr(!Prepared)
#endif
        if(old.same(value)) return;
#ifdef DSIM_TYPED_STORES_ENABLED
        if constexpr(Prepared)value.w=old.w;
#endif
        s.value=value;
#ifdef DSIM_PROPERTY_ENABLED
        property_changed(id,old,value);
#endif
#ifdef DSIM_CHECKS_ENABLED
        record_check_change(id,old.bit(0),value.bit(0));
#endif
#ifdef DSIM_PATH_ENABLED
        record_path_change(id,old,value);
#endif
#ifdef DSIM_WAVE_ENABLED
        record_wave_change(id,value);
#endif
#ifdef DSIM_PARALLEL_ENABLED
        if(resolved_observer) {
            if(speculating)speculative_effects.push_back([observer=resolved_observer,time=now,id,value]{observer(time,id,value);});
            else resolved_observer(now,id,value);
        }
#endif
        if(s.watches.empty()) return;
#if !defined(DSIM_REFERENCE_EDGE_MASKS) && !defined(DSIM_WIDE_VALUES) && !defined(DSIM_STRING_ENABLED) && !defined(DSIM_COMPACT_GATES)
        // Both X and Z have identical edge rules. Index their native bit planes
        // directly; vector change events still fire for changes above bit zero.
        static constexpr uint8_t edge_masks[16]={4,6,6,6,5,4,5,5,5,6,4,4,5,6,4,4};
        const unsigned key=unsigned((old.a&1)|((old.b&1)<<1)|((value.a&1)<<2)|((value.b&1)<<3));
        const int edges=edge_masks[key];
#else
        int a=old.bit(0),b=value.bit(0);
        bool pos=(a==0 && b!=0)||(a>=2 && b==1);
        bool neg=(a==1 && b!=1)||(a>=2 && b==0);
        int edges=4|(pos?1:0)|(neg?2:0);
#endif
        for(const auto& w:s.watches) {
#ifdef DSIM_COMB_REGION_ENABLED
#ifdef DSIM_MASKED_COMB_REGION_ENABLED
            if(w.process<0){notify_masked_comb_region(-1-w.process,w.generation);continue;}
#else
            if(w.process<0){notify_comb_region(-1-w.process);continue;}
#endif
#endif
#ifdef DSIM_SDF_JOBS_ENABLED
            if(w.process<0){if(w.edges&edges)wake_sdf_job(w.process);continue;}
#endif
#ifdef DSIM_EVENT_NBA_ENABLED
            if(w.edges==-1){notify_event_nba(w.process,edges);continue;}
#endif
#ifdef DSIM_EXPRESSION_EVENTS_ENABLED
            if(w.edges>=64){
#ifdef DSIM_DYNAMIC_FORK_ENABLED
                // A subscription on a former automatic frame must never
                // evaluate using its process's newer invocation.
                const auto& owner=processes[size_t(w.process)];
                if(owner.activation&&(!owner.waiting||owner.generation!=w.generation))continue;
#endif
                queue_expression_wait((w.edges>>6)-1,w.generation);continue;
            }
#endif
            auto& p=processes[w.process];
            if(!p.waiting||p.generation!=w.generation)continue;
            if(w.edges&edges) {
#ifdef DSIM_SELECTION_CHECKS_ENABLED
                flush_selection_reports(w.process);
#endif
                p.waiting=false; enqueue(w.process); }
        }
    }
#ifdef DSIM_FORCE_ENABLED
    bool force_active(int id,int owner) const {
        auto found=forced_values.find(id);return found!=forced_values.end()&&found->second.owner==owner;
    }
    void force_value(int id,int owner,V value) {
        if(signals.at(id).aliased)throw std::runtime_error("force on an aliased net is not supported yet");
        value=value.size(signals.at(id).value.w);forced_values[id]={owner,value};
        updating_force=true;
        try{set(id,std::move(value));}catch(...){updating_force=false;throw;}
        updating_force=false;
    }
    void release_value(int id) {
        if(!forced_values.erase(id))return;
        // A variable retains its forced value; a net resumes its stored drivers.
        if(signals.at(id).net)set(id,local_value(id));
    }
#endif
#if !defined(DSIM_WIDE_VALUES) && !defined(DSIM_STRING_ENABLED) && !defined(DSIM_REFERENCE_SCALAR_STORES)
    void drive(int id,int driver,V value) {drive_planes(id,driver,value.a,value.b);}
    void drive_planes(int id,int driver,uint64_t av,uint64_t bv) {
        V value(av,bv,64);
#else
    void drive(int id,int driver,V value) {
#endif
#ifdef DSIM_COMPACT_GATES
        if(id<0) {
            auto& slot=compact_signals.at(compact_index(id));
            if(connections_ready&&!slot.fallback&&(!slot.driven||slot.driver==driver)) {
                const uint8_t bits=pack_scalar(value);
                slot.driver=driver;slot.driven_value=bits;slot.driven=true;
                publish_compact(id,slot,bits);
                return;
            }
            store_driver(id,driver,value);
            if(!connections_ready)finish_connections();
            const auto& c=compact_signals.at(compact_index(id));
            if(c.fallback&&c.fallback->aliased)settle({id});else set_compact(id,local_value(id));
            return;
        }
#endif
        auto& s=signals.at(id);value=value.size(s.value.w);
        if(connections_ready&&!s.aliased&&s.drivers.assign_single(driver,value)) {
            set(id,value);return;
        }
        s.drivers[driver]=value;
        if(!connections_ready) finish_connections();
        // Unrelated nets do not pay for another port's bit connections.
        if(!s.aliased) set(id,local_value(id));
        else settle({id});
    }
    void assign_parts(const std::vector<Part>& parts,V value,bool nonblocking) {
        if(nonblocking) queue_nba({0,Nba::Parts,value,parts});
        else commit_parts(parts,value);
    }
    void drive_parts(const std::vector<Part>& parts,V value) {
        std::set<int> changed;
        for(auto part:parts) {
#ifdef DSIM_COMPACT_GATES
            auto& signal=signal_record(part.signal);
#else
            auto& signal=signals.at(part.signal);
#endif
            if(!signal.net || part.driver<0) throw std::runtime_error("invalid generated net driver");
            signal.drivers[part.driver]=replace(V::z(signal.value.w),part.lo,part.width,slice(value,part.rhs_lo,part.width));
            changed.insert(part.signal);
        }
        settle(changed);
    }
    // Copy a structural bit vector atomically, preserving repeated destination
    // drivers and reading every RHS before resolving any aliased destination.
    void drive_copies(const int* destination,const int* source,int driver,size_t count) {
        std::set<int> changed;
        for(size_t i=0;i<count;++i) {
#ifdef DSIM_COMPACT_GATES
            if(!is_net(destination[i])||get(destination[i]).w!=1||get(source[i]).w!=1)
                throw std::runtime_error("invalid structural bit copy");
            store_driver(destination[i],driver+int(i),get(source[i]));
#else
            auto& signal=signals.at(destination[i]);
            if(!signal.net || signal.value.w!=1 || get(source[i]).w!=1)
                throw std::runtime_error("invalid structural bit copy");
            signal.drivers[driver+int(i)]=get(source[i]);
#endif
            changed.insert(destination[i]);
        }
        settle(changed);
    }
    void connect_net(int a,int abit,int b,int bbit) {
        structural_change();
        if(connections_ready) throw std::runtime_error("net connections must precede simulation");
        auto index=[&](int signal,int bit) {
#ifdef DSIM_COMPACT_GATES
            const auto& entry=signal_record(signal);
#else
            const auto& entry=signals.at(signal);
#endif
            if(!entry.net || bit<0 || bit>=entry.value.w) throw std::runtime_error("invalid generated net connection");
            auto inserted=connection_nodes.emplace(Bit{signal,bit},int(connection_parent.size()));
            if(inserted.second) connection_parent.push_back(inserted.first->second);
            return inserted.first->second;
        };
        int left=index(a,abit),right=index(b,bbit);
        connection_parent[connection_root(left)]=connection_root(right);
    }
    void finish_connections() {
        if(connections_ready) return;
        std::map<int,int> roots;
        for(auto node:connection_nodes) {
            int root=connection_root(node.second);
            auto group=roots.emplace(root,int(bit_groups.size()));
            if(group.second) bit_groups.emplace_back();
            int id=group.first->second;
            bit_groups[id].push_back(node.first);
            signal_groups[node.first.first].push_back({id,node.first.second});
#ifdef DSIM_COMPACT_GATES
            signal_record(node.first.first).aliased=true;
#else
            signals[node.first.first].aliased=true;
#endif
        }
        connection_nodes.clear(); connection_parent.clear();
        connection_parent.shrink_to_fit(); connections_ready=true;
    }
#if defined(DSIM_COMPACT_NBA_STORAGE) && !defined(DSIM_WIDE_VALUES) && !defined(DSIM_STRING_ENABLED) && !defined(DSIM_REFERENCE_NBA_STORAGE)
    // Keep the small scalar ABI adapter at its caller. Otherwise the vector's
    // rare growth path can make the compiler outline this wrapper and pass the
    // 24-byte V on the stack for every whole-variable NBA assignment.
#if (defined(__clang__) || defined(__GNUC__)) && !defined(DSIM_REFERENCE_NBA_INLINE)
    __attribute__((always_inline)) inline
#endif
    void assign_nba(int id,V value) {assign_nba_planes(id,value.a,value.b);}
    void assign_nba_planes(int id,uint64_t a,uint64_t b) {queue_nba({id,Nba::Assign,a,b});}
#else
    void assign_nba(int id,V value) { queue_nba({id,Nba::Assign,value,{}}); }
#endif
#ifdef DSIM_DELAYED_NBA_ENABLED
    // Values and constant destination parts are sampled now. Timed updates
    // enter the NBA region at their timestamp, after its Active/Inactive work.
    void assign_nba_after(int id,V value,uint64_t dt) {
        (void)get(id);
        schedule_nba({id,Nba::Assign,std::move(value),{}},dt);
    }
    void assign_parts_after(const std::vector<Part>& parts,V value,uint64_t dt) {
        schedule_nba({0,Nba::Parts,std::move(value),parts},dt);
    }
#endif
    void enqueue_nba(int p) { (void)processes.at(p); queue_nba({p,Nba::Wake,V(),{}}); }
    void wait(int p,const std::vector<std::pair<int,int>>& events) { wait_dynamic(p,events); }
    void wait(int p,std::initializer_list<std::pair<int,int>> events) { wait_dynamic(p,events); }
    template<class Events> int register_wait_site(int p,const Events& events) {
        structural_change();
        auto& proc=processes.at(p);
        if(proc.wait_kind==WaitKind::Fixed)throw std::runtime_error("fixed-sensitive process cannot register another wait site");
        proc.wait_kind=WaitKind::Dynamic;
        WaitSite site{p,wait_refs.size(),events.size()};
        for(auto [id,edge]:events) {
#ifdef DSIM_COMPACT_GATES
            auto& list=signal_watches(id);
#else
            auto& list=signals.at(id).watches;
#endif
            wait_refs.push_back({id,int(list.size())});
            int mask=edge==0?4:edge==1?1:2;
#ifdef DSIM_NAMED_EVENTS_ENABLED
            if(edge>=3) {
                if(edge>4||!named_events.count(id))throw std::runtime_error("invalid named event query wait");
                mask=edge==3?8:16;
            }
#endif
            list.push_back({p,mask,0});
        }
        wait_sites.push_back(site); return int(wait_sites.size())-1;
    }
    int add_wait_site(int p,std::initializer_list<std::pair<int,int>> events) { return register_wait_site(p,events); }
    int add_wait_site(int p,const std::vector<std::pair<int,int>>& events) { return register_wait_site(p,events); }
#ifdef DSIM_WAIT_ORDER_ENABLED
    int add_wait_order_site(int p,const std::vector<int>& events) {
        if(events.empty())throw std::runtime_error("wait_order requires at least one named event");
        for(int event:events)if(!named_events.count(event))
            throw std::runtime_error("wait_order requires named events");
        int site=register_wait_site(p,std::vector<std::pair<int,int>>{});
        subscribe_ordered_wait(site,events);return site;
    }
    bool wait_order_succeeded(int site) const {return ordered_waits.at(site).succeeded;}
#endif
#ifdef DSIM_EXPRESSION_EVENTS_ENABLED
    int add_expression_wait_site(int p,const std::vector<std::pair<int,int>>& ordinary,
                                 std::vector<EventExpression> expressions) {
        int site=register_wait_site(p,ordinary);
        for(auto& expression:expressions) {
            bool valid_occurrence=false;
#ifdef DSIM_NAMED_EVENTS_ENABLED
            valid_occurrence=expression.named_source||(expression.edge==3&&expression.dependencies.size()==1&&named_events.count(expression.dependencies.front()));
#endif
            if((!expression.evaluate&&!expression.named_source)||expression.edge<0||expression.edge>(expression.named_source?6:3)||(expression.named_source&&!valid_occurrence)||(expression.edge==3&&!valid_occurrence)||expression_waits.size()>=size_t((INT32_MAX>>6)-1))
                throw std::runtime_error("invalid event expression");
            int id=int(expression_waits.size());
            expression_sites[site].push_back(id);
            V before=expression.defer_until_armed||expression.named_source?V():expression.evaluate(*this);
            expression_waits.push_back({std::move(expression),std::move(before),p});
            for(int signal:expression_waits.back().expression.dependencies) {
#ifdef DSIM_COMPACT_GATES
                auto& list=signal_watches(signal);
#else
                auto& list=signals.at(signal).watches;
#endif
                wait_refs.push_back({signal,int(list.size())});
                list.push_back({p,(id+1)<<6,0});++wait_sites[size_t(site)].count;
            }
        }
        return site;
    }
#endif
#ifdef DSIM_EVENT_NBA_ENABLED
    int add_event_nba_site(const std::vector<std::pair<int,int>>& ordinary,
                           std::vector<EventExpression> expressions={}) {
        structural_change();
        if(event_nba_sites.size()>=size_t(INT32_MAX))throw std::runtime_error("too many event NBA sites");
        const int id=int(event_nba_sites.size());event_nba_sites.emplace_back();
        auto add_source=[&](EventExpression expression,int mask) {
            bool occurrence=false;
#ifdef DSIM_NAMED_EVENTS_ENABLED
            occurrence=expression.edge==3&&expression.dependencies.size()==1&&named_events.count(expression.dependencies.front());
#endif
            if(!mask&&(!expression.evaluate||expression.edge<0||expression.edge>3||(expression.edge==3&&!occurrence)))
                throw std::runtime_error("invalid event NBA expression");
            if(event_nba_sources.size()>=size_t(INT32_MAX))throw std::runtime_error("too many event NBA sources");
            const int source=int(event_nba_sources.size()),offset=int(event_nba_sites[size_t(id)].sources.size());
            for(int signal:expression.dependencies)(void)get(signal);
            V before=mask||expression.defer_until_armed?V():expression.evaluate(*this);
            event_nba_sources.push_back({std::move(expression),std::move(before),id,offset,mask});
            event_nba_sites[size_t(id)].sources.push_back(source);
            for(int signal:event_nba_sources.back().expression.dependencies) {
#ifdef DSIM_COMPACT_GATES
                auto& watches=signal_watches(signal);
#else
                auto& watches=signals.at(signal).watches;
#endif
                watches.push_back({source,-1,0});
            }
        };
        for(auto [signal,edge]:ordinary) {
            if(edge<0||edge>4)throw std::runtime_error("invalid event NBA edge");
            EventExpression expression;expression.dependencies={signal};
            if(edge<3)add_source(std::move(expression),edge==0?4:edge==1?1:2);
            else {
#ifdef DSIM_NAMED_EVENTS_ENABLED
                (void)named_events.at(signal);
                const int event_id=signal;
                expression.evaluate=[event_id](Sim& sim){return V(sim.event_triggered(event_id),0,1);};
                expression.edge=edge==3?1:2;expression.sample_on_arm=true;add_source(std::move(expression),0);
#else
                throw std::runtime_error("named events are disabled");
#endif
            }
        }
        for(auto& expression:expressions)add_source(std::move(expression),0);
        return id;
    }
    void assign_event_nba(int id,std::vector<Part> parts,V value,uint64_t count=1) {
        auto& site=event_nba_sites.at(size_t(id));
        if(!count){queue_nba({0,Nba::Parts,std::move(value),std::move(parts)});return;}
        EventNbaPending issue{count,std::move(value),std::move(parts),{},std::vector<bool>(site.sources.size(),false)};
        for(int source_id:site.sources) {
            const auto& source=event_nba_sources[size_t(source_id)];
            issue.before.push_back(!source.mask&&source.expression.sample_on_arm?source.expression.evaluate(*this):source.before);
        }
        site.pending.push_back(std::move(issue));
    }
#endif
#ifdef DSIM_FORK_JOIN_ENABLED
    int add_fork_group(int parent,std::vector<int> children,int kind=1) {
        structural_change();
#ifdef DSIM_FUNCTION_FORKS_ENABLED
        if(parent!=-1||kind!=3)
#endif
        (void)processes.at(size_t(parent));
        if(kind<1||kind>3)throw std::runtime_error("invalid fork join kind");
        if(fork_groups.size()>=size_t(INT32_MAX))throw std::runtime_error("too many fork groups");
        std::set<int> unique;
        for(int child:children) {
            (void)processes.at(size_t(child));
            if(child==parent||!unique.insert(child).second)throw std::runtime_error("invalid fork child");
        }
        auto completed=std::vector<bool>(children.size(),true);
        fork_groups.push_back({parent,std::move(children),std::move(completed),0,kind,true});
#ifdef DSIM_DYNAMIC_FORK_ENABLED
        fork_groups.back().source=int(fork_groups.size())-1;
#endif
        return int(fork_groups.size())-1;
    }
#ifdef DSIM_DYNAMIC_FORK_ENABLED
    // Execution records and private automatic storage may grow after start.
    // Module/gate topology stays fixed; pristine compiled closures, values and
    // immutable ID maps belong to Sim and participate in ordinary snapshots.
    void enable_dynamic_forks() {
        structural_change();
        if(!fork_templates.empty())throw std::runtime_error("dynamic forks already configured");
        fork_templates=fork_groups;
        fork_template_waits=wait_sites.size();fork_template_targets=disable_targets.size();
        for(const auto& group:fork_templates)for(int child:group.children) {
            const auto& process=processes.at(size_t(child));
            if(process.handler!=UINT32_MAX)throw std::runtime_error("fork requires a compiled RTL closure");
            fork_actions.emplace(child,actions.at(process.payload));
        }
#ifdef DSIM_EXPRESSION_EVENTS_ENABLED
        // A branch can start after an operand change has already queued an
        // expression job. Establish its baseline when it actually enters the
        // wait, so a pre-start change cannot become a new activation's edge.
        for(const auto& site:expression_sites)if(fork_actions.count(wait_sites[size_t(site.first)].process))
            for(int expression:site.second)expression_waits[size_t(expression)].expression.sample_on_arm=true;
#endif
    }
private:
    int clone_fork(int id,int owner=-2,int task_owner=-1) {
        auto origin=fork_groups.at(size_t(id));
        if(owner!=-2)origin.parent=owner;
        auto frame=std::make_shared<ForkFrame>();
        if(origin.parent>=0&&processes[size_t(origin.parent)].fork_frame)*frame=*processes[size_t(origin.parent)].fork_frame;
#ifdef DSIM_SHARED_TASKS_ENABLED
        if(task_owner>=0&&processes[size_t(task_owner)].fork_frame)*frame=*processes[size_t(task_owner)].fork_frame;
#else
        (void)task_owner;
#endif
        std::vector<int> groups{origin.source},children;
        for(size_t next=0;next<groups.size();++next)for(int child:fork_templates.at(size_t(groups[next])).children) {
            children.push_back(child);
            for(size_t g=0;g<fork_templates.size();++g)if(fork_templates[g].parent==child)groups.push_back(int(g));
        }
        if(processes.size()+children.size()>=size_t(INT32_MAX)||actions.size()+children.size()>=UINT32_MAX||fork_groups.size()+groups.size()>=size_t(INT32_MAX))
            throw std::runtime_error("too many dynamic fork activations");
        for(int child:children) {
#ifdef DSIM_SHARED_TASKS_ENABLED
            if(task_owner>=0&&child==origin.children.front()) {
                // A task uses its caller's process identity and RNG. Only its
                // resumable closure and immutable site map are newly owned.
                frame->processes[child]=task_owner;
                actions.push_back(fork_actions.at(child));
                processes[size_t(task_owner)].payload=uint32_t(actions.size()-1);
                processes[size_t(task_owner)].fork_frame=frame;continue;
            }
#endif
            frame->processes[child]=int(processes.size());
            actions.push_back(fork_actions.at(child));
            Process process;process.payload=uint32_t(actions.size()-1);process.wait_kind=processes[size_t(child)].wait_kind;
            process.fork_frame=frame;processes.push_back(std::move(process));
        }
        for(int group:groups) {frame->groups[group]=int(fork_groups.size());fork_groups.push_back(fork_templates[size_t(group)]);}
        for(int group:groups) {
            auto& copy=fork_groups[size_t(frame->groups.at(group))];copy.remaining=0;copy.released=true;
            copy.parent=group==origin.source?origin.parent:frame->processes.at(copy.parent);
            for(int& child:copy.children)child=frame->processes.at(child);
            std::fill(copy.completed.begin(),copy.completed.end(),true);
        }
        std::set<int> members(children.begin(),children.end());
        for(size_t w=0;w<fork_template_waits;++w)if(members.count(wait_sites[w].process)) {
            const auto source=wait_sites[w];const int parent=frame->processes.at(source.process),dest=int(wait_sites.size());
            frame->waits[int(w)]=dest;WaitSite copy{parent,wait_refs.size(),source.count};
#ifdef DSIM_EXPRESSION_EVENTS_ENABLED
            std::map<int,int> expressions;
            auto found=expression_sites.find(int(w));
            if(found!=expression_sites.end())for(int expression:found->second) {
                if(expression_waits.size()>=size_t((INT32_MAX>>6)-1))throw std::runtime_error("too many fork expression waits");
                const int index=int(expression_waits.size());expressions[expression]=index;
                auto wait=expression_waits[size_t(expression)];wait.process=parent;wait.generation=0;wait.queued=false;
#ifdef DSIM_NAMED_EVENTS_ENABLED
                wait.named_event=-1;wait.named_slots.clear();
#endif
                expression_waits.push_back(std::move(wait));expression_sites[dest].push_back(index);
            }
#endif
            for(size_t i=source.first;i<source.first+source.count;++i) {
                const auto ref=wait_refs[i];
#ifdef DSIM_COMPACT_GATES
                auto& watches=signal_watches(ref.signal);
#else
                auto& watches=signals.at(ref.signal).watches;
#endif
                auto watch=watches[size_t(ref.slot)];watch.process=parent;watch.generation=0;
#ifdef DSIM_EXPRESSION_EVENTS_ENABLED
                if(watch.edges>=64)watch.edges=(expressions.at((watch.edges>>6)-1)+1)<<6;
#endif
                wait_refs.push_back({ref.signal,int(watches.size())});watches.push_back(watch);
            }
            wait_sites.push_back(copy);
#ifdef DSIM_WAIT_ORDER_ENABLED
            auto ordered=ordered_waits.find(int(w));
            if(ordered!=ordered_waits.end())subscribe_ordered_wait(dest,ordered->second.events);
#endif
        }
        for(size_t t=0;t<fork_template_targets;++t)if(members.count(disable_targets[t].process)) {
            auto target=disable_targets[t];target.process=frame->processes.at(target.process);
#ifdef DSIM_SHARED_TASKS_ENABLED
            target.payload=processes[size_t(target.process)].payload;
#endif
            for(int& group:target.groups)if(auto found=frame->groups.find(group);found!=frame->groups.end())group=found->second;
                else if(fork_templates.at(size_t(group)).parent>=0)throw std::runtime_error("disable target fork is outside its activation");
            frame->targets[int(t)]=int(disable_targets.size());disable_targets.push_back(std::move(target));
        }
        return frame->groups.at(origin.source);
    }
public:
#ifdef DSIM_SHARED_TASKS_ENABLED
    void enter_task(int source) {
        const int caller=fork_current_process;
        if(caller<0||processes.at(size_t(caller)).handler!=UINT32_MAX)
            throw std::runtime_error("task requires an executing RTL process");
        const auto& model=fork_templates.at(size_t(source));
        if(model.parent!=-1||model.kind!=3||model.children.size()!=1)
            throw std::runtime_error("invalid task template");
        auto& state=processes[size_t(caller)];
        if(state.task_calls.size()>=1024)throw std::runtime_error("task recursion depth exceeds 1024");
        state.task_calls.push_back({state.payload,state.fork_frame,state.activation,state.activation_level,state.location});
        (void)clone_fork(source,-1,caller);
        auto& entered=processes[size_t(caller)];entered.activation_level=0;
        const auto& saved=entered.task_calls.back();task_invocations.emplace(entered.payload,TaskInvocation{saved.payload,saved.location});
        entered.location=-1;entered.last_wait_site=-1;entered.task_transfer=true;
    }
    void leave_task() {
        auto& state=processes.at(size_t(fork_current_process));
        if(state.task_calls.empty())throw std::runtime_error("task return has no caller");
        auto saved=std::move(state.task_calls.back());state.task_calls.pop_back();
        state.payload=saved.payload;state.fork_frame=std::move(saved.fork_frame);
        state.activation=std::move(saved.activation);state.activation_level=saved.activation_level;
        state.location=saved.location;state.last_wait_site=-1;state.task_transfer=true;
    }
    ReferenceActivation task_output_context() {
        const int id=fork_current_process;auto& state=processes.at(size_t(id));
        if(!state.activation||!state.activation_level)throw std::runtime_error("task output has no activation");
        auto previous=state.activation;const auto depth=state.activation_level;
        state.activation=previous->parent;--state.activation_level;
        return ReferenceActivation(*this,id,std::move(previous),depth);
    }
    void dispatch_task_action(int process) {
        do {
            processes[size_t(process)].task_transfer=false;
            const auto payload=processes[size_t(process)].payload;
            actions[payload]();
        } while(processes[size_t(process)].task_transfer);
    }
#endif
#endif
    bool fork_descendants_busy(int parent) const {
        std::vector<int> pending{parent};std::set<int> visited;
        while(!pending.empty()) {
            int process=pending.back();pending.pop_back();if(!visited.insert(process).second)continue;
            for(const auto& group:fork_groups)if(group.parent==process) {
                if(group.remaining)return true;
                pending.insert(pending.end(),group.children.begin(),group.children.end());
            }
        }
        return false;
    }
    // Static call slots can be reused after every descendant has completed or
    // been cancelled. Detect unsupported overlapping activation before restart.
    bool start_fork(int id) {
#ifdef DSIM_DYNAMIC_FORK_ENABLED
        auto available=[&](int group) {
            if(fork_groups[size_t(group)].remaining)return false;
            for(int child:fork_groups[size_t(group)].children)if(processes[size_t(child)].queued||processes[size_t(child)].waiting||fork_descendants_busy(child))return false;
            return true;
        };
        if(!available(id)) {
            const int parent=fork_groups[size_t(id)].parent,source=fork_groups[size_t(id)].source;int reuse=-1;
            for(size_t i=0;i<fork_groups.size();++i)if(fork_groups[i].parent==parent&&fork_groups[i].source==source&&available(int(i))){reuse=int(i);break;}
            id=reuse>=0?reuse:clone_fork(id);
        }
#endif
        auto& group=fork_groups.at(size_t(id));
#ifdef DSIM_SHARED_TASKS_ENABLED
        if(group.parent>=0)group.owner_payload=processes[size_t(group.parent)].payload;
#endif
        if(group.remaining)throw std::runtime_error("overlapping fork activations are not supported yet");
        if(group.children.empty())return false;
        for(int child:group.children)if(processes[size_t(child)].queued||processes[size_t(child)].waiting||fork_descendants_busy(child))
            throw std::runtime_error("overlapping fork activations are not supported yet");
        group.released=group.kind==3;
        if(!group.released){auto& parent=processes[size_t(group.parent)];parent.last_wait_site=-1;parent.waiting=true;++parent.generation;}
        group.remaining=group.children.size();std::fill(group.completed.begin(),group.completed.end(),false);
        for(int child:group.children) {
#ifdef DSIM_PROCESS_HANDLES_ENABLED
            detach_process_handle(child);
#endif
#ifdef DSIM_PROCESS_LIFETIME_ENABLED
            processes[size_t(child)].lifecycle=1;
#endif
#ifdef DSIM_RANDOM_ENABLED
            processes[size_t(child)].random_state=random_next(group.parent<0?root_random_state:processes[size_t(group.parent)].random_state);
#endif
#ifdef DSIM_DYNAMIC_FORK_ENABLED
            processes[size_t(child)].activation=group.parent<0?startup_activation:processes[size_t(group.parent)].activation;
            processes[size_t(child)].activation_level=0;
#endif
            enqueue(child);
        }
        return !group.released;
    }
#ifdef DSIM_FUNCTION_FORKS_ENABLED
    // Function sites are templates. Each call attaches children to the current
    // process and captures its live automatic frame, including startup calls.
    void start_function_fork(int source) {
        const auto& model=fork_templates.at(size_t(source));
        if(model.parent!=-1||model.kind!=3)throw std::runtime_error("invalid function fork template");
        const int owner=fork_current_process;int selected=-1;
        for(size_t i=0;i<fork_groups.size();++i) {
            const auto& candidate=fork_groups[i];
            if(int(i)==source||candidate.source!=source||candidate.parent!=owner||candidate.remaining)continue;
            bool available=true;
            for(int child:candidate.children)if(processes[size_t(child)].queued||processes[size_t(child)].waiting||fork_descendants_busy(child)){available=false;break;}
            if(available){selected=int(i);break;}
        }
        if(selected<0)selected=clone_fork(source,owner);
        if(start_fork(selected))throw std::runtime_error("function fork unexpectedly suspended its caller");
    }
#endif
    bool wait_fork(int parent) {
        (void)processes.at(size_t(parent));
        bool pending=false;for(const auto& group:fork_groups)if(group.parent==parent&&group.remaining){pending=true;break;}
        if(!pending)return false;
        fork_waiters.insert(parent);auto& process=processes[size_t(parent)];process.last_wait_site=-1;process.waiting=true;++process.generation;
        return true;
    }
    void finish_fork(int id,size_t branch) {
        auto& group=fork_groups.at(size_t(id));
        if(branch>=group.children.size()||!group.remaining||group.completed[branch])
            throw std::runtime_error("invalid fork completion");
#ifdef DSIM_PROCESS_LIFETIME_ENABLED
        complete_process(group.children[branch]);
#endif
        group.completed[branch]=true;--group.remaining;
#ifdef DSIM_DYNAMIC_FORK_ENABLED
        auto& child=processes[size_t(group.children[branch])];child.activation.reset();child.activation_level=0;
#endif
        if(!group.released&&(group.kind==2||!group.remaining)) {
            group.released=true;processes[size_t(group.parent)].waiting=false;enqueue(group.parent);
        }
        if(fork_waiters.count(group.parent)) {
            bool pending=false;for(const auto& other:fork_groups)if(other.parent==group.parent&&other.remaining){pending=true;break;}
            if(!pending){fork_waiters.erase(group.parent);processes[size_t(group.parent)].waiting=false;enqueue(group.parent);}
        }
    }

#endif
#ifdef DSIM_PROCESS_CONTROL_ENABLED
    void disable_fork(int parent) {
        (void)processes.at(size_t(parent));std::vector<int> pending{parent};std::set<int> visited;
#ifdef DSIM_IPC_ENABLED
        ++ipc_cancellation_depth;
#endif
        while(!pending.empty()) {
            int process=pending.back();pending.pop_back();if(!visited.insert(process).second)continue;
            for(auto& group:fork_groups)if(group.parent==process) {
                group.remaining=0;group.released=true;std::fill(group.completed.begin(),group.completed.end(),true);
                for(int child:group.children){invalidate_process(child);pending.push_back(child);}
            }
        }
#ifdef DSIM_IPC_ENABLED
        ipc_cancel_end();
#endif
    }
    void process_location(int process,int pc) {processes[size_t(process)].location=pc;}
    int add_disable_target(int process,int continuation,std::vector<int> groups,int identity=-1,int begin=0) {
        structural_change();(void)processes.at(size_t(process));
        if(continuation<0||disable_targets.size()>=size_t(INT32_MAX))throw std::runtime_error("invalid disable target");
        for(int group:groups)(void)fork_groups.at(size_t(group));
        disable_targets.push_back({process,continuation,std::move(groups),identity,begin});
#ifdef DSIM_SHARED_TASKS_ENABLED
        disable_targets.back().payload=processes[size_t(process)].payload;
#endif
        return int(disable_targets.size())-1;
    }
    int take_process_transfer(int id) {
        auto& target=processes.at(size_t(id)).transfer;const int pc=target;target=-1;return pc;
    }
    // A named block in an automatic task is one lexical target across all
    // active invocations. PCs identify active static call slots; transfers,
    // returns and loop jumps automatically leave their old ranges. Function
    // bodies use zero-time local jumps and do not enter this process API.
    // Already-issued value NBA records own their payloads and remain pending.
    int disable_block(int id,int caller) {
        const auto& origin=disable_targets.at(size_t(id));(void)processes.at(size_t(caller));
#ifdef DSIM_IPC_ENABLED
        ++ipc_cancellation_depth;
#endif
        std::vector<int> active{id};
        if(origin.identity>=0)for(size_t i=0;i<disable_targets.size();++i) {
            const auto& target=disable_targets[i];const int pc=processes[size_t(target.process)].location;
            bool live=pc>=target.begin&&pc<target.continuation;
#ifdef DSIM_DYNAMIC_FORK_ENABLED
            // A returned task can still own escaped descendants. Cancel those
            // lexical activations too, without restarting the returned caller.
            live=true;
#endif
            if(int(i)!=id&&target.identity==origin.identity&&live)active.push_back(int(i));
        }
        int continuation=-1;
        for(int index:active) {
            const auto& target=disable_targets[size_t(index)];
#ifdef DSIM_DYNAMIC_FORK_ENABLED
            int location=processes[size_t(target.process)].location;
#ifdef DSIM_SHARED_TASKS_ENABLED
            auto& target_process=processes[size_t(target.process)];size_t suspended=SIZE_MAX;
            if(target_process.payload!=target.payload) {
                location=-1;
                for(size_t i=target_process.task_calls.size();i>0;--i)if(target_process.task_calls[i-1].payload==target.payload) {
                    suspended=i-1;location=target_process.task_calls[i-1].location;break;
                }
            }
            // Descendants can outlive a returned task. Their invocation ancestry
            // retains the lexical call site without confusing equal PC numbers
            // in different task bodies.
            for(auto& group:fork_groups)if(group.parent==target.process&&group.remaining&&group.owner_payload!=target.payload) {
                uint32_t owner=group.owner_payload;bool within=false;
                for(auto found=task_invocations.find(owner);found!=task_invocations.end();found=task_invocations.find(owner)) {
                    if(found->second.parent==target.payload) {within=found->second.location>=target.begin&&found->second.location<target.continuation;break;}
                    owner=found->second.parent;
                }
                if(within) {
                    group.remaining=0;group.released=true;std::fill(group.completed.begin(),group.completed.end(),true);
                    for(int child:group.children){invalidate_process(child);disable_fork(child);}
                }
            }
#endif
            const bool parent_active=location>=target.begin&&location<target.continuation;
#endif
            for(int group_id:target.groups) {
#ifdef DSIM_DYNAMIC_FORK_ENABLED
                const int source=fork_groups[size_t(group_id)].source;
                const int parent=fork_groups[size_t(group_id)].parent<0?target.process:fork_groups[size_t(group_id)].parent;
                for(size_t g=0;g<fork_groups.size();++g)if(fork_groups[g].source==source&&fork_groups[g].parent==parent) {
                    auto& group=fork_groups[g];group.remaining=0;group.released=true;
                    std::fill(group.completed.begin(),group.completed.end(),true);
                    for(int child:group.children){invalidate_process(child);disable_fork(child);}
                }
#else
                auto& group=fork_groups[size_t(group_id)];
                group.remaining=0;group.released=true;std::fill(group.completed.begin(),group.completed.end(),true);
                for(int child:group.children)invalidate_process(child);
#endif
            }
#ifdef DSIM_DYNAMIC_FORK_ENABLED
            if(!parent_active)continue;
#endif
#ifdef DSIM_SHARED_TASKS_ENABLED
            if(suspended!=SIZE_MAX) {
                auto saved=std::move(target_process.task_calls[suspended]);target_process.task_calls.resize(suspended);
                target_process.payload=saved.payload;target_process.fork_frame=std::move(saved.fork_frame);
                target_process.activation=std::move(saved.activation);target_process.activation_level=saved.activation_level;
                target_process.last_wait_site=-1;
                if(caller==target.process) {
                    target_process.transfer=target.continuation;target_process.task_transfer=true;
                    target_process.location=target.continuation;continue;
                }
            }
#endif
            if(caller==target.process)continuation=target.continuation;
            else {invalidate_process(target.process,target.continuation);enqueue(target.process);}
            processes[size_t(target.process)].location=target.continuation;
        }
#ifdef DSIM_DYNAMIC_FORK_ENABLED
        // An escaped block's caller may now be waiting outside that block.
        for(auto it=fork_waiters.begin();it!=fork_waiters.end();) {
            int parent=*it;bool pending=false;
            for(const auto& group:fork_groups)if(group.parent==parent&&group.remaining){pending=true;break;}
            if(pending){++it;continue;}
            it=fork_waiters.erase(it);processes[size_t(parent)].waiting=false;enqueue(parent);
        }
#endif
#ifdef DSIM_IPC_ENABLED
        ipc_cancel_end();
#endif
        return continuation;
    }

#endif
#ifdef DSIM_COMPILED_WAIT_ENABLED
    template<int ProcessId,int Site> void arm_wait_known() {
        // The compiler has bound this site to this process. Keep the uncommon
        // first arm/site switch on the generic path; same-site rearm needs no
        // wait-table lookup. Delay/dynamic waits invalidate last_wait_site.
        auto& p=processes[size_t(ProcessId)];p.waiting=true;
        if(p.last_wait_site!=Site)arm_wait(Site);
    }
#endif
    void arm_wait(int id) {
        const auto& site=wait_sites.at(id);
        auto& proc=processes[site.process]; proc.waiting=true;
#if !defined(DSIM_DISABLE_WAIT_REARM_CACHE) && !defined(DSIM_PROCESS_CONTROL_ENABLED) && !defined(DSIM_DYNAMIC_FORK_ENABLED) && !defined(DSIM_WAIT_ORDER_ENABLED) && !defined(DSIM_EXPRESSION_EVENTS_ENABLED) && !defined(DSIM_NAMED_EVENTS_ENABLED)
        // Reusing an ordinary sensitivity list leaves every subscription valid.
        // A different site/dynamic wait invalidates its old generation; a delay
        // clears the cache. Complex event controls must still resample on arm.
        if(proc.last_wait_site==id)return;
        proc.last_wait_site=id;
#endif
        ++proc.generation;
#ifdef DSIM_WAIT_ORDER_ENABLED
        auto ordered=ordered_waits.find(id);
        if(ordered!=ordered_waits.end()) {
            auto& wait=ordered->second;wait.next=0;wait.succeeded=false;wait.generation=proc.generation;
        }
#endif
#ifdef DSIM_EXPRESSION_EVENTS_ENABLED
        auto expressions=expression_sites.find(id);
        if(expressions!=expression_sites.end())for(int expression:expressions->second) {
            auto& wait=expression_waits[size_t(expression)];
            wait.generation=proc.generation;
#ifdef DSIM_NAMED_EVENTS_ENABLED
            if(wait.expression.named_source) {
                wait.named_event=wait.expression.named_source(*this);
#ifdef DSIM_EVENT_ALIASES_ENABLED
                if(wait.named_event<0)continue;
#endif
                (void)named_events.at(wait.named_event);
                wait.before=V(event_triggered(wait.named_event)?1:0,0,1);
#ifdef DSIM_COMPACT_GATES
                auto& watches=signal_watches(wait.named_event);
#else
                auto& watches=signals.at(size_t(wait.named_event)).watches;
#endif
                auto [slot,inserted]=wait.named_slots.emplace(wait.named_event,int(watches.size()));
                if(inserted)watches.push_back({site.process,(expression+1)<<6,proc.generation});
                else watches.at(size_t(slot->second)).generation=proc.generation;
            } else
#endif
            if(wait.expression.sample_on_arm)wait.before=wait.expression.evaluate(*this);
        }
#endif
        for(size_t i=site.first;i<site.first+site.count;++i) {
#ifdef DSIM_DYNAMIC_FORK_ENABLED
            const auto original=wait_refs[i];int physical=activation_signal(original.signal);
#ifdef DSIM_COMPACT_GATES
            const auto source=signal_watches(original.signal)[original.slot];
            auto& list=signal_watches(physical);
#else
            const auto source=signals[original.signal].watches[original.slot];
            auto& list=signals[physical].watches;
#endif
            int slot=original.slot;
            if(physical!=original.signal) {
                auto key=std::make_pair(i,physical);auto found=activation_watches.find(key);
                if(found==activation_watches.end()) {
                    found=activation_watches.emplace(key,int(list.size())).first;list.push_back(source);
                }
                slot=found->second;
            }
            auto& watch=list[size_t(slot)];
#else
#ifdef DSIM_COMPACT_GATES
            auto ref=wait_refs[i]; auto& watch=signal_watches(ref.signal)[ref.slot];
#else
            auto ref=wait_refs[i]; auto& watch=signals[ref.signal].watches[ref.slot];
#endif
#endif
            watch.generation=proc.generation;
#ifdef DSIM_NAMED_EVENTS_ENABLED
            if(watch.edges==8||watch.edges==32)watch.edges=event_triggered(wait_refs[i].signal)?32:8;
#endif
        }
    }
    // A compiled gate process has exactly one lifetime sensitivity list. Its
    // generation and every watch stay at zero, so set() keeps the same wake
    // predicate while rearming no longer rewrites all input watches. Dynamic
    // sites/delays are forbidden for this process, including before binding.
    template<class Events> int register_fixed_wait(int p,const Events& events) {
        structural_change();
        auto& proc=processes.at(p);
        if(proc.handler==UINT32_MAX || proc.wait_kind!=WaitKind::Unbound)
            throw std::runtime_error("fixed sensitivity requires an unbound compiled process");
#ifdef DSIM_COMPACT_GATES
        for(auto [id,edge]:events){(void)edge;(void)get(id);}
        proc.wait_kind=WaitKind::Fixed;
        for(auto [id,edge]:events)signal_watches(id).push_back({p,edge==0?4:edge==1?1:2,0});
#else
        for(auto [id,edge]:events) { (void)edge; (void)signals.at(id); }
        proc.wait_kind=WaitKind::Fixed;
        for(auto [id,edge]:events)signals[id].watches.push_back({p,edge==0?4:edge==1?1:2,0});
#endif
        return p;
    }
    int add_fixed_wait(int p,std::initializer_list<std::pair<int,int>> events) {return register_fixed_wait(p,events);}
    int add_fixed_wait(int p,const std::vector<std::pair<int,int>>& events) {return register_fixed_wait(p,events);}
    void arm_fixed_wait(int p) {
        auto& proc=processes.at(p);
        if(proc.wait_kind!=WaitKind::Fixed)throw std::runtime_error("process has no fixed sensitivity");
        proc.waiting=true;
    }
    void delay(int p,uint64_t dt) {
        auto& proc=processes.at(p);
#ifdef DSIM_PROCESS_LIFETIME_ENABLED
        proc.lifecycle=2;
#endif
        if(proc.wait_kind==WaitKind::Fixed)throw std::runtime_error("fixed-sensitive process cannot use delay waiting");
        proc.last_wait_site=-1;
        proc.wait_kind=WaitKind::Dynamic;
        if(dt==0) {
            Ready event{p,true};
#ifdef DSIM_PROCESS_CONTROL_ENABLED
            event.control_epoch=proc.control_epoch;
#endif
            inactive.push(event);
        }
        else {
            if(dt>std::numeric_limits<uint64_t>::max()-now) throw std::runtime_error("simulation time overflow");
            if(timer_order==std::numeric_limits<uint64_t>::max()) throw std::runtime_error("timer sequence overflow");
            Timer event{now+dt,timer_order++,p};
#ifdef DSIM_PROCESS_CONTROL_ENABLED
            event.control_epoch=proc.control_epoch;
#endif
            push_timer(event);
        }
    }
#ifdef DSIM_TIMING_ENABLED
#ifdef DSIM_PATH_ENABLED
    const PathStamp& path_stamp(int id) const {
#ifdef DSIM_COMPACT_GATES
        if(id<0)return compact_path_stamps.at(size_t(-int64_t(id)-1));
#endif
        return path_stamps.at(size_t(id));
    }
#endif
    uint32_t delayed_driver(int signal,int driver,DelayPolicy policy) {
        structural_change();
#ifdef DSIM_COMPACT_GATES
        // A compact net already has its own scalar driver storage. Creating a
        // general Signal here would force every delayed delivery onto fallback
        // storage even when the receiver has exactly one driver.
        if(!is_net(signal))throw std::runtime_error("delayed driver requires a net");
        const int width=signal<0?1:signals.at(signal).value.w;
#else
        const auto& net=signals.at(signal);
        if(!net.net)throw std::runtime_error("delayed driver requires a net");
        const int width=net.value.w;
#endif
        if(policy!=DelayPolicy::ReplacePending&&policy!=DelayPolicy::PreserveTransitions)
            throw std::runtime_error("invalid delayed driver policy");
        if(delayed_bindings.count({signal,driver}))throw std::runtime_error("duplicate delayed driver binding");
        if(delayed_drivers.size()>=UINT32_MAX)throw std::runtime_error("too many delayed drivers");
        auto channel=uint32_t(delayed_drivers.size());
#ifdef DSIM_SCALAR_TIMING_ENABLED
        uint32_t wide=UINT32_MAX;
        if(width!=1) {
            if(vector_drivers.size()>=UINT32_MAX)throw std::runtime_error("too many vector delayed drivers");
            wide=uint32_t(vector_drivers.size());vector_drivers.push_back({V::x(width),V::z(width)});
        }
        delayed_drivers.push_back({signal,driver,0,wide,policy,2,3,false});
#else
        delayed_drivers.push_back({signal,driver,policy,V::x(width),V::z(width),0,false});
#endif
        delayed_bindings.emplace(std::make_pair(signal,driver),channel);
        return channel;
    }
    void cancel_delayed(uint32_t id) {
        auto& channel=delayed_drivers.at(id);
        if(channel.generation==UINT64_MAX)throw std::runtime_error("delayed driver generation overflow");
        ++channel.generation;channel.initialized=false;
    }
#ifdef DSIM_PATH_ENABLED
    uint32_t module_path_driver(int signal,int driver) {
        auto id=delayed_driver(signal,driver,DelayPolicy::ReplacePending);
        initial_path_drivers.push_back(id);return id;
    }
    void initialize_module_paths() {
        structural_change();
        // Path destinations start at X before procedural event controls arm.
        // Defer resolution until every structural port connection is installed.
        finish_connections();
        for(auto id:initial_path_drivers) {
            auto& channel=delayed_drivers.at(id);
#ifdef DSIM_SCALAR_TIMING_ENABLED
            if(channel.wide==UINT32_MAX)channel.output=2;
            else vector_drivers.at(channel.wide).output=V::x(get(channel.signal).w);
#else
            channel.output=V::x(get(channel.signal).w);
#endif
            drive(channel.signal,channel.driver,V::x(get(channel.signal).w));
        }
        initial_path_drivers.clear();initial_path_drivers.shrink_to_fit();
    }
#endif
#ifdef DSIM_CONTINUOUS_DELAY_ENABLED
    // Continuous assignments own a complete RHS value even when the LHS is a
    // slice/concatenation. Delay selection and cancellation use that driver's
    // committed value, independently of other drivers on the resolved net.
    uint32_t continuous_driver(std::vector<Part> parts,int width) {
        structural_change();
        if(parts.empty()||width<1||width>1048576)throw std::runtime_error("invalid continuous driver target");
        std::set<std::pair<int,int>> bindings;
        for(const auto& part:parts) {
#ifdef DSIM_COMPACT_GATES
            const bool net=is_net(part.signal);
#else
            const bool net=signals.at(part.signal).net;
#endif
            if(
#ifdef DSIM_CONTINUOUS_VARIABLE_ENABLED
               (net ? part.driver<0 : part.driver!=-1)||
#else
               !net||part.driver<0||
#endif
               part.lo<0||part.width<1||part.rhs_lo<0||
               part.width>get(part.signal).w||part.lo>get(part.signal).w-part.width||
               part.width>width||part.rhs_lo>width-part.width)
                throw std::runtime_error("invalid continuous driver part");
            if(!net)continue; // Compiler checks variable bit ownership.
            auto key=std::make_pair(part.signal,part.driver);
            if(delayed_bindings.count(key)||!bindings.insert(key).second)
                throw std::runtime_error("duplicate continuous driver binding");
        }
        if(delayed_drivers.size()>=UINT32_MAX||continuous_parts.size()>=UINT32_MAX)
            throw std::runtime_error("too many continuous drivers");
        const auto id=uint32_t(delayed_drivers.size());
        const auto part_index=uint32_t(continuous_parts.size());
#ifdef DSIM_SCALAR_TIMING_ENABLED
        uint32_t wide=UINT32_MAX;
        if(width!=1) {
            if(vector_drivers.size()>=UINT32_MAX)throw std::runtime_error("too many vector delayed drivers");
            wide=uint32_t(vector_drivers.size());vector_drivers.push_back({V::x(width),V::x(width)});
        }
        delayed_drivers.push_back({parts[0].signal,parts[0].driver,0,wide,DelayPolicy::ReplacePending,2,2,false,part_index});
#else
        delayed_drivers.push_back({parts[0].signal,parts[0].driver,DelayPolicy::ReplacePending,V::x(width),V::x(width),0,false,part_index});
#endif
#ifdef DSIM_CONTINUOUS_VARIABLE_ENABLED
        std::vector<Part> nets,variables;
        for(auto part:parts)(part.driver>=0?nets:variables).push_back(part);
        continuous_parts.push_back(std::move(nets));
        continuous_variable_parts.push_back(std::move(variables));
#else
        continuous_parts.push_back(std::move(parts));
#endif
        for(auto key:bindings)delayed_bindings.emplace(key,id);
        return id;
    }
    void initialize_continuous(uint32_t id) {
        structural_change();
        const auto& channel=delayed_drivers.at(id);
        if(channel.parts==UINT32_MAX)throw std::runtime_error("not a continuous driver");
        const auto& parts=continuous_parts[channel.parts];
        int width=0;for(const auto& part:parts)width=std::max(width,part.rhs_lo+part.width);
#ifdef DSIM_CONTINUOUS_VARIABLE_ENABLED
        for(const auto& part:continuous_variable_parts[channel.parts])width=std::max(width,part.rhs_lo+part.width);
#endif
        commit_continuous_or_drive(id,V::x(width));
    }
    void drive_continuous(uint32_t id,V value,uint64_t rise,uint64_t fall,uint64_t turnoff,bool scalar) {
        const auto& channel=delayed_drivers.at(id);
        if(channel.parts==UINT32_MAX)throw std::runtime_error("not a continuous driver");
#ifdef DSIM_SCALAR_TIMING_ENABLED
        const int width=channel.wide==UINT32_MAX?1:vector_drivers[channel.wide].output.w;
#else
        const int width=channel.output.w;
#endif
        value=value.size(width);
        if(scalar&&width!=1)throw std::runtime_error("scalar continuous driver requires one bit");
        uint64_t dt;
#ifdef DSIM_CONTINUOUS_DELAY_IEEE_MODE
        if(scalar) {
            const int bit=value.bit(0);
            dt=bit==0?fall:bit==1?rise:bit==3?turnoff:std::min(rise,std::min(fall,turnoff));
        } else dt=value.truth()==0?fall:value.same(V::z(width))?turnoff:rise;
#else
        // VCS W-2024.09 compatibility: select from RHS bit 0 and deliver the
        // whole vector atomically. Packed/part/concat targets use this too.
        const int bit=value.bit(0);
        dt=bit==0?fall:bit==1?rise:bit==3?turnoff:std::min(rise,std::min(fall,turnoff));
#endif
        drive_after(id,std::move(value),dt);
    }
#endif
    void drive_after(uint32_t id,V value,uint64_t dt) {
#ifdef DSIM_SCALAR_TIMING_ENABLED
        auto& channel=delayed_drivers.at(id);
        if(channel.wide==UINT32_MAX){drive_scalar_after(id,uint8_t(value.bit(0)),dt);return;}
        auto& state=vector_drivers[channel.wide];value=value.size(state.output.w);
        if(channel.initialized&&state.input.same(value))return;
        const bool replace=channel.policy==DelayPolicy::ReplacePending;
        const bool issue=!replace||!state.output.same(value);
        check_delivery(channel,dt,issue);
        if(issue&&free_delivery_values.empty()&&delivery_values.size()>=UINT32_MAX)
            throw std::runtime_error("too many vector delayed payloads");
        uint32_t payload=0;
        if(issue) {
            if(free_delivery_values.empty()){payload=uint32_t(delivery_values.size());delivery_values.push_back(value);}
            else {payload=free_delivery_values.back();free_delivery_values.pop_back();delivery_values[payload]=value;}
        }
        if(replace)++channel.generation;
        state.input=value;channel.initialized=true;
        if(issue)queue_delivery(id,payload,dt);
#else
        auto& channel=delayed_drivers.at(id);value=value.size(channel.output.w);
        if(channel.initialized&&channel.input.same(value))return;
        if(dt>UINT64_MAX-now)throw std::runtime_error("simulation time overflow");
        bool replace=channel.policy==DelayPolicy::ReplacePending;
        if(replace&&channel.generation==UINT64_MAX)throw std::runtime_error("delayed driver generation overflow");
        bool issue=!replace||!channel.output.same(value);
        if(issue&&dt&&timer_order==UINT64_MAX)throw std::runtime_error("timer sequence overflow");
        if(issue&&free_deliveries.empty()&&deliveries.size()>=size_t(INT32_MAX))throw std::runtime_error("too many pending delayed drives");
        if(replace)++channel.generation;
        channel.input=value;channel.initialized=true;
        // Returning to this driver's committed value rejects an outstanding
        // pulse. Use driver value, never the resolved value of a shared net.
        if(!issue)return;
        int slot;
        Delivery event{id,channel.generation,value};
        if(free_deliveries.empty()) {slot=int(deliveries.size());deliveries.push_back(event);}
        else {slot=free_deliveries.back();free_deliveries.pop_back();deliveries[size_t(slot)]=event;}
        if(!dt)active.push({-slot-1,false});
        else push_timer({now+dt,timer_order++,-slot-1});
#endif
    }
#ifdef DSIM_SCALAR_TIMING_ENABLED
    // Exactly one bit; unlike V::bit(), reject accidental vector use here.
    uint8_t get_scalar(int id) const {
#ifdef DSIM_COMPACT_GATES
        if(id<0) {
            const auto& slot=compact_signals.at(compact_index(id));
            if(slot.fallback)return uint8_t(slot.fallback->value.bit(0));
            return slot.value<2?slot.value:uint8_t(slot.value^1);
        }
#endif
        const auto& value=signals.at(id).value;
        if(value.w!=1)throw std::runtime_error("scalar timing source requires one bit");
        return uint8_t(value.bit(0));
    }
    void drive_scalar_after(uint32_t id,uint8_t value,uint64_t dt) {
        auto& channel=delayed_drivers.at(id);
        if(channel.wide!=UINT32_MAX||value>3)throw std::runtime_error("invalid scalar delayed drive");
        if(channel.initialized&&channel.input==value)return;
        const bool replace=channel.policy==DelayPolicy::ReplacePending;
        const bool issue=!replace||channel.output!=value;
        check_delivery(channel,dt,issue);
        if(replace)++channel.generation;
        channel.input=value;channel.initialized=true;
        if(issue)queue_delivery(id,uint32_t(value),dt);
    }
#endif
#endif
#ifdef DSIM_PROPERTY_ENABLED
 #ifdef DSIM_CLOCKING_ENABLED
    int add_clocking(int clock,int edges) {
        structural_change();int id=int(clocking_sites.size());
        clocking_sites.push_back({clock,edges});clocking_clocks[clock].push_back(id);return id;
    }
    void add_clocking_input(int site,int signal,std::function<V(Sim&)> sample,const std::vector<int>& signals) {
        structural_change();property_sampled_signals.insert(signals.begin(),signals.end());
        clocking_sites.at(size_t(site)).inputs.push_back({signal,std::move(sample)});
    }
    V clocking_sample(int site,int input) const {return get(clocking_sites.at(size_t(site)).inputs.at(size_t(input)).signal);}
    void clocking_wait(int site,int process,uint64_t cycles) {
        if(!cycles)throw std::runtime_error("clocking cycle wait requires a positive count");
        wait_dynamic(process,std::vector<std::pair<int,int>>{});
        clocking_sites.at(size_t(site)).waiters.push_back({process,processes.at(size_t(process)).generation,cycles});
    }
    void clocking_drive(int site,std::vector<Part> parts,V value,uint64_t skew) {
        auto& clock=clocking_sites.at(size_t(site));ClockingDrive drive{std::move(parts),std::move(value),skew};
        if(clock.tick==now)schedule_clocking_drive(std::move(drive));
        else clock.drives.push_back(std::move(drive));
    }
 #endif
    void initialize_properties() {
        property_samples.clear();
        // SV's default sampled value includes static declaration initialization,
        // before time-zero procedural assignments. Preserve the expression's
        // initial value (including two-state types and constants), not blanket X.
        for(auto& site:property_sites)for(auto& sample:site.samples) {
            sample.initial=sample.value(*this);sample.history.clear();sample.cursor=0;
            sample.result=sample.kind<2?sample.initial:V(sample.kind==4);
        }
    }
    V property_sample(int site,int slot) {
        auto& sampling=property_sites.at(size_t(site));
        // Procedural RHS evaluation runs in Active, before Observed. Evaluate
        // once on first use; Observed advances clocks skipped by conditionals.
        if(sampling.kind==0&&sampling.clock_pending) {
            sampling.clock_pending=false;prepare_property_samples(sampling);
        }
        return sampling.samples.at(size_t(slot)).result;
    }
    void add_property_sample(int site,int kind,int depth,std::function<V(Sim&)> value,std::function<bool(Sim&)> gate) {
        structural_change();
        if(kind<0||kind>5||depth<1||depth>65536)throw std::runtime_error("invalid property sampling specification");
        property_sites.at(size_t(site)).samples.push_back({kind,depth,std::move(value),std::move(gate),{},{},{},0});
    }
    V sampled_get(int id) const {
        auto found=property_samples.find(id);
        return found==property_samples.end()?get(id):found->second;
    }
    int add_property(int clock,int edges,int process,int delay,int kind,
                     std::function<bool(Sim&)> antecedent,
                     std::function<bool(Sim&)> consequent,
                     std::function<bool(Sim&)> disable,
                     const std::vector<int>& sampled,const std::vector<int>& disabling) {
        structural_change();
        if(property_sites.size()>=size_t(INT32_MAX))throw std::runtime_error("too many concurrent properties");
        int id=int(property_sites.size());
        property_sampled_signals.insert(sampled.begin(),sampled.end());
        for(int signal:disabling)property_disables[signal].push_back(id);
        property_sites.push_back({clock,edges,process,delay,kind,std::move(antecedent),std::move(consequent),std::move(disable),false,false,{},{},{},{}});
        property_clocks[clock].push_back(id);return id;
    }
    void add_property_stage(int site,int delay,std::function<bool(Sim&)> value) {
        structural_change();
        if(delay<0||delay>65536)throw std::runtime_error("invalid property stage delay");
        property_sites.at(size_t(site)).stages.push_back({delay,std::move(value)});
    }
#ifdef DSIM_PROPERTY_ANTECEDENT_ENABLED
    void set_property_antecedent_stages(int site,size_t count) {
        structural_change();
        auto& state=property_sites.at(size_t(site));
        if(!count||count>=state.stages.size())throw std::runtime_error("invalid property antecedent boundary");
        state.antecedent_stages=count;
    }
#endif
    bool property_result(int id) {
        auto& site=property_sites.at(size_t(id));
        if(site.results.empty())throw std::runtime_error("concurrent property action without result");
        bool result=site.results.front();site.results.erase(site.results.begin());
        if(!site.results.empty())enqueue_property(site.process);
        return result;
    }
#endif
#ifdef DSIM_COMPILED_ACTIVATION_ENABLED
    bool compiled_activation_fits(uint64_t count) const {return steps<=limit&&count<=limit-steps;}
    // The compiler proves a finite activation and guards its worst-case cost.
    // Charge at each original instruction before its observable effects.
    void compiled_step() {++steps;}
#endif
    void step() { if(++steps>limit) throw std::runtime_error("event/instruction limit exceeded (execution budget exhausted; a zero-delay loop is one possible cause)"); }
    void process_step() {if(++steps>limit)throw InstructionBudgetExhausted();}
private:
    void commit_nba_batch(std::vector<Nba>& source) {
        source.swap(nba_batch);
        for(const auto& event:nba_batch) {
            if(event.kind==Nba::Wake)enqueue(event.signal);
            else if(event.kind==Nba::Assign)
#if defined(DSIM_COMPACT_NBA_STORAGE) && !defined(DSIM_WIDE_VALUES) && !defined(DSIM_STRING_ENABLED) && !defined(DSIM_REFERENCE_NBA_STORAGE) && !defined(DSIM_REFERENCE_SCALAR_STORES) && !defined(DSIM_REFERENCE_NBA_PLANES)
                // The scalar V ABI passes 24 bytes on the stack. Keep the two
                // stored planes in registers across this publication boundary;
                // set_planes still normalizes and performs every notification.
                set_planes(event.signal,event.a,event.b);
#else
                set(event.signal,
#if defined(DSIM_COMPACT_NBA_STORAGE) && !defined(DSIM_WIDE_VALUES) && !defined(DSIM_STRING_ENABLED) && !defined(DSIM_REFERENCE_NBA_STORAGE)
                event.value()
#else
                event.value
#endif
                );
#endif
#ifdef DSIM_NAMED_EVENTS_ENABLED
            else if(event.kind==Nba::NamedEvent)trigger_event(event.signal);
#endif
            else commit_parts(
#if defined(DSIM_COMPACT_NBA_STORAGE) && !defined(DSIM_WIDE_VALUES) && !defined(DSIM_STRING_ENABLED) && !defined(DSIM_REFERENCE_NBA_STORAGE)
                event.parts(),event.value()
#else
                event.parts,event.value
#endif
                );
            if(finished)break;
        }
        nba_batch.clear();
    }
    void run_to(uint64_t horizon,bool bounded) {
        if(running||horizon<now)throw std::runtime_error("invalid/reentrant simulation time window");
        running=true;
        struct Guard {bool& flag;~Guard(){flag=false;}} guard{running};
#ifdef DSIM_TERMINATION_UNWIND_ENABLED
        try {
#endif
        while(!finished) {
#ifdef DSIM_PROPERTY_ENABLED
            // Drain all Reactive actions and their Re-NBA updates before
            // returning to design Active work triggered by those actions.
            if(property_reacting&&property_reactive.empty()) {
                property_reacting=false;
                if(!property_nba.empty())commit_nba_batch(property_nba);
                if(finished)break;
            }
#endif
#ifdef DSIM_TIMING_ENABLED
            // Invalidated timers must not move time or hide the next live
            // event. Active invalidations are consumed in their FIFO position.
            discard_stale_deliveries();
#endif
#ifdef DSIM_PROCESS_CONTROL_ENABLED
            discard_stale_process_timers();
#endif
#ifdef DSIM_PARALLEL_ENABLED
            receive_inputs();
#endif
            if(!active.empty()
#ifdef DSIM_PROPERTY_ENABLED
               ||property_reacting
#endif
               ) {
#ifdef DSIM_COMB_REGION_ENABLED
                if(active.front().process<0) {run_comb_region(-1-active.front().process);continue;}
#endif
#ifdef DSIM_PROPERTY_ENABLED
                if(!(property_reacting?property_reactive.front():active.front()).resume)process_step();
                auto event=property_reacting?property_reactive.pop():active.pop();
#else
                if(!active.front().resume)process_step();
                auto event=active.pop();
#endif
#ifdef DSIM_PROCESS_CONTROL_ENABLED
                if(stale_process_ready(event))continue;
#endif
#ifdef DSIM_EVENT_NBA_ENABLED
                if(event.event_nba){evaluate_event_nba(event.process);continue;}
#endif
#ifdef DSIM_EXPRESSION_EVENTS_ENABLED
                if(event.expression){evaluate_expression_wait(event.process);continue;}
#endif
#ifdef DSIM_SDF_JOBS_ENABLED
                if(event.sdf_job) {
                    auto& job=sdf_jobs[size_t(event.process)];
                    job.queued=false;job.waiting=true;
                    const auto& handler=handlers[job.handler];
                    handler.run(*this,contexts[handler.context].get(),job.payload);
                } else
#endif
#ifdef DSIM_TIMING_ENABLED
                if(event.process<0)apply_delivery(event.process);
                else
#endif
                {
                    if(event.wake) {
#if !defined(DSIM_REFERENCE_WAKE_DISPATCH) && !defined(DSIM_TIMING_ENABLED) && !defined(DSIM_PROCESS_CONTROL_ENABLED) && !defined(DSIM_PARALLEL_ENABLED) && !defined(DSIM_PROPERTY_ENABLED)
                        // A lone wake would append exactly this process and consume
                        // it on the next iteration. Elide that queue round trip only
                        // when the second logical dispatch cannot exhaust the budget.
                        // Otherwise retain the queued event for checkpoint/retry.
                        if(active.empty()&&!processes[event.process].queued&&steps<limit) {
                            step();
#ifdef DSIM_SCHEDULING_STATS
                            ++wake_dispatch_runs;
#endif
                        }
                        else {enqueue(event.process);continue;}
#else
                        enqueue(event.process);continue;
#endif
                    }
                    auto& process=processes[event.process];process.queued=false;
#ifdef DSIM_PROCESS_LIFETIME_ENABLED
                    process.lifecycle=1;
#endif
#ifdef DSIM_RANDOM_ENABLED
                    const int previous_random_process=random_process;random_process=event.process;
                    struct RandomGuard {int& current;int previous;~RandomGuard(){current=previous;}} random_guard{random_process,previous_random_process};
#endif
#ifdef DSIM_DYNAMIC_FORK_ENABLED
                    fork_current_process=event.process;
                    struct ForkGuard {int& process;~ForkGuard(){process=-1;}} fork_guard{fork_current_process};
#endif
#ifdef DSIM_SELECTION_CHECKS_ENABLED
                    selection_process=event.process;
                    struct SelectionGuard {int& process;~SelectionGuard(){process=-1;}} selection_guard{selection_process};
#endif
                    try {
                        if(process.handler==UINT32_MAX)
#ifdef DSIM_SHARED_TASKS_ENABLED
                            dispatch_task_action(event.process);
#else
                            actions[process.payload]();
#endif
                        else { const auto& handler=handlers[process.handler];handler.run(*this,contexts[handler.context].get(),process.payload); }
                    } catch(const InstructionBudgetExhausted&) {
                        // The closure retains its current PC. Resume it before
                        // any work it already enqueued, without a second wake
                        // or dispatch charge. Ordinary exceptions are not retryable.
                        event.wake=false;event.resume=true;
                        processes[size_t(event.process)].queued=true;
#ifdef DSIM_PROPERTY_ENABLED
                        if(property_reacting)property_reactive.prepend(event);else
#endif
                        active.prepend(event);
                        throw;
#ifdef DSIM_PROCESS_LIFETIME_ENABLED
                    } catch(const ProcessTermination&) {
                        // A killed current process unwinds functions and task frames.
#endif
                    }
#ifdef DSIM_SELECTION_CHECKS_ENABLED
                    selection_process=-1;
#endif
                }
            } else if(!inactive.empty()) active.swap(inactive);
            else if(!nba.empty()) {
                // Apply the current NBA batch before processing newly triggered Active work.
                commit_nba_batch(nba);
            }
#ifdef DSIM_SELECTION_CHECKS_ENABLED
            else if(!selection_reports.empty()) {
                // The supported Active/Inactive/NBA set is now stable. Mature
                // reports before advancing time; print retains transaction order.
                auto reports=std::move(selection_reports);selection_reports.clear();
                for(const auto& report:reports)print(report.message+" time=%0d",{V(now,0,64)});
            }
#endif
#ifdef DSIM_PROPERTY_ENABLED
            else if(properties_pending()) {
                observe_properties();
            } else if(!property_reactive.empty()) {
                property_reacting=true;
#ifdef DSIM_CLOCKING_ENABLED
            } else if(!property_nba.empty()) {
                property_reacting=true;
#endif
            }
#endif
            else if(!timed.empty()
#ifdef DSIM_PARALLEL_ENABLED
                      ||!arrivals.empty()
#endif
                      ) {
#ifdef DSIM_WAVE_ENABLED
                record_wave_tick();
#endif
                uint64_t next_time=timed.empty()?UINT64_MAX:timed.front().time;
#ifdef DSIM_PARALLEL_ENABLED
                if(!arrivals.empty())next_time=std::min(next_time,arrivals.front().time);
#endif
                if(next_time>horizon){
#ifdef DSIM_PROPERTY_ENABLED
                    if(bounded&&horizon>now)property_samples.clear();
#endif
                    if(bounded)now=horizon;break;}

#ifdef DSIM_PROPERTY_ENABLED
                property_samples.clear();
#endif
                now=next_time;
#ifdef DSIM_TIME_WHEEL_ENABLED
                timed.advance(now);
#endif
#ifdef DSIM_PARALLEL_ENABLED
                // Received inputs precede local Active work at that timestamp.
                receive_inputs();
#endif
                while(!timed.empty()&&timed.front().time==now) {
                    auto timer=pop_timer();
#ifdef DSIM_DELAYED_NBA_ENABLED
                    if(timer.delayed_nba) {
                        int slot=timer.process;
#ifdef DSIM_CLOCKING_ENABLED
                        if(timer.clocking_drive)property_nba.push_back(std::move(delayed_nba[size_t(slot)]));
                        else
#endif
                        queue_nba(std::move(delayed_nba[size_t(slot)]));
                        delayed_nba[size_t(slot)]={0,Nba::Assign,V(),{}};
                        free_delayed_nba.push_back(slot);
                        continue;
                    }
#endif
#ifdef DSIM_TIMING_ENABLED
                    Ready wake{timer.process,timer.process>=0};
#else
                    Ready wake{timer.process,true};
#endif
#ifdef DSIM_PROCESS_CONTROL_ENABLED
                    wake.control_epoch=timer.control_epoch;
#endif
                    active.push(wake);
                }
            } else {
#ifdef DSIM_WAVE_ENABLED
                if(bounded&&now<horizon)record_wave_tick();
#endif
#ifdef DSIM_PROPERTY_ENABLED
                if(bounded&&horizon>now)property_samples.clear();
#endif
                if(bounded)now=horizon;
                break;
            }
        }
#ifdef DSIM_TERMINATION_UNWIND_ENABLED
        } catch(const SimulationTermination&) {}
#endif
#ifdef DSIM_WAVE_ENABLED
        record_wave_tick();
#endif
    }
public:
    void run() {run_to(std::numeric_limits<uint64_t>::max(),false);
#ifdef DSIM_FINAL_ENABLED
        if(!defer_finalization)finalize();
#endif
    }
    // Run available work through a finite horizon without creating an idle
    // timestamp. Natural parallel runs use this to retain the last real event
    // time while batching several timestamps in a conservative window.
    void run_available(uint64_t horizon) {run_to(horizon,false);}
    void run_until(uint64_t horizon) {run_to(horizon,true);
#ifdef DSIM_FINAL_ENABLED
        if(finished&&!defer_finalization)finalize();
#endif
    }
};
} // namespace dsim
