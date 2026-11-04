// Included inside rtl_compiler.cpp's anonymous namespace after emit_expression.
bool constraint_dependent(const E& e) {
    if(e->op=="constraint_var"||e->op=="constraint_foreach"||e->op=="constraint_array_read"||e->op=="constraint_array_size")return true;
    for(const auto& a:e->args)if(constraint_dependent(a))return true;
    return false;
}
void validate_constraint_operators(const E& e,VeriNode* source) {
    if(e->op=="==="||e->op=="!==")fail(source,"four-state equality operators are illegal in constraints");
    for(const auto& a:e->args)validate_constraint_operators(a,source);
}
std::string emit_constraint(const E& e,VeriNode* source,bool mapped,int context=0,int sign_context=-1) {
    validate_constraint_operators(e,source);
    if(e->real_width||e->text_value||e->object_type!=-1||e->array_value)fail(source,"constraint requires integral values");
    if(e->random_state||e->io_state||!e->writes.empty())fail(source,"constraint expression cannot have side effects");
    const auto& op=e->op;int w=std::max(context,e->width);bool sign=e->signed_value&&sign_context!=0;
    auto resize=[&](std::string code){return "q.resize("+code+","+std::to_string(w)+","+(sign?"true":"false")+")";};
    if(op=="constraint_foreach") {
        // Each evaluation constructs a conjunction from the current state
        // container. No parser pointers or procedural loop PC survive here.
        return "([&](){auto constraint_all=q.constant(V(1));"+e->literal+
            "constraint_all=q.binary(\"&&\",constraint_all,"+
            emit_constraint(e->args.back(),source,mapped)+");"+
            std::string(size_t(e->value),'}')+"return constraint_all;}())";
    }
    if(!constraint_dependent(e))return "q.constant("+emit_expression(e,context,mapped,sign_context)+")";
    if(op=="constraint_var"||op=="constraint_array_size")return resize(e->literal);
    if(op=="constraint_array_read") {
        const auto index=emit_constraint(e->args.at(0),source,mapped),width=std::to_string(e->width);
        return resize("("+e->literal+"_enabled?q.element("+e->literal+","+index+","+width+"):q.state_element("+e->literal+"_state,"+index+","+width+"))");
    }
    auto sub=[&](size_t i,int c=0,int s=-1){return emit_constraint(e->args.at(i),source,mapped,c,s);};
    if(op=="cast"||op=="two_state")return resize(sub(0));
    if(op=="fixed_cast"||op=="fixed_cast_2")return resize("q.resize("+sub(0,e->width)+","+std::to_string(e->width)+")");
    if(op=="concat")return resize("q.binary(\"concat\","+sub(0)+","+sub(1)+")");
    if(op=="slice")return resize("q.slice("+sub(0)+","+e->literal+")");
    if(op=="mux")return "q.choose("+sub(0)+","+sub(1,w,int(sign))+","+sub(2,w,int(sign))+")";
    if(op=="inside") {
        int width=e->args[0]->width;bool signed_set=e->args[0]->signed_value;
        for(size_t i=1;i<e->args.size();++i){width=std::max(width,e->args[i]->width);signed_set&=e->args[i]->signed_value;}
        std::string code="q.constant(V(0))";auto value=sub(0,width,int(signed_set));
        for(size_t i=1;i<e->args.size();++i) {
            auto item=e->args[i];std::string match;
            if(item->op=="inside_range") {
                auto low=emit_constraint(item->args[0],source,mapped,width,int(signed_set));
                auto high=emit_constraint(item->args[1],source,mapped,width,int(signed_set));
                const auto flag=signed_set?",true)":",false)";
                match="q.binary(\"&&\",q.binary(\">=\","+value+","+low+flag+",q.binary(\"<=\","+value+","+high+flag+")";
            } else match="q.binary(\"==\","+value+","+sub(i,width,int(signed_set))+")";
            code="q.binary(\"||\","+code+","+match+")";
        }
        return resize(code);
    }
    static const std::set<std::string> unary={"+","-","~","!","&","|","^"};
    if(e->args.size()==1&&unary.count(op)) {
        bool reduce=op=="!"||op=="&"||op=="|"||op=="^";
        return resize("q.unary("+quote(op)+","+sub(0,reduce?0:w,reduce?-1:int(sign))+")");
    }
    static const std::set<std::string> binary={"+","-","*","/","%","&","|","^","&&","||","==","!=","===","!==","<",">","<=",">=","<<",">>",">>>"};
    if(e->args.size()==2&&binary.count(op)) {
        bool logical=op=="&&"||op=="||";
        bool compare=op=="=="||op=="!="||op=="==="||op=="!=="||op=="<"||op==">"||op=="<="||op==">=";
        bool shift=op=="<<"||op==">>"||op==">>>";
        bool operands_signed=compare?e->args[0]->signed_value&&e->args[1]->signed_value:sign;
        int a=logical?0:compare?std::max(e->args[0]->width,e->args[1]->width):w;
        int b=logical||shift?0:a;
        return resize("q.binary("+quote(op)+","+sub(0,a,logical?-1:int(operands_signed))+","+sub(1,b,logical||shift?-1:int(operands_signed))+","+(operands_signed?"true":"false")+")");
    }
    fail(source,"unsupported symbolic constraint operation: "+op);
}
