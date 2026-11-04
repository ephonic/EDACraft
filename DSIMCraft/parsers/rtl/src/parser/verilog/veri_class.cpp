// Parameterized class syntax and canonical semantic specializations.
#include "veri_parser.hpp"
#include "veri_module.hpp"
#include "cfg_mgr.hpp"
#include "veri_exp.hpp"
#include "veri_decl.hpp"
#include "veri_stmt.hpp"
#include "veri_symbol_table.hpp"
#include "veri_num.hpp"
#include "veri_tfmg.hpp"
#include <algorithm>
#include <set>
#include <sstream>
#include <stdexcept>
namespace rtl {
VeriNode* VeriParser::qualify_rand_property(VeriNode* declaration,bool cyclic) {
  if(_class_lifetimes.empty()||(declaration->detail_type()!=vsDECL_VAR&&declaration->detail_type()!=vsDECL_INT)||
     (declaration->detail_type()==vsDECL_VAR&&static_cast<VeriVarDecl*>(declaration)->is_typedef()))
    throw std::runtime_error("rand requires a class variable property");
  auto* decl=static_cast<VeriDecl*>(declaration);
  if(decl->rand_property())throw std::runtime_error("duplicate rand qualifier");
  decl->set_rand_property(cyclic);return declaration;
}
VeriNode* VeriParser::gen_constraint(const char* name,int line,int col,VeriNode* body) {
  if(_class_lifetimes.empty())throw std::runtime_error("constraint declaration requires a class");
  auto* node=new VeriConstraintDecl(next_id(),line,col,_mod,name,body);insert_node(node);return node;
}
VeriNode* VeriParser::gen_constraint_foreach(int line,int col,VeriNode* array,VeriNode* indices,VeriNode* body) {
  if(!systemverilog())throw std::runtime_error("constraint foreach requires SystemVerilog");
  auto items=veri_system_arguments(indices);
  std::vector<std::string> names;std::set<std::string> used;VeriNode* declarations=nullptr;
  for(auto* item:items) {
    if(item->detail_type()!=veEXP_PRI||static_cast<VeriPrimaryExp*>(item)->pri_type()!=veVAR)
      throw std::runtime_error("constraint foreach iterator must be an identifier or omitted");
    const auto name=static_cast<VeriPrimaryExp*>(item)->str();names.push_back(name);
    if(name.empty())continue;
    if(!used.insert(name).second||(array->detail_type()==veEXP_PRI&&static_cast<VeriPrimaryExp*>(array)->str()==name))
      throw std::runtime_error("constraint foreach indices must be distinct from each other and the array");
    auto* declaration=gen_var_decl(line,col,vpNO_IO,vvINT2,IS_TRUE,vpSCALAR,nullptr,nullptr,nullptr,gen_primary(name.c_str(),line,col,veVAR));
    declarations=declarations?append_block_item_list(declarations,declaration):gen_block_item_list(declaration);
  }
  if(used.empty())throw std::runtime_error("constraint foreach requires at least one index");
  auto* node=new VeriConstraintForeach(next_id(),line,col,_mod,array,declarations,body,names);insert_node(node);return node;
}
int VeriConstraintForeach::process_node_2nd(NodeVec& stack,String&) {
  if(pstatus()==vSTART_S) {
    _index_scope=scope()->append_scope("$constraint_foreach"+std::to_string(idx()),vNAMED_BLOCK_SCOPE);
    set_pstatus(vCALL_S);stack.push_back(this);
    _declarations->set_scope(_index_scope);stack.push_back(_declarations);
    _array->set_scope(scope());stack.push_back(_array);return OK;
  }
  if(pstatus()==vCALL_S) {
    const auto shape=veri_array_shape(_array);
    if(shape.unpacked<1)throw std::runtime_error("constraint foreach currently requires an unpacked array");
    if(_names.size()>size_t(shape.unpacked))throw std::runtime_error("constraint foreach currently supports unpacked dimensions only");
    auto* symbol=veri_array_element_symbol(_array);
    unsigned axis=0;
    for(const auto& name:_names) {
      const int kind=veri_array_container_kind(_array,axis);auto* key=veri_associative_key_type(_array,axis++);
      if(name.empty())continue;
      auto* var=static_cast<VeriVar*>(_index_scope->value_same_level(name));
      static_cast<VeriVarDecl*>(var->father())->infer_foreach_index(kind==vrASSOC_STRING,kind==vrASSOC_UINT,key);
      var->set_net_type(kind==vrASSOC_STRING?vvSTRING:vvINT2);
      var->set_is_signed(kind==vrASSOC_STRING||kind==vrASSOC_UINT?IS_FALSE:IS_TRUE);
      if(key)var->infer_associative_index(key);
    }
    set_pstatus(vEND_S);_body->set_scope(_index_scope);stack.push_back(_body);
  }
  return OK;
}
int VeriConstraintForeach::push_for_replacement(NodeVec& stack) {
  for(auto* child:{_array,_declarations,_body})stack.push_back(child);return OK;
}
int VeriConstraintForeach::push_dot_children(NodeQueue& nodes,IQueue& levels) {
  for(auto* child:{_array,_declarations,_body}){nodes.push(child);levels.push(levels.front()+1);}return OK;
}
int VeriConstraintForeach::replace_node(Uint id,NodeList& list,NodeList::iterator& current) {
  // Replacement children are immediately before the parent, in reverse push order.
  auto take=[&](){auto it=current;--it;auto* child=*it;list.erase(it);return child;};
  auto* body=take();auto* declarations=take();auto* array=take();
  *current=new VeriConstraintForeach(id,line(),col(),birth_mod(),array,declarations,body,_names);return OK;
}
int VeriConstraintDecl::process_node_2nd(NodeVec&,String&) {
  if(!scope()||!scope()->class_owner())throw std::runtime_error("constraint requires class scope");
  if(pstatus()==vSTART_S) {
    if(scope()->value_same_level(_name))throw std::runtime_error("duplicate class declaration: "+_name);
    scope()->insert(_name,this);
  }
  set_pstatus(vEND_S);return OK;
}
void VeriConstraintDecl::bind() {if(!_bound){veri_bind_semantic(_body,scope());_bound=true;}}
int VeriConstraintDecl::push_dot_children(NodeQueue& nodes,IQueue& levels) {
  if(_body){nodes.push(_body);levels.push(levels.front()+1);}return OK;
}
int VeriConstraintDecl::replace_node(Uint id,NodeList& list,NodeList::iterator& current) {
  auto* node=new VeriConstraintDecl(id,line(),col(),birth_mod(),_name,nullptr);
  if(_body){auto it=current;--it;node->_body=*it;node->_body->set_father(node);list.erase(it);}
  *current=node;return OK;
}

VeriDecl* veri_class_member_declaration(VeriNode* symbol) {
  if(!symbol)return nullptr;
  VeriNode* declaration=nullptr;
  if(symbol->tok_type()==vtFUNC)declaration=static_cast<VeriFunc*>(symbol)->func();
  else if(symbol->tok_type()==vtTASK)declaration=static_cast<VeriTask*>(symbol)->task();
  else if(symbol->tok_type()==vtVAR||symbol->tok_type()==vtINT)declaration=symbol->father();
  if(!declaration||declaration->tok_type()!=vtDECL)return nullptr;
  auto* context=declaration->scope();
  if(symbol->tok_type()==vtFUNC||symbol->tok_type()==vtTASK)context=context?context->floater():nullptr;
  return context&&context->class_owner()?static_cast<VeriDecl*>(declaration):nullptr;
}
bool veri_local_class_member(VeriNode* symbol) {
  auto* declaration=veri_class_member_declaration(symbol);
  return declaration&&declaration->class_access()==VeriDecl::LOCAL;
}
void veri_check_class_access(VeriNode* symbol,VeriSymbolTable* context) {
  auto* declaration=veri_class_member_declaration(symbol);
  if(!declaration||declaration->class_access()==VeriDecl::PUBLIC)return;
  auto* declaring_scope=declaration->scope();
  if(symbol->tok_type()==vtFUNC||symbol->tok_type()==vtTASK)declaring_scope=declaring_scope->floater();
  auto* owner=declaring_scope->class_owner();
  VeriSeqBlock* lexical=nullptr;
  for(auto* scope=context;scope;scope=scope->floater())if(scope->class_owner()){lexical=scope->class_owner();break;}
  for(auto* allowed=lexical;allowed;allowed=declaration->class_access()==VeriDecl::PROTECTED?allowed->base_class():nullptr)
    if(allowed==owner)return;
  throw std::runtime_error(std::string("inaccessible ")+(declaration->class_access()==VeriDecl::LOCAL?"local":"protected")+
    " class member declared in "+owner->label()+" at line "+std::to_string(declaration->line()));
}

VeriNode* veri_clone_syntax(VeriNode* root) {
  VeriNode::NodeVec pending{root},nodes;
  while(!pending.empty()) {auto* n=pending.back();pending.pop_back();nodes.push_back(n);n->push_for_replacement(pending);}
  VeriNode::NodeList list(nodes.rbegin(),nodes.rend());auto* parser=VeriParser::get_instance();
  for(auto it=list.begin();it!=list.end();++it) {
    auto* source=*it;source->replace_node(parser->next_id(),list,it);parser->insert_node(*it);
  }
  if(list.size()!=1)throw std::runtime_error("class syntax clone has unowned children");
  return list.front();
}
void veri_bind_semantic(VeriNode* root,VeriSymbolTable* context) {
  root->set_scope(context);VeriNode::NodeVec pending{root};std::string help;
  while(!pending.empty()) {
    auto* n=pending.back();pending.pop_back();int result=n->process_node_2nd(pending,help);
    if(result==vSEARCH_DECL)result=n->process_node_2nd(pending,help);
    if(result!=OK)throw std::runtime_error("class parameter binding failed\n"+VeriParser::get_instance()->get_err_info());
  }
}
VeriNode* VeriParser::gen_type_expression(int line,int col,const char* name,int builtin,int sign,VeriNode* range,VeriNode* arguments) {
  auto* n=new VeriTypeExp(next_id(),line,col,_mod,name?name:"",builtin,sign,range,arguments);insert_node(n);
  if(range)range->set_father(n);if(arguments)arguments->set_father(n);return n;
}
VeriNode* VeriParser::gen_type_parameter(int line,int col,const char* name,VeriNode* value) {
  auto* n=static_cast<VeriVarDecl*>(gen_typedef(line,col,vvLOGIC,IS_FALSE,nullptr,name));
  n->set_type_parameter();n->set_type_expression(value);return n;
}
VeriNode* VeriParser::gen_class_value_parameter(int line,int col,int sign,int type,VeriNode* range,VeriNode* variable) {
  // Unlike body parameters, class header parameters may require an actual.
  auto* n=new VeriParamDecl(next_id(),line,col,sign,type,IS_FALSE,range,_mod);insert_node(n);
  n->append_var(variable);variable->set_father(n);if(range)range->set_father(n);
  n->check_child_validation();return n;
}
VeriNode* VeriParser::append_class_parameter(VeriNode* list,VeriNode* parameter) {
  if(parameter->tok_type()==vtEXP) {
    VeriNode* previous=list?static_cast<VeriModuleItemList*>(list)->item_list().back():nullptr;
    auto* name=parameter;VeriNode* value=nullptr;
    if(parameter->detail_type()==veEXP_ASSIGN) {
      auto* assignment=static_cast<VeriAssignExp*>(parameter);name=assignment->lval();value=assignment->rval();
    }
    if(previous&&previous->detail_type()==vsDECL_VAR) {
      // Each formal has its own declaration/override; grouping aliases in a
      // single typedef would make specializing U also override T.
      if(value&&value->detail_type()!=veEXP_TYPE) {
        if(value->detail_type()!=veEXP_PRI||static_cast<VeriPrimaryExp*>(value)->pri_type()!=veVAR)
          throw std::runtime_error("class type parameter requires a data type");
        value=gen_type_expression(value->line(),value->col(),static_cast<VeriPrimaryExp*>(value)->str().c_str(),-1,0);
      }
      parameter=gen_type_parameter(name->line(),name->col(),static_cast<VeriPrimaryExp*>(name)->str().c_str(),value);
    } else {
      if(value&&value->detail_type()==veEXP_TYPE)
        throw std::runtime_error("class value parameter requires a constant expression");
      auto* inherited=previous?static_cast<VeriParamDecl*>(previous):nullptr;
      parameter=gen_class_value_parameter(name->line(),name->col(),inherited?inherited->is_signed():IS_FALSE,
        inherited?inherited->is_int():IS_FALSE,inherited&&inherited->range()?veri_clone_syntax(inherited->range()):nullptr,parameter);
      if(inherited)static_cast<VeriParamDecl*>(parameter)->set_type_name(inherited->type_name());
    }
  }
  return list?append_mod_item_list(list,parameter):gen_mod_item_list(parameter);
}
VeriVar* veri_resolve_type(VeriSymbolTable* context,const std::string& name,VeriNode* arguments) {
  auto* n=context->value_within_module(name);
  if(!n&&name=="process")return VeriParser::get_instance()->process_type(arguments);
  if(!n&&(name=="mailbox"||name=="semaphore"))return VeriParser::get_instance()->ipc_type(name,arguments,context);
  if(!n||n->tok_type()!=vtTYPE)throw std::runtime_error("unknown integral type "+name);
  auto* type=static_cast<VeriVar*>(n);auto* c=type->class_type();
  if(c&&c->generic_class())return c->specialize(arguments,context);
  if(arguments)throw std::runtime_error("type is not a parameterized class: "+name);
  return type;
}
VeriVar* VeriTypeExp::resolve(VeriSymbolTable* context) {
  if(_virtual_interface)return VeriParser::get_instance()->virtual_interface_type(line(),col(),_name,_interface_view,context);
  if(!_name.empty())return veri_resolve_type(context,_name,_arguments);
  auto* parser=VeriParser::get_instance();auto name="$type_argument"+std::to_string(idx());
  auto* local=context->append_scope(name,vNAMED_BLOCK_SCOPE);
  auto* declaration=parser->gen_typedef(line(),col(),_builtin,_sign,_range?veri_clone_syntax(_range):nullptr,name.c_str());
  veri_bind_semantic(declaration,local);return static_cast<VeriVar*>(local->value_same_level(name));
}
int VeriTypeExp::process_node_2nd(NodeVec&,String&) {_resolved=resolve(scope());set_pstatus(vEND_S);return OK;}
int VeriTypeExp::push_for_replacement(NodeVec& stack) {if(_range)stack.push_back(_range);if(_arguments)stack.push_back(_arguments);return OK;}
int VeriTypeExp::push_dot_children(NodeQueue& queue,IQueue& depth) {
  if(_range){queue.push(_range);depth.push(depth.front()+1);}if(_arguments){queue.push(_arguments);depth.push(depth.front()+1);}return OK;
}
int VeriTypeExp::replace_node(Uint id,NodeList& list,NodeList::iterator& inl) {
  auto* n=new VeriTypeExp(id,line(),col(),birth_mod(),_name,_builtin,_sign,nullptr,nullptr);
  n->_virtual_interface=_virtual_interface;n->_interface_view=_interface_view;
  auto take=[&](){auto it=inl;--it;auto* node=*it;node->set_father(n);list.erase(it);return node;};
  if(_arguments)n->_arguments=take();if(_range)n->_range=take();*inl=n;return OK;
}
namespace {
std::vector<VeriNode*> list_arguments(VeriNode* node) {
  if(!node)return {};
  if(node->detail_type()==veEXP_MULTI) {auto& items=static_cast<VeriMultiExp*>(node)->exp();return {items.begin(),items.end()};}
  return {node};
}
std::string formal_name(VeriNode* node) {
  if(node->detail_type()==veEXP_ASSIGN)node=static_cast<VeriAssignExp*>(node)->lval();
  if(node->detail_type()!=veEXP_PRI)throw std::runtime_error("invalid class parameter name");
  return static_cast<VeriPrimaryExp*>(node)->str();
}
std::string type_key(VeriVar* type) {
  if(type->class_binding()&&!type->class_type())
    throw std::runtime_error("incomplete forward class typedef in class parameter actual");
  std::ostringstream s;s<<type->net_type()<<':'<<type->is_signed()<<':'<<type->dstart()<<':'<<type->dend()<<':'<<type->vec_scalar();
  for(const auto& dim:veri_array_shape(type).dimensions)s<<":d"<<dim.first<<','<<dim.second;
  if(type->class_type())s<<":c"<<type->class_type()->idx();
  if(type->enum_type())s<<":e"<<type->enum_type()->idx();
  if(type->aggregate_type())s<<":a"<<type->aggregate_type()->idx();
  if(auto vif=type->virtual_interface())s<<":vif:"<<vif->name<<":"<<vif->view;return s.str();
}
VeriVar* actual_type(VeriNode* actual,VeriSymbolTable* context) {
  if(actual->detail_type()==veEXP_TYPE)return static_cast<VeriTypeExp*>(actual)->resolve(context);
  if(actual->detail_type()==veEXP_PRI&&static_cast<VeriPrimaryExp*>(actual)->pri_type()==veVAR)return veri_resolve_type(context,static_cast<VeriPrimaryExp*>(actual)->str());
  throw std::runtime_error("class type parameter requires a data type");
}
}
VeriVar* VeriParser::process_type(VeriNode* arguments) {
  if(arguments)throw std::runtime_error("process is not parameterized");
  auto found=_ipc_types.find("process");if(found!=_ipc_types.end())return found->second->class_symbol();
  if(!_builtin_scope){_builtin_scope=new VeriSymbolTable;_builtin_scope->init(_cmgr->symbol_table_size(),"$builtin_ipc");}
  VeriNode* members=nullptr;
  for(const char* name:{"FINISHED","RUNNING","WAITING","SUSPENDED","KILLED"}) {
    auto* member=gen_primary(name,0,0,veVAR);
    members=members?gen_multi(members,member,vemCOMMA_EXP,0,0):member;
  }
  auto* items=gen_mod_item_list(gen_enum(0,0,vvINT2,IS_TRUE,nullptr,"state",members));
  const auto label="$process"+std::to_string(next_id());
  auto* definition=new VeriSeqBlock(next_id(),0,0,label,0,0,items,nullptr,_mod);
  insert_node(definition);items->set_father(definition);
  definition->set_class_declaration();definition->set_process_type();
  definition->set_scope(_builtin_scope);definition->ensure_class_elaborated();
  _ipc_types.emplace("process",definition);return definition->class_symbol();
}
VeriVar* VeriParser::ipc_type(const std::string& name,VeriNode* arguments,VeriSymbolTable* context) {
  auto actuals=list_arguments(arguments);VeriVar* payload=nullptr;
  if(name=="semaphore"&&!actuals.empty())throw std::runtime_error("semaphore is not parameterized");
  if(actuals.size()>1)throw std::runtime_error("mailbox requires one message type");
  if(!actuals.empty()) {
    payload=actual_type(actuals.front(),context);
    if(veri_array_shape(payload).unpacked)throw std::runtime_error("mailbox message type must be singular");
    if(auto* c=payload->class_type())c->ensure_class_elaborated();
  }
  const auto key=name+":"+(payload?type_key(payload):"dynamic");
  auto found=_ipc_types.find(key);if(found!=_ipc_types.end())return found->second->class_symbol();
  if(!_builtin_scope){_builtin_scope=new VeriSymbolTable;_builtin_scope->init(_cmgr->symbol_table_size(),"$builtin_ipc");}
  const auto label="$"+name+std::to_string(next_id());
  auto* definition=new VeriSeqBlock(next_id(),0,0,label,0,0,nullptr,nullptr,_mod);
  insert_node(definition);definition->set_class_declaration();definition->set_ipc_type(name=="mailbox"?1:2,payload);
  definition->set_scope(_builtin_scope);definition->ensure_class_elaborated();
  _ipc_types.emplace(key,definition);return definition->class_symbol();
}
VeriVar* VeriSeqBlock::specialize(VeriNode* arguments,VeriSymbolTable* context) {
  static thread_local unsigned depth=0;
  if(depth>=128)throw std::runtime_error("recursive class specialization exceeds 128 levels");
  struct Depth {unsigned& depth;Depth(unsigned& n):depth(n){++depth;}~Depth(){--depth;}} guard(depth);
  auto* parameters=static_cast<VeriModuleItemList*>(veri_clone_syntax(_class_parameters));
  struct Formal {std::string name;VeriNode* declaration;bool type;bool required_value;};std::vector<Formal> formals;
  std::set<std::string> names;
  for(auto* declaration:parameters->item_list()) {
    bool type=declaration->detail_type()==vsDECL_VAR;
    auto& variables=type?static_cast<VeriVarDecl*>(declaration)->vars():static_cast<VeriParamDecl*>(declaration)->vars();
    for(auto* v:variables) {auto name=formal_name(v);if(!names.insert(name).second)throw std::runtime_error("duplicate class parameter: "+name);formals.push_back({name,declaration,type,!type&&v->detail_type()==veEXP_PRI});}
  }
  std::map<std::string,VeriNode*> actuals;size_t position=0;bool named=false,positional=false;
  for(auto* actual:list_arguments(arguments)) {
    std::string name;
    if(actual->detail_type()==veEXP_NAMED_PARAM) {
      if(positional)throw std::runtime_error("class arguments cannot mix positional and named parameters");named=true;
      auto* value=static_cast<VeriNamedParamExp*>(actual);name=value->ref();actual=value->port_exp();
      auto values=list_arguments(actual);if(values.size()>1)throw std::runtime_error("class named parameter requires at most one actual");actual=values.empty()?nullptr:values.front();
    } else {
      if(named)throw std::runtime_error("class arguments cannot mix positional and named parameters");positional=true;
      if(position>=formals.size())throw std::runtime_error("too many class parameter actuals");name=formals[position++].name;
    }
    if(!names.count(name))throw std::runtime_error("unknown class parameter: "+name);
    if(!actuals.emplace(name,actual).second)throw std::runtime_error("duplicate class parameter actual: "+name);
  }
  auto* bindings=scope()->append_scope("$class_arguments"+std::to_string(parameters->idx()),vNAMED_BLOCK_SCOPE);
  for(const auto& formal:formals) {
    auto actual=actuals.find(formal.name);
    if(actual==actuals.end()||!actual->second) {
      if(formal.required_value)throw std::runtime_error("missing class parameter: "+formal.name);
      continue;
    }
    if(formal.type)static_cast<VeriVarDecl*>(formal.declaration)->set_type_override(actual_type(actual->second,context));
    else {
      if(actual->second->detail_type()==veEXP_TYPE)throw std::runtime_error("class value parameter requires a constant expression");
      veri_bind_semantic(actual->second,context);auto* value=static_cast<VeriExp*>(actual->second);
      if(!veri_elaboration_constant(value))throw std::runtime_error("class value parameter requires a constant expression");
      static_cast<VeriParamDecl*>(formal.declaration)->set_class_argument(formal.name,value);
    }
  }
  veri_bind_semantic(parameters,bindings);std::string key;
  for(const auto& formal:formals) {
    auto* symbol=bindings->value_same_level(formal.name);if(!symbol)throw std::runtime_error("missing class parameter: "+formal.name);
    key+=formal.name+'=';
    if(formal.type)key+='T'+type_key(static_cast<VeriVar*>(symbol));
    else {
      auto* value=static_cast<VeriParam*>(symbol)->get_val();key+='V'+std::to_string(value->bits())+':'+std::to_string(value->is_signed())+':';
      if(auto* e=veri_enum_type(symbol))key+='E'+std::to_string(e->idx())+':';
      for(int bit=0;bit<value->bits();++bit)key+=char('0'+value->get_certain_bit(bit));
    }
    key+=';';
  }
  auto prior=_specializations.find(key);if(prior!=_specializations.end())return prior->second->class_symbol();
  auto* instance=static_cast<VeriSeqBlock*>(veri_clone_syntax(this));
  instance->_class_origin=this;instance->_label=_label+"$specialization"+std::to_string(instance->idx());instance->set_scope(scope());
  for(const auto& formal:formals) {
    instance->_class_bindings[formal.name]=bindings->value_same_level(formal.name);
    instance->_class_parameter_order.push_back(formal.name);
  }
  instance->register_class_symbol();_specializations.emplace(key,instance);
  // A typedef of a forward-declared template establishes its canonical type,
  // but must not elaborate a body whose declaration point has not been visited.
  // Finish these bodies after lexical declarations, like forward initializers.
  if(!_class_state)VeriParser::get_instance()->defer_semantic(instance);
  else instance->ensure_class_elaborated();
  return instance->class_symbol();
}
} // namespace rtl

namespace rtl {
VeriNode* VeriParser::gen_virtual_interface_type(int line,int col,const char* name,const char* view) {
  auto* type=static_cast<VeriTypeExp*>(gen_type_expression(line,col,name,-1,IS_FALSE));
  type->set_virtual_interface(view?view:"");return type;
}
VeriVar* VeriParser::virtual_interface_type(int line,int col,const std::string& name,const std::string& view,VeriSymbolTable*) {
  const auto key=std::make_pair(name,view);auto found=_virtual_interface_types.find(key);
  if(found!=_virtual_interface_types.end())return found->second;
  auto* definition=module(name);
  if(!definition||!definition->is_interface())throw std::runtime_error("virtual interface requires an interface type: "+name);
  if(!view.empty()&&!definition->modports().count(view))throw std::runtime_error("unknown virtual interface modport: "+view);
  auto* prototype=static_cast<VeriMod*>(veri_clone_syntax(definition));
  prototype->init(_cmgr->symbol_table_size());
  // Resolve interface declarations in their own compilation-unit context,
  // never in the class/package requesting a virtual handle type.
  const auto count=definition->compilation_item_count();
  prototype->set_compilation_scope(count&&count<=_compilation_scopes.size()?_compilation_scopes.at(count-1):nullptr);
  veri_bind_semantic(prototype,prototype->scope());
  auto* type=new VeriVar(next_id(),line,col,"$virtual_interface_"+name+"_"+view,vpNO_IO,vvLONGINT,IS_FALSE,vpSCALAR,0,0,63,0,nullptr,nullptr,0,nullptr,vtTYPE);
  auto binding=std::make_shared<VeriVirtualInterface>();binding->name=name;binding->view=view;binding->prototype=prototype;
  type->set_virtual_interface(binding);insert_node(type);_virtual_interface_types.emplace(key,type);return type;
}
std::shared_ptr<VeriVirtualInterface> veri_virtual_interface(VeriNode* n) {
  if(!n)return {};
  if(n->tok_type()==vtVAR||n->tok_type()==vtTYPE)return static_cast<VeriVar*>(n)->virtual_interface();
  if(n->tok_type()==vtTFVAR)return static_cast<VeriTfVar*>(n)->virtual_interface();
  if(n->detail_type()==veEXP_PRI)return veri_virtual_interface(static_cast<VeriPrimaryExp*>(n)->var());
  if(n->detail_type()==veEXP_ARRAY)return veri_virtual_interface(static_cast<VeriArrayExp*>(n)->id());
  if(n->detail_type()==veEXP_TYPE)return veri_virtual_interface(static_cast<VeriTypeExp*>(n)->resolved_type());
  if(n->tok_type()==vtFUNC)return veri_virtual_interface(static_cast<VeriFunc*>(n)->func()->resolved_type());
  if(n->detail_type()==veEXP_CALLER){auto* hive=veri_call_hive(n);if(hive&&hive->detail_type()==vsDECL_FUNC_DECL)return veri_virtual_interface(static_cast<VeriFuncDecl*>(hive)->resolved_type());}
  if(n->detail_type()==veEXP_MEMBER){auto* m=static_cast<VeriMemberExp*>(n);if(m->called()&&m->hive()&&m->hive()->detail_type()==vsDECL_FUNC_DECL)return veri_virtual_interface(static_cast<VeriFuncDecl*>(m->hive())->resolved_type());return veri_virtual_interface(m->class_member()?m->class_member():m->hierarchical_symbol());}
  return {};
}
}
