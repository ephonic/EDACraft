// Included in Lower: DPI ABI lowering uses the ordinary subroutine frames.
struct DpiType {
    std::string scalar;int width=0;bool text=false,logic=false,vector=false,opaque=false;int real_width=0;
    std::string ctype(bool input=false,bool output=false) const {
        if(vector)return std::string(input?"const ":"")+(logic?"svLogicVecVal*":"svBitVecVal*");
        return scalar+(output?"*":"");
    }
    std::string from_c(const std::string& value) const {
        if(opaque)return "V(uint64_t(reinterpret_cast<uintptr_t>("+value+")),0,64)";
        if(real_width)return "V::real("+value+","+std::to_string(real_width)+")";
        if(text)return "V::text("+value+"?"+value+":\"\")";
        if(vector)return std::string(logic?"dpi_from_logic(":"dpi_from_bits(")+value+","+std::to_string(width)+")";
        if(logic)return "V(uint64_t("+value+")&1,(uint64_t("+value+")>>1)&1,1)";
        return width?"V(uint64_t("+value+"),0,"+std::to_string(width)+")":"V(0,0,1)";
    }
    std::string to_c(const std::string& value,const std::string& key={}) const {
        if(opaque)return "reinterpret_cast<void*>(uintptr_t(("+value+").a))";
        if(real_width)return "static_cast<"+scalar+">(("+value+").real_value())";
        if(text)return key.empty()?"("+value+").text_value().c_str()":"dpi_export_string("+quote(key)+","+value+")";
        if(vector)return std::string(logic?"dpi_logic(":"dpi_bits(")+value+","+std::to_string(width)+")";
        if(logic)return "svLogic((("+value+").a&1)|((("+value+").b&1)<<1))";
        return "static_cast<"+scalar+">(("+value+").a&~("+value+").b)";
    }
};
struct DpiSignature {DpiType result;std::vector<DpiType> args;std::vector<int> directions;};
bool needs_dpi=false;
std::vector<std::string> dpi_libraries;
std::map<std::string,std::string> dpi_prototypes;
std::string dpi_definitions,dpi_bindings;
DpiType dpi_type(VeriNode* symbol,bool result=false) {
    if(!symbol)return {"void"};
    Variable var{symbol};
    if(var.range_depth()||var.dynamic()||class_type(symbol)>=0||veri_aggregate_type(symbol))fail(symbol,"DPI currently requires scalar or packed integral/string values; open/unpacked arrays, aggregates and handles are not supported yet");
    int type;bool packed=false;
    if(symbol->tok_type()==vtFUNC) {
        auto* f=static_cast<VeriFunc*>(symbol)->func();type=f->result_type();
        packed=f->dpi_packed_result()||(f->resolved_type()&&f->resolved_type()->vec_scalar()==vpVECTOR);
    } else if(symbol->tok_type()==vtTFVAR) {
        type=static_cast<VeriTfVar*>(symbol)->net_type();
        auto* decl=static_cast<VeriTfDecl*>(symbol->father());
        packed=decl->range()||(decl->resolved_type()&&decl->resolved_type()->vec_scalar()==vpVECTOR);
    } else fail(symbol,"unresolved DPI type");
    DpiType t;t.width=var.dlen();
    if(type==vvCHANDLE){t.scalar="void*";t.opaque=true;}
    else if(veri_real(type)){t.real_width=veri_type_width(type);t.scalar=t.real_width==32?"float":"double";needs_real=true;}
    else if(type==vvSTRING){t.scalar="const char*";t.text=true;needs_text=true;}
    else if(type==vvBYTE||type==vvSHORTINT||type==vvINT2||type==vvLONGINT) {
        t.scalar=std::string(var.is_signed()==IS_TRUE?"":"unsigned ")+(type==vvBYTE?"char":type==vvSHORTINT?"short":type==vvINT2?"int":"long long");
        if(type==vvBYTE&&var.is_signed()==IS_TRUE)t.scalar="signed char";
    } else if(type==vvBIT||type==vvLOGIC||type==vvREG||type==vvINT||type==vvTIME) {
        t.logic=type!=vvBIT;t.vector=packed||t.width>1;
        t.scalar=t.logic?"svLogic":"svBit";
        if(t.vector&&result)fail(symbol,"DPI packed-vector returns are not supported yet; use an output formal");
    } else fail(symbol,"unsupported DPI C type");
    if(t.width>64)needs_wide=true;return t;
}
DpiSignature dpi_signature(VeriFuncDecl* declaration) {
    DpiSignature signature;
    if(!declaration->is_void()&&!declaration->scope()->value_within_module(declaration->func_name()))fail(declaration,"unresolved DPI return type");
    signature.result=dpi_type(declaration->is_void()?nullptr:declaration->scope()->value_within_module(declaration->func_name()),true);
    for(auto* formal:veri_subroutine_formals(declaration)) {
        auto* symbol=veri_formal_symbol(formal);if(!symbol||symbol->tok_type()!=vtTFVAR)fail(formal,"unresolved DPI formal");
        int direction=static_cast<VeriTfVar*>(symbol)->inout();
        if(direction!=vpIN&&direction!=vpOUT&&direction!=vpINOUT)fail(formal,"DPI formals cannot use ref or const ref");
        if(declaration->dpi_import()&&declaration->dpi_property()==1&&direction!=vpIN)fail(formal,"pure DPI functions require input-only formals");
        signature.args.push_back(dpi_type(symbol));signature.directions.push_back(direction);
    }
    if(declaration->dpi_import()&&declaration->dpi_property()==1&&declaration->is_void())fail(declaration,"pure DPI functions require a return value");
    return signature;
}
void dpi_declare(const std::string& name,const DpiSignature& signature,VeriNode* source) {
    if(name.empty()||!(std::isalpha(static_cast<unsigned char>(name.front()))||name.front()=='_')||
       std::any_of(name.begin(),name.end(),[](unsigned char c){return !std::isalnum(c)&&c!='_';}))fail(source,"DPI C name must be a C identifier");
    std::string prototype=signature.result.ctype()+" "+name+"(";
    for(size_t i=0;i<signature.args.size();++i){if(i)prototype+=",";prototype+=signature.args[i].ctype(signature.directions[i]==vpIN,signature.directions[i]!=vpIN);}
    prototype+=")";
    auto found=dpi_prototypes.emplace(name,prototype);
    if(!found.second&&found.first->second!=prototype)fail(source,"conflicting DPI C signatures: "+name+" ("+found.first->second+" versus "+prototype+")");
}
void dpi_function_body(Callable& fn,VeriFuncDecl* decl) {
    const auto signature=dpi_signature(decl);dpi_declare(decl->dpi_name(),signature,decl);
    std::string code="{DpiInvocation dpi_invocation(dpi,s,"+quote(fn.scope->parent->path)+","+(decl->dpi_property()==2?"true":"false")+","+(decl->dpi_property()==1?"true":"false")+");";
    std::string pointer=signature.result.ctype()+"(*)(",actuals;
    for(size_t i=0;i<signature.args.size();++i) {
        if(i){pointer+=",";actuals+=",";}
        const auto& type=signature.args[i];const bool input=fn.directions[i]==vpIN;
        pointer+=type.ctype(input,!input);
        const int id=fn.scope->ids.at(Variable{veri_formal_symbol(fn.formals[i])}.name());
        auto source=signal_expr(id);if(fn.directions[i]!=vpOUT)read(fn.process,source);
        const std::string local="dpi_arg"+std::to_string(i);
        code+="auto "+local+"="+type.to_c("s.get("+sid(id)+")")+";";
        actuals+=local+(type.vector?".data()":input?"":"_pointer");
        if(!input&&!type.vector)code+="auto* "+local+"_pointer=&"+local+";";
    }
    pointer+=")";const auto invoke="dpi.resolve<"+pointer+">("+quote(decl->dpi_name())+")("+actuals+")";
    if(decl->is_void())code+=invoke+";";
    else {
        code+="auto dpi_return="+invoke+";s.set("+sid(fn.result)+","+signature.result.from_c("dpi_return")+");";
        fn.process.writes.push_back({fn.result,0,signals[fn.result].width,0});fn.process.touches.insert(fn.result);
    }
    for(size_t i=0;i<signature.args.size();++i)if(fn.directions[i]!=vpIN) {
        int id=fn.scope->ids.at(Variable{veri_formal_symbol(fn.formals[i])}.name());
        code+="s.set("+sid(id)+","+signature.args[i].from_c("dpi_arg"+std::to_string(i)+(signature.args[i].vector?".data()":""))+");";
        fn.process.writes.push_back({id,0,signals[id].width,0});fn.process.touches.insert(id);
    }
    code+="}";add(fn.process,code);
    if(decl->dpi_property()!=1){fn.process.io_state=true;fn.process.side_effect=true;fn.process.event_safe=false;}
}
std::string dpi_export_wrapper(const std::string& name,const DpiSignature& signature) {
    std::string code="extern \"C\" "+signature.result.ctype()+" "+name+"(";
    for(size_t i=0;i<signature.args.size();++i){if(i)code+=",";code+=signature.args[i].ctype(signature.directions[i]==vpIN,signature.directions[i]!=vpIN)+" arg"+std::to_string(i);}
    code+="){using namespace dsim;";
    for(size_t i=0;i<signature.args.size();++i)if(signature.directions[i]!=vpIN)code+="if(!arg"+std::to_string(i)+")throw std::runtime_error(\"null DPI output pointer\");";
    code+="auto values=dpi_export_call("+quote(name)+",{";
    for(size_t i=0;i<signature.args.size();++i) {
        const auto& type=signature.args[i];const bool input=signature.directions[i]==vpIN;
        if(signature.directions[i]==vpOUT)code+=type.real_width?"V::real(0,"+std::to_string(type.real_width)+"),":type.text?"V::text(\"\"),":"V(0,0,"+std::to_string(type.width)+"),";
        else code+=type.from_c((!input&&!type.vector?"*":"")+std::string("arg")+std::to_string(i))+",";
    }
    code+="});";
    for(size_t i=0;i<signature.args.size();++i)if(signature.directions[i]!=vpIN) {
        const auto& type=signature.args[i];auto value="values.at("+std::to_string(i+1)+")";
        code+="{auto value="+type.to_c(value,name+"_arg"+std::to_string(i))+";";
        if(type.vector)code+="std::copy(value.begin(),value.end(),arg"+std::to_string(i)+");";
        else code+="*arg"+std::to_string(i)+"=value;";
        code+="}";
    }
    if(signature.result.width)code+="return "+signature.result.to_c("values.at(0)",name+"_result")+";";
    return code+"}\n";
}
void detect_dpi() {
    const size_t count=scopes.size();
    for(size_t i=0;i<count;++i)for(auto* n:scopes[i]->items)
        if((n->detail_type()==vsDECL_FUNC_DECL&&static_cast<VeriFuncDecl*>(n)->dpi_import())||dynamic_cast<VeriDpiExportStmt*>(n))needs_dpi=true;
    if(!needs_dpi)return;
    // Foreign callbacks can access any exported scope. Start with one kernel;
    // the fallback is reported by the normal --parallel-stats adapter.
    if(parallel_count){parallel_count=0;serial_parallel_stats=true;}
}
void prepare_dpi() {
    if(!needs_dpi)return;
    const size_t count=scopes.size();
    std::set<std::string> wrappers;std::map<std::string,std::string> export_shapes;std::set<std::pair<Scope*,std::string>> bindings;
    for(size_t i=0;i<count;++i) {
        auto* owner=scopes[i].get();
        for(auto* n:owner->items) {
            if(n->detail_type()==vsDECL_FUNC_DECL&&static_cast<VeriFuncDecl*>(n)->dpi_import()) {
                auto* decl=static_cast<VeriFuncDecl*>(n);dpi_declare(decl->dpi_name(),dpi_signature(decl),decl);
            }
            auto* item=dynamic_cast<VeriDpiExportStmt*>(n);if(!item)continue;
            if(item->task())fail(item,"DPI exported tasks are not supported yet");
            auto* symbol=item->scope()->value_same_level(item->name());
            if(!symbol||symbol->tok_type()!=vtFUNC)fail(item,"DPI export requires a function defined in the same scope: "+item->name());
            auto* decl=static_cast<VeriFunc*>(symbol)->func();if(decl->dpi_import())fail(item,"DPI cannot export an imported function");
            if(item->c_name()=="main"||item->c_name()=="svGetScope"||item->c_name()=="svSetScope"||item->c_name()=="svGetScopeFromName"||item->c_name()=="svGetNameFromScope")fail(item,"DPI export C name is reserved");
            auto signature=dpi_signature(decl);dpi_declare(item->c_name(),signature,item);
            // One native wrapper per C name must have the same conversion
            // contract in every scope, including packed widths and directions.
            std::string shape=std::to_string(signature.result.width);
            for(size_t j=0;j<signature.args.size();++j)shape+=":"+std::to_string(signature.args[j].width)+"/"+std::to_string(signature.directions[j]);
            auto existing=export_shapes.emplace(item->c_name(),shape);
            if(!existing.second&&existing.first->second!=shape)fail(item,"DPI exports sharing a C name require identical SV widths and directions in this version");
            if(!bindings.insert({owner,item->c_name()}).second)fail(item,"duplicate DPI export in scope: "+item->c_name());
            if(wrappers.insert(item->c_name()).second)dpi_definitions+=dpi_export_wrapper(item->c_name(),signature);
            VeriNode* args=nullptr;
            for(const auto& type:signature.args) {
                auto* value=type.opaque?veri_parser->gen_multi(nullptr,nullptr,vemNULL,item->line(),item->col()):veri_parser->gen_primary(type.text?"\"\"":"0",item->line(),item->col(),type.text?veSTR:veNUM);
                args=args?veri_parser->gen_multi(args,value,vemCOMMA_EXP,item->line(),item->col()):value;
            }
            auto* call=veri_parser->gen_caller(veri_parser->gen_primary(item->name().c_str(),item->line(),item->col(),veVAR),args);
            veri_bind_semantic(call,item->scope());scope=owner;
            auto& fn=callable(call,true);
            // Foreign entry uses the same owned automatic frame as an SV call,
            // then returns output values before the guard restores that frame.
            needs_explicit_automatic=needs_process_control=true;
            std::string body="dpi.bind("+quote(owner->path)+","+quote(item->c_name())+",[&](const std::vector<V>& args)->std::vector<V>{"+reference_entry(fn,"",true);
            for(size_t j=0;j<fn.formals.size();++j)if(fn.directions[j]!=vpOUT) {
                int id=fn.scope->ids.at(Variable{veri_formal_symbol(fn.formals[j])}.name());body+="s.set("+sid(id)+",args.at("+std::to_string(j)+"));";
            }
            body+="int pc=0;";
            for(int j=0;j<fn.process.repeat_counters;++j)body+="uint64_t repeat"+std::to_string(j)+"=0;";
            for(size_t j=0;j<fn.process.array_values.size();++j)body+="std::vector<V> array_value"+std::to_string(j)+"("+std::to_string(fn.process.array_values[j])+");";
            body+="for(;;){s.process_step();switch(pc){";
            for(size_t j=0;j<fn.process.instructions.size();++j) {
                const auto& inst=fn.process.instructions[j];body+="case "+std::to_string(j)+":{";
                if(inst.condition)body+="pc=("+emit(inst.condition)+").truth()==1?"+std::to_string(inst.yes)+":"+std::to_string(inst.no)+";continue;";
                else if(inst.yes>=0)body+="pc="+std::to_string(inst.yes)+";continue;";
                else body+=inst.code+"pc="+std::to_string(j+1)+";continue;";
                body+="}";
            }
            body+="default:return {"+(fn.result<0?std::string("V(0,0,1)"):"s.get("+sid(fn.result)+")")+",";
            for(auto* formal:fn.formals)body+="s.get("+sid(fn.scope->ids.at(Variable{veri_formal_symbol(formal)}.name()))+"),";
            dpi_bindings+=body+"};}}});\n";
        }
    }
}
void emit_dpi_setup(std::ostream& out) const {
    if(!needs_dpi)return;
    out<<"DpiRuntime dpi;\nstd::vector<std::string> dpi_libraries;std::vector<char*> dpi_options{argv[0]};\n"
          "for(int i=1;i<argc;++i){if(std::string(argv[i])==\"--dpi-lib\"){if(++i==argc)throw std::runtime_error(\"--dpi-lib requires a path\");dpi_libraries.emplace_back(argv[i]);}else dpi_options.push_back(argv[i]);}\n"
          "argc=int(dpi_options.size());dpi_options.push_back(nullptr);argv=dpi_options.data();\n"
          "if(dpi_libraries.empty())dpi_libraries={";
    for(const auto& path:dpi_libraries)out<<quote(path)<<",";
    out<<"};for(const auto& path:dpi_libraries)dpi.load(path);\n";
    for(const auto& sc:scopes)if(!sc->procedural)out<<"dpi.scope("<<quote(sc->path)<<");\n";
}
