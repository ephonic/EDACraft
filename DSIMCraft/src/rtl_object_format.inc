    E formatted_object(E source) {
        needs_object_format=needs_text=true;
        auto value=node("object_format",1,{source});value->text_value=true;
        value->literal="return s.object_text(call_arg0);";
        value->reads.insert(objects_signal);
        // Static members participate in a class dump even though they live
        // outside the object heap. Keep partition and function dependencies intact.
        for(const auto& type:classes)for(const auto& item:type.second.scope->ids) {
            value->reads.insert(item.second);
        }
        return value;
    }
    bool contains_object_format(const std::vector<E>& roots) {
        std::set<const Expr*> seen;std::vector<E> pending=roots;
        while(!pending.empty()) {
            auto value=pending.back();pending.pop_back();if(!seen.insert(value.get()).second)continue;
            if(value->op=="object_format")return true;
            pending.insert(pending.end(),value->args.begin(),value->args.end());
            pending.insert(pending.end(),value->sensitivity_reads.begin(),value->sensitivity_reads.end());
        }
        return false;
    }
    void emit_object_print_types(std::ostream& out) {
        if(!needs_object_format)return;
        std::vector<VeriSeqBlock*> ordered;for(const auto& entry:classes)ordered.push_back(entry.first);
        std::sort(ordered.begin(),ordered.end(),[&](auto* a,auto* b){return classes.at(a).id<classes.at(b).id;});
        for(auto* definition:ordered) {
            const auto& type=classes.at(definition);
            std::string name;
            try {
                name=definition->type_name().substr(6);
                const auto parameters=name.find("#(");
                const auto prefix=name.rfind("::",parameters==std::string::npos?name.size():parameters);
                if(prefix!=std::string::npos)name.erase(0,prefix+2);
            } catch(const std::runtime_error&) {} // Diagnose an unavailable name only when used as a reference.
            out<<"s.object_print_type("<<type.id<<","<<quote(name)<<",{";
            std::vector<VeriSeqBlock*> bases;
            for(auto* base=definition;base;base=base->base_class())bases.push_back(base);
            std::reverse(bases.begin(),bases.end());
            for(auto* base:bases)for(auto* item:classes.at(base).scope->items) {
                if(item->detail_type()!=vsDECL_VAR&&item->detail_type()!=vsDECL_INT)continue;
                const bool integer=item->detail_type()==vsDECL_INT;
                if(!integer&&static_cast<VeriVarDecl*>(item)->is_typedef())continue;
                auto& variables=integer?static_cast<VeriIntDecl*>(item)->vars():static_cast<VeriVarDecl*>(item)->vars();
                for(auto* variable: variables) {
                    if(variable->detail_type()==veEXP_ASSIGN)variable=static_cast<VeriAssignExp*>(variable)->lval();
                    auto* symbol=veri_formal_symbol(variable);Variable property{symbol};
                    const bool is_static=static_cast<VeriDecl*>(item)->explicit_static();
                    char kind=property.is_signed()==IS_TRUE||property.net_type()==vvTIME?'d':'h';
                    if(property.real_width())kind='r';
                    if(veri_string_value(symbol))kind='s';
                    if(veri_class_type(symbol))kind='o';
                    if(property.net_type()==vvEVENT)kind='e';
                    if(veri_chandle_value(symbol)||veri_aggregate_type(symbol))kind='?';
                    auto* enumeration=veri_enum_type(symbol);if(enumeration)kind='n';
                    std::vector<int> axes;
                    for(int axis=0;axis<property.range_depth();++axis) {
                        const int k=veri_array_container_kind(symbol,axis);
                        axes.push_back(k==vrQUEUE||k==vrOPEN?1:associative_kind(k)?2:3);
                        if(axes.back()==3)kind='?';
                    }
                    int signal=-1;size_t field=0;
                    if(kind!='?') {
                        if(is_static)signal=classes.at(base).scope->ids.at(property.name());
                        else field=size_t(object_fields.at(symbol).second);
                    }
                    out<<"{"<<quote(property.name())<<","<<field<<","<<(signal<0?std::string("-1"):sid(signal))<<",'"<<kind<<"',"<<(property.is_signed()==IS_TRUE?"true":"false")<<",{";
                    for(int axis:axes)out<<axis<<",";
                    out<<"},{";
                    if(enumeration)for(size_t i=0;i<enumeration->enum_values().size();++i)
                        out<<"{"<<emit(number(enumeration->enum_values()[i]))<<","<<quote(enumeration->enum_names().at(i))<<"},";
                    out<<"}},";
                }
            }
            out<<"});\n";
        }
    }
