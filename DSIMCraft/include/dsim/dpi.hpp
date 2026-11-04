#pragma once
#include "svdpi.h"
#include <dlfcn.h>
#include <map>
#include <memory>
#include <functional>
#include <string>
#include <vector>
#include <stdexcept>
#include <cstring>
namespace dsim {
struct DpiScope {std::string name;};
struct DpiRuntime;
struct DpiContext {DpiRuntime* runtime=nullptr;DpiScope* scope=nullptr;};
inline thread_local DpiContext dpi_context;
struct DpiRuntime {
    using Callback=std::function<std::vector<V>(const std::vector<V>&)>;
    std::map<std::string,std::unique_ptr<DpiScope>> scopes;
    std::map<std::pair<std::string,std::string>,Callback> exports;
    std::map<std::string,void*> symbols;
    std::vector<void*> libraries;
    DpiRuntime()=default;
    DpiRuntime(const DpiRuntime&)=delete;
    ~DpiRuntime(){for(auto i=libraries.rbegin();i!=libraries.rend();++i)dlclose(*i);}
    void load(const std::string& name) {
        auto* handle=dlopen(name.c_str(),RTLD_NOW|RTLD_GLOBAL);
        if(!handle)throw std::runtime_error("DPI library "+name+": "+dlerror());
        libraries.push_back(handle);
    }
    DpiScope* scope(const std::string& name) {
        auto& slot=scopes[name];if(!slot)slot=std::make_unique<DpiScope>(DpiScope{name});return slot.get();
    }
    DpiScope* find(svScope opaque) const {
        for(const auto& entry:scopes)if(entry.second.get()==opaque)return entry.second.get();return nullptr;
    }
    template<class F> F resolve(const std::string& name) {
        auto i=symbols.find(name);
        if(i==symbols.end()) {
            void* symbol=nullptr;
            for(auto* lib:libraries)if((symbol=dlsym(lib,name.c_str())))break;
            if(!symbol)symbol=dlsym(RTLD_DEFAULT,name.c_str());
            if(!symbol)throw std::runtime_error("DPI symbol not found: "+name);
            i=symbols.emplace(name,symbol).first;
        }
        F fn;static_assert(sizeof(fn)==sizeof(i->second),"unsupported function pointer ABI");
        std::memcpy(&fn,&i->second,sizeof(fn));return fn;
    }
    void bind(const std::string& path,const std::string& name,Callback callback) {
        scope(path);if(!exports.emplace(std::make_pair(path,name),std::move(callback)).second)
            throw std::runtime_error("duplicate DPI export: "+path+"."+name);
    }
};
struct DpiInvocation {
    DpiContext previous;
    DpiInvocation(DpiRuntime& runtime,Sim& sim,const std::string& path,bool context,bool pure):previous(dpi_context) {
        if(!pure&&sim.prediction_active())throw ForeignCallBarrier{};
        dpi_context=context?DpiContext{&runtime,runtime.scope(path)}:DpiContext{};
    }
    ~DpiInvocation(){dpi_context=previous;}
};
inline std::vector<V> dpi_export_call(const std::string& name,const std::vector<V>& args) {
    const auto context=dpi_context;
    if(!context.runtime||!context.scope)throw std::runtime_error("DPI export requires a context import and valid scope: "+name);
    auto i=context.runtime->exports.find({context.scope->name,name});
    if(i==context.runtime->exports.end())throw std::runtime_error("DPI export not found in scope: "+context.scope->name+"."+name);
    struct Restore{DpiContext saved;~Restore(){dpi_context=saved;}} restore{context};
    return i->second(args);
}
inline uint64_t dpi_word_a(const V& v,size_t word) {
#ifdef DSIM_WIDE_VALUES
    return v.word_a(word);
#else
    return word?0:v.a;
#endif
}
inline uint64_t dpi_word_b(const V& v,size_t word) {
#ifdef DSIM_WIDE_VALUES
    return v.word_b(word);
#else
    return word?0:v.b;
#endif
}
inline std::vector<svBitVecVal> dpi_bits(const V& v,int width) {
    std::vector<svBitVecVal> out(size_t(width+31)/32);
    for(size_t i=0;i<out.size();++i)out[i]=uint32_t((dpi_word_a(v,i/2)&~dpi_word_b(v,i/2))>>(32*(i%2)));
    if(width%32)out.back()&=uint32_t(mask(width%32));return out;
}
inline std::vector<svLogicVecVal> dpi_logic(const V& v,int width) {
    std::vector<svLogicVecVal> out(size_t(width+31)/32);
    for(size_t i=0;i<out.size();++i)out[i]={uint32_t(dpi_word_a(v,i/2)>>(32*(i%2))),uint32_t(dpi_word_b(v,i/2)>>(32*(i%2)))};
    if(width%32){out.back().aval&=uint32_t(mask(width%32));out.back().bval&=uint32_t(mask(width%32));}return out;
}
inline V dpi_from_logic(const svLogicVecVal* data,int width) {
    if(!data)throw std::runtime_error("null DPI packed-vector pointer");
#ifdef DSIM_WIDE_VALUES
    std::vector<V::Word> words(size_t(width+63)/64);
    for(size_t i=0;i<size_t(width+31)/32;++i){words[i/2].a|=uint64_t(data[i].aval)<<(32*(i%2));words[i/2].b|=uint64_t(data[i].bval)<<(32*(i%2));}
    return V::from_words(std::move(words),width);
#else
    return V(uint64_t(data[0].aval)|(width>32?uint64_t(data[1].aval)<<32:0),uint64_t(data[0].bval)|(width>32?uint64_t(data[1].bval)<<32:0),width);
#endif
}
inline V dpi_from_bits(const svBitVecVal* data,int width) {
    if(!data)throw std::runtime_error("null DPI packed-vector pointer");
    std::vector<svLogicVecVal> logic(size_t(width+31)/32);
    for(size_t i=0;i<logic.size();++i)logic[i]={data[i],0};return dpi_from_logic(logic.data(),width);
}
#ifdef DSIM_STRING_ENABLED
inline const char* dpi_export_string(const std::string& key,const V& value) {
    static thread_local std::map<std::string,std::string> storage;
    auto& slot=storage[key];slot=value.text_value();return slot.c_str();
}
#endif
}
extern "C" svScope svGetScope(void) {return dsim::dpi_context.scope;}
extern "C" svScope svSetScope(const svScope scope) {
    auto& context=dsim::dpi_context;
    if(!context.runtime)throw std::runtime_error("svSetScope requires a DPI context import");
    auto* target=context.runtime->find(scope);if(!target)throw std::runtime_error("invalid DPI scope handle");
    auto previous=context.scope;context.scope=target;return previous;
}
extern "C" svScope svGetScopeFromName(const char* name) {
    auto& context=dsim::dpi_context;if(!context.runtime||!name)return nullptr;
    auto i=context.runtime->scopes.find(name);return i==context.runtime->scopes.end()?nullptr:i->second.get();
}
extern "C" const char* svGetNameFromScope(const svScope scope) {
    auto& context=dsim::dpi_context;if(!context.runtime)return nullptr;
    auto* found=context.runtime->find(scope);return found?found->name.c_str():nullptr;
}
