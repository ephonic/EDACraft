// Bind out-of-block class methods before module/class syntax is cloned.
#include "veri_parser.hpp"
#include "veri_module.hpp"
#include "veri_mod_container.hpp"
#include "veri_decl.hpp"
#include "veri_stmt.hpp"
#include "veri_exp.hpp"
#include "veri_var.hpp"
#include "veri_tfmg.hpp"
#include "veri_symbol_table.hpp"
#include <functional>
#include <iterator>
#include <map>
#include <stdexcept>
namespace rtl {
namespace {
bool method(VeriNode* n){return n->detail_type()==vsDECL_FUNC_DECL||n->detail_type()==vsDECL_TASK_DECL;}
std::string name(VeriNode* n){return n->detail_type()==vsDECL_FUNC_DECL?static_cast<VeriFuncDecl*>(n)->func_name():static_cast<VeriTaskDecl*>(n)->task_name();}
void rename(VeriNode* n,const std::string& value){if(n->detail_type()==vsDECL_FUNC_DECL)static_cast<VeriFuncDecl*>(n)->set_method_name(value);else static_cast<VeriTaskDecl*>(n)->set_method_name(value);}
[[noreturn]] void error(VeriNode* n,const std::string& text){throw std::runtime_error("line "+std::to_string(n->line())+": extern method "+text);}
std::string syntax(VeriNode* n) {
  if(!n)return "_";
  std::string key=std::to_string(n->detail_type())+":";
  if(n->detail_type()==veEXP_PRI)key+=std::to_string(static_cast<VeriPrimaryExp*>(n)->pri_type())+":"+static_cast<VeriPrimaryExp*>(n)->str();
  else if(n->detail_type()==veEXP_BIN)key+=std::to_string(static_cast<VeriBinaryExp*>(n)->op());
  else if(n->detail_type()==veEXP_UNA)key+=std::to_string(static_cast<VeriUnaryExp*>(n)->op());
  else if(n->detail_type()==veEXP_MULTI)key+=std::to_string(static_cast<VeriMultiExp*>(n)->multi_type());
  else if(n->detail_type()==veEXP_MEMBER)key+=static_cast<VeriMemberExp*>(n)->member();
  else if(n->detail_type()==veEXP_TYPE)key+=static_cast<VeriTypeExp*>(n)->syntax_key();
  VeriNode::NodeVec children;n->push_for_replacement(children);
  for(auto* child:children)key+="["+syntax(child)+"]";
  return key;
}
struct Formal {std::string name;VeriTfDecl* declaration;VeriNode* default_value;};
Formal formal(VeriNode* port) {
  auto* decl=static_cast<VeriTfDecl*>(port->father());
  auto* id=port->detail_type()==veEXP_ARRAY?static_cast<VeriArrayExp*>(port)->id():port;
  const auto& key=static_cast<VeriPrimaryExp*>(id)->str();return {key,decl,decl->default_argument(key)};
}
void attach(VeriNode* prototype,VeriNode* definition) {
  auto* p=static_cast<VeriDecl*>(prototype);auto* d=static_cast<VeriDecl*>(definition);
  if(!p->extern_method())error(definition,"definition requires an extern prototype: "+name(prototype));
  if(p->extern_header())error(definition,"has more than one definition: "+name(prototype));
  if(prototype->detail_type()!=definition->detail_type())error(definition,"function/task kind mismatch: "+name(prototype));
  if(d->virtual_method()||d->static_method()||d->class_access()!=VeriDecl::PUBLIC)error(definition,"definition must omit class qualifiers");
  auto pf=veri_subroutine_formals(prototype),df=veri_subroutine_formals(definition);
  if(pf.size()!=df.size())error(definition,"formal count mismatch: "+name(prototype));
  for(size_t i=0;i<pf.size();++i) {
    const auto a=formal(pf[i]),b=formal(df[i]);
    if(a.name!=b.name)error(definition,"formal name mismatch: "+a.name);
    if(b.default_value&&(!a.default_value||syntax(a.default_value)!=syntax(b.default_value)))error(definition,"default argument mismatch: "+a.name);
  }
  rename(definition,"$extern_header_"+name(prototype));
  if(prototype->detail_type()==vsDECL_FUNC_DECL)static_cast<VeriFuncDecl*>(prototype)->adopt_extern_body(static_cast<VeriFuncDecl*>(definition));
  else static_cast<VeriTaskDecl*>(prototype)->adopt_extern_body(static_cast<VeriTaskDecl*>(definition));
}
bool same_named_binding(const std::string& a,VeriVar* at,const std::string& b,VeriVar* bt) {
  auto leaf=[](const std::string& n){const auto p=n.empty()||n.front()=='\\'?std::string::npos:n.rfind("::");return p==std::string::npos?n:n.substr(p+2);};
  // Corresponding named type identifiers must resolve to the same declaration,
  // even when two shadowing typedefs happen to have identical storage shape.
  return a.empty()||b.empty()||leaf(a)!=leaf(b)||at==bt;
}
bool same_identity(VeriNode* a,VeriNode* b) {
  return veri_class_type(a)==veri_class_type(b)&&veri_enum_type(a)==veri_enum_type(b)&&veri_aggregate_type(a)==veri_aggregate_type(b);
}
bool same_shape(VeriNode* a,VeriNode* b) {
  const auto x=veri_array_shape(a),y=veri_array_shape(b);
  return x.dimensions==y.dimensions&&x.unpacked==y.unpacked&&x.unbound==y.unbound&&veri_array_container_kind(a)==veri_array_container_kind(b);
}
bool same_formal(VeriTfVar* a,VeriTfVar* b) {
  if(a->inout()!=b->inout()||a->net_type()!=b->net_type()||a->is_signed()!=b->is_signed()||a->dstart()!=b->dstart()||a->dend()!=b->dend()||a->range_depth()!=b->range_depth()||a->dynamic_array()!=b->dynamic_array()||a->container_kind()!=b->container_kind()||a->container_bound()!=b->container_bound()||!same_identity(a,b)||!same_shape(a,b))return false;
  for(int d=1;d<=a->range_depth();++d) {
    if(a->open_range(d)!=b->open_range(d))return false;
    int af,al,an,bf,bl,bn;a->get_range(d,af,al,an);b->get_range(d,bf,bl,bn);if(af!=bf||al!=bl)return false;
  }
  return true;
}
}
VeriNode* VeriParser::qualify_extern(VeriNode* declaration) {
  if(_class_lifetimes.empty())error(declaration,"prototype requires class scope");
  auto* decl=static_cast<VeriDecl*>(declaration);
  if(decl->pure_virtual())error(declaration,"cannot combine extern and pure virtual");
  decl->set_extern_method();return declaration;
}
void VeriParser::resolve_extern_methods() {
  std::function<void(VeriNode*)> visit;
  visit=[&](VeriNode* node) {
    if(!node)return;
    if(node->detail_type()==vsSTMT_MOD_ITEM_LIST) {
      auto& items=static_cast<VeriModuleItemList*>(node)->item_list();std::map<std::string,VeriSeqBlock*> classes;
      for(auto it=items.begin();it!=items.end();) {
        auto* item=*it;++it;
        if(item->detail_type()==vsSTMT_SEQ_BLOCK&&static_cast<VeriSeqBlock*>(item)->class_declaration()) {
          auto* cls=static_cast<VeriSeqBlock*>(item);classes.emplace(cls->label(),cls);continue;
        }
        if(!method(item))continue;
        auto full=name(item);if(full.empty()||full.front()=='\\')continue;auto split=full.rfind("::");if(split==std::string::npos)continue;
        auto cls=classes.find(full.substr(0,split));if(cls==classes.end())error(item,"definition requires a preceding class in the same scope: "+full);
        auto* members=cls->second->decl_list();VeriNode* prototype=nullptr;
        if(members)for(auto* m:static_cast<VeriModuleItemList*>(members)->item_list())if(method(m)&&name(m)==full.substr(split+2)) {prototype=m;break;}
        if(!prototype)error(item,"definition has no prototype: "+full);
        attach(prototype,item);
        items.erase(std::prev(it));
      }
      for(const auto& entry:classes)if(auto* members=entry.second->decl_list())
        for(auto* m:static_cast<VeriModuleItemList*>(members)->item_list())if(method(m)&&static_cast<VeriDecl*>(m)->extern_method()&&!static_cast<VeriDecl*>(m)->extern_header())error(m,"prototype has no definition: "+entry.first+"::"+name(m));
      for(auto* item:items)visit(item);
    } else {VeriNode::NodeVec children;node->push_for_replacement(children);for(auto* child:children)visit(child);}
  };
  for(auto* package:_package_order)visit(package->item());
  for(auto* owner:_compilation_declarations)visit(owner->item());
  for(auto* module:_mods->all_modules())visit(module->item());
}
void veri_validate_extern_methods(VeriSeqBlock* cls) {
  if(!cls->decl_list())return;
  for(auto* node:static_cast<VeriModuleItemList*>(cls->decl_list())->item_list()) {
    if(!method(node))continue;auto* decl=static_cast<VeriDecl*>(node);auto* header=decl->extern_header();if(!header)continue;
    // The prototype saw types at its declaration point. The definition header
    // sees the completed class, in its own isolated scope, never as an overload.
    auto* checks=cls->scope()->append_scope("$extern_checks_"+name(node),vNAMED_BLOCK_SCOPE);
    veri_bind_semantic(header,checks);
    auto pf=veri_subroutine_formals(node),df=veri_subroutine_formals(header);
    for(size_t i=0;i<pf.size();++i) {
      auto* a=static_cast<VeriTfVar*>(veri_formal_symbol(pf[i]));auto* b=static_cast<VeriTfVar*>(veri_formal_symbol(df[i]));
      auto* ad=formal(pf[i]).declaration;auto* bd=formal(df[i]).declaration;
      if(!a||!b||!same_formal(a,b)||!same_named_binding(ad->type_name(),ad->resolved_type(),bd->type_name(),bd->resolved_type()))error(header,"formal type/direction mismatch: "+formal(pf[i]).name);
    }
    if(node->detail_type()==vsDECL_FUNC_DECL) {
      auto* a=static_cast<VeriFuncDecl*>(node);auto* b=static_cast<VeriFuncDecl*>(header);
      if(a->is_void()!=b->is_void()||a->result_type()!=b->result_type()||a->is_signed()!=b->is_signed()||!same_named_binding(a->type_name(),a->resolved_type(),b->type_name(),b->resolved_type()))error(header,"return type mismatch: "+name(node));
      auto* av=static_cast<VeriFunc*>(a->scope()->value_same_level(a->func_name()));auto* bv=static_cast<VeriFunc*>(b->scope()->value_same_level(b->func_name()));
      if(!av||!bv||av->dstart()!=bv->dstart()||av->dend()!=bv->dend()||!same_identity(av,bv)||(!a->is_void()&&!same_shape(av,bv)))error(header,"return type mismatch: "+name(node));
    }
  }
}
}
