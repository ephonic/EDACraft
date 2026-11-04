// Functional coverage stays in the compiled design. Syntax is owned/cloned by
// the RTL parser; counters and receiver handles belong to each Sim checkpoint.
struct CoverageIR {
    VeriSeqBlock* type; VeriClocking* syntax; Scope* owner;
    std::string definition; std::vector<E> values,gates;
};
std::vector<CoverageIR> coverages;
static std::vector<VeriClocking*> coverage_items(VeriNode* list) {
    std::vector<VeriClocking*> result;
    if(list)for(auto* item:static_cast<VeriModuleItemList*>(list)->item_list())result.push_back(static_cast<VeriClocking*>(item));
    return result;
}
int coverage_option_value(VeriClocking* option) {
    auto* value=option->children.at(0);
    if(!veri_elaboration_constant(value)||veri_real_width(value)||veri_string_value(value))fail(option,"coverage option requires an integral constant");
    auto number_value=veri_constant_value(static_cast<VeriExp*>(value),0);
    if(!number_value)fail(option,"coverage option could not be evaluated as a constant");
    auto converted=number(number_value.get());
    if(converted->unknown||converted->negative||converted->host_overflow||converted->value>65536)fail(option,"coverage option is outside 0..65536");
    return int(converted->value);
}
void prepare_coverages() {
    auto* previous=scope;auto saved_receiver=argument_receiver;
    // Parser IDs survive instance cloning and do not depend on allocator/host
    // pointer ordering. Use them for emitted registration and event processes.
    std::vector<VeriSeqBlock*> types;
    for(const auto& entry:classes)if(entry.first->coverage_type())types.push_back(entry.first);
    std::sort(types.begin(),types.end(),[](auto* a,auto* b){return a->idx()<b->idx();});
    for(auto* type:types) {
        auto* owner=classes.at(type).scope->parent;scope=owner;
        auto* syntax=static_cast<VeriClocking*>(static_cast<VeriModuleItemList*>(type->decl_list())->item_list().front());
        CoverageIR coverage{type,syntax,owner,"",{}, {}};
        needs_real=true;
        if(owner->class_definition) {
            argument_receiver=node("saved",64);argument_receiver->literal="coverage_owner";argument_receiver->object_type=int(owner->class_definition->idx());
        } else argument_receiver={};
        int per_instance=0,merge=0,group_weight=1,group_goal=100,group_least=1,group_auto=64;
        std::set<std::string> group_options;
        auto apply_option=[&](VeriClocking* option,bool group,int& weight,int& goal,int& least,int& automatic) {
            const auto& name=option->name;int value=coverage_option_value(option);
            if(group&&!group_options.insert(name).second)fail(option,"duplicate coverage option: "+name);
            if(name=="option.weight")weight=value;
            else if(name=="option.goal"&&value>0&&value<=100)goal=value;
            else if(name=="option.at_least"&&value>0)least=value;
            else if(name=="option.auto_bin_max"&&value>0)automatic=value;
            else if(group&&name=="option.per_instance"&&value<=1)per_instance=value;
            else if(group&&name=="type_option.merge_instances"&&value<=1)merge=value;
            else fail(option,"unsupported coverage option or value: "+name);
        };
        for(auto* item:coverage_items(syntax->children[1]))if(item->detail_type()==vsDECL_COVER_OPTION)
            apply_option(item,true,group_weight,group_goal,group_least,group_auto);
        if(group_weight!=1)fail(syntax,"covergroup option.weight requires global coverage aggregation, which is not supported yet");
        std::string points="{";std::map<std::string,int> point_names;
        for(auto* point:coverage_items(syntax->children[1])) {
            if(point->detail_type()!=vsDECL_COVERPOINT)continue;
            const auto name=point->name.empty()&&point->children[0]->detail_type()==veEXP_PRI?static_cast<VeriPrimaryExp*>(point->children[0])->str():point->name;
            if(!name.empty()&&!point_names.emplace(name,int(coverage.values.size())).second)fail(point,"duplicate coverpoint: "+name);
            auto value=expr(point->children[0]);
            if(value->width>32||value->width<1||value->text_value||value->real_width||value->object_type!=-1||veri_array_shape(point->children[0]).unpacked)
                fail(point,"coverpoint currently requires a packed integral expression of at most 32 bits");
            if(value->procedural_only||!value->writes.empty())fail(point,"coverpoint sampling expression must not have side effects");
            coverage.values.push_back(value);
            auto gate=point->children[1]?expr(point->children[1]):node("literal",1);if(!point->children[1])gate->literal="V(1)";
            if(gate->text_value||gate->real_width||gate->object_type!=-1||gate->procedural_only||!gate->writes.empty())fail(point,"coverpoint iff requires a side-effect-free integral expression");
            coverage.gates.push_back(gate);
            int weight=1,goal=group_goal,least=group_least,automatic=group_auto;
            std::set<std::string> options,names;std::string bins="{";bool explicit_bins=false;
            for(auto* bin:coverage_items(point->children[2])) {
                if(bin->detail_type()==vsDECL_COVER_OPTION) {
                    if(!options.insert(bin->name).second)fail(bin,"duplicate coverpoint option: "+bin->name);
                    apply_option(bin,false,weight,goal,least,automatic);continue;
                }
                if(!names.insert(bin->name).second)fail(bin,"duplicate coverage bin: "+bin->name);
                explicit_bins|=bin->direction==0;
                if(bin->children[1])fail(bin,"bin-level iff is not supported yet; use coverpoint iff");
                if(!bin->children[0]&&bin->direction)fail(bin,"ignore_bins/illegal_bins default is not supported yet");
                bins+="{"+quote(bin->name)+","+std::to_string(bin->direction)+","+(bin->step?"true":"false")+","+(!bin->children[0]?"true":"false")+",{";
                for(auto* range:coverage_items(bin->children[0])) {
                    std::vector<std::string> bounds;
                    for(auto* bound:range->children) {
                        if(!bound) {bounds.push_back(bounds.front());continue;}
                        if(!veri_elaboration_constant(bound)||veri_real_width(bound)||veri_string_value(bound)||veri_class_type(bound))fail(bound,"coverage bin bound requires a known integral constant");
                        auto number_value=veri_constant_value(static_cast<VeriExp*>(bound),value->width,int(value->signed_value));
                        if(!number_value)fail(bound,"coverage bin bound could not be evaluated as a constant");
                        auto converted=number(number_value.get());if(converted->unknown)fail(bound,"X/Z coverage bin bounds are not supported yet");
                        bounds.push_back("Sim::coverage_integer("+emit(converted,value->width)+","+std::to_string(value->width)+","+(value->signed_value?"true":"false")+")");
                    }
                    bins+="{"+bounds[0]+","+bounds[1]+"},";
                }
                bins+="}},";
            }
            if(!explicit_bins)if(auto* enumeration=veri_enum_type(point->children[0])) {
                const auto& names=enumeration->enum_names();const auto& values=enumeration->enum_values();
                for(size_t i=0;i<values.size();++i) {
                    auto bound="Sim::coverage_integer("+emit(number(values[i]),value->width)+","+std::to_string(value->width)+","+(value->signed_value?"true":"false")+")";
                    bins+="{"+quote("auto["+names.at(i)+"]")+",0,false,false,{{"+bound+","+bound+"}}},";
                }
            }
            points+="{"+std::to_string(value->width)+","+(value->signed_value?"true":"false")+","+std::to_string(weight)+","+std::to_string(goal)+","+std::to_string(least)+","+std::to_string(automatic)+","+bins+"}},";
        }
        const auto point_count=coverage.values.size();
        for(auto* cross:coverage_items(syntax->children[1]))if(cross->detail_type()==vsDECL_COVER_CROSS) {
            if(!cross->name.empty()&&!point_names.emplace(cross->name,int(coverage.values.size())).second)fail(cross,"duplicate coverpoint/cross: "+cross->name);
            int weight=1,goal=group_goal,least=group_least,automatic=group_auto;
            std::set<std::string> options;
            for(auto* item:coverage_items(cross->children[2])) {
                if(item->detail_type()!=vsDECL_COVER_OPTION)fail(item,"explicit cross bins/binsof are not supported yet");
                if(!options.insert(item->name).second)fail(item,"duplicate cross option: "+item->name);
                apply_option(item,false,weight,goal,least,automatic);
            }
            std::string sources="{";std::set<int> unique;
            for(auto* item:coverage_items(cross->children[0])) {
                auto found=point_names.find(item->name);
                if(found==point_names.end()||size_t(found->second)>=point_count||!unique.insert(found->second).second)fail(item,"cross requires distinct declared coverpoints: "+item->name);
                sources+=std::to_string(found->second)+",";
            }
            auto gate=cross->children[1]?expr(cross->children[1]):node("literal",1);if(!cross->children[1])gate->literal="V(1)";
            if(gate->text_value||gate->real_width||gate->object_type!=-1||gate->procedural_only||!gate->writes.empty())fail(cross,"cross iff requires a side-effect-free integral expression");
            auto dummy=node("literal",1);dummy->literal="V(0)";coverage.values.push_back(dummy);coverage.gates.push_back(gate);
            points+="{1,false,"+std::to_string(weight)+","+std::to_string(goal)+","+std::to_string(least)+",0,{},"+sources+"}},";
        }
        if(coverage.values.empty())fail(syntax,"covergroup requires at least one coverpoint");
        coverage.definition=std::to_string(type->idx())+","+(per_instance?"true":"false")+","+(merge?"true":"false")+","+std::to_string(group_goal)+","+points+"}";
        coverages.push_back(std::move(coverage));
        if(auto* control=syntax->children[0]) {
            if(owner->class_definition)fail(control,"event sampling in an embedded covergroup is not supported yet; use sample()");
            auto* events=static_cast<VeriEventStmt*>(control);
            if(events->is_all()==IS_TRUE||events->event_list().size()!=1)fail(control,"covergroup event requires one scalar edge event");
            auto* event=events->event_list().front();if(event->detail_type()!=veEXP_EVENT)fail(event,"covergroup event requires posedge or negedge");
            auto* edge=static_cast<VeriEventExp*>(event);auto clock=expr(edge->exp_child());
            if(edge->condition()||clock->op!="signal"||clock->width!=1||(edge->etype()!=vtUPOSE&&edge->etype()!=vtUNEGE))fail(event,"covergroup event requires one scalar posedge/negedge without iff");
            ProcessIR p;int pid=int(processes.size());p.reads.insert(clock->signal);p.touches.insert(objects_signal);p.reads.insert(objects_signal);p.writes.push_back({objects_signal,0,64,0});
            add(p,"pc=1;"+wait_code(pid,"{{"+sid(clock->signal)+","+std::to_string(edge->etype()==vtUPOSE?1:2)+"}}")+"return;");
            add(p,"s.coverage_event("+std::to_string(type->idx())+");pc=0;continue;");
            processes.push_back(std::move(p));
        }
    }
    scope=previous;argument_receiver=saved_receiver;
}
void emit_coverages(std::ostream& out) {
    for(const auto& coverage:coverages) {
        out<<"s.add_coverage_type("<<coverage.definition<<",[](Sim& s,V coverage_self,V coverage_owner){(void)coverage_owner;s.coverage_sample(coverage_self,"<<coverage.type->idx()<<",{";
        for(auto value:coverage.values)out<<emit(value)<<",";
        out<<"},{";for(auto gate:coverage.gates)out<<"("<<emit(gate)<<").truth()==1,";
        out<<"});});\n";
    }
}
E coverage_expression(VeriMemberExp* member,bool statement=false) {
    if(!member->called())fail(member,"coverpoint/cross requires a coverage query");
    const auto& method=member->member();const bool query=method=="get_coverage"||method=="get_inst_coverage";
    if(!query&&!statement)fail(member,"void covergroup method cannot be used as a value");
    auto* receiver=member->coverage_point()>=0?static_cast<VeriMemberExp*>(member->object())->object():member->object();
    auto value=node("call",query?64:1,{expr(receiver)});value->procedural_only=true;value->event_safe=false;
    value->reads.insert(objects_signal);value->real_width=query?64:0;
    const auto type=std::to_string(member->class_owner()->idx());
    if(query)value->literal="return V::real(s.coverage_query(call_arg0,"+type+","+(method=="get_inst_coverage"?"true":"false")+","+std::to_string(member->coverage_point())+"));";
    else {
        value->writes.insert(objects_signal);value->write_ranges.emplace(objects_signal,0,64);
        if(method=="sample")value->literal="s.coverage_invoke(call_arg0,"+type+");";
        else if(method=="start"||method=="stop")value->literal="s.coverage_enable(call_arg0,"+type+","+(method=="start"?"true":"false")+");";
        else {needs_text=true;auto args=veri_system_arguments(member->arguments());value->args.push_back(text_context(expr(args.front())));value->literal="s.coverage_name(call_arg0,"+type+",call_arg1.text_value());";}
        value->literal+="return V();";
    }
    return value;
}
