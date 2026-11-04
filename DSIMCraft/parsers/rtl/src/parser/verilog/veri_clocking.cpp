#include "veri_parser.hpp"
#include "veri_stmt.hpp"
#include "veri_exp.hpp"
#include "veri_symbol_table.hpp"
#include <stdexcept>

namespace rtl {
VeriNode* VeriParser::gen_covergroup(int line,int col,const char* name,VeriNode* event,VeriNode* items,const char* closing) {
  if(closing&&std::string(name)!=closing)throw std::runtime_error("covergroup closing label does not match: "+std::string(name));
  const bool embedded=!_class_lifetimes.empty();
  const auto type=embedded?std::string("$covergroup$")+name:std::string(name);
  auto* metadata=gen_clocking(line,col,vsDECL_COVERAGE,name,{event,items});
  begin_class();auto* group=static_cast<VeriSeqBlock*>(gen_class(line,col,type.c_str(),gen_mod_item_list(metadata),nullptr));
  group->set_coverage_type();
  if(!embedded)return group;
  auto* handle=gen_named_var_decl(line,col,type.c_str(),gen_primary(name,line,col,veVAR));
  return append_mod_item_list(gen_mod_item_list(group),handle);
}
VeriNode* VeriParser::gen_clocking(int line,int col,int kind,const std::string& name,
                                  const NodeVec& children,int direction,bool step) {
  auto* node=new VeriClocking(next_id(),line,col,_mod,kind,name,children,direction,step);
  insert_node(node);return node;
}
VeriClocking* veri_clocking_reference(VeriNode* node) {
  if(!node)return nullptr;
  if(node->detail_type()==veEXP_PRI)node=static_cast<VeriPrimaryExp*>(node)->var();
  else if(node->detail_type()==veEXP_MEMBER)node=static_cast<VeriMemberExp*>(node)->hierarchical_symbol();
  return node&&node->detail_type()==vsDECL_CLOCKING?static_cast<VeriClocking*>(node):nullptr;
}
int VeriClocking::process_node_2nd(NodeVec& stack,String&) {
  if(pstatus()!=vSTART_S)return OK;
  set_pstatus(vEND_S);
  for(auto it=children.rbegin();it!=children.rend();++it)if(*it) {
    (*it)->set_scope(detail_type()==vsDECL_COVERAGE?scope()->floater():scope());stack.push_back(*it);
  }
  return OK;
}
int VeriClocking::push_dot_children(NodeQueue& queue,IQueue& levels) {
  for(auto* child:children)if(child){queue.push(child);levels.push(levels.front()+1);}return OK;
}
int VeriClocking::push_for_replacement(NodeVec& stack) {
  for(auto* child:children)if(child)stack.push_back(child);return OK;
}
int VeriClocking::replace_node(Uint id,NodeList& list,NodeList::iterator& current) {
  auto* copy=new VeriClocking(id,line(),col(),birth_mod(),detail_type(),name,{},direction,step);
  copy->default_clock=default_clock;copy->children.resize(children.size());
  for(size_t i=children.size();i--;)if(children[i]) {
    auto it=current;--it;copy->children[i]=*it;(*it)->set_father(copy);list.erase(it);
  }
  *current=copy;return OK;
}
std::vector<VeriClocking*> VeriClocking::ports() const {
  std::vector<VeriClocking*> result;
  if(detail_type()!=vsDECL_CLOCKING||children.size()!=2)return result;
  NodeVec pending{children[1]};
  while(!pending.empty()) {
    auto* node=pending.back();pending.pop_back();if(!node)continue;
    if(node->detail_type()==vsSTMT_MOD_ITEM_LIST) {
      auto& items=static_cast<VeriModuleItemList*>(node)->item_list();
      for(auto it=items.rbegin();it!=items.rend();++it)pending.push_back(*it);
    } else if(node->detail_type()==vsDECL_CLOCKING_ITEM)result.push_back(static_cast<VeriClocking*>(node));
    else throw std::runtime_error("invalid clocking item");
  }
  return result;
}
}
