#include "src_mgr.hpp"
#include "veri_parser.hpp"
#include "veri_mod_container.hpp"
#include "veri_module.hpp"
#include "veri_node_pool.hpp"
#include "veri_num.hpp"
#include "veri_var.hpp"
#include "veri_exp.hpp"
#include "veri_inst.hpp"
#include "veri_stmt.hpp"
#include "veri_tfmg.hpp"
#include "veri_decl.hpp"
#include "veri_symbol_table.hpp"

#include <cassert>
#include <iostream>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>
#include <stdexcept>

namespace {
struct TestPool : rtl::VeriNodePool {
  using rtl::VeriNodePool::clear_tosses;
};

void test_nonexpression_type_queries() {
  // Token-kind and expression-subtype enums overlap. A genvar is not a
  // member expression even though both enum values currently equal 20.
  rtl::VeriGenVar index(0,1,1,"index",nullptr,nullptr,nullptr);
  assert(index.detail_type()==veEXP_MEMBER&&index.tok_type()!=vtEXP);
  assert(rtl::veri_aggregate_type(&index)==nullptr);
  assert(rtl::veri_enum_type(&index)==nullptr);
}

void test_growing_symbol_scopes() {
  struct Table : rtl::VeriSymbolTable {using rtl::VeriSymbolTable::hash_delete;};
  Table table;assert(table.init(524287,"growth")==rtl::OK);
  rtl::VeriNum outer(0,0,0,nullptr),inner(1,0,0,nullptr);
  for(int i=0;i<4096;++i)assert(table.insert("symbol"+std::to_string(i),&outer)==rtl::OK);
  auto* child=table.append_scope("child",vNAMED_BLOCK_SCOPE);
  for(int i=0;i<4096;++i) {
    const auto name="symbol"+std::to_string(i);
    assert(table.value_same_level(name)==&outer);
    assert(child->value_within_module(name)==&outer);
    assert(child->insert(name,&inner)==rtl::OK);
  }
  for(int i=0;i<4096;++i) {
    const auto name="symbol"+std::to_string(i);
    assert(table.insert(name,&inner)==rtl::ERR);
    assert(child->value_same_level(name)==&inner);
    assert(table.hash_delete(name)==rtl::OK);
    assert(!table.value_same_level(name));
  }
  table.clean_up();
  assert(table.insert("reused",&outer)==rtl::OK);
  assert(table.value_same_level("reused")==&outer);
}

void test_pool_reset(bool retain_storage) {
  TestPool pool;
  pool.init(16,15);
  const auto id=pool.next_id();
  pool.insert(new rtl::VeriNum(id,1,1,nullptr));
  pool.toss_node(id);
  pool.clear_tosses();
  if(retain_storage) pool.clean_up();
  else { pool.clear(); pool.init(16,15); }
  const auto first=pool.next_id(),second=pool.next_id();
  assert(first!=second);
}

// Exercise the public parse entry, including automatic semantic analysis for
// a selected top. A syntax-only success must not hide invalid declarations.
rtl::VeriMod* analyze(const std::string& source, int expected=rtl::OK, const std::string& top="top") {
  auto* parser=rtl::VeriParser::get_instance();
  rtl::Src_mgr::get_instance()->set_src(source+std::string(1,'\0'));
  rtl::Src_mgr::get_instance()->set_fname("semantic_memory.v");
  assert(parser->init()==rtl::OK);
  parser->set_top_module(top);
  const int result=parser->parse();
  if(result!=expected) std::cerr<<"parse result "<<result<<"\n"<<parser->get_err_info()<<"\n"<<source<<"\n";
  assert(result==expected);
  assert(parser->has_err()==(expected==rtl::OK ? rtl::IS_FALSE : rtl::IS_TRUE));
  auto* mod=parser->module(top);
  assert(mod || expected==rtl::vMOD_TOP_MODULE_MISSING);
  return mod;
}

void test_shared_subroutine_cleanup() {
  const std::string source=R"(
    module top;
      class C;
        function int add(int a,int b=a+1);return a+b;endfunction
      endclass
      C c;int a,b;
      initial begin c=new;a=c.add(3);b=c.add(5);end
    endmodule
  )";
  for(int round=0;round<3;++round) {
    rtl::VeriNode::NodeVec pending{analyze(source)};
    std::vector<rtl::VeriNode*> bodies;
    while(!pending.empty()) {
      auto* n=pending.back();pending.pop_back();
      if(n->detail_type()==veEXP_MEMBER) {
        auto* call=static_cast<rtl::VeriMemberExp*>(n);
        if(call->member()=="add"&&call->called())bodies.push_back(call->hive());
      }
      n->push_for_replacement(pending);
    }
    assert(bodies.size()==2&&bodies[0]&&bodies[0]==bodies[1]);
  }
}

void test_default_formal_scope_cleanup() {
  const std::string source=R"(
    package p;
      function automatic int inc(int a,int b=a+1);return b;endfunction
    endpackage
    module leaf #(parameter W=8);
      int a=100,b=200,observed;
      function automatic int f(int a,int b=a+1,int c=b+1);return c;endfunction
      function automatic int outer(int a=b+1,int b=2);return a;endfunction
      function automatic int self(int a=a+1);return a;endfunction
      initial observed=f(p::inc(W))+outer()+self();
    endmodule
    module top;leaf #(65) one();leaf #(129) two();endmodule
  )";
  for(int round=0;round<5;++round) {
    auto* top=analyze(source);rtl::VeriNode* previous=nullptr;
    for(const auto& name:{"one","two"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* unit=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* declaration=static_cast<rtl::VeriFunc*>(unit->scope()->value_same_level("f"))->func();
      auto formals=rtl::veri_subroutine_formals(declaration);
      auto* a=rtl::veri_formal_symbol(formals[0]);auto* b=rtl::veri_formal_symbol(formals[1]);
      assert(a!=previous);previous=a;
      auto* b_default=static_cast<rtl::VeriTfDecl*>(b->father())->default_argument("b");
      auto* c_default=static_cast<rtl::VeriTfDecl*>(rtl::veri_formal_symbol(formals[2])->father())->default_argument("c");
      assert(b_default->scope()->value("a")==a);
      assert(c_default->scope()->value("b")==b);
      assert(b_default->scope()->value("b")==unit->scope()->value_same_level("b"));
      for(const auto& fn:{"outer","self"}) {
        auto* f=static_cast<rtl::VeriFunc*>(unit->scope()->value_same_level(fn))->func();
        auto* formal=rtl::veri_formal_symbol(rtl::veri_subroutine_formals(f)[0]);
        auto* value=static_cast<rtl::VeriTfDecl*>(formal->father())->default_argument("a");
        const char* outer_name=std::string(fn)=="self"?"a":"b";
        assert(value->scope()->value(outer_name)==unit->scope()->value_same_level(outer_name));
      }
    }
    analyze("module top;function int bad(int a,int b=later);return b;endfunction endmodule",rtl::vSEC_SYMBOL_NOT_FOUND);
    analyze(source);
  }
}

void test_process_type_cleanup() {
  const std::string source=R"(
    package p;typedef process proc_t;endpackage
    module child #(parameter N=3);
      process handle;p::proc_t alias_handle;process::state st;
      initial begin handle=process::self();alias_handle=handle;st=process::WAITING;end
    endmodule
    module top;child #(2) one();child #(5) two();endmodule
  )";
  for(int round=0;round<5;++round) {
    auto* top=analyze(source);rtl::VeriSeqBlock* shared=nullptr;
    for(const auto& name:{"one","two"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* type=rtl::veri_class_type(mod->scope()->value_same_level("handle"));
      assert(type&&type->process_type()&&!type->ipc_kind());
      assert(!shared||shared==type);shared=type;
      assert(rtl::veri_class_type(mod->scope()->value_same_level("alias_handle"))==type);
      assert(rtl::veri_enum_type(mod->scope()->value_same_level("st"))==rtl::veri_enum_type(type->class_member("state")));
    }
    bool rejected=false;
    try{analyze("module top;process p=new;endmodule");}catch(const std::runtime_error&){rejected=true;}
    assert(rejected);analyze(source);
  }
}

void test_ipc_type_cleanup() {
  const std::string source=R"(
    module child #(parameter N=3);
      typedef mailbox #(int) int_box;
      mailbox generic_box=new;
      int_box box=new(N);mailbox #(int) alias_box;
      mailbox #(string) words=new;
      semaphore keys=new(N);
      int value;
      initial begin alias_box=box;box.put(N);alias_box.get(value);keys.get();keys.put();end
    endmodule
    module top;child #(2) one();child #(5) two();endmodule
  )";
  for(int round=0;round<6;++round) {
    auto* top=analyze(source);rtl::VeriSeqBlock* shared=nullptr;
    for(const auto& name:{"one","two"}) {
      auto* symbol=top->scope()->value_same_level(name);
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(static_cast<rtl::VeriModInst*>(symbol)->instance())->hive());
      auto* box=rtl::veri_class_type(mod->scope()->value_same_level("box"));
      assert(box&&box->ipc_kind()==1&&box->ipc_payload());
      assert(rtl::veri_class_type(mod->scope()->value_same_level("alias_box"))==box);
      assert(!shared||shared==box);shared=box;
      auto* generic=rtl::veri_class_type(mod->scope()->value_same_level("generic_box"));
      assert(generic&&generic->ipc_kind()==1&&!generic->ipc_payload()&&generic!=box);
      assert(rtl::veri_class_type(mod->scope()->value_same_level("words"))!=box);
      assert(rtl::veri_class_type(mod->scope()->value_same_level("keys"))->ipc_kind()==2);
    }
  }
}

void test_queue_last_and_unsigned_key_cleanup() {
  const std::string source=R"(
    module child #(parameter N=3);
      typedef int table_t[int unsigned];table_t entries;
      int q[$:5];int observed;
      class Store;int values[int unsigned];endclass
      Store box=new;
      function automatic int get(input int v[$]);return v[($-1)];endfunction
      initial begin
        q.push_back(N);q.push_back(N+1);q[$]=N+2;
        entries[-1]=q[$];box.values[-1]=entries[-1];
        foreach(entries[i])if(i<0)observed=-1;
        observed=get(q)+q[$-1]+box.values[-1];q={};q={N};
      end
    endmodule
    module top;child #(3) one();child #(7) two();endmodule
  )";
  for(int round=0;round<6;++round) {
    auto* top=analyze(source);
    for(const auto& name:{"one","two"}) {
      auto* symbol=top->scope()->value_same_level(name);
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(static_cast<rtl::VeriModInst*>(symbol)->instance())->hive());
      auto* values=static_cast<rtl::VeriVar*>(mod->scope()->value_same_level("entries"));
      assert(values->container_kind()==vrASSOC_UINT);
      auto* queue=static_cast<rtl::VeriVar*>(mod->scope()->value_same_level("q"));
      assert(queue->container_kind()==vrQUEUE&&queue->container_bound()==5);
    }
  }
}

void test_interface_binding_cleanup() {
  const std::string source=R"(interface bus_if #(parameter W=8);
    logic[W-1:0] data;logic[7:0] cells[0:1];
    function automatic logic[W-1:0] peek(input integer n=1);return data+n;endfunction
    task automatic put(input logic[W-1:0] n);#1;data=n;endtask
    modport rw(output data,cells,import peek,put),ro(input data,cells);
    endinterface
    module child(bus_if.rw p);initial begin p.data=3;p.cells[1]=7;p.put(p.peek());end endmodule
    module wrapper(bus_if.rw b);child c(.p(b));endmodule
    module top;bus_if #(7) one();bus_if #(13) two();wrapper x(.b(one));wrapper y(two.rw);endmodule
  )";
  auto hive=[](rtl::VeriMod* mod,const std::string& name) {
    auto* symbol=mod->scope()->value_same_level(name);assert(symbol&&symbol->tok_type()==vtMOD_INST);
    return static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(static_cast<rtl::VeriModInst*>(symbol)->instance())->hive());
  };
  for(int round=0;round<4;++round) {
    auto* top=analyze(source);auto* one=hive(top,"one");auto* two=hive(top,"two");
    assert(one!=two&&one->is_interface()&&two->is_interface());
    assert(one->modports().at("rw").at("cells")==vpOUT);
    assert(one->modports().at("ro").at("data")==vpIN);
    assert(static_cast<rtl::VeriVar*>(one->scope()->value_same_level("data"))->dlen()==7);
    assert(static_cast<rtl::VeriVar*>(two->scope()->value_same_level("data"))->dlen()==13);
    for(const auto& entry:std::vector<std::pair<std::string,rtl::VeriMod*>>{{"x",one},{"y",two}}) {
      auto* wrap=hive(top,entry.first);auto* child=hive(wrap,"c");
      auto* b=static_cast<rtl::VeriVar*>(wrap->scope()->value_same_level("b"));
      auto* port=static_cast<rtl::VeriVar*>(child->scope()->value_same_level("p"));
      assert(b->interface_instance()==entry.second&&port->interface_instance()==entry.second);
      assert(b->interface_modport()=="rw"&&port->interface_modport()=="rw");
      auto* decl=static_cast<rtl::VeriVarDecl*>(static_cast<rtl::VeriPortDeclList*>(wrap->port())->port_list().front());
      assert(decl->interface_type()=="bus_if"&&decl->interface_modport()=="rw");
      rtl::VeriNode::NodeVec pending{child->item()};int calls=0;
      while(!pending.empty()) {
        auto* node=pending.back();pending.pop_back();
        if(node->detail_type()==veEXP_MEMBER) {
          auto* call=static_cast<rtl::VeriMemberExp*>(node);
          if(call->called()) {assert(call->hive());assert(call->call_instance()==entry.second);++calls;}
        }
        node->push_for_replacement(pending);
      }
      assert(calls==2);assert(one->modports().at("rw").at("peek")==vpIMPORT);
    }
  }
}

void test_modport_prototype_cleanup() {
  const std::string source=R"(interface bus_if #(parameter W=8);
    logic[W-1:0] data;
    modport rw(import function logic[W-1:0] peek(input integer renamed=W),task put(input logic[W-1:0] n)),
      unused(import task external_method(input integer n));
    function automatic logic[W-1:0] peek(input integer original=1);return data+original;endfunction
    task automatic put(input logic[W-1:0] n);#1;data=n;endtask
    endinterface
    module child(bus_if.rw p);initial p.put(p.peek());endmodule
    module top;bus_if #(5) one();bus_if #(13) two();child x(one);child y(two.rw);endmodule
  )";
  auto hive=[](rtl::VeriMod* mod,const std::string& name) {
    auto* symbol=mod->scope()->value_same_level(name);assert(symbol&&symbol->tok_type()==vtMOD_INST);
    return static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(static_cast<rtl::VeriModInst*>(symbol)->instance())->hive());
  };
  for(int round=0;round<4;++round) {
    auto* top=analyze(source);auto* one=hive(top,"one");auto* two=hive(top,"two");
    assert(one->modport_prototype("rw","peek")!=two->modport_prototype("rw","peek"));
    for(auto entry:std::vector<std::pair<std::string,rtl::VeriMod*>>{{"x",one},{"y",two}}) {
      auto* bus=entry.second;auto* proto=bus->modport_prototype("rw","peek");assert(proto);
      assert(bus->modport_prototype("unused","external_method"));
      assert(!bus->scope()->value_same_level("external_method"));
      auto* actual=static_cast<rtl::VeriFunc*>(bus->scope()->value_same_level("peek"));
      assert(actual->func()!=proto);
      auto* formal=rtl::veri_formal_symbol(rtl::veri_subroutine_formals(proto).at(0));
      assert(static_cast<rtl::VeriTfVar*>(formal)->name()=="renamed");
      auto* child=hive(top,entry.first);rtl::VeriNode::NodeVec pending{child->item()};int calls=0;
      while(!pending.empty()) {
        auto* node=pending.back();pending.pop_back();
        if(node->detail_type()==veEXP_MEMBER) {
          auto* call=static_cast<rtl::VeriMemberExp*>(node);
          if(call->called()) {
            assert(call->interface_prototype()==bus->modport_prototype("rw",call->member()));
            assert(call->call_instance()==bus&&call->hive());++calls;
          }
        }
        node->push_for_replacement(pending);
      }
      assert(calls==2);
    }
    assert(static_cast<rtl::VeriVar*>(one->scope()->value_same_level("data"))->dlen()==5);
    assert(static_cast<rtl::VeriVar*>(two->scope()->value_same_level("data"))->dlen()==13);
  }
}

void test_multidimensional_associative_cleanup() {
  const std::string source=R"(
    module bank #(parameter W=8);
      class Item;endclass
      typedef enum bit[W-1:0] {FIRST=1,LAST='1} Key;
      typedef int Leaf[Key];typedef Leaf Middle[string];Middle data[Item];
      typedef int Queue[$:W];typedef Queue QueueMap[string];QueueMap queues[Item];
      initial foreach(data[a,b,c])begin end
    endmodule
    module top;bank #(8) one();bank #(65) two();endmodule
  )";
  for(int repeat=0;repeat<3;++repeat) {
    auto* top=analyze(source);rtl::VeriVar* previous=nullptr;
    for(auto entry:{std::make_pair("one",8),std::make_pair("two",65)}) {
      auto* inst=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(entry.first));
      auto* module=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(inst->instance())->hive());
      auto* map=static_cast<rtl::VeriVar*>(module->scope()->value_same_level("data"));
      assert(map->dynamic_array()&&map->range_depth()==3&&rtl::veri_array_shape(map).unpacked==3);
      assert(map->container_kind(0)==vrASSOC_CLASS&&map->associative_key_type(0)->class_type());
      assert(map->container_kind(1)==vrASSOC_STRING&&!map->associative_key_type(1));
      assert(map->container_kind(2)==vrASSOC_UINT&&map->associative_key_type(2)->dlen()==entry.second);
      assert(map->associative_key_type(2)->enum_type()==module->scope()->value_same_level("Key"));
      assert(map->associative_key_type(2)!=previous);previous=map->associative_key_type(2);
      auto* queues=static_cast<rtl::VeriVar*>(module->scope()->value_same_level("queues"));
      assert(queues->range_depth()==3&&queues->container_kind(0)==vrASSOC_CLASS);
      assert(queues->container_kind(1)==vrASSOC_STRING&&queues->container_kind(2)==vrQUEUE);
      assert(queues->container_bound()==-1&&queues->container_bound(1)==-1);
      assert(queues->container_bound(2)==entry.second);
    }
    for(const auto& invalid:{"int a[$][int];","typedef int Leaf[string];Leaf a[2];"}) {
      bool rejected=false;try{analyze(std::string("module top;")+invalid+"endmodule");}
      catch(const std::runtime_error& e){rejected=std::string(e.what()).find("mixed runtime container dimensions")!=std::string::npos;}assert(rejected);
    }
  }
  analyze(source);
}

void test_runtime_container_cloning_cleanup() {
  const std::string source=R"(
    module store #(parameter N=2);int q[$:N];integer a[int];
      initial begin q.push_back(1);a[-3]=2;end
    endmodule
    module top;store #(2) one();store #(7) two();endmodule
  )";
  for(int repeat=0;repeat<3;++repeat) {
    auto* top=analyze(source);
    for(auto entry:{std::make_pair("one",2),std::make_pair("two",7)}) {
      auto* symbol=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(entry.first));
      auto* instance=static_cast<rtl::VeriModInstance*>(symbol->instance());
      auto* module=static_cast<rtl::VeriMod*>(instance->hive());
      auto* q=static_cast<rtl::VeriVar*>(module->scope()->value_same_level("q"));
      auto* a=static_cast<rtl::VeriInt*>(module->scope()->value_same_level("a"));
      assert(q->container_kind()==vrQUEUE&&q->container_bound()==entry.second&&q->dynamic_array());
      assert(a->container_kind()==vrASSOC_INT&&a->dynamic_array());
    }
  }
  bool rejected=false;try {analyze("module top;int q[$:-1];endmodule");}
  catch(const std::runtime_error& e){rejected=std::string(e.what()).find("queue upper bound")!=std::string::npos;}
  assert(rejected);analyze(source);
  auto* parser=rtl::VeriParser::get_instance();
  rtl::Src_mgr::get_instance()->set_src(std::string("module top;int q[$;endmodule")+char(0));
  parser->init();parser->set_top_module("top");assert(parser->parse()!=rtl::OK);analyze(source);
}

void test_named_container_cloning_cleanup() {
  const std::string source=R"(
    module unit_test #(parameter W=8);
      typedef enum logic[W-1:0] {ONE=1,ALL='1} State;
      typedef class C;
      State states[$],mapping[int],values[];
      C objects[$],item;
      class C;logic[W-1:0] bits;endclass
      initial begin
        item=new;objects.push_back(item);states.push_back(ONE);
        mapping[-1]=states.pop_front();values=new[1];values[0]=mapping[-1];
        item=objects.pop_back();$display("%s",values[0].name());
      end
    endmodule
    module top;unit_test #(8) a();unit_test #(129) b();endmodule
  )";
  for(int round=0;round<4;++round) {
    auto* top=analyze(source);rtl::VeriVar* previous=nullptr;
    for(auto entry:{std::make_pair("a",8),std::make_pair("b",129)}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(entry.first));
      auto* unit=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto var=[&](const char* name){return static_cast<rtl::VeriVar*>(unit->scope()->value_same_level(name));};
      auto* type=var("State");assert(type&&type!=previous);previous=type;
      assert(var("states")->container_kind()==vrQUEUE&&var("states")->enum_type()==type);
      assert(var("mapping")->container_kind()==vrASSOC_INT&&var("mapping")->dlen()==entry.second);
      assert(var("values")->dynamic_array()&&var("values")->enum_type()==type);
      assert(var("objects")->container_kind()==vrQUEUE&&var("objects")->class_type()==var("item")->class_type());
    }
    bool rejected=false;try{analyze("module top;typedef int T;T q[];int n;initial n=q[];endmodule");}catch(const std::runtime_error&){rejected=true;}
    assert(rejected);analyze(source);
  }
}

void test_class_forward_cloning_cleanup() {
  const std::string source=R"(
    module unit_test #(parameter W=8);
      typedef class B;
      typedef B Alias;
      class A; B peer; function B pass(B value);return value;endfunction endclass
      Alias b=new;
      class B; A peer; logic[W-1:0] bits='1; endclass
      typedef class B;
      A a;
      initial begin a=new;a.peer=b;b.peer=a;b=a.pass(b);end
    endmodule
    module top;unit_test #(8) a();unit_test #(129) b();endmodule
  )";
  for(int round=0;round<4;++round) {
    auto* top=analyze(source);rtl::VeriSeqBlock* previous=nullptr;
    for(auto entry:{std::make_pair("a",8),std::make_pair("b",129)}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(entry.first));
      auto* unit=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* b=static_cast<rtl::VeriVar*>(unit->scope()->value_same_level("b"))->class_type();
      auto* a=static_cast<rtl::VeriVar*>(unit->scope()->value_same_level("a"))->class_type();
      assert(b&&a&&b!=previous);previous=b;
      assert(b->class_symbol()==unit->scope()->value_same_level("B"));
      assert(rtl::veri_class_type(unit->scope()->value_same_level("Alias"))==b);
      assert(rtl::veri_class_type(a->class_member("peer"))==b);
      assert(rtl::veri_class_type(b->class_member("peer"))==a);
      assert(static_cast<rtl::VeriVar*>(b->class_member("bits"))->dlen()==entry.second);
      assert(rtl::veri_class_type(a->class_member("pass"))==b);
    }
    for(const auto* bad:{"module top;typedef class C;endmodule",
                         "module top;class C;endclass class O;typedef class C;endclass endmodule",
                         "module top;typedef class A;typedef class B;class A extends B;endclass class B extends A;endclass endmodule"}) {
      bool rejected=false;try{analyze(bad);}catch(const std::runtime_error&){rejected=true;}
      assert(rejected);analyze(source);
    }
  }
}

void test_forward_alias_cleanup() {
  const std::string source=R"(
    module leaf #(parameter W=8);
      typedef class Handle;typedef Handle Alias;
      class Client;
        Alias item;
        function Handle pass(Handle value);return value;endfunction
      endclass
      class Store#(type T=int);T bits;endclass
      typedef Store#(logic[W-1:0]) Handle;
      typedef Store#(logic[W-1:0]) Direct;
      Alias item;Client client;
      int pending[process];
    endmodule
    module top;leaf#(65) one();leaf#(129) two();endmodule
  )";
  for(int round=0;round<4;++round) {
    auto* top=analyze(source);rtl::VeriSeqBlock* previous=nullptr;
    for(auto entry:{std::make_pair("one",65),std::make_pair("two",129)}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(entry.first));
      auto* unit=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto cls=[&](const char* name){return rtl::veri_class_type(unit->scope()->value_same_level(name));};
      auto* item=cls("Handle");assert(item&&item!=previous);previous=item;
      assert(item==cls("Alias")&&item==cls("Direct")&&item==cls("item"));
      assert(rtl::veri_class_type(cls("Client")->class_member("item"))==item);
      assert(rtl::veri_class_type(cls("Client")->class_member("pass"))==item);
      assert(static_cast<rtl::VeriVar*>(item->class_member("bits"))->dlen()==entry.second);
      auto* map=static_cast<rtl::VeriVar*>(unit->scope()->value_same_level("pending"));
      assert(map->container_kind()==vrASSOC_CLASS&&map->associative_key_type()->class_type()->process_type());
    }
    for(const auto* bad:{"typedef class A;typedef A A;", "typedef class A;typedef class B;typedef B A;typedef A B;",
                         "typedef class A;typedef int A;"}) {
      bool rejected=false;try{analyze(std::string("module top;")+bad+"endmodule");}
      catch(const std::runtime_error&){rejected=true;}assert(rejected);analyze(source);
    }
  }
}

void test_signature_initializer_cleanup() {
  const std::string source=R"(
    module leaf #(parameter W=8);
      typedef class Reporter;
      function automatic int invoke();Reporter r;r=new;return r.value();endfunction
      int startup=invoke();
      function automatic int defaults(int prior=3,int value=invoke()+prior);return value;endfunction
      class Client;extern static function int read();typedef int result_t;endclass
      function int Client::read();result_t n=invoke();return n;endfunction
      typedef class Handler;
      class Reporter;
        Handler h;
        function int value();h=new;return h.n;endfunction
      endclass
      class Handler;logic[W-1:0] bits;int n=23;endclass
      int observed;
      initial observed=Client::read();
    endmodule
    module top;leaf #(65) one();leaf #(129) two();endmodule
  )";
  for(int round=0;round<5;++round) {
    auto* top=analyze(source);rtl::VeriSeqBlock* previous=nullptr;
    for(auto entry:{std::make_pair("one",65),std::make_pair("two",129)}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(entry.first));
      auto* unit=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto cls=[&](const char* name){return rtl::veri_class_type(unit->scope()->value_same_level(name));};
      auto* reporter=cls("Reporter");auto* handler=cls("Handler");
      assert(reporter&&handler&&handler!=previous);previous=handler;
      assert(rtl::veri_class_type(reporter->class_member("h"))==handler);
      assert(static_cast<rtl::VeriVar*>(handler->class_member("bits"))->dlen()==entry.second);
      auto* fn=static_cast<rtl::VeriFunc*>(cls("Client")->class_member("read"))->func();
      assert(fn->scope()->value_same_level("n"));
    }
    bool rejected=false;
    try{analyze("module top;typedef class C;class C;Missing field;endclass endmodule");}
    catch(const std::runtime_error&){rejected=true;}
    assert(rejected);analyze(source);
  }
}

void test_forward_specialization_cleanup() {
  const std::string source=R"SV(
    module unit_test #(parameter W=8);
      typedef class D;
      typedef D#(logic[W-1:0]) Early;
      class B#(type T=int);T value;endclass
      class D#(type T=int) extends B#(T);D#(T) peer;endclass
      typedef D#(logic[W-1:0]) Late;
      Early early;Late late;B#(logic[W-1:0]) base;
      initial begin early=new;late=early;base=late;end
    endmodule
    module top;unit_test #(65) a();unit_test #(129) b();endmodule
  )SV";
  for(int round=0;round<5;++round) {
    auto* top=analyze(source);rtl::VeriSeqBlock* previous=nullptr;
    for(auto entry:{std::make_pair("a",65),std::make_pair("b",129)}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(entry.first));
      auto* unit=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto cls=[&](const char* name){return rtl::veri_class_type(unit->scope()->value_same_level(name));};
      auto* derived=cls("early");assert(derived&&derived!=previous);previous=derived;
      assert(derived==cls("Early")&&derived==cls("Late")&&derived==cls("late"));
      assert(derived->base_class()==cls("base"));
      assert(rtl::veri_class_type(derived->class_member("peer"))==derived);
      assert(static_cast<rtl::VeriVar*>(derived->class_member("value"))->dlen()==entry.second);
    }
    bool rejected=false;
    try{analyze("module top;typedef class D;typedef D#(int) E;class D#(type T=int) extends Missing;endclass endmodule");}
    catch(const std::runtime_error&){rejected=true;}
    assert(rejected);analyze(source);
  }
}

void test_class_inheritance_cloning_cleanup() {
  const std::string source=R"(
    module unit_test #(parameter W=8);
      class Base;
        logic [W-1:0] bits;
        function new(int n=1);bits=n;endfunction
        virtual function int get();return bits;endfunction
      endclass
      class Derived extends Base;
        function new();super.new(W);endfunction
        function int get();return super.get()+1;endfunction
        virtual task empty();endtask
      endclass
      Derived d;Base b;
      initial begin d=new;b=d;d.empty();end
    endmodule
    module top;unit_test #(8) a();unit_test #(65) b();endmodule
  )";
  for(int repeat=0;repeat<4;++repeat) {
    auto* top=analyze(source);rtl::VeriSeqBlock* previous=nullptr;
    for(auto entry:{std::make_pair("a",8),std::make_pair("b",65)}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(entry.first));
      auto* unit=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* derived=static_cast<rtl::VeriVar*>(unit->scope()->value_same_level("d"))->class_type();
      auto* base=static_cast<rtl::VeriVar*>(unit->scope()->value_same_level("b"))->class_type();
      assert(derived->base_class()==base&&base!=previous);previous=base;
      auto* bits=derived->class_member("bits");assert(bits==base->class_member("bits")&&static_cast<rtl::VeriVar*>(bits)->dlen()==entry.second);
      assert(derived->scope()->value_within_module("bits")==bits);
      auto* parent=static_cast<rtl::VeriVar*>(derived->scope()->value_same_level("super"));assert(parent->class_type()==base);
      auto* method=static_cast<rtl::VeriFunc*>(base->class_member("get"));assert(method->func()->virtual_method());
    }
  }
  bool rejected=false;try{analyze("module top;class D extends Missing;endclass endmodule");}
  catch(const std::runtime_error&){rejected=true;}assert(rejected);analyze(source);
}

void test_string_associative_cloning_cleanup() {
  const std::string source=R"(
    module store #(parameter W=8);
      logic[W-1:0] words[string];
      class C;logic[W-1:0] entries[string];
        function void put(string key,logic[W-1:0] value);entries[key]=value;endfunction
        function int total();int n;foreach(entries[k])n=n+k.len();return n;endfunction
      endclass
      C object;
      initial begin object=new;words["x"]=1;foreach(words[k])words[k]=k.len();
        foreach(object.entries[k])words[k]=object.entries[k];end
    endmodule
    module top;store #(8) a();store #(129) b();endmodule
  )";
  for(int round=0;round<4;++round) {
    auto* top=analyze(source);rtl::VeriNode* previous=nullptr;
    for(auto entry:{std::make_pair("a",8),std::make_pair("b",129)}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(entry.first));
      auto* unit=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* words=static_cast<rtl::VeriVar*>(unit->scope()->value_same_level("words"));
      assert(words!=previous&&words->container_kind()==vrASSOC_STRING&&words->dlen()==entry.second);previous=words;
      auto* type=static_cast<rtl::VeriVar*>(unit->scope()->value_same_level("object"))->class_type();
      auto* member=static_cast<rtl::VeriVar*>(type->class_member("entries"));
      assert(member->container_kind()==vrASSOC_STRING&&member->dlen()==entry.second);
    }
    auto* parser=rtl::VeriParser::get_instance();
    rtl::Src_mgr::get_instance()->set_src(std::string("module top;int a[string];initial foreach(a[k]) begin")+char(0));
    assert(parser->init()==rtl::OK);parser->set_top_module("top");assert(parser->parse()!=rtl::OK);
  }
  analyze(source);
}

void test_string_queue_cloning_cleanup() {
  const std::string source=R"SV(module leaf #(parameter int W=8);
    typedef string Strings[$];Strings values;
    class Store #(type T=string);T entries[$];endclass
    Store #(string) object;
    function automatic Strings copy(input Strings source);
      Strings result;result=source;result.push_back("suffix");return result;
    endfunction
    initial begin object=new();values.push_back("first");object.entries=values;
      values=copy(object.entries);$display(values[0].len(),object.entries.pop_front());end
    endmodule
    module top;leaf #(8) one();leaf #(65) two();endmodule)SV";
  for(int repeat=0;repeat<4;++repeat) {
    auto* top=analyze(source);rtl::VeriNode* previous=nullptr;
    for(const auto& name:{"one","two"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* unit=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* values=unit->scope()->value_same_level("values");
      assert(values!=previous&&rtl::veri_string_value(values)&&rtl::veri_array_shape(values).unpacked==1);previous=values;
      auto* type=static_cast<rtl::VeriVar*>(unit->scope()->value_same_level("object"))->class_type();
      auto* entries=static_cast<rtl::VeriVar*>(type->class_member("entries"));
      assert(entries->container_kind()==vrQUEUE&&rtl::veri_string_value(entries));
    }
    bool rejected=false;
    try{analyze("module top;string scalar;initial scalar.push_back(1);endmodule");}
    catch(const std::runtime_error&){rejected=true;}assert(rejected);
  }
  analyze(source);
}

void test_packed_key_associative_cleanup() {
  const std::string source=R"SV(module leaf #(parameter int W=64);
    typedef struct packed {bit[W-1:0] address;bit valid;} Key;
    typedef Key Alias;
    typedef int Table[Alias];Table values;
    Key found[$];
    class Store #(type K=Key);int entries[K][int];endclass
    Store #(Key) object;
    initial begin
      foreach(values[k])$display(k.address,k.valid);
      found=values.find_index() with(item>0);
      foreach(object.entries[k,j])$display(k.address,k.valid,j);
    end
    endmodule
    module top;leaf #(32) one();leaf #(64) two();leaf #(128) three();endmodule)SV";
  for(int repeat=0;repeat<4;++repeat) {
    auto* top=analyze(source);rtl::VeriVar* previous=nullptr;
    for(const char* name:{"one","two","three"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* values=static_cast<rtl::VeriVar*>(mod->scope()->value_same_level("values"));
      auto* key=values->associative_key_type();auto* aggregate=key->aggregate_type();
      const int width=std::string(name)=="one"?33:std::string(name)=="two"?65:129;
      assert(aggregate&&aggregate!=previous&&!aggregate->unpacked_struct());previous=aggregate;
      assert(key->dlen()==width&&aggregate->packed_fields().size()==2&&values->container_kind()==vrASSOC_UINT);
      auto* found=static_cast<rtl::VeriVar*>(mod->scope()->value_same_level("found"));
      assert(found->aggregate_type()==aggregate);
      auto* store=static_cast<rtl::VeriVar*>(mod->scope()->value_same_level("object"))->class_type();
      auto* entries=static_cast<rtl::VeriVar*>(store->class_member("entries"));
      assert(entries->associative_key_type()->aggregate_type()==aggregate);
    }
    for(const char* body:{"typedef struct {int n;} Key;int values[Key];",
                          "typedef struct packed {string n;} Key;int values[Key];"}) {
      bool rejected=false;
      try{analyze(std::string("module top;")+body+"endmodule");}catch(const std::runtime_error&){rejected=true;}
      assert(rejected);analyze(source);
    }
  }
}

void test_integral_key_associative_cloning_cleanup() {
  const std::string source=R"(
    module leaf #(parameter W=65);
      typedef bit [W-1:0] Key;
      typedef enum bit [27:0] {A=0,B=1<<16} EnumKey;
      typedef int Table[Key];Table values;
      int enums[EnumKey];
      class Store;Table entries;endclass
      Store object;
      initial begin foreach(values[k])values[k]=1;foreach(enums[e])$display("%s",e.name());end
    endmodule
    module top;leaf #(.W(65)) one();leaf #(.W(129)) two();endmodule
  )";
  for(int repeat=0;repeat<8;++repeat) {
    auto* top=analyze(source);rtl::VeriVar* previous=nullptr;int width=65;
    for(const auto& name:{"one","two"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* unit=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* map=static_cast<rtl::VeriVar*>(unit->scope()->value_same_level("values"));
      auto* key=map->associative_key_type();assert(key&&key->dlen()==width&&key!=previous);previous=key;width=129;
      auto* enums=static_cast<rtl::VeriVar*>(unit->scope()->value_same_level("enums"));
      assert(enums->associative_key_type()->enum_type()&&enums->associative_key_type()->dlen()==28);
      auto* store=static_cast<rtl::VeriVar*>(unit->scope()->value_same_level("object"))->class_type();
      assert(static_cast<rtl::VeriVar*>(store->class_member("entries"))->associative_key_type()==key);
    }
    bool rejected=false;try {analyze("module top;typedef real K;int a[K];endmodule");}catch(const std::runtime_error&){rejected=true;}
    assert(rejected);
  }
  analyze(source);
}

void test_object_key_associative_cloning_cleanup() {
  const std::string source=R"(
    module leaf #(parameter W=65);
      class Key;logic [W-1:0] value;endclass
      typedef Key Alias;
      typedef int Table[Alias];Table values;
      class Store;Table entries;endclass
      Store object;
      initial begin foreach(values[k])values[k]=k.value;end
    endmodule
    module top;leaf #(.W(65)) one();leaf #(.W(129)) two();endmodule
  )";
  for(int repeat=0;repeat<12;++repeat) {
    auto* top=analyze(source);rtl::VeriSeqBlock* previous=nullptr;
    for(const auto& name:{"one","two"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* unit=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* map=static_cast<rtl::VeriVar*>(unit->scope()->value_same_level("values"));
      assert(map->container_kind()==vrASSOC_CLASS&&map->associative_key_type());
      auto* key=map->associative_key_type()->class_type();assert(key&&key!=previous);previous=key;
      auto* store=static_cast<rtl::VeriVar*>(unit->scope()->value_same_level("object"))->class_type();
      auto* field=static_cast<rtl::VeriVar*>(store->class_member("entries"));
      assert(field->associative_key_type()->class_type()==key);
    }
    auto* parser=rtl::VeriParser::get_instance();
    rtl::Src_mgr::get_instance()->set_src(std::string("module top;class K;endclass int a[K];initial foreach(a[k])begin")+char(0));
    assert(parser->init()==rtl::OK);parser->set_top_module("top");assert(parser->parse()!=rtl::OK);
  }
  analyze(source);
}

void test_foreach_selection_cloning_cleanup() {
  const std::string source=R"(
    module store #(parameter W=8);
      class Cell;logic[W-1:0] values[string];endclass
      Cell nodes[2];int matrix[2][3][4];
      function automatic int total(input int which);
        int sum=0;
        foreach(nodes[which+0].values[key])sum+=nodes[which].values[key];
        foreach(matrix[which][,col])sum+=matrix[which][0][col];
        return sum;
      endfunction
    endmodule
    module top;store #(8) a();store #(129) b();endmodule
  )";
  for(int round=0;round<6;++round) {
    auto* top=analyze(source);rtl::VeriNode* previous=nullptr;
    for(auto entry:{std::make_pair("a",8),std::make_pair("b",129)}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(entry.first));
      auto* unit=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* cells=static_cast<rtl::VeriVar*>(unit->scope()->value_same_level("nodes"));
      auto* type=cells->class_type();assert(type&&type!=previous);previous=type;
      auto* member=static_cast<rtl::VeriVar*>(type->class_member("values"));
      assert(member->container_kind()==vrASSOC_STRING&&member->dlen()==entry.second);
    }
  }
}

void test_extern_method_cloning_cleanup() {
  const std::string source=R"(
    module unit_test #(parameter W=8);
      class C #(type T=logic[W-1:0]);
        local T value;
        extern function new(T x=3);
        extern function T get(T x=1);
        extern static task wait_for(input int n,output int y);
      endclass
      function C::new(T x);value=x;endfunction:new
      function C::T C::get(C::T x);return value+x;endfunction:get
      task C::wait_for(input int n,output int y);#1;y=n;endtask:wait_for
      C #() c;logic[W-1:0] result;int n;
      initial begin c=new;result=c.get();C#()::wait_for(2,n);end
    endmodule
    module top;unit_test #(8) a();unit_test #(129) b();endmodule
  )";
  for(int round=0;round<4;++round) {
    auto* top=analyze(source);rtl::VeriNode* prior=nullptr;
    for(auto entry:{std::make_pair("a",8),std::make_pair("b",129)}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(entry.first));
      auto* unit=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* type=rtl::veri_class_type(unit->scope()->value_same_level("c"));
      auto* symbol=static_cast<rtl::VeriFunc*>(type->class_member("get"));
      auto* declaration=symbol->func();assert(declaration!=prior);prior=declaration;
      assert(declaration->extern_method()&&declaration->extern_header());
      assert(declaration->extern_header()->father()==declaration);
      assert(declaration->stmt()->father()==declaration&&symbol->dlen()==entry.second);
      auto* task=static_cast<rtl::VeriTask*>(type->class_member("wait_for"))->task();
      assert(task->extern_method()&&task->static_method()&&task->extern_header()->father()==task);
    }
  }
  for(const auto& invalid:std::vector<std::string>{
      "class C;extern function int f();endclass",
      "class C;extern function int f(int x);endclass function int C::f(byte x);return x;endfunction",
      "typedef int T;class C;extern function int f(T x);typedef int T;endclass function int C::f(T x);return x;endfunction"}) {
    bool rejected=false;try{analyze("module top;"+invalid+"\nendmodule");}
    catch(const std::runtime_error& e){rejected=std::string(e.what()).find("extern method")!=std::string::npos;}
    assert(rejected);analyze(source);
  }
}

void test_class_access_cloning_cleanup() {
  const std::string source=R"(
    module unit_test #(parameter W=8);
      class B;
        local logic[W-1:0] bits;
        protected int n;
        local function int hidden();return bits;endfunction
        function int get();return hidden()+n;endfunction
      endclass
      class D extends B;
        protected static int count;
        function int read_other(B other);return other.n;endfunction
      endclass
      D object;int result;
      initial begin object=new;result=object.get();end
    endmodule
    module top;unit_test #(8) a();unit_test #(129) b();endmodule
  )";
  for(int round=0;round<4;++round) {
    auto* top=analyze(source);rtl::VeriNode* previous=nullptr;
    for(auto entry:{std::make_pair("a",8),std::make_pair("b",129)}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(entry.first));
      auto* unit=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* type=rtl::veri_class_type(unit->scope()->value_same_level("object"));
      auto* base=type->base_class();assert(type->scope()->class_owner()==type&&base->scope()->class_owner()==base);
      auto* bits=base->class_member("bits");assert(bits!=previous);previous=bits;
      assert(static_cast<rtl::VeriVar*>(bits)->dlen()==entry.second);
      assert(rtl::veri_class_member_declaration(bits)->class_access()==rtl::VeriDecl::LOCAL);
      assert(rtl::veri_class_member_declaration(base->class_member("n"))->class_access()==rtl::VeriDecl::PROTECTED);
      assert(rtl::veri_local_class_member(base->class_member("hidden")));
      rtl::veri_check_class_access(bits,base->scope());
      rtl::veri_check_class_access(base->class_member("n"),type->scope());
      assert(type->scope()->value("bits")==nullptr);
      for(auto* context:{unit->scope(),type->scope()}) {
        bool rejected=false;try{rtl::veri_check_class_access(bits,context);}
        catch(const std::runtime_error& e){rejected=std::string(e.what()).find("inaccessible local")!=std::string::npos;}
        assert(rejected);
      }
    }
  }
  bool rejected=false;
  try{analyze("module top;class C;local int n;endclass C c;int x;initial x=c.n;endmodule");}
  catch(const std::runtime_error&){rejected=true;}
  assert(rejected);analyze(source);
}

void test_class_static_cloning_cleanup() {
  const std::string source=R"(
    module unit_test #(parameter W=8);
      class C #(parameter int N=W);
        static logic[N-1:0] bits;
        static logic[N-1:0] words[0:1]='{1,2};
        static function int get();return bits;endfunction
        static task put(int v);#1;bits=v;endtask
      endclass
      typedef C#(W) A;
      A object;
      int n;
      initial begin n=C#(W)::get();A::put(n);object.bits=A::bits;end
    endmodule
    module top;unit_test #(8) a();unit_test #(129) b();endmodule
  )";
  for(int round=0;round<4;++round) {
    auto* top=analyze(source);rtl::VeriNode* previous=nullptr;
    for(auto entry:{std::make_pair("a",8),std::make_pair("b",129)}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(entry.first));
      auto* unit=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* type=rtl::veri_class_type(unit->scope()->value_same_level("object"));
      auto* bits=type->class_member("bits");assert(bits!=previous);previous=bits;
      assert(static_cast<rtl::VeriVar*>(bits)->dlen()==entry.second);
      assert(unit->scope()->value_within_module("A::bits")==bits);
      assert(static_cast<rtl::VeriDecl*>(bits->father())->explicit_static());
      auto* f=static_cast<rtl::VeriFunc*>(type->class_member("get"))->func();
      auto* t=static_cast<rtl::VeriTask*>(type->class_member("put"))->task();
      assert(f->static_method()&&t->static_method());
      assert(f->is_auto()==rtl::IS_TRUE&&t->is_auto()==rtl::IS_TRUE);
      assert(!f->explicit_static()&&!f->virtual_method());
      assert(rtl::veri_array_shape(type->class_member("words")).unpacked==1);
    }
  }
}

void test_parameterized_class_cloning_cleanup() {
  const std::string source=R"(
    module unit_test #(parameter W=8);
      class C #(parameter int N=W,type T=logic[N-1:0]);
        T bits;
        function T get();return bits;endfunction
      endclass
      C a;C#(.T(logic[W-1:0]),.N(W)) b;C#(3) c;C#(W,logic[W-1:0]) d;
    endmodule
    module top;unit_test #(8) a();unit_test #(129) b();endmodule
  )";
  for(int round=0;round<4;++round) {
    auto* top=analyze(source);rtl::VeriSeqBlock* previous=nullptr;
    for(auto entry:{std::make_pair("a",8),std::make_pair("b",129)}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(entry.first));
      auto* unit=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto type=[&](const char* name){return static_cast<rtl::VeriVar*>(unit->scope()->value_same_level(name))->class_type();};
      auto* a=type("a");auto* c=type("c");assert(a==type("b")&&a==type("d")&&a!=c&&a!=previous);previous=a;
      assert(!a->generic_class()&&a->class_origin()->generic_class());
      assert(a->class_origin()->specializations().size()==2);
      assert(static_cast<rtl::VeriVar*>(a->class_member("bits"))->dlen()==entry.second);
      assert(static_cast<rtl::VeriVar*>(c->class_member("bits"))->dlen()==3);
      assert(static_cast<rtl::VeriFunc*>(a->class_member("get"))->dlen()==entry.second);
    }
  }
  bool rejected=false;try{analyze("module top;class C#(type T);T v;endclass C a;endmodule");}
  catch(const std::runtime_error&){rejected=true;}assert(rejected);analyze(source);
}

void test_class_parameter_lists_cleanup() {
  analyze("package p;parameter V=1;endpackage module top;initial $display(\"%0d\",p::V\finside {1});endmodule");
  const std::string source=R"(
    module unit_test #(parameter W=8);
      class C #(int N, M=N+1, type T=logic[N-1:0], U=T);
        T a;U b;
      endclass
      C#(W) first;C#(.N(W),.M(W+1),.T(logic[W-1:0]),.U(logic[W-1:0])) same;
      C#(.N(W),.U(byte)) distinct;
    endmodule
    module top;unit_test#(8) a();unit_test#(129) b();endmodule
  )";
  for(int round=0;round<4;++round) {
    auto* top=analyze(source);rtl::VeriSeqBlock* previous=nullptr;
    for(auto entry:{std::make_pair("a",8),std::make_pair("b",129)}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(entry.first));
      auto* unit=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto type=[&](const char* name){return static_cast<rtl::VeriVar*>(unit->scope()->value_same_level(name))->class_type();};
      auto* first=type("first");auto* distinct=type("distinct");
      assert(first==type("same")&&first!=distinct&&first!=previous);previous=first;
      assert(static_cast<rtl::VeriVar*>(first->class_member("a"))->dlen()==entry.second);
      assert(static_cast<rtl::VeriVar*>(first->class_member("b"))->dlen()==entry.second);
      assert(static_cast<rtl::VeriVar*>(distinct->class_member("a"))->dlen()==entry.second);
      assert(static_cast<rtl::VeriVar*>(distinct->class_member("b"))->dlen()==8);
    }
  }
  for(const auto& body:{"class C#(int W,N=W);endclass C c;",
                        "class C#(type T=int,U=3);endclass C c;"}) {
    bool rejected=false;try{analyze(std::string("module top;")+body+"endmodule");}
    catch(const std::runtime_error&){rejected=true;}assert(rejected);analyze(source);
  }
}

void test_class_body_parameters_cleanup() {
  const std::string source=R"SV(
    module unit_test #(parameter W=8);
      class C #(int N=W);
        parameter int A=N+1;
        localparam int B=A+2;
        logic[B-1:0] data;
      endclass
      class Child extends C#(W);
        localparam int NEXT=B+1;
      endclass
      C first;Child second;
      localparam int SIZE=C#(W)::B;
      logic[SIZE-1:0] value;
    endmodule
    module top;unit_test#(8) a();unit_test#(129) b();endmodule)SV";
  for(int round=0;round<5;++round) {
    auto* top=analyze(source);rtl::VeriNode* previous=nullptr;
    for(auto entry:{std::make_pair("a",11),std::make_pair("b",132)}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(entry.first));
      auto* unit=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* cls=rtl::veri_class_type(unit->scope()->value_same_level("first"));
      auto* child=rtl::veri_class_type(unit->scope()->value_same_level("second"));
      auto* bound=cls->class_member("B");assert(bound&&bound->tok_type()==vtPARAM&&bound!=previous);previous=bound;
      assert(child->class_member("B")==bound);
      assert(static_cast<rtl::VeriParam*>(bound)->get_val()->get_first_int()==entry.second);
      assert(static_cast<rtl::VeriVar*>(cls->class_member("data"))->dlen()==entry.second);
      assert(static_cast<rtl::VeriVar*>(unit->scope()->value_same_level("value"))->dlen()==entry.second);
      assert(static_cast<rtl::VeriParamDecl*>(bound->father())->is_local()==rtl::IS_TRUE);
    }
  }
}

void test_struct_container_metadata_cleanup() {
  const std::string source=R"SV(
    module top;
      class Item;int id;endclass
      typedef struct {string name;Item handle;} Entry;
      class Holder;Entry queue[$];Entry value;endclass
      Holder h;Entry value;int observed;
      initial begin h=new;value=h.queue.pop_front();observed=h.value.handle.id;end
    endmodule)SV";
  for(int round=0;round<5;++round) {
    auto* top=analyze(source);
    auto* type=rtl::veri_aggregate_type(top->scope()->value_same_level("value"));
    auto* holder=rtl::veri_class_type(top->scope()->value_same_level("h"));
    assert(rtl::veri_aggregate_type(holder->class_member("queue"))==type);
    rtl::VeriNode::NodeVec pending{top};bool pop=false,handle=false;
    while(!pending.empty()) {
      auto* node=pending.back();pending.pop_back();
      if(node->detail_type()==veEXP_MEMBER) {
        auto* member=static_cast<rtl::VeriMemberExp*>(node);
        if(member->member()=="pop_front"){assert(rtl::veri_aggregate_type(member)==type);pop=true;}
        if(member->member()=="handle"){assert(rtl::veri_class_type(member)==rtl::veri_class_type(top->scope()->value_same_level("Item")));handle=true;}
      }
      node->push_for_replacement(pending);
    }
    assert(pop&&handle);
  }
}

void test_parameterized_formals_cleanup() {
  // Exercise raw parser input (the CLI preprocessor may strip comments),
  // Flex buffer refills, long lookahead, cloning and canonical type binding.
  for(const size_t padding:{size_t(0),size_t(8191),size_t(16380),size_t(32780)}) {
    const std::string comment="/*"+std::string(66000,'x')+"*/";
    const std::string source="/*"+std::string(padding,'p')+"*/"+R"(
      module unit_test#(parameter W=8);
        class Box#(int N=1);logic[N-1:0] value;endclass
        class Node#(type T=int);T value;endclass
        function int width_n(int n,)"+comment+"Box /*t*/ # /*h*/ (W "+comment+R"() /*p*/ item,
                              Node#(Box#(W)) chain);
          return n+$bits(item.value);
        endfunction
        Box#(W) obj;Node#(Box#(W)) outer;
      endmodule
      module top;unit_test#(8) a();unit_test#(129) b();endmodule
    )";
    auto* top=analyze(source);
    for(const char* name:{"a","b"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* unit=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* function=static_cast<rtl::VeriFunc*>(unit->scope()->value_same_level("width_n"));
      const auto formals=rtl::veri_subroutine_formals(function->func());assert(formals.size()==3);
      for(const auto entry:{std::make_pair(size_t(1),"obj"),std::make_pair(size_t(2),"outer")})
        assert(rtl::veri_class_type(rtl::veri_formal_symbol(formals[entry.first]))==
          static_cast<rtl::VeriVar*>(unit->scope()->value_same_level(entry.second))->class_type());
    }
  }
  for(const std::string suffix:{"int] item);endfunction endmodule", "$bits(\"unterminated", "int /*unterminated"}) {
    auto* parser=rtl::VeriParser::get_instance();
    rtl::Src_mgr::get_instance()->set_src("module top;class C#(type T=int);endclass function int f(int n,C#("+suffix+std::string(1,'\0'));
    assert(parser->init()==rtl::OK);parser->set_top_module("top");assert(parser->parse()!=rtl::OK);
    analyze("module top;class C#(type T=int);endclass function int f(int n,C#(int) obj);return n;endfunction endmodule");
  }
}

void test_abstract_class_cloning_cleanup() {
  const std::string source=R"(
    module unit_test #(parameter W=8);
      virtual class Base;
        pure virtual function logic[W-1:0] get(int value=3);
        pure virtual task run(int value=2);
      endclass
      class Derived extends Base;
        function logic[W-1:0] get(int value=3);return value;endfunction
        task run(int value=2);#1;endtask
      endclass
      Base base;Derived derived;int ok;
      initial begin derived=new;base=derived;ok=$cast(derived,base);end
    endmodule
    module top;unit_test #(8) a();unit_test #(129) b();endmodule
  )";
  for(int repeat=0;repeat<4;++repeat) {
    auto* top=analyze(source);rtl::VeriSeqBlock* previous=nullptr;
    for(auto entry:{std::make_pair("a",8),std::make_pair("b",129)}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(entry.first));
      auto* unit=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* base=static_cast<rtl::VeriVar*>(unit->scope()->value_same_level("base"))->class_type();
      auto* derived=static_cast<rtl::VeriVar*>(unit->scope()->value_same_level("derived"))->class_type();
      assert(base!=previous&&base->abstract_class()&&!derived->abstract_class()&&derived->base_class()==base);previous=base;
      auto* get=static_cast<rtl::VeriFunc*>(base->class_member("get"));
      assert(get->func()->pure_virtual()&&get->func()->virtual_method()&&get->dlen()==entry.second);
      assert(static_cast<rtl::VeriTask*>(base->class_member("run"))->task()->pure_virtual());
      assert(!static_cast<rtl::VeriFunc*>(derived->class_member("get"))->func()->pure_virtual());
    }
  }
  bool rejected=false;try{analyze("module top;virtual class Bad extends Missing;pure virtual function int f();endclass endmodule");}
  catch(const std::runtime_error&){rejected=true;}assert(rejected);analyze(source);
}

void test_class_object_cloning_cleanup() {
  const std::string source=R"(
    module unit_test #(parameter W=8);
      class Word;
        logic [W-1:0] bits;
        function new(int value=1);this.bits=value;endfunction
        function Word identity();return this;endfunction
      endclass
      Word p,q;
      initial begin p=new(W);q=p.identity();q.bits=3;end
    endmodule
    module top;unit_test #(8) a();unit_test #(65) b();endmodule
  )";
  for(int repeat=0;repeat<4;++repeat) {
    auto* top=analyze(source);rtl::VeriSeqBlock* first=nullptr;
    for(auto entry:{std::make_pair("a",8),std::make_pair("b",65)}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(entry.first));
      auto* unit=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* p=static_cast<rtl::VeriVar*>(unit->scope()->value_same_level("p"));
      auto* definition=p->class_type();assert(definition&&definition->class_declaration());
      assert(definition!=first);first=definition;
      assert(static_cast<rtl::VeriVar*>(definition->scope()->value_same_level("bits"))->dlen()==entry.second);
      auto* self=static_cast<rtl::VeriVar*>(definition->scope()->value_same_level("this"));assert(self->class_type()==definition);
      auto* constructor=static_cast<rtl::VeriFunc*>(definition->scope()->value_same_level("new"));
      assert(constructor->func()->is_auto()==rtl::IS_TRUE&&constructor->func()->is_void());
      assert(static_cast<rtl::VeriVar*>(unit->scope()->value_same_level("q"))->class_type()==definition);
    }
  }
}

void test_header_import_cloning_cleanup() {
  const std::string source=R"(
    package p;parameter integer W=3;typedef bit[W-1:0] T;integer total=0;endpackage
    interface bus import p::*; #(parameter N=W)(input T seed);
      logic[N-1:0] data;endinterface
    module child import p::T,p::W,p::total; #(parameter N=W)
      (input T seed,output logic[N-1:0] value);
      initial begin total=total+1;value=seed;end endmodule
    module top;logic[2:0] seed;wire[4:0] a;wire[8:0] b;
      child #(5) x(seed,a);child #(9) y(seed,b);bus #(7) z(seed);endmodule
  )";
  auto hive=[](rtl::VeriMod* mod,const std::string& name) {
    auto* symbol=mod->scope()->value_same_level(name);assert(symbol&&symbol->tok_type()==vtMOD_INST);
    return static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(static_cast<rtl::VeriModInst*>(symbol)->instance())->hive());
  };
  for(int round=0;round<5;++round) {
    auto* top=analyze(source);auto* parser=rtl::VeriParser::get_instance();
    auto* pkg=parser->package("p");auto* x=hive(top,"x");auto* y=hive(top,"y");auto* z=hive(top,"z");
    assert(x->header_imports()!=y->header_imports());
    assert(x->header_imports()!=parser->module("child")->header_imports());
    assert(!top->scope()->value_same_level("W")&&!top->scope()->value_same_level("T"));
    for(auto* mod:{x,y,z}) {
      assert(mod->header_imports()&&mod->header_imports()->father()==mod);
      assert(mod->header_imports()->scope()==mod->scope());
      assert(mod->scope()->value_within_module("T")==pkg->scope()->value_same_level("T"));
      auto* seed=static_cast<rtl::VeriVar*>(mod->scope()->value_same_level("seed"));
      assert(seed->dlen()==3&&seed->net_type()==vvBIT);
    }
    for(auto* mod:{x,y})
      assert(mod->scope()->value_within_module("total")==pkg->scope()->value_same_level("total"));
    assert(static_cast<rtl::VeriVar*>(x->scope()->value_same_level("value"))->dlen()==5);
    assert(static_cast<rtl::VeriVar*>(y->scope()->value_same_level("value"))->dlen()==9);
    assert(static_cast<rtl::VeriVar*>(z->scope()->value_same_level("data"))->dlen()==7);
  }
}

void test_compilation_import_cloning_cleanup() {
  const std::string source=R"(
    package p;parameter W=3;typedef bit[W-1:0] T;integer total=0;endpackage
    module early;parameter W=17;integer x;initial x=W;endmodule
    import p::*;
    package q;parameter EXTRA=11;endpackage
    module child #(parameter N=W)(input T seed);T data;initial begin data=seed;total=total+N;end endmodule
    interface bus #(parameter N=W);T data;endinterface
    module local_shadow;parameter W=7;typedef logic[5:0] T;T data;endmodule
    import q::EXTRA;
    module top;
      child #(5) x(3),y(4);bus z();early before_i();local_shadow shadow_i();
      integer result;initial result=EXTRA;
    endmodule
  )";
  auto hive=[](rtl::VeriMod* m,const char* name) {
    auto* symbol=static_cast<rtl::VeriModInst*>(m->scope()->value_same_level(name));assert(symbol);
    return static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(symbol->instance())->hive());
  };
  for(int round=0;round<5;++round) {
    auto* top=analyze(source);auto* parser=rtl::VeriParser::get_instance();
    auto* p=parser->package("p");auto* q=parser->package("q");
    assert(top->scope()->value_within_module("EXTRA")==q->scope()->value_same_level("EXTRA"));
    assert(!top->scope()->value_same_level("T"));
    auto* x=hive(top,"x");auto* y=hive(top,"y");auto* z=hive(top,"z");
    assert(x!=y&&x->scope()!=y->scope());
    for(auto* mod:{x,y,z}) {
      assert(!mod->scope()->value_same_level("W"));
      assert(mod->scope()->value_within_module("W")==p->scope()->value_same_level("W"));
      assert(mod->scope()->value_within_module("T")==p->scope()->value_same_level("T"));
      assert(mod->scope()->value_within_module("total")==p->scope()->value_same_level("total"));
      assert(static_cast<rtl::VeriVar*>(mod->scope()->value_same_level("data"))->dlen()==3);
    }
    assert(!hive(top,"before_i")->scope()->value_within_module("T"));
    assert(!q->scope()->value_within_module("T"));
    assert(static_cast<rtl::VeriVar*>(hive(top,"shadow_i")->scope()->value_same_level("data"))->dlen()==6);
    analyze("module top;integer W;endmodule");
    assert(!parser->module("top")->scope()->value_within_module("T"));
    // Both a semantic exception and an incomplete source must release all
    // non-owning import links before the parser is reused.
    bool rejected=false;
    try {analyze("import missing::*;module top;endmodule");}
    catch(const std::runtime_error&) {rejected=true;}
    assert(rejected);
    analyze("module top;endmodule");
    rtl::Src_mgr::get_instance()->set_src(std::string("package p;endpackage import p::*;module")+std::string(1,'\0'));
    assert(parser->init()==rtl::OK);parser->set_top_module("top");assert(parser->parse()!=rtl::OK);
    auto* clean=analyze("module top;endmodule");assert(!clean->scope()->value_within_module("T"));
  }
}

void test_compilation_types_identity_cleanup() {
  const std::string source=R"(
    package p;parameter N=5;typedef bit[N-1:0] T;endpackage
    import p::*;
    typedef T Word;
    class C;static int count=0;Word data;function new();count++;data=N;endfunction endclass
    class D extends C;endclass
    module child;C value;initial value=new;endmodule
    module local_scope;class C;int x;endclass C value;initial value=new;endmodule
    module top;child a(),b();local_scope l();D derived;initial derived=new;endmodule
  )";
  auto hive=[](rtl::VeriMod* mod,const char* name) {
    auto* symbol=static_cast<rtl::VeriModInst*>(mod->scope()->value_same_level(name));assert(symbol);
    return static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(symbol->instance())->hive());
  };
  for(int round=0;round<6;++round) {
    auto* top=analyze(source);auto* parser=rtl::VeriParser::get_instance();
    assert(parser->compilation_declarations().size()==3);
    assert(parser->packages().size()==1&&!parser->package("$unit"));
    auto* a=hive(top,"a");auto* b=hive(top,"b");auto* local=hive(top,"l");
    auto* global_type=top->scope()->value_within_module("C");assert(global_type);
    assert(!a->scope()->value_same_level("C")&&!b->scope()->value_same_level("C"));
    auto* definition=rtl::veri_class_type(global_type);assert(definition);
    assert(definition==rtl::veri_class_type(a->scope()->value_same_level("value")));
    assert(definition==rtl::veri_class_type(b->scope()->value_same_level("value")));
    assert(definition!=rtl::veri_class_type(local->scope()->value_same_level("value")));
    assert(rtl::veri_class_type(top->scope()->value_within_module("D"))->base_class()==definition);
    assert(definition->birth_mod()->is_compilation_unit()&&!definition->birth_mod()->is_package());
    assert(static_cast<rtl::VeriVar*>(definition->scope()->value_same_level("data"))->dlen()==5);
    auto* clean=analyze("module top;endmodule");
    assert(!clean->scope()->value_within_module("C")&&parser->compilation_declarations().empty());
    bool rejected=false;
    try {analyze("class C;endclass class C;endclass module top;endmodule");}
    catch(const std::runtime_error&){rejected=true;}assert(rejected);
    analyze("class C;int x;endclass module top;C value;endmodule");
    rtl::Src_mgr::get_instance()->set_src(std::string("class C;int x;")+std::string(1,'\0'));
    assert(parser->init()==rtl::OK);parser->set_top_module("top");assert(parser->parse()!=rtl::OK);
    clean=analyze("module top;endmodule");assert(!clean->scope()->value_within_module("C"));
  }
}

void test_package_export_identity_cleanup() {
  const std::string source=R"(
    package p;parameter int X=3,HIDDEN=9;typedef logic[4:0] T;integer total=0;endpackage
    package a;export p::*;import p::*;parameter COPY=X;export p::T,p::total;endpackage
    package b;export *::*;import a::X,a::T,a::total;endpackage
    module child import b::*; (input T v);initial total=total+v;endmodule
    module top;import p::*;import b::*;T v;child x(v);child y(v);endmodule
  )";
  for(int round=0;round<5;++round) {
    auto* top=analyze(source);auto* parser=rtl::VeriParser::get_instance();
    auto* original=parser->package("p")->scope();
    for(const auto& name:{"X","T","total"}) {
      auto* symbol=original->package_value(name);assert(symbol);
      assert(parser->package("a")->scope()->package_value(name)==symbol);
      assert(parser->package("b")->scope()->package_value(name)==symbol);
      assert(top->scope()->value_within_module(name)==symbol);
    }
    assert(!parser->package("a")->scope()->package_value("HIDDEN"));
    assert(!parser->package("b")->scope()->package_value("HIDDEN"));
    // Failed exports must not leave pointers or export filters in the next parse.
    rtl::Src_mgr::get_instance()->set_src(
      "package p;parameter X=1;endpackage package a;export p::X;endpackage module top;endmodule"+std::string(1,'\0'));
    assert(parser->init()==rtl::OK);parser->set_top_module("top");
    bool rejected=false;
    try {parser->parse();}catch(const std::runtime_error& error) {
      rejected=std::string(error.what()).find("export requires an import")!=std::string::npos;
    }
    assert(rejected);parser->clean_up();
  }
}

void test_final_bind_cleanup() {
  const std::string source=R"(
    bind lane observer #(.W(W)) watch(.value(value));
    module observer #(parameter W=1)(input wire[W-1:0] value);
      final $display("%m %0d",value);
    endmodule
    module lane #(parameter W=4);logic[W-1:0] value;endmodule
    module top;lane #(4) u();lane #(8) v();endmodule
  )";
  auto hive=[](rtl::VeriMod* mod,const std::string& name) {
    auto* symbol=mod->scope()->value_same_level(name);assert(symbol&&symbol->tok_type()==vtMOD_INST);
    return static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(static_cast<rtl::VeriModInst*>(symbol)->instance())->hive());
  };
  for(int round=0;round<4;++round) {
    auto* top=analyze(source);
    for(const auto& entry:std::vector<std::pair<std::string,int>>{{"u",4},{"v",8}}) {
      auto* observer=hive(hive(top,entry.first),"watch");
      assert(static_cast<rtl::VeriVar*>(observer->scope()->value_same_level("value"))->dlen()==entry.second);
      bool found=false;
      for(auto* item:static_cast<rtl::VeriModuleItemList*>(observer->item())->item_list())
        if(item->detail_type()==vsSTMT_INIT)found|=static_cast<rtl::VeriInitStmt*>(item)->final_process();
      assert(found); // The flag must survive per-instance module cloning.
    }
    auto* parser=rtl::VeriParser::get_instance();
    rtl::Src_mgr::get_instance()->set_src("module top;endmodule bind absent observer o();"+std::string(1,'\0'));
    assert(parser->init()==rtl::OK);parser->set_top_module("top");
    bool rejected=false;try{parser->parse();}catch(const std::runtime_error& error){rejected=std::string(error.what()).find("declared module type")!=std::string::npos;}
    assert(rejected);parser->clean_up();
  }
}

void test_scope_cleanup() {
  rtl::VeriNum number(1,1,1,nullptr);
  rtl::VeriSymbolTable symbols;
  symbols.init(16,"scope");
  symbols.insert("x",&number);
  symbols.clean_up();
  assert(symbols.value_same_level("x")==nullptr);
  symbols.insert("x",&number);
  symbols.clean_up();
  symbols.clean_up();
  rtl::VeriMod mod(2);
  mod.init(16);
  mod.scope()->insert("x",&number);
  mod.clean_up();
  mod.clean_up();
  assert(mod.scope()==nullptr);
}

void test_ports() {
  auto* mod=analyze(
    "module top(input [7:0] a,output [7:0] z); child u(.z(z),.a(a)); endmodule\n"
    "module child(input [7:0] a,output [7:0] z); assign z=a; endmodule\n");
  auto* symbol=mod->scope()->value_same_level("u");
  assert(symbol && symbol->tok_type()==vtMOD_INST);
  auto* inst=static_cast<rtl::VeriModInstance*>(static_cast<rtl::VeriModInst*>(symbol)->instance());
  auto* hive=static_cast<rtl::VeriMod*>(inst->hive());
  assert(hive && hive->port()->father()==hive && hive->item()->father()==hive);
  for(auto* node : static_cast<rtl::VeriMultiExp*>(inst->arg())->exp()) {
    auto* named=static_cast<rtl::VeriNamedParamExp*>(node);
    assert(named->port_ref()==hive->scope()->value_same_level(named->ref()));
    assert(named->port_ref()!=nullptr);
  }
  analyze("module top; child u(); endmodule module child; wire x; endmodule\n");
  analyze("module top(a,z); input [7:0] a; output [7:0] z; wire [7:0] z; assign z=a; endmodule\n");
  analyze("module top(input a); child u(a,a); endmodule module child(input a); endmodule\n",rtl::vSEC_MOD_PORT_MISMATCH);
  analyze("module top(input a); child u(.a(a),.a(a)); endmodule module child(input a); endmodule\n",rtl::vSEC_MOD_PORT_MISMATCH);
  analyze("module top(input a); child u(.missing(a)); endmodule module child(input a); endmodule\n",rtl::vSEC_MOD_PORT_MISMATCH);
  analyze("module top; child u(.z()); endmodule module child(output z); assign z=1'b0; endmodule\n");
  analyze("module top; child u(); endmodule module child(W); parameter W=1; endmodule\n",rtl::vSEC_MOD_PORT_MISMATCH);
  analyze("module top; child u(); child u(); endmodule module child; endmodule\n",rtl::vMOD_INST_REDEFINE);
}

void test_array_ports_and_cleanup() {
  const std::string source="module c(input logic[7:0]a[2:1][5:6],output logic[7:0]q[7:8]);assign q[7]=a[2][5];endmodule "
      "module top;logic[7:0]a[4:5][0:1][9:8],q[0:1];c u(a[5],q);endmodule\n";
  for(int i=0;i<3;++i)analyze(source);
  for(int i=0;i<3;++i)analyze("module c(inout tri[7:0]a[2:1][5:6],input wire[7:0]b[7:8]);assign a[2][5]=b[7];endmodule "
      "module top;wire[7:0]a[4:5][0:1][9:8],b[0:1];c u(a[5],b);endmodule\n");
  analyze("module c(input logic[7:0]a[0:1]);endmodule module top;logic[7:0]a[0:1][0:1][0:1];c u(a[0]);endmodule\n",rtl::vSEC_MOD_PORT_MISMATCH);
  analyze("module c(input logic[7:0]a[0:1][0:1]);endmodule module top;logic[7:0]a[0:1][0:1];c u(a[0]);endmodule\n",rtl::vSEC_MOD_PORT_MISMATCH);
}

void test_report_fixes_cleanup() {
  const std::string source=R"(module leaf #(parameter W=8)(input var logic clk);
    logic[W-1:0] hidden=1;
    always_ff @(posedge clk)hidden<=hidden+1;
    endmodule module top;
    logic clk=0;integer a=0;leaf u(clk);leaf #(.W(16)) v(clk);
    task incr;begin a=a+1;end endtask
    initial begin incr;incr();a=u.hidden+v.hidden;assert(a)else a<=1;end
    endmodule)";
  for(int i=0;i<3;++i)analyze(source);
}

void test_properties_cleanup() {
  const std::string source=R"(module lane #(parameter ID=0)();
    logic clk=0,a=ID,b=1,rst=0;integer failures=0;
    property p;@(posedge clk) disable iff(rst) a |=> ##(ID+1) combined() ##0 $past(a)[*2];endproperty
    sequence combined();(pair[* (ID+1)]);endsequence:combined
    sequence pair;b ##0 $past(a);endsequence
    if(ID==1)begin:nested
      sequence pair;b[*2];endsequence
      assert property(@(posedge clk) a |-> pair());
    end
    check_p:assert property(p) else failures=failures+1;
    premise:assert property(@(posedge clk) disable iff(rst) combined() |=> pair)
      failures=failures+1;
    grouped_premise:assert property(@(posedge clk) (a[*2] ##0 pair) |-> b);
    always @(negedge clk) if($time>0) failures=failures+0;
    history:assert property(@(posedge clk) ($past(a,2,b)===$sampled(a))||$rose(a)||$fell(a)||$stable(a)||$changed(a))
      failures=$sampled(failures)+1;
    cover property(@(negedge clk) a |-> b) failures=failures+1;
    endmodule module top;lane #(0) a();lane #(1) b();endmodule)";
  for(int round=0;round<3;++round) {
    auto* top=analyze(source);
    for(auto name:{"a","b"}) {
      auto* symbol=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* instance=static_cast<rtl::VeriModInstance*>(symbol->instance());
      auto* module=static_cast<rtl::VeriMod*>(instance->hive());
      assert(module->scope()->value_within_module("failures"));
    }
  }
}

void test_strings_cleanup() {
  const std::string source=R"(module lane;
    typedef enum logic[3:0]{IDLE=0,LONG_NAME=5,EX=4'bx101} state_t;
    state_t state=LONG_NAME;string value;
    initial begin value=state.name();value={value,"suffix"};if(value.len()!=0)value=value.substr(0,2);end
    endmodule module top;lane a();lane b();endmodule)";
  for(int round=0;round<3;++round) {
    auto* top=analyze(source);
    for(auto name:{"a","b"}) {
      auto* symbol=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* instance=static_cast<rtl::VeriModInstance*>(symbol->instance());auto* module=static_cast<rtl::VeriMod*>(instance->hive());
      auto* type=static_cast<rtl::VeriVar*>(module->scope()->value_within_module("state_t"));
      assert(type->enum_names()==std::vector<std::string>({"IDLE","LONG_NAME","EX"}));
      assert(rtl::veri_string_value(module->scope()->value_within_module("value")));
    }
  }
}

void test_packages_cleanup() {
  const std::string source=R"(package p;
    parameter int W=8;
    typedef enum logic[1:0]{IDLE=0,RUN=1} state_t;
    typedef struct packed{logic[W-1:0] data;state_t state;} packet_t;
    integer shared=0;
    function automatic integer f(integer x);return x+W;endfunction
    endpackage
    module lane;import p::*;p::packet_t value;integer q;
      initial begin value='{default:0};q=f(W)+int'(RUN);shared=shared+1;end
    endmodule
    module top;lane a();lane b();endmodule)";
  for(int round=0;round<3;++round) {
    auto* top=analyze(source);auto* package=rtl::VeriParser::get_instance()->package("p");
    assert(package&&package->is_package()&&package->scope()!=top->scope());
    auto* exported=package->scope()->package_value("packet_t");assert(exported&&exported->tok_type()==vtTYPE);
    for(auto name:{"a","b"}) {
      auto* symbol=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* instance=static_cast<rtl::VeriModInstance*>(symbol->instance());
      auto* module=static_cast<rtl::VeriMod*>(instance->hive());
      assert(module->scope()->value_within_module("packet_t")==exported);
      assert(module->scope()->value_within_module("W")==package->scope()->package_value("W"));
      assert(module->scope()->value_within_module("shared")==package->scope()->package_value("shared"));
    }
  }
}

void test_reduction_with_cleanup() {
  const std::string source=R"(module lane #(parameter N=2)();
    logic signed[7:0] a[N],b[];integer item=99,q;
    function automatic integer f(input logic signed[7:0] data[]);
      return data.sum(x) with(int'(x)+1);
    endfunction
    initial begin b=new[N];q=a.sum with(int'(item))+b.xor(x) with(int'(x));q=f(a);end
    for(genvar i=0;i<2;i++)begin:g integer c[2];integer v;
      initial v=c.sum(x) with(c.sum(y) with(x*y+i));
    end
    endmodule module top;lane u();lane #(.N(3)) v();endmodule)";
  for(int i=0;i<3;++i)analyze(source);
}

void test_array_reductions_cleanup() {
  const std::string source=R"(module lane #(parameter N=2)();
    logic signed[7:0] a[N],b[];logic[7:0] q;
    function automatic integer f(input logic signed[7:0] data[]);return data.sum();endfunction
    initial begin b=new[N];q=a.sum()+a.product()+a.and()+a.or()+a.xor()+b.sum();q=f(a);end
    for(genvar i=0;i<2;i++)begin:g logic[129:0] c[2],v;initial v=c.xor();end
    endmodule module top;lane u();lane #(.N(3)) v();endmodule)";
  for(int i=0;i<3;++i)analyze(source);
}

void test_streaming_cleanup() {
  const std::string source=R"(module lane #(parameter N=4)();
    typedef logic[7:0] octet;
    localparam [23:0] C={<<8{16'h1234}};
    logic[7:0] a[2:0];logic[23:0] q;
    initial begin q={<<octet{a}};{<<N{a}}<=#2 C;end
    for(genvar i=0;i<2;i++)begin:g
      localparam [7:0] B={<<2{8'h12}};
      logic[7:0] v;initial v={<<N{B}};
    end
    endmodule module top;lane u();lane #(.N(3)) v();endmodule)";
  for(int i=0;i<3;++i)analyze(source);
}

void test_assignment_patterns_cleanup() {
  const std::string source=R"(module lane #(parameter N=2)();
    typedef struct packed {bit[3:0] a;logic[7:0] b;} t;
    integer a[2][2]='{default:'{default:N}};
    t s='{b:8'h80,a:4'hf};
    initial begin a<=#2 '{N{'{2{1}}}};s='{default:'1};end
    endmodule module top;lane u();lane #(.N(2)) v();endmodule)";
  for(int i=0;i<3;++i)analyze(source);
}

void test_array_copy_and_cleanup() {
  for(int i=0;i<3;++i)analyze("module top;logic[7:0]a[3:2][7:6],b[0:1][0:1];"
      "initial begin a[3][7]=1;b=a;b[0]=a[3];b<=a;b=#2 a;end endmodule\n");
  for(int i=0;i<3;++i)analyze("module top;function automatic integer f(input integer n);"
      "logic[7:0]a[3:2],b[0:1];begin a[3]=n;a[2]=n+1;b=a;return b[0]+b[1];end endfunction "
      "integer result;initial result=f(3);endmodule\n");
}

void test_parameters() {
  auto* mod=analyze(
    "module top #(parameter N=32)(input [N:0] a,output [N:0] z);\n"
    "child #(.W(N),.V(N+1)) u(.z(z),.a(a));\n"
    "child #(16,17) v(); child #(.W(64)) w(); child q(); endmodule\n"
    "module child #(parameter W=8,V=W+1)(input [V-1:0] a,output [V-1:0] z);\n"
    "localparam X=V+2; wire [X-1:0] t; assign z=a; endmodule\n");
  for(const auto& name : {"u","v","w","q"}) {
    auto* symbol=static_cast<rtl::VeriModInst*>(mod->scope()->value_same_level(name));
    assert(symbol);
    auto* hive=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(symbol->instance())->hive());
    const int expected=std::string(name)=="u" ? 33 : std::string(name)=="v" ? 17 : std::string(name)=="w" ? 65 : 9;
    auto* port=static_cast<rtl::VeriVar*>(hive->scope()->value_same_level("a"));
    auto* wire=static_cast<rtl::VeriVar*>(hive->scope()->value_same_level("t"));
    assert(port && port->dlen()==expected);
    assert(wire && wire->dlen()==expected+2);
    auto* param=static_cast<rtl::VeriParam*>(hive->scope()->value_same_level("W"));
    assert(param && param->get_val()->get_first_int()==expected-1);
  }
  for(const auto& args : {".missing(3)",".W(3),.W(4)","1,2,3",".X(3)"}) {
    analyze(std::string("module top; child #(")+args+") u(); endmodule\n"
      "module child #(parameter W=8,V=W+1)(); localparam X=1; endmodule\n",rtl::vSEC_MOD_PARAM_MISMATCH);
  }
}

void test_public_entry() {
  analyze("module top(input a,output z); assign z=missing; endmodule\n",rtl::vSEC_SYMBOL_NOT_FOUND);
  analyze("module top; endmodule\n",rtl::vMOD_TOP_MODULE_MISSING,"absent");
  auto* parser=rtl::VeriParser::get_instance();
  rtl::Src_mgr::get_instance()->set_src("module first; endmodule module second; endmodule\n"+std::string(1,'\0'));
  assert(parser->init()==rtl::OK);
  assert(parser->parse()==rtl::OK);
  assert(parser->has_err()==rtl::IS_FALSE);
  assert(parser->module("first") && parser->module("second"));
  parser->clean_up();
  parser->clean_up();
  parser->clear();
  parser->clear();
}

void test_hierarchical_procedural_loops() {
  for(int round=0;round<3;++round) {
    auto* mod=analyze(
      "module child #(parameter D=2); reg a; integer i;\n"
      "initial for(i=0;i<D;i=i+1) #1 a=~a;\n"
      "initial while(a) #1 a=~a;\n"
      "initial do #1 a=~a; while(a);\n"
      "initial repeat(D) #1 a=~a;\n"
      "initial forever #1 a=~a; endmodule\n"
      "module top; child #(2) x(); child #(3) y(); endmodule\n");
    for(const auto& name : {"x","y"}) {
      auto* symbol=static_cast<rtl::VeriModInst*>(mod->scope()->value_same_level(name));
      assert(symbol);
      auto* hive=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(symbol->instance())->hive());
      auto* parameter=static_cast<rtl::VeriParam*>(hive->scope()->value_same_level("D"));
      assert(parameter && parameter->get_val()->get_first_int()==(std::string(name)=="x"?2:3));
      unsigned seen=0;
      for(auto* item:static_cast<rtl::VeriModuleItemList*>(hive->item())->item_list()) {
        if(item->detail_type()!=vsSTMT_INIT)continue;
        auto* loop=static_cast<rtl::VeriLoopStmt*>(static_cast<rtl::VeriInitStmt*>(item)->stmt());
        assert(loop->detail_type()==vsSTMT_LOOP);
        assert(loop->kind()==static_cast<rtl::VeriLoopStmt::Kind>(seen));
        assert((loop->init()!=nullptr)==(loop->kind()==rtl::VeriLoopStmt::FOR));
        assert((loop->iter()!=nullptr)==(loop->kind()==rtl::VeriLoopStmt::FOR));
        assert((loop->judge()!=nullptr)==(loop->kind()!=rtl::VeriLoopStmt::FOREVER));
        for(auto* child:{loop->init(),loop->iter(),loop->judge(),loop->content()}) {
          if(child)assert(child->father()==loop);
        }
        ++seen;
      }
      assert(seen==5);
    }
  }
}

void test_primitive_groups() {
  for(int round=0;round<3;++round) {
    auto* mod=analyze(
      "module top(input a,b); wire x,y,z,n0,n1,t0,t1;\n"
      "and (x,a,b), named(y,a,b), (z,a,~b);\n"
      "not #(2,3) (n0,a), ni(n1,b);\n"
      "buf #2 (t0,a), (t1,b); endmodule\n");
    unsigned groups=0,instances=0,named=0;
    for(auto* item:static_cast<rtl::VeriModuleItemList*>(mod->item())->item_list()) {
      if(item->detail_type()!=vsINST_GATE_INSTANTIATION)continue;
      auto* group=static_cast<rtl::VeriGateInstantiation*>(item);
      assert(group->gate_list().size()==(groups==0?3u:2u));
      for(auto* node:group->gate_list()) {
        auto* inst=static_cast<rtl::VeriGateInstance*>(node);
        assert(inst->father()==group && inst->arg()->father()==inst);
        assert(inst->arg()->detail_type()==veEXP_MULTI);
        assert(static_cast<rtl::VeriMultiExp*>(inst->arg())->exp().size()==(groups==0?3u:2u));
        ++instances; if(inst->inst_name())++named;
      }
      ++groups;
    }
    assert(groups==3 && instances==7 && named==2);
  }
}

void test_dump_targets() {
  const std::string separator(1,'\x1f');
  for(int round=0;round<3;++round) {
    auto* mod=analyze(
      "module leaf; wire q; endmodule\n"
      "module top; parameter D=2; reg \\a.b ; leaf \\u.dot ();\n"
      "initial begin $dumpvars(D,top,top.\\u.dot .q,\\a.b );\n"
      "$dumpvars(); $dumpon(); $dumpoff(); $dumpall(); end endmodule\n");
    unsigned checked=0;
    for(auto* item:static_cast<rtl::VeriModuleItemList*>(mod->item())->item_list()) {
      if(item->detail_type()!=vsSTMT_INIT)continue;
      auto* block=static_cast<rtl::VeriSeqBlock*>(static_cast<rtl::VeriInitStmt*>(item)->stmt());
      auto& stmts=static_cast<rtl::VeriStmtList*>(block->stmt_list())->stmt_list();
      assert(stmts.size()==5);
      auto* call=static_cast<rtl::VeriSysCallerStmt*>(stmts.front());
      assert(call->caller()=="$dumpvars" && call->arg()->father()==call);
      auto& args=static_cast<rtl::VeriMultiExp*>(call->arg())->exp();
      assert(args.size()==4);
      auto arg=args.begin();
      auto* depth=static_cast<rtl::VeriPrimaryExp*>(*arg++);
      assert(depth->pri_type()==veVAR && depth->var()->tok_type()==vtPARAM);
      const std::vector<std::string> expected={separator+"top",separator+"top"+separator+"\\u.dot"+separator+"q",separator+"\\a.b"};
      for(const auto& value:expected) {
        auto* target=static_cast<rtl::VeriPrimaryExp*>(*arg++);
        assert(target->pri_type()==veSTR && target->str()==value && !target->var());
      }
      ++checked;
    }
    assert(checked==1);
  }
}

void test_declarations() {
  // Repeated parsing also checks that recycled node IDs cannot collide
  // with newly allocated AST and constant-result nodes.
  for(int round=0;round<3;++round) {
    auto* mod=analyze(
      "module top #(parameter W=64)(input [W-1:0] a, output [W-1:0] z);\n"
      "wire [W-1:0] named_wire = 17; integer named_integer = 19;\n"
      "assign z=a; endmodule\n");
    for(const auto& name : {"a","z","named_wire"}) {
      auto* node=mod->scope()->value_same_level(name);
      assert(node && node->tok_type()==vtVAR);
      auto* var=static_cast<rtl::VeriVar*>(node);
      assert(var->name()==name);
      assert(var->dstart()==63 && var->dend()==0 && var->dlen()==64);
      if(std::string(name)=="named_wire") {
        auto* value=var->get_one_num({},rtl::IS_TRUE,0,0);
        assert(value && value->get_first_int()==17 && value->bits()==64);
      }
    }
    auto* node=mod->scope()->value_same_level("named_integer");
    assert(node && node->tok_type()==vtINT);
    auto* integer=static_cast<rtl::VeriInt*>(node);
    assert(integer->name()=="named_integer");
    auto* value=integer->get_one_num({},rtl::IS_TRUE,0,0);
    assert(value && value->get_first_int()==19);
  }
}

void test_integer_block_scopes() {
  for(int round=0;round<3;++round) {
    auto* mod=analyze(
      "module top; integer value=10; integer mem[5:2]; initial begin "
      "integer value=-3; begin integer value=7; value=value+1; end "
      "value=value+1; end initial begin integer value=100; value=value-1; end endmodule\n");
    auto* root=mod->scope()->value_same_level("value");
    auto* mem=static_cast<rtl::VeriInt*>(mod->scope()->value_same_level("mem"));
    int first,last,count;mem->get_range(1,first,last,count);
    assert(first==5&&last==2&&count==4);
    std::vector<rtl::VeriSeqBlock*> blocks;
    for(auto* item:static_cast<rtl::VeriModuleItemList*>(mod->item())->item_list())
      if(item->detail_type()==vsSTMT_INIT)blocks.push_back(static_cast<rtl::VeriSeqBlock*>(static_cast<rtl::VeriInitStmt*>(item)->stmt()));
    assert(blocks.size()==2);
    auto* a=blocks[0]->scope()->value_same_level("value");
    auto* b=blocks[1]->scope()->value_same_level("value");
    assert(a&&b&&a!=b&&a!=root&&b!=root);
    auto& stmts=static_cast<rtl::VeriStmtList*>(blocks[0]->stmt_list())->stmt_list();
    auto* inner=static_cast<rtl::VeriSeqBlock*>(stmts.front());
    auto* c=inner->scope()->value_same_level("value");
    assert(c&&c!=a&&c!=b&&c!=root);
    auto* assign=static_cast<rtl::VeriBlockStmt*>(stmts.back());
    assert(static_cast<rtl::VeriPrimaryExp*>(assign->lval())->var()==a);
  }
  analyze("module top; initial begin integer private_value; end initial private_value=1; endmodule\n",rtl::vSEC_SYMBOL_NOT_FOUND);
}

void test_reduction_parity() {
  for(int width:{1,8,31,32,33,65,80,130})for(int ones:{0,1,2,3})for(int unknown:{0,1,2}) {
    std::string bits(size_t(width),'0');int count=0;
    for(int i=0;i<ones&&i<width;++i){bits[size_t(i)]='1';++count;}
    if(unknown)bits.back()=unknown==1?'x':'z';
    std::string literal=std::to_string(width)+"'b"+bits;
    for(int op:{vtUXOR,vtUXNOR}) {
      rtl::VeriNum value(1,1,1,nullptr);assert(value.parse(literal.c_str(),literal.size())==rtl::OK);
      assert(value.unary_operation(op)==rtl::OK);
      assert(value.bits()==1&&value.get_certain_bit(0)==(unknown?VX:((count&1)^(op==vtUXNOR))));
    }
  }
}

void test_subroutine_types() {
  for(int round=0;round<3;++round) {
    auto* mod=analyze("module top; function integer f(input integer a);begin if(0)f=9;else f=a;end endfunction "
                      "function bit_result(input en);begin bit_result=en;end endfunction "
                      "task t;begin end endtask integer q;initial begin q=1?f(3):f(4);t();end endmodule\n");
    auto* f=static_cast<rtl::VeriFunc*>(mod->scope()->value_same_level("f"));
    assert(f->dstart()==31&&f->dend()==0&&f->dlen()==32);
    auto* decl=f->func();auto* ports=static_cast<rtl::VeriFuncPortList*>(decl->port_list());
    auto* port=static_cast<rtl::VeriTfDecl*>(ports->func_port().front());
    auto* symbol=static_cast<rtl::VeriTfVar*>(static_cast<rtl::VeriPrimaryExp*>(port->port_ids().front())->var());
    assert(symbol->dlen()==32&&symbol->dend()==0&&symbol->is_signed()==rtl::IS_TRUE);
    auto* scalar=static_cast<rtl::VeriFunc*>(mod->scope()->value_same_level("bit_result"));
    assert(scalar->dlen()==1&&scalar->dstart()==0&&scalar->dend()==0);
  }
}

void test_action_cloning() {
  for(int round=0;round<3;++round) {
    auto* top=analyze("module child #(parameter N=3);integer a=1;initial begin a+=N;a>>>=1;end "
       "function integer f(input [7:0] x);begin if(x[0])return x;f=2;return;end endfunction "
       "task t;begin return;end endtask initial begin a=f(1);t();end endmodule "
       "module top;child #(3) u();child #(7) v();endmodule\n");
    std::vector<rtl::VeriNode*> variables;
    for(const auto& name:{"u","v"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* a=mod->scope()->value_same_level("a");variables.push_back(a);
      rtl::VeriSeqBlock* block=nullptr;
      for(auto* item:static_cast<rtl::VeriModuleItemList*>(mod->item())->item_list())
        if(item->detail_type()==vsSTMT_INIT){block=static_cast<rtl::VeriSeqBlock*>(static_cast<rtl::VeriInitStmt*>(item)->stmt());break;}
      auto& actions=static_cast<rtl::VeriStmtList*>(block->stmt_list())->stmt_list();
      assert(actions.size()==2);
      auto* first=static_cast<rtl::VeriActionStmt*>(actions.front());
      auto* last=static_cast<rtl::VeriActionStmt*>(actions.back());
      assert(first->detail_type()==vsSTMT_COMPOUND&&first->op()==vtBADD&&last->op()==vtBARS);
      assert(first->target()->father()==first&&first->value()->father()==first);
      assert(static_cast<rtl::VeriPrimaryExp*>(first->target())->var()==a);
      assert(static_cast<rtl::VeriPrimaryExp*>(first->value())->var()->tok_type()==vtPARAM);
    }
    assert(variables[0]!=variables[1]);
  }
}

void test_integral_type_cloning() {
  for(int round=0;round<3;++round) {
    auto* top=analyze("module child #(parameter N=3)(input integer x,output time q);"
      "integer unsigned a=1;integer signed b=-1;time t;"
      "function time f(input time value);begin return value+N;end endfunction "
      "function integer unsigned u(input integer unsigned value);begin return value/3;end endfunction "
      "endmodule module top;wire[63:0]q,r;child #(3) u(1,q);child #(7) v(2,r);endmodule\n");
    std::vector<rtl::VeriNode*> variables;
    for(const auto& name:{"u","v"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* a=static_cast<rtl::VeriVar*>(mod->scope()->value_same_level("a"));variables.push_back(a);
      auto* b=static_cast<rtl::VeriVar*>(mod->scope()->value_same_level("b"));
      auto* t=static_cast<rtl::VeriVar*>(mod->scope()->value_same_level("t"));
      auto* x=static_cast<rtl::VeriVar*>(mod->scope()->value_same_level("x"));
      auto* q=static_cast<rtl::VeriVar*>(mod->scope()->value_same_level("q"));
      assert(a->dlen()==32&&a->is_signed()==rtl::IS_FALSE);
      assert(b->dlen()==32&&b->is_signed()==rtl::IS_TRUE);
      assert(t->dlen()==64&&t->is_signed()==rtl::IS_FALSE);
      assert(x->dlen()==32&&x->is_signed()==rtl::IS_TRUE&&x->inout()==vpIN);
      assert(q->dlen()==64&&q->inout()==vpOUT);
      auto* f=static_cast<rtl::VeriFunc*>(mod->scope()->value_same_level("f"));
      auto* u=static_cast<rtl::VeriFunc*>(mod->scope()->value_same_level("u"));
      assert(f->dlen()==64&&f->func()->is_signed()==rtl::IS_FALSE);
      assert(f->func()->integral_result()&&f->func()->is_int()==rtl::IS_FALSE);
      assert(u->dlen()==32&&u->func()->is_signed()==rtl::IS_FALSE);
      auto* ports=static_cast<rtl::VeriFuncPortList*>(f->func()->port_list());
      auto* port=static_cast<rtl::VeriTfDecl*>(ports->func_port().front());
      auto* formal=static_cast<rtl::VeriTfVar*>(static_cast<rtl::VeriPrimaryExp*>(port->port_ids().front())->var());
      assert(formal->dlen()==64&&formal->is_signed()==rtl::IS_FALSE);
    }
    assert(variables[0]!=variables[1]);
  }
}

void test_two_state_type_cloning() {
  for(int round=0;round<3;++round) {
    auto* top=analyze("module child #(parameter N=3)(input int x,output longint q);"
      "bit[79:0] a;byte b;shortint c;int d;longint unsigned e;integer old;"
      "function bit[79:0] f(input bit[79:0] value);begin return value;end endfunction "
      "function byte g(input shortint value);begin return value+N;end endfunction "
      "endmodule module top;wire[63:0]q,r;child #(3) u(1,q);child #(7) v(2,r);endmodule\n");
    std::vector<rtl::VeriNode*> variables;
    for(const auto& name:{"u","v"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      const char* names[]={"a","b","c","d","e","x","q"};
      const int widths[]={80,8,16,32,64,32,64};
      for(int i=0;i<7;++i){auto* v=static_cast<rtl::VeriVar*>(mod->scope()->value_same_level(names[i]));
        assert(v&&v->dlen()==widths[i]&&veri_two_state(v->net_type()));
        assert(v->is_signed()==((i==0||i==4)?rtl::IS_FALSE:rtl::IS_TRUE));
        if(i==0)variables.push_back(v);
      }
      assert(mod->scope()->value_same_level("old")->tok_type()==vtINT);
      auto* f=static_cast<rtl::VeriFunc*>(mod->scope()->value_same_level("f"));
      auto* g=static_cast<rtl::VeriFunc*>(mod->scope()->value_same_level("g"));
      assert(f->dlen()==80&&f->func()->result_type()==vvBIT&&!f->func()->integral_result());
      assert(g->dlen()==8&&g->func()->result_type()==vvBYTE&&g->func()->integral_result());
      auto* ports=static_cast<rtl::VeriFuncPortList*>(g->func()->port_list());
      auto* port=static_cast<rtl::VeriTfDecl*>(ports->func_port().front());
      auto* formal=static_cast<rtl::VeriTfVar*>(static_cast<rtl::VeriPrimaryExp*>(port->port_ids().front())->var());
      assert(formal->dlen()==16&&formal->net_type()==vvSHORTINT&&formal->is_signed()==rtl::IS_TRUE);
    }
    assert(variables[0]!=variables[1]);
  }
}

void test_file_function_cloning() {
  for(int round=0;round<3;++round) {
    auto* top=analyze("module child #(parameter N=3);integer fd,n;reg[127:0]line;initial begin "
      "fd=$fopen(\"file.txt\",\"w+\");n=$fgetc(fd);n=$ungetc(65,fd);n=$feof(fd);"
      "n=$fgets(line,fd);n=$ftell(fd);n=$fseek(fd,0,0);n=$rewind(fd);"
      "void'($fgetc(fd));$fflush(fd);$fclose(fd);end endmodule "
      "module top;child #(3) u();child #(7) v();endmodule\n");
    std::vector<rtl::VeriNode*> variables;
    for(const auto& name:{"u","v"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* target=mod->scope()->value_same_level("line");variables.push_back(target);
      rtl::VeriSeqBlock* block=nullptr;
      for(auto* item:static_cast<rtl::VeriModuleItemList*>(mod->item())->item_list())
        if(item->detail_type()==vsSTMT_INIT){block=static_cast<rtl::VeriSeqBlock*>(static_cast<rtl::VeriInitStmt*>(item)->stmt());break;}
      int position=0;
      for(auto* action:static_cast<rtl::VeriStmtList*>(block->stmt_list())->stmt_list()) {
        if(position>=8)break;
        auto* value=static_cast<rtl::VeriBlockStmt*>(action)->rval();assert(value->detail_type()==veEXP_UNA&&value->father()==action);
        auto* call=static_cast<rtl::VeriUnaryExp*>(value);
        assert(call->op()==vtSYS_FOPEN+position&&rtl::veri_bit_width(value)==32&&call->is_signed()==rtl::IS_TRUE);
        assert(!call->calc_value()&&!rtl::veri_elaboration_constant(value)&&call->exp_child()->father()==call);
        if(position==4)assert(static_cast<rtl::VeriPrimaryExp*>(rtl::veri_system_arguments(call->exp_child())[0])->var()==target);
        ++position;
      }
      assert(position==8);
    }
    assert(variables[0]!=variables[1]);
  }
}

void test_scan_function_cloning() {
  for(int round=0;round<3;++round) {
    auto* top=analyze("module child #(parameter N=3);integer fd,n;initial begin "
      "n=$sscanf(\"12\",\"%d\",n);n=$fscanf(fd,\"%d\",n);"
      "void'($sscanf(\"1\",\"%d\",n));$fscanf(fd,\"%d\",n);end endmodule "
      "module top;child #(3) u();child #(7) v();endmodule\n");
    std::vector<rtl::VeriNode*> variables;
    for(const auto& name:{"u","v"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* target=mod->scope()->value_same_level("n");variables.push_back(target);
      rtl::VeriSeqBlock* block=nullptr;
      for(auto* item:static_cast<rtl::VeriModuleItemList*>(mod->item())->item_list())
        if(item->detail_type()==vsSTMT_INIT){block=static_cast<rtl::VeriSeqBlock*>(static_cast<rtl::VeriInitStmt*>(item)->stmt());break;}
      int position=0;
      for(auto* action:static_cast<rtl::VeriStmtList*>(block->stmt_list())->stmt_list()) {
        if(position>=2)break;
        auto* value=static_cast<rtl::VeriBlockStmt*>(action)->rval();assert(value->detail_type()==veEXP_UNA&&value->father()==action);
        auto* call=static_cast<rtl::VeriUnaryExp*>(value);
        assert(call->op()==vtSYS_SSCANF+position&&rtl::veri_bit_width(value)==32&&call->is_signed()==rtl::IS_TRUE);
        assert(!call->calc_value()&&!rtl::veri_elaboration_constant(value)&&call->exp_child()->father()==call);
        assert(static_cast<rtl::VeriPrimaryExp*>(rtl::veri_system_arguments(call->exp_child())[2])->var()==target);
        ++position;
      }
      assert(position==2);
    }
    assert(variables[0]!=variables[1]);
  }
}

void test_testbench_function_cloning() {
  for(int round=0;round<3;++round) {
    auto* top=analyze("module child #(parameter N=3);integer n;string s;initial begin "
      "n=$test$plusargs(\"mode\");n=$value$plusargs(\"n=%d\",n);s=$sformatf(\"%m:%0d\",N);"
      "void'($value$plusargs(\"n=%d\",n));$sformat(s,\"%0d\",n);end endmodule "
      "module top;child #(3) u();child #(7) v();endmodule\n");
    std::vector<rtl::VeriNode*> variables;
    for(const auto& name:{"u","v"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* target=mod->scope()->value_same_level("n");variables.push_back(target);
      rtl::VeriSeqBlock* block=nullptr;
      for(auto* item:static_cast<rtl::VeriModuleItemList*>(mod->item())->item_list())
        if(item->detail_type()==vsSTMT_INIT){block=static_cast<rtl::VeriSeqBlock*>(static_cast<rtl::VeriInitStmt*>(item)->stmt());break;}
      int position=0;
      for(auto* action:static_cast<rtl::VeriStmtList*>(block->stmt_list())->stmt_list()) {
        if(position>=3)break;
        auto* value=static_cast<rtl::VeriBlockStmt*>(action)->rval();assert(value->detail_type()==veEXP_UNA&&value->father()==action);
        auto* call=static_cast<rtl::VeriUnaryExp*>(value);
        const int ops[]={vtSYS_TEST_PLUSARGS,vtSYS_VALUE_PLUSARGS,vtSYS_SFORMATF};assert(call->op()==ops[position]);
        assert(!call->calc_value()&&!rtl::veri_elaboration_constant(value));assert(call->exp_child()->father()==call);
        if(position==2)assert(rtl::veri_dynamic_string_value(value));
        else assert(rtl::veri_bit_width(value)==32&&call->is_signed()==rtl::IS_TRUE);
        if(position==1)assert(static_cast<rtl::VeriPrimaryExp*>(rtl::veri_system_arguments(call->exp_child())[1])->var()==target);
        ++position;
      }
      assert(position==3);
    }
    assert(variables[0]!=variables[1]);
  }
}

void test_random_expression_cloning() {
  for(int round=0;round<3;++round) {
    auto* top=analyze("module child #(parameter N=3);integer seed=1;reg[31:0]r;initial begin "
      "r=$random;r=$random(seed);r=$urandom();r=$urandom(seed);r=$urandom_range(9,2);end endmodule "
      "module top;child #(3) u();child #(7) v();endmodule\n");
    std::vector<rtl::VeriNode*> variables;
    for(const auto& name:{"u","v"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* seed=mod->scope()->value_same_level("seed");variables.push_back(seed);
      rtl::VeriSeqBlock* block=nullptr;
      for(auto* item:static_cast<rtl::VeriModuleItemList*>(mod->item())->item_list())
        if(item->detail_type()==vsSTMT_INIT){block=static_cast<rtl::VeriSeqBlock*>(static_cast<rtl::VeriInitStmt*>(item)->stmt());break;}
      const int wanted[]={vtSYS_RANDOM,vtSYS_RANDOM_SEEDED,vtSYS_URANDOM,vtSYS_URANDOM_SEEDED,vtSYS_URANDOM_RANGE};int position=0;
      for(auto* action:static_cast<rtl::VeriStmtList*>(block->stmt_list())->stmt_list()) {
        auto* value=static_cast<rtl::VeriBlockStmt*>(action)->rval();assert(value->detail_type()==veEXP_UNA&&value->father()==action);
        auto* expression=static_cast<rtl::VeriUnaryExp*>(value);int op=expression->op();assert(op==wanted[position++]);
        assert(!expression->calc_value()&&!rtl::veri_elaboration_constant(value)&&rtl::veri_bit_width(value)==32);
        assert(expression->is_signed()==(op==vtSYS_RANDOM||op==vtSYS_RANDOM_SEEDED?rtl::IS_TRUE:rtl::IS_FALSE));
        assert(expression->exp_child()->father()==expression);
        if(op==vtSYS_RANDOM_SEEDED||op==vtSYS_URANDOM_SEEDED) {
          auto args=rtl::veri_system_arguments(expression->exp_child());assert(args.size()==1);
          assert(static_cast<rtl::VeriPrimaryExp*>(args.front())->var()==seed);
        }
      }
      assert(position==5);
    }
    assert(variables[0]!=variables[1]);
  }
}

void test_increment_expression_cloning() {
  for(int round=0;round<3;++round) {
    auto* top=analyze("module child #(parameter N=3);integer a=1,b;initial begin "
      "b=++a;b=--a;b=a++;b=a--;end endmodule "
      "module top;child #(3) u();child #(7) v();endmodule\n");
    std::vector<rtl::VeriNode*> variables;
    for(const auto& name:{"u","v"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* a=mod->scope()->value_same_level("a");variables.push_back(a);
      rtl::VeriSeqBlock* block=nullptr;
      for(auto* item:static_cast<rtl::VeriModuleItemList*>(mod->item())->item_list())
        if(item->detail_type()==vsSTMT_INIT){block=static_cast<rtl::VeriSeqBlock*>(static_cast<rtl::VeriInitStmt*>(item)->stmt());break;}
      auto& actions=static_cast<rtl::VeriStmtList*>(block->stmt_list())->stmt_list();
      assert(actions.size()==4);int position=0;
      const int wanted[]={vtUPREINC,vtUPREDEC,vtUPOSTINC,vtUPOSTDEC};
      for(auto* action:actions) {
        auto* value=static_cast<rtl::VeriBlockStmt*>(action)->rval();
        assert(value->detail_type()==veEXP_UNA&&value->father()==action);
        auto* expression=static_cast<rtl::VeriUnaryExp*>(value);
        assert(expression->op()==wanted[position++]);
        assert(expression->exp_child()->father()==expression);
        assert(static_cast<rtl::VeriPrimaryExp*>(expression->exp_child())->var()==a);
      }
    }
    assert(variables[0]!=variables[1]);
  }
}

void test_loop_control_cloning() {
  for(int round=0;round<3;++round) {
    auto* top=analyze(
      "module child #(parameter N=3); integer seed=1; initial begin "
      "for(int i=seed;i<N;i++)begin if(i==1)continue; if(i==2)break; end end endmodule "
      "module top; child #(3) a(); child #(4) b(); endmodule\n");
    std::vector<rtl::VeriNode*> counters;
    for(const auto& name:{"a","b"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto& items=static_cast<rtl::VeriModuleItemList*>(mod->item())->item_list();
      auto* initial=static_cast<rtl::VeriInitStmt*>(items.back());
      auto* outer=static_cast<rtl::VeriSeqBlock*>(initial->stmt());
      auto* local=static_cast<rtl::VeriSeqBlock*>(static_cast<rtl::VeriStmtList*>(outer->stmt_list())->stmt_list().front());
      auto* counter=local->scope()->value_same_level("i");
      assert(counter&&counter->tok_type()==vtVAR);
      assert(static_cast<rtl::VeriVar*>(counter)->net_type()==vvINT2);counters.push_back(counter);
      assert(!mod->scope()->value_same_level("i"));
      auto* loop=static_cast<rtl::VeriLoopStmt*>(static_cast<rtl::VeriStmtList*>(local->stmt_list())->stmt_list().front());
      auto* update=static_cast<rtl::VeriUpdateStmt*>(static_cast<rtl::VeriStmtList*>(loop->iter())->stmt_list().front());
      assert(update->detail_type()==vsSTMT_UPDATE&&update->delta()==1);
      assert(update->target()->father()==update);
      assert(static_cast<rtl::VeriPrimaryExp*>(update->target())->var()==counter);
      auto* body=static_cast<rtl::VeriSeqBlock*>(loop->content());
      auto& branches=static_cast<rtl::VeriStmtList*>(body->stmt_list())->stmt_list();
      auto* continuing=static_cast<rtl::VeriCondStmt*>(branches.front())->if_stmt();
      auto* breaking=static_cast<rtl::VeriCondStmt*>(branches.back())->if_stmt();
      assert(continuing->detail_type()==vsSTMT_CONTINUE&&breaking->detail_type()==vsSTMT_BREAK);
    }
    assert(counters[0]!=counters[1]);
  }
}

void test_systemverilog_sized_casts() {
  // Numeric and parameterized sized casts must survive both syntax parsing
  // and the second semantic traversal without turning the apostrophe into a
  // stray token or corrupting the range/port symbol table.
  analyze(
    "module top #(parameter W=32)(input [W-1:0] a, output [W-1:0] z);\n"
    "assign z = 32'(a + 1'b0);\n"
    "endmodule\n");
  analyze(
    "module top #(parameter W=32)(input [W-1:0] a, output [W-1:0] z);\n"
    "assign z = W'(a);\n"
    "endmodule\n");
  analyze(
    "module top #(parameter W=32)(input [W-1:0] a, output [W-1:0] z);\n"
    "assign z = logic'(a);\n"
    "endmodule\n");
  analyze(
    "module top #(parameter W=32)(input [W-1:0] a, output [W-1:0] z);\n"
    "assign z = signed'(a);\n"
    "endmodule\n");
}

void test_relational_constants() {
  // Host integer ordering is an independent oracle for the loop predicates.
  for(bool sign : {false,true})for(int width : {8,32,65}) {
    for(int a : {-3,-1,0,1,3,127})for(int b : {-3,-1,0,1,3,127}) {
      if(!sign && (a<0 || b<0))continue;
      for(int op : {vtBLT,vtBGT,vtBLE,vtBGE}) {
        rtl::VeriNum left(1,1,1,nullptr),right(2,1,1,nullptr);
        auto literal=[&](int value) {
          std::string bits;
          for(int i=width-1;i>=0;--i)bits+=(i>=32?(value<0):((uint32_t(value)>>i)&1))?'1':'0';
          return std::to_string(width)+(sign?"'sb":"'b")+bits;
        };
        auto la=literal(a),lb=literal(b);
        assert(left.parse(la.c_str(),int(la.size()))==rtl::OK);
        assert(right.parse(lb.c_str(),int(lb.size()))==rtl::OK);
        const bool expected=op==vtBLT?a<b:op==vtBGT?a>b:op==vtBLE?a<=b:a>=b;
        assert(left.binary_operation(op,&right)==rtl::OK);
        assert(left.bits()==1 && left.is_signed()==rtl::IS_FALSE);
        if(left.get_certain_bit(0)!=(expected?1:0))std::cerr<<"relational mismatch width="<<width<<" signed="<<sign<<" a="<<a<<" b="<<b<<" op="<<op<<"\n";
        assert(left.get_certain_bit(0)==(expected?1:0));
      }
    }
  }
  for(int op : {vtBLT,vtBGT,vtBLE,vtBGE}) {
    rtl::VeriNum left(1,1,1,nullptr),right(2,1,1,nullptr);
    assert(left.parse("4'bx001",7)==rtl::OK);
    assert(right.parse("8'd0",4)==rtl::OK);
    assert(left.binary_operation(op,&right)==rtl::OK);
    assert(left.bits()==1 && left.get_certain_bit(0)==VX);
  }
  // Unsigned context zero-extends a narrower signed operand.
  rtl::VeriNum left(1,1,1,nullptr),right(2,1,1,nullptr);
  assert(left.parse("4'shf",5)==rtl::OK);
  assert(right.parse("8'd16",5)==rtl::OK);
  assert(left.binary_operation(vtBLT,&right)==rtl::OK);
  assert(left.get_certain_bit(0)==1);
}

void test_word_boundaries() {
  for(int width : {1,31,32,33,63,64,65,256}) {
    rtl::VeriNum number(1,1,1,nullptr);
    number.init_val(rtl::IS_FALSE,width);
    assert(number.unary_operation(vtUNEG)==rtl::OK);
    assert(number.bits()==width);
    for(int k=0;k<width;++k) assert(number.get_certain_bit(k)==1);
    assert(number.unary_operation(vtUNEG)==rtl::OK);
    for(int k=0;k<width;++k) assert(number.get_certain_bit(k)==0);
    assert(number.get_certain_bit(-1)==0);
    assert(number.get_certain_bit(width)==0);
    for(bool negative : {false,true}) {
      number.init_val(rtl::IS_TRUE,width);
      if(negative) number.unary_operation(vtUNEG);
      number.truncate_assign(width+37);
      for(int k=0;k<width+37;++k) assert(number.get_certain_bit(k)==(negative?1:0));
    }
  }
}
void test_padded_negative_constants() {
  for(int width : {4,31,32,33,64,65,80,130})for(const char* radix : {"sd3","sh3","sb11"}) {
    rtl::VeriNum value(0,1,1,nullptr);
    auto text=std::to_string(width)+"'"+radix;
    assert(value.parse(text.c_str(),text.size())==rtl::OK);
    assert(value.unary_operation(vtUSUB)==rtl::OK);
    for(int bit=0;bit<width;++bit)assert(value.get_certain_bit(bit)==(bit==1?0:1));
  }
  rtl::VeriNum value(0,1,1,nullptr);std::string text="65'sbx01";
  assert(value.parse(text.c_str(),text.size())==rtl::OK);
  assert(value.unary_operation(vtUSUB)==rtl::OK);
  for(int bit=0;bit<65;++bit)assert(value.get_certain_bit(bit)==VX);
}

void test_typed_parameter_cloning() {
  for(int round=0;round<3;++round) {
    auto* mod=analyze(
      "module child #(parameter int P=32'hxz000003, Q=P+1, parameter byte B=-1,"
      "parameter longint L=32'hffffffff+1,parameter bit[79:0] MASK='1)();"
      "localparam shortint S=-17;localparam time T=64'hxz123456789abcde;"
      "localparam logic[7:0] MUX=1'bx ? 8'hf0 : 8'hf1;endmodule\n"
      "module top; child u();child #(.P(32'hxz000007),.B(8'hxz),.L(32'hffffffff+2))v();endmodule\n");
    for(const auto& instance:{"u","v"}) {
      auto* symbol=static_cast<rtl::VeriModInst*>(mod->scope()->value_same_level(instance));
      auto* hive=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(symbol->instance())->hive());
      const bool changed=std::string(instance)=="v";
      auto param=[&](const char* name)->rtl::VeriParam*{auto* n=hive->scope()->value_same_level(name);assert(n&&n->tok_type()==vtPARAM);return static_cast<rtl::VeriParam*>(n);};
      for(const auto& spec:std::vector<std::pair<std::string,int>>{{"P",32},{"Q",32},{"B",8},{"L",64},{"MASK",80},{"S",16},{"T",64},{"MUX",8}}) {
        auto* p=param(spec.first.c_str());assert(p->dlen()==spec.second&&p->get_val()->bits()==spec.second);
        auto* d=static_cast<rtl::VeriParamDecl*>(p->father());assert(d->typed());
        if(veri_two_state(d->data_type()))for(int bit=0;bit<p->dlen();++bit)assert(p->get_val()->get_certain_bit(bit)<VX);
      }
      assert(param("P")->get_val()->get_first_int()==(changed?7:3));
      assert(param("Q")->get_val()->get_first_int()==(changed?8:4));
      assert(param("P")->is_signed()==rtl::IS_TRUE);
      assert(param("B")->get_val()->get_first_int()==(changed?0:255));
      assert(param("L")->get_val()->get_certain_bit(32)==1);
      assert(param("L")->get_val()->get_certain_bit(0)==(changed?1:0));
      for(int bit=0;bit<80;++bit)assert(param("MASK")->get_val()->get_certain_bit(bit)==1);
      assert(param("T")->get_val()->get_certain_bit(63)==VX);
      assert(param("T")->get_val()->get_certain_bit(59)==VZ);
      assert(param("MUX")->get_val()->get_certain_bit(0)==VX);
    }
  }
}
void test_constant_division_shifts() {
  auto parse=[](rtl::VeriNum& n,const std::string& text){assert(n.parse(text.c_str(),text.size())==rtl::OK);};
  auto literal=[](int width,int64_t value,bool sign) {
    std::string bits;for(int bit=width-1;bit>=0;--bit)bits+=(bit>=64?(value<0):((uint64_t(value)>>bit)&1))?'1':'0';
    return std::to_string(width)+(sign?"'sb":"'b")+bits;
  };
  for(int width:{8,32,64,65,130})for(bool sign:{false,true})
    for(int a:{-127,-17,-1,0,1,17,127})for(int b:{-7,-1,0,1,7}) {
      if(!sign&&(a<0||b<0))continue;
      for(int op:{vtBDIV,vtBMOD}) {
        rtl::VeriNum left(0,1,1,nullptr),right(0,1,1,nullptr);
        parse(left,literal(width,a,sign));parse(right,literal(width,b,sign));
        assert(left.binary_operation(op,&right)==rtl::OK);assert(left.bits()==width);
        const int64_t expected=b==0?0:op==vtBDIV?a/b:a%b;
        for(int bit=0;bit<width;++bit)assert(left.get_certain_bit(bit)==(b==0?VX:bit>=64?(expected<0):int((uint64_t(expected)>>bit)&1)));
      }
    }
  for(int width:{8,32,64,65,130})for(int amount:{0,1,31,32,63,64,129,130,255})
    for(int op:{vtBLLS,vtBLRS,vtBARS,vtBALS}) {
      rtl::VeriNum left(0,1,1,nullptr),right(0,1,1,nullptr);
      parse(left,literal(width,-17,true));parse(right,std::string("64'd")+std::to_string(amount));
      assert(left.binary_operation(op,&right)==rtl::OK);assert(left.bits()==width);
      for(int bit=0;bit<width;++bit) {
        const bool shift_left=op==vtBLLS||op==vtBALS;
        const int source=shift_left?bit-amount:bit+amount;
        const int expected=source<0?0:source>=width?(op==vtBARS?1:0):source>=64?1:int((uint64_t(-17)>>source)&1);
        assert(left.get_certain_bit(bit)==expected);
      }
    }
  for(const auto& text:{"1'hf","1'o7","1'b111","1'd7"}) {
    rtl::VeriNum n(0,1,1,nullptr);parse(n,text);assert(n.bits()==1&&n.get_certain_bit(0)==1);
  }
  for(int op:{vtBDIV,vtBMOD,vtBLLS,vtBLRS,vtBARS,vtBALS}) {
    rtl::VeriNum left(0,1,1,nullptr),right(0,1,1,nullptr);
    parse(left,"65'shffffffffffffffff");parse(right,"80'hx");
    assert(left.binary_operation(op,&right)==rtl::OK);
    for(int bit=0;bit<left.bits();++bit)assert(left.get_certain_bit(bit)==VX);
  }
}

void test_reduction_truth_tables() {
  for(int code=0;code<256;++code)for(int op:{vtUAND,vtUOR,vtUNAND,vtUNOR,vtUNOT,vtUXOR,vtUXNOR}) {
    std::string literal="4'b";bool zero=false,one=false,unknown=false;int parity=0;
    for(int bit=3;bit>=0;--bit) {
      const int value=(code>>(2*bit))&3;literal+=value==VX?'x':value==VZ?'z':value?'1':'0';
      zero|=value==V0;one|=value==V1;unknown|=value>=VX;parity^=value==V1;
    }
    int expected=0;
    if(op==vtUAND||op==vtUNAND)expected=zero?V0:unknown?VX:V1;
    else if(op==vtUOR||op==vtUNOR||op==vtUNOT)expected=one?V1:unknown?VX:V0;
    else expected=unknown?VX:parity;
    if((op==vtUNAND||op==vtUNOR||op==vtUNOT||op==vtUXNOR)&&expected<VX)expected=1-expected;
    rtl::VeriNum value(0,1,1,nullptr);assert(value.parse(literal.c_str(),literal.size())==rtl::OK);
    assert(value.unary_operation(op)==rtl::OK);assert(value.bits()==1&&value.is_signed()==rtl::IS_FALSE);
    assert(value.get_certain_bit(0)==expected);
  }
  for(int width:{1,31,32,33,64,65,130})for(int op:{vtUAND,vtUOR,vtUNAND,vtUNOR,vtUNOT}) {
    rtl::VeriNum value(0,1,1,nullptr);std::string literal=std::to_string(width)+"'sb"+std::string(width,'1');
    assert(value.parse(literal.c_str(),literal.size())==rtl::OK);assert(value.unary_operation(op)==rtl::OK);
    assert(value.bits()==1&&value.is_signed()==rtl::IS_FALSE);
    assert(value.get_certain_bit(0)==(op==vtUAND||op==vtUOR?V1:V0));
    value.truncate_assign(64);for(int bit=1;bit<64;++bit)assert(value.get_certain_bit(bit)==V0);
  }
}

void test_immediate_assertion_cloning() {
  for(int round=0;round<3;++round) {
    auto* mod=analyze("module child #(parameter int N=1)();initial begin "
      "a:assert(N>0); b:assume(N==1)else; c:cover(N>0);end endmodule "
      "module top;child u();child #(.N(2))v();endmodule\n");
    for(const auto& instance:{"u","v"}) {
      auto* symbol=static_cast<rtl::VeriModInst*>(mod->scope()->value_same_level(instance));
      auto* hive=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(symbol->instance())->hive());
      unsigned checked=0;
      for(auto* item:static_cast<rtl::VeriModuleItemList*>(hive->item())->item_list()) {
        if(item->detail_type()!=vsSTMT_INIT)continue;
        auto* block=static_cast<rtl::VeriSeqBlock*>(static_cast<rtl::VeriInitStmt*>(item)->stmt());
        for(auto* stmt:static_cast<rtl::VeriStmtList*>(block->stmt_list())->stmt_list()) {
          assert(stmt->detail_type()==vsSTMT_COND);auto* a=static_cast<rtl::VeriCondStmt*>(stmt);
          assert(a->assertion_kind()==int(checked+1));assert(a->assertion_label()==std::string(1,'a'+checked));
          assert(a->if_exp()->father()==a&&a->if_stmt()->father()==a);
          if(checked==1)assert(a->else_stmt()&&a->else_stmt()->father()==a);else assert(!a->else_stmt());
          ++checked;
        }
      }
      assert(checked==3);
    }
  }
}

void test_explicit_casts() {
  for(int round=0;round<3;++round) {
    auto* mod=analyze("module child #(parameter int W=8)();"
      "localparam A=W'(16'h12ff);localparam B=longint'(32'hffffffff+1);"
      "localparam C=130'(8'sh80);localparam D=int'(8'b1xz001z1);"
      "localparam E=4'(32'hff)+4'(2);localparam F=8'('1);"
      "localparam G=longint'(byte'(32'hff));endmodule "
      "module top;child u();child #(.W(12))v();endmodule\n");
    for(const auto& instance:{"u","v"}) {
      auto* symbol=static_cast<rtl::VeriModInst*>(mod->scope()->value_same_level(instance));
      auto* hive=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(symbol->instance())->hive());
      for(const auto& name:{"A","B","C","D","E","F","G"}) {
        auto* param=static_cast<rtl::VeriParam*>(hive->scope()->value_same_level(name));assert(param);
        auto* num=param->get_val();assert(num);
        if(std::string(name)=="A"){assert(num->bits()==(std::string(instance)=="u"?8:12));assert(num->get_first_int()==(std::string(instance)=="u"?255:767));}
        if(std::string(name)=="B"){assert(num->bits()==64);assert(num->get_certain_bit(32)==1);assert(num->get_certain_bit(0)==0);}
        if(std::string(name)=="C"){assert(num->bits()==130);assert(num->is_signed()==rtl::IS_TRUE);for(int i=7;i<130;++i)assert(num->get_certain_bit(i)==1);}
        if(std::string(name)=="D"){assert(num->bits()==32);assert(num->no_xz()==rtl::IS_TRUE);assert(num->get_first_int()==133);}
        if(std::string(name)=="E"){assert(num->bits()==4);assert(num->get_first_int()==1);}
        if(std::string(name)=="F"){assert(num->bits()==8);assert(num->get_first_int()==255);}
        if(std::string(name)=="G"){assert(num->bits()==64);for(int i=0;i<64;++i)assert(num->get_certain_bit(i)==1);}
      }
    }
  }
}

void test_real_types_and_constants() {
  for(int round=0;round<4;++round) {
    auto* top=analyze("module child #(parameter real P=1.25,parameter shortreal S=16777217)();"
      "typedef real fp_t;fp_t r;localparam A=P+0.5;localparam int B=int'(-1.5);"
      "localparam C=$bitstoreal(64'h3ff4000000000000);"
      "function automatic fp_t f(fp_t a,real b=0.5);return a+b;endfunction endmodule "
      "module top;child u();child #(.P(2.5)) v();endmodule\n");
    for(const auto& instance:{"u","v"}) {
      auto* symbol=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(instance));
      auto* hive=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(symbol->instance())->hive());
      const auto number=[&](const char* name){return static_cast<rtl::VeriParam*>(hive->scope()->value_same_level(name))->get_val();};
      assert(number("P")->real_width()==64&&number("P")->real_value()==(std::string(instance)=="u"?1.25:2.5));
      assert(number("S")->real_width()==32&&number("S")->real_value()==16777216);
      assert(number("A")->real_width()==64&&number("A")->real_value()==(std::string(instance)=="u"?1.75:3.0));
      assert(number("B")->real_width()==0&&number("B")->get_first_int()==-2);
      assert(number("C")->real_width()==64&&number("C")->real_value()==1.25);
      assert(rtl::veri_real_width(hive->scope()->value_same_level("r"))==64);
      auto* fn=static_cast<rtl::VeriFunc*>(hive->scope()->value_same_level("f"));
      assert(rtl::veri_real_width(fn)==64);
      rtl::VeriNum copy(0,number("A"));assert(copy.real_width()==64&&copy.real_value()==number("A")->real_value());
      copy.parse("32'sd7",6);assert(copy.real_width()==0&&copy.get_first_int()==7);
    }
  }
}

void test_string_casts_and_parameters() {
  for(int round=0;round<4;++round) {
    auto* top=analyze("package labels;typedef string text_t;endpackage "
      "module child #(parameter labels::text_t LABEL=string'(32'h410042));"
      "localparam INFERRED=string'(32'h4344);localparam EMPTY=string'(0);"
      "localparam JOINED={LABEL,\":suffix\"};"
      "localparam CHOSEN=0?LABEL:\"literal\";"
      "function unsigned flag(input int x);return x;endfunction endmodule "
      "module top;child u();child #(.LABEL(string'(32'h4546))) v();endmodule\n");
    for(const auto& instance:{"u","v"}) {
      auto* symbol=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(instance));
      auto* hive=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(symbol->instance())->hive());
      auto number=[&](const char* name){return static_cast<rtl::VeriParam*>(hive->scope()->value_same_level(name))->get_val();};
      const std::string label=std::string(instance)=="u"?"AB":"EF";
      for(auto entry:std::vector<std::pair<const char*,std::string>>{{"LABEL",label},{"INFERRED","CD"},{"EMPTY",""},{"JOINED",label+":suffix"},{"CHOSEN","literal"}}) {
        auto* value=number(entry.first);assert(value->string_type()&&value->string_value()==entry.second);
        rtl::VeriNum copy(0,value);assert(copy.string_type()&&copy.string_value()==entry.second);
        copy.parse("32'sd7",6);assert(!copy.string_type()&&!copy.real_width()&&copy.get_first_int()==7);
      }
      auto* flag=static_cast<rtl::VeriFunc*>(hive->scope()->value_same_level("flag"));
      assert(flag->dlen()==1&&flag->func()->is_signed()==rtl::IS_FALSE);
    }
  }
}

void test_named_integral_types() {
  for(int round=0;round<3;++round) {
    auto* mod=analyze("module child #(parameter int W=8)();"
      "typedef logic signed [W-1:0] word_t;typedef word_t alias_t;"
      "typedef bit [W:0] bits_t;alias_t q;bits_t z;"
      "typedef bit scalar_t;typedef bit [0:0] packed_t;scalar_t scalar;packed_t packed_value;"
      "localparam A=alias_t'(-2);localparam B=bits_t'(32'hxz8000ff);"
      "endmodule module top;child u();child #(.W(13))v();endmodule\n");
    for(const auto& instance:{"u","v"}) {
      auto* symbol=static_cast<rtl::VeriModInst*>(mod->scope()->value_same_level(instance));
      auto* hive=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(symbol->instance())->hive());
      const int width=std::string(instance)=="u"?8:13;
      auto get=[&](const char* name){auto* n=hive->scope()->value_same_level(name);assert(n);return n;};
      for(auto name:{"word_t","alias_t","bits_t"})assert(get(name)->tok_type()==vtTYPE);
      for(auto name:{"scalar_t","scalar"})assert(static_cast<rtl::VeriVar*>(get(name))->vec_scalar()==vpSCALAR);
      for(auto name:{"packed_t","packed_value"})assert(static_cast<rtl::VeriVar*>(get(name))->vec_scalar()==vpVECTOR);
      auto* type=static_cast<rtl::VeriVar*>(get("alias_t"));
      auto* q=static_cast<rtl::VeriVar*>(get("q"));
      auto* z=static_cast<rtl::VeriVar*>(get("z"));
      assert(type->dlen()==width&&q->dlen()==width&&q->is_signed()==rtl::IS_TRUE);
      assert(z->dlen()==width+1&&z->is_signed()==rtl::IS_FALSE&&veri_two_state(z->net_type()));
      auto* a=static_cast<rtl::VeriParam*>(get("A"))->get_val();
      auto* b=static_cast<rtl::VeriParam*>(get("B"))->get_val();
      assert(a->bits()==width&&a->is_signed()==rtl::IS_TRUE);
      for(int bit=0;bit<width;++bit)assert(a->get_certain_bit(bit)==(bit?V1:V0));
      assert(b->bits()==width+1&&b->no_xz()==rtl::IS_TRUE&&b->get_first_int()==255);
    }
  }
}

void test_array_queries() {
  for(int round=0;round<3;++round) {
    analyze(R"(module lane #(parameter W=3);
      typedef logic[W+2:3] word_t;
      word_t words[2:6];
      localparam D=$dimensions(words),U=$unpacked_dimensions(words),S=$size(words,2);
      localparam L=$left(word_t),R=$right(word_t),I=$increment(words);
      localparam X=$left(words,64'h100000002),Y=$right(words,3);
      localparam C=$countbits({65{1'bx}},1'bx,1'bx,1'bz);
      localparam B=$right(logic[3:-2]),A=$increment(bit[0:4]);
      endmodule module top;lane #(.W(3)) u();lane #(.W(9)) v();endmodule)");
    auto* mod=veri_parser->module("top");
    for(const auto& instance:{"u","v"}) {
      auto* symbol=static_cast<rtl::VeriModInst*>(mod->scope()->value_same_level(instance));
      auto* hive=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(symbol->instance())->hive());
      int width=std::string(instance)=="u"?3:9;
      auto value=[&](const char* name){auto* p=hive->scope()->value_same_level(name);assert(p&&p->tok_type()==vtPARAM);return static_cast<rtl::VeriParam*>(p)->get_val();};
      for(const auto& name:{"D","U","S","L","R","I","C","B","A"})assert(value(name)->bits()==32&&value(name)->is_signed()==rtl::IS_TRUE);
      assert(value("D")->get_first_int()==2&&value("U")->get_first_int()==1&&value("S")->get_first_int()==width);
      assert(value("L")->get_first_int()==width+2&&value("R")->get_first_int()==3);
      assert(value("I")->get_first_int()==-1&&value("A")->get_first_int()==-1&&value("B")->get_first_int()==-2);
      assert(value("C")->get_first_int()==65);
      for(auto name:{"X","Y"})for(int bit=0;bit<32;++bit)assert(value(name)->get_certain_bit(bit)==VX);
      auto shape=rtl::veri_array_shape(hive->scope()->value_same_level("words"));
      assert(shape.unpacked==1&&shape.dimensions.size()==2&&shape.dimensions[0].first==2&&shape.dimensions[0].second==6);
      assert(shape.dimensions[1].first==width+2&&shape.dimensions[1].second==3);
    }
  }
}

void test_vector_system_functions() {
  for(int round=0;round<3;++round) {
    analyze(R"(module lane #(parameter W=3);
      typedef logic[W-1:0] word_t;
      typedef struct packed{word_t data;bit valid;} packet_t;
      word_t q,words[0:2];
      localparam B=$bits(packet_t), M=$bits(words), A=$clog2(W);
      localparam C=$countones({4'b1xz0,4'b1011}), X=$clog2(4'bx010);
      localparam O=$onehot(4'b1xz0),Z=$onehot0(4'b0xz0),U=$isunknown(4'b0xz0);
      localparam R=$countones({65{1'b1}});
      endmodule module top;lane #(.W(3)) u();lane #(.W(9)) v();endmodule)");
    auto* mod=veri_parser->module("top");
    for(const auto& instance:{"u","v"}) {
      auto* symbol=static_cast<rtl::VeriModInst*>(mod->scope()->value_same_level(instance));
      auto* hive=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(symbol->instance())->hive());
      int width=std::string(instance)=="u"?3:9;
      auto value=[&](const char* name){auto* p=hive->scope()->value_same_level(name);assert(p&&p->tok_type()==vtPARAM);return static_cast<rtl::VeriParam*>(p)->get_val();};
      for(const auto& name:{"B","M","A","C","R"})assert(value(name)->bits()==32&&value(name)->is_signed()==rtl::IS_TRUE);
      assert(value("B")->get_first_int()==width+1&&value("M")->get_first_int()==width*3);
      assert(value("A")->get_first_int()==(width==3?2:4));
      assert(value("C")->get_first_int()==4&&value("R")->get_first_int()==65);
      for(const auto& name:{"O","Z","U"})assert(value(name)->bits()==1&&value(name)->get_certain_bit(0)==V1&&value(name)->is_signed()==rtl::IS_FALSE);
      assert(value("X")->bits()==32&&value("X")->no_xz()==rtl::IS_FALSE);
      for(int bit=0;bit<32;++bit)assert(value("X")->get_certain_bit(bit)==VX);
    }
  }
}

void test_enum_types() {
  for(int round=0;round<3;++round) {
    analyze(R"(module lane #(parameter int W=3);
      typedef logic signed [W-1:0] base_t;
      typedef enum base_t {NEG=-2,ZERO=0,ONE,TWO} state_t;
      typedef state_t alias_t;
      state_t q;alias_t a;
      localparam P=ONE;
      localparam int NUM=ONE;
      typedef enum {START,RUN=4,DONE} default_t;
      default_t d;
      typedef enum bit [129:0] {LOW=130'hffffffffffffffff,HIGH,NEXT} wide_t;
      wide_t w;
      typedef enum logic [3:0] {EX=4'bx01z,EZ=4'bz10x} four_t;
      four_t f;
      endmodule
      module top;lane #(.W(3)) u();lane #(.W(7)) v();endmodule)");
    auto* mod=veri_parser->module("top");
    rtl::VeriVar* prior=nullptr;
    for(const auto& instance:{"u","v"}) {
      auto* symbol=static_cast<rtl::VeriModInst*>(mod->scope()->value_same_level(instance));
      auto* hive=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(symbol->instance())->hive());
      auto get=[&](const char* name){auto* n=hive->scope()->value_same_level(name);assert(n);return n;};
      auto* type=static_cast<rtl::VeriVar*>(get("state_t"));
      int width=std::string(instance)=="u"?3:7;
      assert(type->tok_type()==vtTYPE&&type->enum_type()==type&&type->dlen()==width);
      assert(type!=prior);prior=type;
      for(const auto& name:{"alias_t","q","a"})assert(static_cast<rtl::VeriVar*>(get(name))->enum_type()==type);
      for(const auto& name:{"NEG","ZERO","ONE","TWO","P"}) {
        auto* member=static_cast<rtl::VeriParam*>(get(name));
        assert(member->tok_type()==vtPARAM&&member->enum_type()==type&&member->get_val()->bits()==width);
      }
      assert(!static_cast<rtl::VeriParam*>(get("NUM"))->enum_type());
      assert(static_cast<rtl::VeriParam*>(get("NEG"))->get_val()->get_certain_bit(width-1)==V1);
      auto* d=static_cast<rtl::VeriVar*>(get("d"));
      assert(d->dlen()==32&&d->is_signed()==rtl::IS_TRUE&&veri_two_state(d->net_type()));
      auto* next=static_cast<rtl::VeriParam*>(get("NEXT"))->get_val();
      assert(next->bits()==130&&next->get_certain_bit(64)==V1&&next->get_certain_bit(0)==V1);
      for(int bit=1;bit<130;++bit)if(bit!=64)assert(next->get_certain_bit(bit)==V0);
      auto* ex=static_cast<rtl::VeriParam*>(get("EX"))->get_val();
      auto* ez=static_cast<rtl::VeriParam*>(get("EZ"))->get_val();
      assert(ex->bits()==4&&ex->get_certain_bit(3)==VX&&ex->get_certain_bit(0)==VZ);
      assert(ez->bits()==4&&ez->get_certain_bit(3)==VZ&&ez->get_certain_bit(0)==VX);
    }
  }
  for(const auto& body:{"typedef enum {A=1,B=1} t;","typedef enum logic[1:0] {A=3,B} t;",
      "typedef enum bit[3:0] {A=4'bx001} t;","typedef enum logic[3:0] {A=4'bz001,B} t;"}) {
    bool rejected=false;
    try {analyze(std::string("module top;")+body+"endmodule\n");}
    catch(const std::runtime_error& e){rejected=std::string(e.what()).find("enum")!=std::string::npos;}
    assert(rejected);
  }
}

void test_unsigned_enum_initializers_cleanup() {
  const char* valid=R"SV(module lane #(parameter int W=32);
    localparam int NEGATIVE=-2;
    typedef bit[W-1:0] base_t;
    typedef enum base_t {PREVIOUS=NEGATIVE,LAST,ZERO=0} state_t;
    state_t state;
    endmodule
    module top;lane #(32) u();lane #(65) v();lane #(129) w();endmodule)SV";
  for(int round=0;round<3;++round) {
    auto* top=analyze(valid);rtl::VeriVar* previous=nullptr;
    for(const char* name:{"u","v","w"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* state=static_cast<rtl::VeriVar*>(mod->scope()->value_same_level("state"));
      auto* type=state->enum_type();assert(type&&type!=previous);previous=type;
      const int width=std::string(name)=="u"?32:std::string(name)=="v"?65:129;
      assert(state->dlen()==width&&state->is_signed()==rtl::IS_FALSE);
      for(const char* label:{"PREVIOUS","LAST"}) {
        auto* member=static_cast<rtl::VeriParam*>(mod->scope()->value_same_level(label));
        auto* value=member->get_val();assert(member->enum_type()==type&&value->bits()==width);
        assert(value->is_signed()==rtl::IS_FALSE);
        for(int bit=0;bit<width;++bit)
          assert(value->get_certain_bit(bit)==(bit==0&&std::string(label)=="PREVIOUS"?V0:V1));
      }
    }
    for(const char* body:{"typedef enum bit[30:0] {A=-1} E;",
                          "parameter int P=-1;typedef enum bit[7:0] {A=P} E;",
                          "typedef enum bit[31:0] {A=-1,B} E;",
                          "typedef enum bit[31:0] {A=-1,B='1} E;",
                          "typedef enum {A=2.5} E;"}) {
      bool rejected=false;
      try{analyze(std::string("module top;")+body+"endmodule");}
      catch(const std::runtime_error& e){rejected=std::string(e.what()).find("enum")!=std::string::npos;}
      assert(rejected);analyze(valid);
    }
  }
}

void test_packed_aggregates() {
  for(int round=0;round<3;++round) {
    auto* mod=analyze(R"(module lane #(parameter int W=3);
      typedef enum logic[1:0]{IDLE,RUN,DONE} state_t;
      typedef struct packed {bit[W-1:0] data;state_t state;} packet_t;
      typedef packet_t alias_t;
      typedef union packed {packet_t packet;logic[W+1:0] bits;} view_t;
      alias_t q;view_t v;
      initial begin q=0;q.data=1;q.state=RUN;v.packet=q;end
      endmodule module top;lane #(.W(3))u();lane #(.W(7))v();endmodule)");
    rtl::VeriVar* prior=nullptr;
    for(const auto& instance:{"u","v"}) {
      auto* symbol=static_cast<rtl::VeriModInst*>(mod->scope()->value_same_level(instance));
      auto* hive=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(symbol->instance())->hive());
      auto get=[&](const char* name){auto* n=hive->scope()->value_same_level(name);assert(n);return n;};
      auto* type=static_cast<rtl::VeriVar*>(get("packet_t"));
      const int w=std::string(instance)=="u"?3:7;
      assert(type->tok_type()==vtTYPE&&type->aggregate_type()==type&&type->dlen()==w+2&&type!=prior);prior=type;
      for(auto name:{"alias_t","q"})assert(static_cast<rtl::VeriVar*>(get(name))->aggregate_type()==type);
      auto& f=type->packed_fields();assert(f.size()==2&&f[0].name=="data"&&f[0].offset==2&&f[0].symbol->dlen()==w);
      assert(f[1].offset==0&&f[1].symbol->enum_type()==get("state_t"));
      auto* view=static_cast<rtl::VeriVar*>(get("view_t"));assert(view->dlen()==w+2);
      assert(view->packed_fields()[0].symbol->aggregate_type()==type&&view->packed_fields()[1].offset==0);
      assert(!hive->scope()->value_same_level("data")&&!hive->scope()->value_same_level("state"));
    }
  }
  for(const auto& body:{"typedef union packed {bit a;bit[1:0] b;} t;",
      "typedef struct packed {bit a=1;} t;","typedef struct packed {bit a[0:1];} t;"}) {
    bool rejected=false;try {analyze(std::string("module top;")+body+"endmodule");}
    catch(const std::runtime_error& error){rejected=std::string(error.what()).find("packed")!=std::string::npos;}
    assert(rejected);
  }
}

void test_implicit_named_connections() {
  for(int round=0;round<3;++round) {
    auto* mod=analyze("module invert(input a,output y);assign y=~a;endmodule "
      "module top;reg a;wire y;invert u(.y,.a);endmodule");
    auto* symbol=static_cast<rtl::VeriModInst*>(mod->scope()->value_same_level("u"));
    auto* instance=static_cast<rtl::VeriModInstance*>(symbol->instance());
    auto& args=static_cast<rtl::VeriMultiExp*>(instance->arg())->exp();assert(args.size()==2);
    auto it=args.begin();
    for(const auto& name:{"y","a"}) {
      auto* n=*it++;assert(n->detail_type()==veEXP_NAMED_PARAM);
      auto* arg=static_cast<rtl::VeriNamedParamExp*>(n);assert(arg->ref()==name);
      auto& actual=static_cast<rtl::VeriMultiExp*>(arg->port_exp())->exp();assert(actual.size()==1);
      auto* primary=static_cast<rtl::VeriPrimaryExp*>(actual.front());assert(primary->str()==name&&primary->var());
    }
  }
}

void test_invalid_typedef_bounds() {
  for(const auto& body:{"int n=7;typedef logic[n:0] t;","typedef logic[8'hx:0] t;",
      "typedef logic[64'h100000007:0] t;","typedef logic[2.5:0] t;","typedef logic[7] t;"}) {
    bool rejected=false;
    try {analyze(std::string("module top;")+body+"endmodule\n");}
    catch(const std::runtime_error& error) {
      const std::string diagnostic=error.what();
      rejected=diagnostic.find("typedef")!=std::string::npos ||
        (std::string(body)=="typedef logic[2.5:0] t;" &&
         diagnostic.find("range or index requires integral operands")!=std::string::npos);
    }
    assert(rejected);
  }
}

void test_four_state_case_equality() {
  const std::string digits="01xz";
  for(int width:{1,31,32,33,64,65,130})for(char a:digits)for(char b:digits)for(int op:{vtBCEQ,vtBCIEQ}) {
    rtl::VeriNum left(1,1,1,nullptr),right(2,1,1,nullptr);
    auto x=std::to_string(width)+"'b"+std::string(width,a);
    auto y=std::to_string(width)+"'b"+std::string(width,b);
    assert(left.parse(x.c_str(),x.size())==rtl::OK&&right.parse(y.c_str(),y.size())==rtl::OK);
    assert(left.binary_operation(op,&right)==rtl::OK);
    assert(left.bits()==1&&left.no_xz()==rtl::IS_TRUE);
    assert(left.get_certain_bit(0)==((a==b)==(op==vtBCEQ)?V1:V0));
  }
}

void test_selection_eof_recovery() {
  auto* parser=rtl::VeriParser::get_instance();
  for(int round=0;round<3;++round) {
    rtl::Src_mgr::get_instance()->set_src("module top; initial unique if(1);"+std::string(1,'\0'));
    rtl::Src_mgr::get_instance()->set_fname("selection_eof.v");
    assert(parser->init()==rtl::OK);parser->set_top_module("top");
    assert(parser->parse()!=rtl::OK);
    analyze("module top;integer q;initial unique case(1)1:q=2;endcase endmodule");
  }
}

void test_variable_port_elements_and_cleanup() {
  const std::string source="module c(input[1:0]d,output[1:0]q);assign q=d;endmodule "
    "module top;typedef struct packed {logic[3:0]hi;logic[3:0]lo;} P;P p;"
    "logic[3:0]words[0:1][2:3];integer ints[0:1];"
    "c a(p.hi[1:0],words[0][2][1:0]);c b(words[1][3],p.lo);"
    "c e(ints[0],words[0][3]);endmodule";
  for(int round=0;round<3;++round)analyze(source);
}

void test_enum_methods_and_cleanup() {
  const std::string source="module top;typedef enum logic[3:0] {A=2,B=7,C=1} E;E e;"
    "parameter P=A.next(2);parameter R=P.prev();parameter N=e.num();"
    "parameter X=A.next(32'b0x1);parameter Z=A.prev(32'b0z1);"
    "parameter BAD=E'(9).next();parameter ZERO=A.next(0);"
    "initial begin e=A;e=e.next(2).prev();end endmodule";
  for(int round=0;round<3;++round) {
    auto* mod=analyze(source);
    for(auto item:std::vector<std::pair<std::string,int>>{{"P",1},{"R",7},{"N",3},{"X",2},{"Z",1},{"ZERO",2}}) {
      auto* p=static_cast<rtl::VeriParam*>(mod->scope()->value_same_level(item.first));
      assert(p&&p->get_val()->get_first_int()==item.second);
    }
    auto* bad=static_cast<rtl::VeriParam*>(mod->scope()->value_same_level("BAD"));
    assert(bad&&bad->get_val()->bits()==4&&bad->get_val()->no_xz()==rtl::IS_FALSE);
    auto* type=static_cast<rtl::VeriVar*>(mod->scope()->value_same_level("E"));
    assert(type&&type->enum_values().size()==3);
    for(size_t i=0;i<3;++i)assert(type->enum_values()[i]->get_first_int()==(i==0?2:i==1?7:1));
  }
}

void test_array_alias_cloning_cleanup() {
  const std::string source=R"(module leaf #(parameter W=8);
    typedef logic[W-1:0] Word;
    typedef Word Queue[$:3];typedef Queue Alias;
    typedef Word Row[2:0];typedef Row Matrix[0:1];
    class C #(type T=Word);
      typedef T Values[$];
      static function Values make(input T value);Values q;q.push_back(value);return q;endfunction
    endclass
    Alias a;Matrix m;
    function automatic Alias copy(input Alias q);return q;endfunction
    initial begin a=C#(Word)::make(1);a=copy(a);end
    endmodule module top;leaf #(8) a();leaf #(129) b();endmodule)";
  for(int round=0;round<4;++round) {
    auto* top=analyze(source);rtl::VeriVar* previous=nullptr;
    for(auto entry:{std::make_pair("a",8),std::make_pair("b",129)}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(entry.first));
      auto* leaf=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* alias=static_cast<rtl::VeriVar*>(leaf->scope()->value_same_level("Alias"));
      assert(alias&&alias!=previous);previous=alias;
      assert(alias->range_depth()==1&&alias->dynamic_array()&&alias->container_kind()==vrQUEUE&&alias->container_bound()==3);
      auto* variable=static_cast<rtl::VeriVar*>(leaf->scope()->value_same_level("a"));
      assert(variable->range_depth()==1&&variable->dlen()==entry.second&&variable->container_bound()==3);
      assert(rtl::veri_array_shape(leaf->scope()->value_same_level("m")).unpacked==2);
      auto* fn=static_cast<rtl::VeriFunc*>(leaf->scope()->value_same_level("copy"))->func();
      assert(fn->resolved_type()==alias);
      auto ports=rtl::veri_subroutine_formals(fn);assert(ports.size()==1);
      auto* formal=static_cast<rtl::VeriTfVar*>(rtl::veri_formal_symbol(ports.front()));
      assert(formal->range_depth()==1&&formal->dynamic_array()&&formal->container_bound()==3);
      assert(rtl::veri_array_shape(formal).unpacked==1&&rtl::veri_array_shape(formal).unbound);
    }
  }
}

void test_subroutine_end_labels_and_recovery() {
  // Both class specializations and automatic call hives traverse these nodes.
  const std::string valid=R"(module leaf #(parameter W=8);
    class C;
      logic[W-1:0] x;
      function new(input int v);x=v;endfunction : new
      static function automatic int count();return W;endfunction : count
      function logic[W-1:0] get();return x;endfunction : get
      task automatic put(input logic[W-1:0] v);#1;x=v;endtask : put
    endclass
    C obj;int result;
    initial begin obj=new(3);obj.put(C::count());result=obj.get();end
    endmodule module top;leaf #(8) a();leaf #(129) b();endmodule)";
  for(int round=0;round<4;++round) {
    for(const auto& bad:{
      "function int f();return 1;endfunction : F",
      "task t();begin end endtask : new",
      "class C;function new();begin end endfunction : C endclass",
      "function int f();return 1;endfunction :"}) {
      auto* parser=rtl::VeriParser::get_instance();
      rtl::Src_mgr::get_instance()->set_src("module top;"+std::string(bad)+" endmodule\n"+std::string(1,'\0'));
      assert(parser->init()==rtl::OK);parser->set_top_module("top");
      bool rejected=false;try{rejected=parser->parse()!=rtl::OK;}catch(const std::runtime_error&){rejected=true;}
      assert(rejected);analyze(valid);
    }
  }
}

void test_empty_subroutine_ports_and_syntax_recovery() {
  const std::string valid="module top; integer g; function void f(); begin g=1;return;end endfunction task t();begin f();end endtask initial begin t();void'(f());end endmodule\n";
  for(int round=0;round<3;++round) {
    auto* parser=rtl::VeriParser::get_instance();
    rtl::Src_mgr::get_instance()->set_src("module top;function void f(,);begin end endfunction endmodule\n"+std::string(1,'\0'));
    assert(parser->init()==rtl::OK);parser->set_top_module("top");
    assert(parser->parse()!=rtl::OK);
    analyze(valid);
  }
}

void test_dynamic_subarray_and_delay_call_cleanup() {
  const std::string source="module top;logic[7:0]a[1:0][2:3],b[0:1];integer i;"
    "function automatic integer tick(input integer v);logic[7:0]local_words[0:1];"
    "begin local_words[0]=v;tick=local_words[0];end endfunction "
    "initial begin i=1;b=a[tick(i)];a[i]<=#(tick(2)) b;#(tick(1));end endmodule";
  for(int round=0;round<3;++round)analyze(source);
}

void test_level_wait_and_cleanup() {
  const std::string source="module child(input logic a,output logic q);"
    "function automatic logic ready(input logic v);ready=v;endfunction "
    "function reg signed[7:0] neg(input logic v);neg=v?8'h80:8'h00;endfunction "
    "task automatic await_edges(input integer n);begin repeat(n)begin wait(a);wait(!a);end end endtask "
    "initial begin q=0;wait(a)q=1;await_edges(2);if(a)wait(!a)if(q)q=0;else q=1;end endmodule "
    "module top;logic a,x,y;child u(a,x);child v(a,y);initial begin wait(1);wait(a===1'b1);end endmodule";
  for(int round=0;round<3;++round) {
    auto* parser=rtl::VeriParser::get_instance();
    rtl::Src_mgr::get_instance()->set_src("module top;initial wait(1;endmodule\n"+std::string(1,'\0'));
    assert(parser->init()==rtl::OK);parser->set_top_module("top");assert(parser->parse()!=rtl::OK);
    analyze(source);
    analyze("module top;function logic f();f=0;endfunction task f();begin end endtask endmodule",rtl::vTASK_REDEFINE);
  }
}

void test_named_events_and_cleanup() {
  const std::string source="module child(output integer q);event start,done;"
    "function automatic void fire();->start;endfunction "
    "task automatic await_done(output integer v);begin @done;v=1;end endtask "
    "initial begin q=0;fire();->> #(2) done;await_done(q);wait(start.triggered);end "
    "initial begin @(start or done);@(start.triggered);@(posedge done.triggered);end endmodule "
    "module top;integer a,b;child u(a);child v(b);initial begin:local_block event e;->> e;@e.triggered;end endmodule";
  for(int round=0;round<3;++round) {
    auto* parser=rtl::VeriParser::get_instance();
    rtl::Src_mgr::get_instance()->set_src("module top;event e;initial ->> #(;endmodule\n"+std::string(1,'\0'));
    assert(parser->init()==rtl::OK);parser->set_top_module("top");assert(parser->parse()!=rtl::OK);
    analyze(source);
  }
}

void test_instance_events_and_cleanup() {
  const std::string source="module child #(parameter N=2);"
    "class Base;event pulse;task fire();->pulse;endtask endclass "
    "class C extends Base;event done;task watch();@(pulse);wait(this.done.triggered);endtask endclass "
    "C c;initial begin c=new;@(c.pulse);@(posedge c.done.triggered);end "
    "endmodule module top;child u();child #(.N(3))v();endmodule";
  for(int round=0;round<4;++round) {
    auto* top=analyze(source);std::vector<rtl::VeriNode*> event_symbols;
    for(const auto& name:{"u","v"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* unit=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      rtl::VeriNode::NodeVec pending{unit};rtl::VeriNode* event=nullptr;int queries=0;
      while(!pending.empty()) {
        auto* n=pending.back();pending.pop_back();
        if(n->tok_type()==vtEXP&&n->detail_type()==veEXP_MEMBER) {
          auto* member=static_cast<rtl::VeriMemberExp*>(n);
          if(member->event_query()) {
            auto* symbol=rtl::veri_event_symbol(member->object());assert(symbol);
            assert(!rtl::veri_event_symbol(n));event=symbol;++queries;
          }
        }
        n->push_for_replacement(pending);
      }
      assert(queries>=1&&event);event_symbols.push_back(event);
    }
    assert(event_symbols.front()!=event_symbols.back());
  }
}

void test_expression_events_and_cleanup() {
  const std::string source="module child;logic[7:0]a,b;integer index;logic[7:0]mem[0:1];"
    "initial begin @(a+b);@(a[index]);@(mem[index]);@(posedge (a^b) or negedge a[1]);@({a,b});end "
    "task automatic watch(input integer i);@(a[i]);endtask endmodule "
    "module top;child u();child v();endmodule";
  for(int round=0;round<3;++round) {
    auto* parser=rtl::VeriParser::get_instance();
    rtl::Src_mgr::get_instance()->set_src("module top;logic a;initial @(a+);endmodule\n"+std::string(1,'\0'));
    assert(parser->init()==rtl::OK);parser->set_top_module("top");assert(parser->parse()!=rtl::OK);
    analyze(source);
  }
}

void test_conditional_events_and_cleanup() {
  const std::string source="module child;logic a,b,g,h;logic[7:0]data;integer i;"
    "always @(posedge a iff g or negedge b iff h) data++;"
    "initial begin @(data[i] iff g);@((posedge a iff g),(negedge b iff h));end "
    "task automatic watch(input logic enabled);@(posedge a iff enabled);endtask endmodule "
    "module top;child u();child v();endmodule";
  for(int round=0;round<3;++round) {
    auto* parser=rtl::VeriParser::get_instance();
    rtl::Src_mgr::get_instance()->set_src("module top;logic a;initial @(a iff );endmodule\n"+std::string(1,'\0'));
    assert(parser->init()==rtl::OK);parser->set_top_module("top");assert(parser->parse()!=rtl::OK);
    analyze(source);
  }
}

void test_function_events_and_cleanup() {
  const std::string source="module child;logic a,b;integer n;"
    "function automatic logic sense(input logic x);logic temporary;temporary=x^b;return temporary;endfunction "
    "initial begin @(sense(a));@(posedge sense(a) iff sense(b));end "
    "task automatic watch(input logic enabled);@(sense(a) iff sense(enabled));endtask endmodule "
    "module top;child u();child v();endmodule";
  for(int round=0;round<3;++round) {
    auto* parser=rtl::VeriParser::get_instance();
    rtl::Src_mgr::get_instance()->set_src("module top;logic a;initial @(f(a+));endmodule\n"+std::string(1,'\0'));
    assert(parser->init()==rtl::OK);parser->set_top_module("top");assert(parser->parse()!=rtl::OK);
    analyze(source);
  }
}

void test_qualified_named_events_and_cleanup() {
  const std::string source="module child;event e,f;logic g;integer n;"
    "function automatic logic allow();return g;endfunction "
    "always @(e iff g or f iff allow() or posedge g)n++;"
    "task automatic watch(input logic enabled);@(e iff enabled);endtask "
    "initial begin ->e;->>#2 f;watch(g);end endmodule "
    "module top;child u();child v();endmodule";
  for(int round=0;round<3;++round) {
    auto* parser=rtl::VeriParser::get_instance();
    rtl::Src_mgr::get_instance()->set_src("module top;event e;initial @(e iff );endmodule\n"+std::string(1,'\0'));
    assert(parser->init()==rtl::OK);parser->set_top_module("top");assert(parser->parse()!=rtl::OK);
    analyze(source);
  }
}

void test_intra_event_assignments_and_cleanup() {
  const std::string source="module child #(parameter N=2)();event e;logic clk,g,q,d;"
    "initial begin q=repeat(N)@(posedge clk iff g)d;q=@e d;q<=repeat(N)@e d;q<=@(posedge clk iff g)d;end "
    "task automatic watch(input integer n);logic value;value=repeat(n)@(e iff g)d;endtask "
    "endmodule module top;child u();child #(.N(3))v();endmodule";
  for(int round=0;round<3;++round) {
    auto* parser=rtl::VeriParser::get_instance();
    rtl::Src_mgr::get_instance()->set_src("module top;logic q;initial q=repeat(2)@();endmodule\n"+std::string(1,'\0'));
    assert(parser->init()==rtl::OK);parser->set_top_module("top");assert(parser->parse()!=rtl::OK);
    analyze(source);
  }
}

void test_fork_join_and_cleanup() {
  const std::string source="module child #(parameter N=2)();integer q;"
    "initial fork : workers integer local_value;begin local_value=N;#1;q=local_value;end #2;join "
    "initial fork fork #1;#2;join_any fork #1;join_none join "
    "task automatic watch();fork integer x;begin x=N;#1;end #2;join endtask "
    "endmodule module top;child u();child #(.N(3))v();endmodule";
  for(int round=0;round<3;++round) {
    auto* parser=rtl::VeriParser::get_instance();
    rtl::Src_mgr::get_instance()->set_src("module top;initial fork #1;end endmodule\n"+std::string(1,'\0'));
    assert(parser->init()==rtl::OK);parser->set_top_module("top");assert(parser->parse()!=rtl::OK);
    auto* mod=analyze(source);
    for(const auto& name:{"u","v"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(mod->scope()->value_same_level(name));
      auto* hive=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      unsigned checked=0;
      for(auto* node:static_cast<rtl::VeriModuleItemList*>(hive->item())->item_list())if(node->detail_type()==vsSTMT_INIT) {
        auto* block=static_cast<rtl::VeriSeqBlock*>(static_cast<rtl::VeriInitStmt*>(node)->stmt());
        assert(block->parallel_kind()==1);
        if(checked==1) {
          int kind=2;
          for(auto* branch:static_cast<rtl::VeriStmtList*>(block->stmt_list())->stmt_list())
            assert(static_cast<rtl::VeriSeqBlock*>(branch)->parallel_kind()==kind++);
          assert(kind==4);
        }
        ++checked;
      }
      assert(checked==2);
    }
  }
}

void test_named_disable_and_labels_cleanup() {
  const std::string source="module child #(parameter N=2)();integer q;"
    "function automatic integer f(input integer n);begin : search f=1;"
    "if(n)disable search;f=2;end : search endfunction "
    "task automatic t();begin : work fork : jobs #1;begin #2;disable work;end join : jobs end : work endtask "
    "initial begin : main q=f(N);t();end : main "
    "endmodule module top;child u();child #(.N(3))v();endmodule";
  for(int round=0;round<3;++round) {
    auto* parser=rtl::VeriParser::get_instance();
    rtl::Src_mgr::get_instance()->set_src("module top;initial begin : a #1;end : b endmodule\n"+std::string(1,'\0'));
    assert(parser->init()==rtl::OK);parser->set_top_module("top");assert(parser->parse()!=rtl::OK);
    analyze(source);
  }
}

void test_fork_control_cleanup() {
  const std::string source="module child #(parameter N=2)();integer q;"
    "initial begin fork : work #N;q=1;join_any : work disable fork;wait fork;"
    "fork #1;q=2;join_none wait fork;end endmodule "
    "module top;child u();child #(.N(3))v();endmodule";
  for(int round=0;round<3;++round)analyze(source);
}

void test_explicit_automatic_cleanup() {
  const std::string source="module child #(parameter N=2)();integer q;"
    "initial begin : work automatic integer a=N;integer shared=0;"
    "automatic logic[7:0] bits;automatic int words[1:2];"
    "q=a;shared++;fork automatic integer saved=a;#1;q=saved;join_none wait fork;end "
    "endmodule module top;child u();child #(.N(3))v();endmodule";
  for(int round=0;round<3;++round) {
    auto* top=analyze(source);
    int checked=0;
    for(const auto& name:{"u","v"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      for(auto* item:static_cast<rtl::VeriModuleItemList*>(mod->item())->item_list()) {
        if(item->detail_type()!=vsSTMT_INIT)continue;
        auto* block=static_cast<rtl::VeriSeqBlock*>(static_cast<rtl::VeriInitStmt*>(item)->stmt());
        const auto& decls=static_cast<rtl::VeriBlockItemDeclList*>(block->decl_list())->block_item();
        assert(decls.size()==4);auto it=decls.begin();
        assert(static_cast<rtl::VeriDecl*>(*it++)->explicit_automatic());
        assert(!static_cast<rtl::VeriDecl*>(*it++)->explicit_automatic());
        assert(static_cast<rtl::VeriDecl*>(*it++)->explicit_automatic());
        assert(static_cast<rtl::VeriDecl*>(*it++)->explicit_automatic());
        ++checked;
      }
    }
    assert(checked==2);
  }
}

void test_explicit_static_cleanup() {
  const std::string source="module child #(parameter N=2)();integer q;"
    "task automatic work;static integer calls=N;integer private_value;"
    "begin : nested static logic[7:0] bits;static int words[1:2];"
    "automatic integer saved=1;calls++;q=calls+saved;end endtask "
    "initial work();endmodule module top;child u();child #(.N(3))v();endmodule";
  for(int round=0;round<3;++round) {
    auto* top=analyze(source);int checked=0;
    for(const auto& name:{"u","v"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      for(auto* item:static_cast<rtl::VeriModuleItemList*>(mod->item())->item_list()) {
        if(item->detail_type()!=vsDECL_TASK_DECL)continue;
        auto* task=static_cast<rtl::VeriTaskDecl*>(item);
        const auto& decls=static_cast<rtl::VeriTaskItemDeclList*>(task->item_decl())->task_item();
        assert(decls.size()==2);auto it=decls.begin();
        assert(static_cast<rtl::VeriDecl*>(*it++)->explicit_static());
        assert(!static_cast<rtl::VeriDecl*>(*it++)->explicit_static());
        ++checked;
      }
    }
    assert(checked==2);
  }
}


void test_dynamic_declaration_initializers_cleanup() {
  for(int round=0;round<3;++round) {
    auto* top=analyze("module child #(parameter N=2)();"
      "logic signed[95:0] a[]=new[N],b[]=a,c[]=new[N+1](b);"
      "function automatic integer f(input integer n);logic[7:0] x[]=new[n],y[]=x;return y.size();endfunction "
      "initial begin integer result;result=f(N);end endmodule "
      "module top;child u();child #(.N(3))v();endmodule");
    std::vector<rtl::VeriNode*> sources;
    for(const auto& name:{"u","v"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* a=static_cast<rtl::VeriVar*>(mod->scope()->value_same_level("a"));
      auto* b=static_cast<rtl::VeriVar*>(mod->scope()->value_same_level("b"));
      assert(a&&b&&a!=b&&a->dynamic_array()&&b->dynamic_array()&&b->dlen()==96);
      bool bound=false;
      for(auto* item:static_cast<rtl::VeriModuleItemList*>(mod->item())->item_list())if(item->detail_type()==vsDECL_VAR) {
        for(auto* var:static_cast<rtl::VeriVarDecl*>(item)->vars())if(var->detail_type()==veEXP_ASSIGN) {
          auto* rhs=static_cast<rtl::VeriAssignExp*>(var)->rval();
          if(rhs->detail_type()==veEXP_PRI) {
            assert(static_cast<rtl::VeriPrimaryExp*>(rhs)->var()==a);bound=true;
          }
        }
      }
      assert(bound);sources.push_back(a);
    }
    assert(sources[0]!=sources[1]);
  }
}

void test_dynamic_array_cleanup() {
  for(int round=0;round<3;++round) {
    auto* top=analyze("module child #(parameter N=2)();integer a[],fixed_values[0:-1],q;int b[];"
      "function automatic integer f(input integer n);integer tmp[];tmp=new[n];tmp[0]=1;return tmp.size();endfunction "
      "initial begin a=new[N];b=new[N](a);a.delete();q=f(N);end endmodule "
      "module top;child u();child #(.N(3))v();endmodule");
    std::vector<rtl::VeriNode*> objects;
    for(const auto& name:{"u","v"}) {
      auto* inst=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(inst->instance())->hive());
      auto* a=static_cast<rtl::VeriInt*>(mod->scope()->value_same_level("a"));
      auto* b=static_cast<rtl::VeriVar*>(mod->scope()->value_same_level("b"));
      auto* fixed=static_cast<rtl::VeriInt*>(mod->scope()->value_same_level("fixed_values"));
      assert(a->dynamic_array()&&b->dynamic_array()&&!fixed->dynamic_array());
      assert(rtl::veri_array_shape(a).unbound&&rtl::veri_array_shape(b).unbound&&!rtl::veri_array_shape(fixed).unbound);
      objects.push_back(a);
    }
    assert(objects[0]!=objects[1]);
  }
}

void test_open_array_cleanup() {
  for(int round=0;round<3;++round) {
    auto* top=analyze("module child #(parameter N=2)();integer x[2][N],y[2],q;"
      "function automatic integer f(input integer a[][N],input integer b[]=y);return $size(a)+$bits(b);endfunction "
      "task automatic t;input integer a[];begin end endtask "
      "initial begin q=f(x,y);t(y);end endmodule module top;child u();child #(.N(3))v();endmodule");
    int expected=2;
    std::vector<rtl::VeriNode*> symbols;
    for(const auto& name:{"u","v"}) {
      auto* inst=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(inst->instance())->hive());
      auto* f=static_cast<rtl::VeriFunc*>(mod->scope()->value_same_level("f"));
      auto* ports=static_cast<rtl::VeriFuncPortList*>(f->func()->port_list());
      auto* decl=static_cast<rtl::VeriTfDecl*>(ports->func_port().front());
      auto* a=static_cast<rtl::VeriTfVar*>(rtl::veri_formal_symbol(decl->port_ids().front()));
      assert(a->range_depth()==2&&a->open_range(1)&&!a->open_range(2)&&a->unbound_ranges());
      int first,last,count;a->get_range(2,first,last,count);assert(count==expected++);
      assert(rtl::veri_array_shape(a).unbound);
      a->bind_open_range(1,5);a->get_range(1,first,last,count);
      assert(first==0&&last==4&&count==5&&!a->unbound_ranges());
      assert(!rtl::veri_array_shape(a).unbound);symbols.push_back(a);
    }
    assert(symbols[0]!=symbols[1]);
  }
}

void test_array_arguments_cleanup() {
  for(int round=0;round<3;++round) {
    auto* top=analyze("module child #(parameter N=2)();integer x[0:N-1],q;"
      "function automatic integer f(input integer a[N]=x,output integer b[3:2]);"
      "b[3]=a[0];b[2]=a[1];return $size(a);endfunction "
      "task automatic t(ref integer a[N]);a[0]++;endtask "
      "initial begin q=f(x,x);t(x);end endmodule "
      "module top;child u();child #(.N(3))v();endmodule");
    std::vector<rtl::VeriNode*> symbols;
    int expected=2;
    for(const auto& name:{"u","v"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* f=static_cast<rtl::VeriFunc*>(mod->scope()->value_same_level("f"));
      auto* ports=static_cast<rtl::VeriFuncPortList*>(f->func()->port_list());
      auto* decl=static_cast<rtl::VeriTfDecl*>(ports->func_port().front());
      auto* a=static_cast<rtl::VeriTfVar*>(rtl::veri_formal_symbol(decl->port_ids().front()));
      int first,last,count;a->get_range(1,first,last,count);
      assert(a->range_depth()==1&&first==0&&last==expected-1&&count==expected);
      auto shape=rtl::veri_array_shape(a);assert(shape.unpacked==1&&shape.dimensions.size()==2);
      assert(decl->default_argument("a")&&a->inout()==vpIN);
      symbols.push_back(a);++expected;
    }
    assert(symbols[0]!=symbols[1]);
  }
}

void test_ref_arguments_cleanup() {
  for(int round=0;round<3;++round) {
    auto* top=analyze("module child #(parameter N=2)();integer x;"
      "function automatic integer f(ref integer a=x,input integer b=N);a+=b;return a;endfunction "
      "task automatic t;ref integer a;input integer b;a+=b;endtask "
      "initial begin x=f();t(x,N);end endmodule "
      "module top;child u();child #(.N(3))v();endmodule");
    std::vector<rtl::VeriNode*> symbols;
    for(const auto& name:{"u","v"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* f=static_cast<rtl::VeriFunc*>(mod->scope()->value_same_level("f"));
      auto* ports=static_cast<rtl::VeriFuncPortList*>(f->func()->port_list());
      assert(ports->func_port().size()==2);
      auto* decl=static_cast<rtl::VeriTfDecl*>(ports->func_port().front());
      assert(decl->inout()==vpREF);
      auto* a=static_cast<rtl::VeriTfVar*>(static_cast<rtl::VeriPrimaryExp*>(decl->port_ids().front())->var());
      assert(a->inout()==vpREF&&a->dlen()==32);symbols.push_back(a);
      assert(static_cast<rtl::VeriTfDecl*>(ports->func_port().back())->inout()==vpIN);
    }
    assert(symbols[0]!=symbols[1]);
  }
}

void test_const_ref_cleanup() {
  for(int round=0;round<3;++round) {
    auto* top=analyze("module child #(parameter N=2)();integer x;"
      "function automatic integer f(const ref integer a=x,input integer b=N);return a+b;endfunction "
      "task automatic t;const ref integer a;input integer b;b=a;endtask "
      "initial begin x=f();t(x,N);end endmodule "
      "module top;child u();child #(.N(3))v();endmodule");
    std::vector<rtl::VeriNode*> symbols;
    for(const auto& name:{"u","v"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* f=static_cast<rtl::VeriFunc*>(mod->scope()->value_same_level("f"));
      auto* ports=static_cast<rtl::VeriFuncPortList*>(f->func()->port_list());
      assert(ports->func_port().size()==2);
      auto* decl=static_cast<rtl::VeriTfDecl*>(ports->func_port().front());
      assert(decl->inout()==vpCONST_REF);
      auto* a=static_cast<rtl::VeriTfVar*>(static_cast<rtl::VeriPrimaryExp*>(decl->port_ids().front())->var());
      assert(a->inout()==vpCONST_REF&&a->dlen()==32);symbols.push_back(a);
      assert(static_cast<rtl::VeriTfDecl*>(ports->func_port().back())->inout()==vpIN);
    }
    assert(symbols[0]!=symbols[1]);
  }
}

void test_wait_order_cleanup() {
  for(int round=0;round<3;++round) {
    auto* top=analyze("module child #(parameter N=2)();event a,b;integer q;"
      "initial wait_order(a,b,a) q=N;else q=-N;endmodule "
      "module top;child u();child #(.N(3))v();endmodule");
    std::vector<rtl::VeriNode*> events;
    for(const auto& name:{"u","v"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      int checked=0;
      for(auto* item:static_cast<rtl::VeriModuleItemList*>(mod->item())->item_list()) {
        if(item->detail_type()!=vsSTMT_INIT)continue;
        auto* wait=static_cast<rtl::VeriCondStmt*>(static_cast<rtl::VeriInitStmt*>(item)->stmt());
        assert(wait->wait_order()&&wait->if_stmt()&&wait->else_stmt());
        auto args=rtl::veri_system_arguments(wait->if_exp());assert(args.size()==3);
        auto* event=static_cast<rtl::VeriPrimaryExp*>(args[0])->var();events.push_back(event);
        assert(event==mod->scope()->value_same_level("a"));
        assert(event==static_cast<rtl::VeriPrimaryExp*>(args[2])->var());++checked;
      }
      assert(checked==1);
    }
    assert(events[0]!=events[1]);
  }
}


void test_fixed_declaration_initializers_cleanup() {
  for(int round=0;round<3;++round) {
    auto* top=analyze("module child #(parameter N=2)();"
      "logic[7:0] source[N][3:2];logic[7:0] copy[1:0][N]=source;"
      "integer ints[N][3:2];integer copied[1:0][N]=ints;"
      "task automatic work(input integer n);"
      "logic[7:0] local_values[1:0][N]=copy,row[N]=source[n];begin end endtask "
      "endmodule module top;child u();child v();endmodule");
    rtl::VeriNode* previous=nullptr;
    for(const auto& name:{"u","v"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* source=mod->scope()->value_same_level("source");
      auto* copy=static_cast<rtl::VeriVar*>(mod->scope()->value_same_level("copy"));
      assert(source&&source!=previous&&copy&&copy->range_depth()==2);
      previous=source;
    }
    auto* parser=rtl::VeriParser::get_instance();
    rtl::Src_mgr::get_instance()->set_src(std::string("module top;integer a[2][2],b[2];initial a[1:0][0]=b;endmodule")+std::string(1,'\0'));
    rtl::Src_mgr::get_instance()->set_fname("fixed_decl_negative.v");
    assert(parser->init()==rtl::OK);parser->set_top_module("top");
    assert(parser->parse()!=rtl::OK&&parser->has_err()==rtl::IS_TRUE);
    assert(parser->get_err_info().find("6117")!=std::string::npos);
  }
}
void test_packed_dimensions_and_keyword_modes_cleanup() {
  const std::string source="module child #(parameter N=2,W=8)(input logic[N-1:0][W-1:0] a,output wire[N-1:0][W-1:0] y);"
    "typedef logic[1:0][W-1:0] pair_t;pair_t typed;logic[1:0][1:0][3:0] cube;"
    "for(genvar i=0;i<N;i++)begin:g assign y[i]=a[i];end endmodule "
    "module compatibility_tb;wire[15:0] a;wire[11:0] b;child u(16'h1234,a);child #(.N(3),.W(4)) v(12'h123,b);endmodule";
  for(int round=0;round<3;++round) {
    auto* parser=rtl::VeriParser::get_instance();
    rtl::Src_mgr::get_instance()->set_src(source+std::string(1,'\0'));
    rtl::Src_mgr::get_instance()->set_fname("packed_dimensions.sv");
    assert(parser->init()==rtl::OK);parser->set_top_module("");
    assert(parser->parse()==rtl::OK&&parser->get_top_module()=="compatibility_tb");
    auto* top=parser->module("compatibility_tb");rtl::VeriNode* previous=nullptr;
    for(const auto& name:{"u","v"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* a=static_cast<rtl::VeriVar*>(mod->scope()->value_same_level("a"));
      const int lanes=std::string(name)=="u"?2:3,width=std::string(name)=="u"?8:4;
      auto shape=rtl::veri_array_shape(a);
      assert(a!=previous&&a->dlen()==lanes*width&&shape.unpacked==0&&shape.dimensions.size()==2);
      assert(shape.dimensions[0]==std::make_pair(lanes-1,0)&&shape.dimensions[1]==std::make_pair(width-1,0));previous=a;
      auto typed=rtl::veri_array_shape(mod->scope()->value_same_level("typed"));
      assert(typed.dimensions.size()==2&&typed.dimensions[1]==std::make_pair(width-1,0));
      auto cube=rtl::veri_array_shape(mod->scope()->value_same_level("cube"));
      assert(cube.dimensions.size()==3&&cube.dimensions[2]==std::make_pair(3,0));
    }
    rtl::Src_mgr::get_instance()->set_src(std::string("module legacy_tb;integer ref,const,logic;function integer new;input integer n;begin new=n+1;end endfunction initial begin ref=new(1);const=2;logic=3;end endmodule")+std::string(1,'\0'));
    assert(parser->init()==rtl::OK&&parser->systemverilog());
    parser->set_systemverilog(false);parser->set_top_module("");
    assert(parser->parse()==rtl::OK&&parser->get_top_module()=="legacy_tb");
    assert(parser->module("legacy_tb")->scope()->value_same_level("ref"));
  }
}

}

void test_complex_report_cleanup() {
  const std::string source=R"SV(
    module child(input logic clk);
      function automatic integer dbl(input integer x);dbl=2*x;endfunction
      function automatic integer fact(input integer n);if(n<=1)fact=1;else fact=n*fact(n-1);endfunction
      localparam integer P=dbl(8),Q=P[3:0];
      typedef struct {bit[7:0]address;logic[129:0]data;} packet_t;
      packet_t packets[0:1];integer r;logic[3:0]x;
      always @(posedge clk)x<=$past(x);
      initial begin packets[0].address=8'h11;r=fact(6);force x=4'd9;release x;end
    endmodule
    module top;logic clk;child a(clk),b(clk);endmodule
  )SV";
  for(int round=0;round<3;++round)analyze(source);
}

void test_package_subroutine_lifetimes_cleanup() {
  for(int round=0;round<3;++round) {
    analyze(R"SV(
      package automatic ap;
        integer shared=1;
        function integer inherited();integer n=1;return n;endfunction
        function static integer overridden();integer n=1;return n;endfunction
        task inherited_t();integer n=1;begin n++;end endtask
        task static overridden_t();integer n=1;begin n++;end endtask
      endpackage
      package static sp;
        function automatic integer overridden();return 1;endfunction
        function integer inherited();return 1;endfunction
      endpackage
      package plain;
        function integer inherited();return 1;endfunction
      endpackage
      module top;function static integer f();return 1;endfunction endmodule
    )SV");
    auto* parser=rtl::VeriParser::get_instance();
    auto* ap=parser->package("ap");auto* sp=parser->package("sp");
    auto function_lifetime=[](rtl::VeriMod* owner,const char* name) {
      return static_cast<rtl::VeriFunc*>(owner->scope()->value_same_level(name))->func()->is_auto();
    };
    assert(function_lifetime(ap,"inherited")==rtl::IS_TRUE);
    assert(function_lifetime(ap,"overridden")==rtl::IS_FALSE);
    assert(static_cast<rtl::VeriTask*>(ap->scope()->value_same_level("inherited_t"))->task()->is_auto()==rtl::IS_TRUE);
    assert(static_cast<rtl::VeriTask*>(ap->scope()->value_same_level("overridden_t"))->task()->is_auto()==rtl::IS_FALSE);
    assert(function_lifetime(sp,"overridden")==rtl::IS_TRUE);
    assert(function_lifetime(sp,"inherited")==rtl::IS_FALSE);
    assert(function_lifetime(parser->package("plain"),"inherited")==rtl::IS_FALSE);
    assert(function_lifetime(parser->module("top"),"f")==rtl::IS_FALSE);
    // A failed parse inside an automatic package must not affect the next unit.
    rtl::Src_mgr::get_instance()->set_src(std::string("package automatic broken; function")+std::string(1,'\0'));
    assert(parser->init()==rtl::OK);parser->set_top_module("top");assert(parser->parse()!=rtl::OK);
    auto* top=analyze("module top;function integer f();return 1;endfunction endmodule");
    assert(function_lifetime(top,"f")==rtl::IS_FALSE);
  }
}

void test_design_unit_subroutine_lifetimes_cleanup() {
  auto lifetime=[](rtl::VeriMod* m,const char* name) {
    return static_cast<rtl::VeriFunc*>(m->scope()->value_same_level(name))->func()->is_auto();
  };
  for(int round=0;round<3;++round) {
    auto* top=analyze(R"SV(
      package automatic p;function integer f();return 1;endfunction endpackage
      module automatic worker #(parameter N=1)();
        function integer f();integer x=N;return x;endfunction
        function static integer g();integer x=N;return x;endfunction
        task t(ref integer x);begin x++;end endtask
      endmodule
      interface automatic api;
        function integer f();return 1;endfunction
        function static integer g();return 1;endfunction
        modport view(import function integer f());
      endinterface
      module static fixed_worker;
        function integer f();return 1;endfunction
        function automatic integer g();return 1;endfunction
      endmodule
      module top;worker #(2) a();worker #(3) b();api bus();fixed_worker c();
        function integer f();return 1;endfunction
      endmodule
    )SV");
    auto instance=[&](const char* name) {
      auto* symbol=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      return static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(symbol->instance())->hive());
    };
    assert(lifetime(instance("a"),"f")==rtl::IS_TRUE);
    assert(lifetime(instance("a"),"g")==rtl::IS_FALSE);
    assert(static_cast<rtl::VeriTask*>(instance("a")->scope()->value_same_level("t"))->task()->is_auto()==rtl::IS_TRUE);
    assert(lifetime(instance("bus"),"f")==rtl::IS_TRUE);
    assert(lifetime(instance("bus"),"g")==rtl::IS_FALSE);
    assert(lifetime(instance("c"),"f")==rtl::IS_FALSE);
    assert(lifetime(instance("c"),"g")==rtl::IS_TRUE);
    assert(lifetime(top,"f")==rtl::IS_FALSE);
    auto* parser=rtl::VeriParser::get_instance();
    for(const char* broken:{"module automatic broken; function", "interface automatic broken; task"}) {
      rtl::Src_mgr::get_instance()->set_src(std::string(broken)+std::string(1,'\0'));
      assert(parser->init()==rtl::OK);parser->set_top_module("top");assert(parser->parse()!=rtl::OK);
      assert(lifetime(analyze("module top;function integer f();return 1;endfunction endmodule"),"f")==rtl::IS_FALSE);
    }
  }
}

// Unsupported declarations must not feed recovery placeholders into later
// class/generate reductions. A subsequent valid parse still owns clean state.
void test_unsupported_class_recovery() {
  auto* parser=rtl::VeriParser::get_instance();
  for(int round=0;round<3;++round) {
    for(const std::string source:{
      "package p; typedef class C; class C;endclass local function void f(); endfunction endpackage module top; endmodule",
      "module top; typedef class C; class C;endclass if(1) begin local function void f(); endfunction end endmodule",
      "package p; typedef class C; class C;endclass class D; rand randc int value; endclass endpackage module top;endmodule"}) {
      rtl::Src_mgr::get_instance()->set_src(source+std::string(1,'\0'));
      rtl::Src_mgr::get_instance()->set_fname("unsupported_class.sv");
      assert(parser->init()==rtl::OK);parser->set_top_module("top");
      bool rejected=false;try{rejected=parser->parse()!=rtl::OK;}catch(const std::runtime_error&){rejected=true;}
      assert(rejected);
      analyze("module top; class C; int value=7; endclass C obj; initial obj=new; endmodule");
    }
  }
}

void test_typed_for_cloning_cleanup() {
  const std::string source=R"SV(
    module child #(parameter int N=3);
      typedef logic[N-1:0] value_t;
      class C#(type T=int);T value;function new(T n);value=n;endfunction endclass
      int observed;
      initial begin
        for(C#(value_t) cursor=new(N),other=cursor;cursor.value>0;cursor.value--)
          observed+=other.value;
        for(value_t i=0,j=i+1;i<2;i++)observed+=j;
        for(int index=0;index<2;index++)observed++;
      end
    endmodule
    module top;child#(3) a();child#(7) b();endmodule
  )SV";
  for(int round=0;round<6;++round) {
    auto* top=analyze(source);
    unsigned expected_width=3;
    for(const char* name:{"a","b"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      unsigned declarations=0,variables=0;
      for(auto* item:static_cast<rtl::VeriModuleItemList*>(mod->item())->item_list()) {
        if(item->detail_type()!=vsSTMT_INIT)continue;
        rtl::VeriNode::NodeVec nodes{static_cast<rtl::VeriInitStmt*>(item)->stmt()};
        while(!nodes.empty()) {
          auto* node=nodes.back();nodes.pop_back();
          if(node->detail_type()==vsDECL_VAR||node->detail_type()==vsDECL_INT) {
            auto* decl=static_cast<rtl::VeriDecl*>(node);
            assert(decl->explicit_automatic()&&!decl->explicit_static());
            auto& vars=node->detail_type()==vsDECL_VAR?static_cast<rtl::VeriVarDecl*>(node)->vars():static_cast<rtl::VeriIntDecl*>(node)->vars();
            for(auto* child:vars) {
              assert(child->detail_type()==veEXP_PRI&&child->father()==node);
              auto* variable=static_cast<rtl::VeriVar*>(static_cast<rtl::VeriPrimaryExp*>(child)->var());
              assert(variable);
              if(auto* cls=rtl::veri_class_type(variable)) {
                auto* field=static_cast<rtl::VeriVar*>(cls->class_member("value"));
                assert(field&&field->dlen()==expected_width);
              } else if(static_cast<rtl::VeriPrimaryExp*>(child)->str()!="index")assert(variable->dlen()==expected_width);
              ++variables;
            }
            ++declarations;
          }
          node->push_for_replacement(nodes);
        }
      }
      assert(declarations==3&&variables==5);expected_width=7;
    }
  }
}

void test_constraint_foreach_cloning_cleanup() {
  for(int round=0;round<6;++round) {
    auto* mod=analyze(R"SV(module top;
      class C #(int N=4);
        rand bit [N-1:0] a;
        int entries[$];int i=99;
        constraint limits {foreach(entries[i]) {
          a>entries[i];foreach(entries[i])a>=i;
        }}
      endclass
      C #(4) one;C #(8) two;
      initial begin one=new;two=new;void'(one.randomize());void'(two.randomize());end
    endmodule)SV");
    rtl::VeriNode* previous=nullptr;
    for(const char* name:{"one","two"}) {
      auto* owner=rtl::veri_class_type(mod->scope()->value(name));assert(owner);
      auto* constraint=static_cast<rtl::VeriConstraintDecl*>(owner->class_member("limits"));
      auto* outer=static_cast<rtl::VeriConstraintForeach*>(constraint->body());
      assert(outer->detail_type()==veEXP_CONSTRAINT_FOREACH&&outer!=previous&&outer->father()==constraint);
      auto* outer_index=outer->index_scope()->value_same_level("i");assert(outer_index&&outer_index!=owner->class_member("i"));
      rtl::VeriNode::NodeVec nodes{outer->body()};bool nested=false,reference=false;
      while(!nodes.empty()) {
        auto* node=nodes.back();nodes.pop_back();
        if(node->detail_type()==veEXP_CONSTRAINT_FOREACH) {
          auto* inner=static_cast<rtl::VeriConstraintForeach*>(node);
          assert(inner->index_scope()!=outer->index_scope());
          assert(inner->index_scope()->value_same_level("i")!=outer_index);nested=true;
        }
        if(node->detail_type()==veEXP_PRI&&static_cast<rtl::VeriPrimaryExp*>(node)->str()=="i") {
          assert(static_cast<rtl::VeriPrimaryExp*>(node)->var()!=owner->class_member("i"));reference=true;
        }
        node->push_for_replacement(nodes);
      }
      assert(nested&&reference);previous=outer;
    }
  }
}

void test_constraint_class_cloning_cleanup() {
  for(int round=0;round<6;++round) {
    auto* mod=analyze(R"SV(module top;
      class C #(parameter int N=4);
        constraint limits {a inside {[1:N]};}
        rand bit [N-1:0] a;
        randc bit [N-1:0] cyclic_value;
      endclass
      C #(4) narrow_h; C #(8) wide_h;
      initial begin narrow_h=new;wide_h=new;
        void'(narrow_h.randomize() with {this.a==2;});
        void'(wide_h.randomize());
      end
    endmodule)SV");
    rtl::VeriNode* previous=nullptr;
    for(const char* name:{"narrow_h","wide_h"}) {
      auto* variable=static_cast<rtl::VeriVar*>(mod->scope()->value(name));
      auto* owner=variable->class_type();assert(owner);
      auto* field=owner->class_member("a");assert(field&&static_cast<rtl::VeriDecl*>(field->father())->rand_property());
      assert(!static_cast<rtl::VeriDecl*>(field->father())->randc_property());
      auto* cyclic=owner->class_member("cyclic_value");assert(cyclic);
      auto* cyclic_decl=static_cast<rtl::VeriDecl*>(cyclic->father());
      assert(cyclic_decl->rand_property()&&cyclic_decl->randc_property());
      auto* declaration=owner->class_member("limits");assert(declaration&&declaration->detail_type()==vsDECL_CONSTRAINT&&declaration!=previous);
      auto* constraint=static_cast<rtl::VeriConstraintDecl*>(declaration);assert(constraint->body()->father()==constraint);
      rtl::VeriNode::NodeVec nodes{constraint->body()};bool found=false;
      while(!nodes.empty()) {auto* node=nodes.back();nodes.pop_back();
        if(node->detail_type()==veEXP_PRI&&static_cast<rtl::VeriPrimaryExp*>(node)->str()=="a") {
          assert(static_cast<rtl::VeriPrimaryExp*>(node)->var()==field);found=true;
        }
        node->push_for_replacement(nodes);
      }
      assert(found);previous=declaration;
    }
  }
}

void test_struct_string_cloning_cleanup() {
  const std::string source=R"SV(
    module endpoint #(parameter int N=1);
      typedef struct {string name;int count;} item_t;
      typedef struct {item_t item;string label;} record_t;
      record_t value;
      function automatic item_t echo(input item_t src);return src;endfunction
    endmodule
    module top;endpoint #(1) a();endpoint #(2) b();endmodule)SV";
  for(int round=0;round<5;++round) {
    auto* top=analyze(source);
    for(const char* name:{"a","b"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* value=static_cast<rtl::VeriVar*>(mod->scope()->value_same_level("value"));
      auto* type=value->aggregate_type();assert(type&&type->unpacked_struct());
      assert(type->packed_fields().size()==2);
      auto* inner=type->packed_fields()[0].symbol->aggregate_type();assert(inner&&inner->unpacked_struct());
      assert(inner->packed_fields()[0].symbol->net_type()==vvSTRING);
      assert(rtl::veri_string_value(inner->packed_fields()[0].symbol));
    }
  }
}

void test_chandle_cloning_cleanup() {
  const std::string source=R"SV(
    module endpoint #(parameter int N=1);
      typedef chandle H;H h;
      function automatic H echo(input H value);return value;endfunction
    endmodule
    module top;endpoint #(1) a();endpoint #(2) b();endmodule)SV";
  for(int round=0;round<5;++round) {
    auto* top=analyze(source);
    for(const char* name:{"a","b"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* handle=static_cast<rtl::VeriVar*>(mod->scope()->value_same_level("h"));
      auto* function=static_cast<rtl::VeriFunc*>(mod->scope()->value_same_level("echo"));
      assert(handle->net_type()==vvCHANDLE&&handle->dlen()==64);
      assert(rtl::veri_chandle_value(handle)&&!rtl::veri_class_type(handle));
      assert(rtl::veri_chandle_value(function));
      assert(veri_two_state(handle->net_type())&&!veri_integral_atom(handle->net_type()));
      assert(rtl::veri_array_shape(handle).dimensions.empty());
    }
  }
}

void test_dpi_declarations_and_cleanup() {
  const std::string valid=R"SV(package api;
    import "DPI-C" pure native = function int f(input int x);
    export "DPI-C" exported = function g;
    function automatic int g(input int x);return f(x);endfunction
    endpackage
    module endpoint #(parameter int W=3);
      import "DPI-C" context function void call_c(input logic[W-1:0] x);
      export "DPI-C" function callback;
      function int callback(input int x);return x;endfunction
    endmodule
    module top;endpoint #(3) a();endpoint #(7) b();endmodule)SV";
  auto* parser=rtl::VeriParser::get_instance();
  for(int round=0;round<3;++round) {
    auto* top=analyze(valid);
    for(const char* name:{"a","b"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* decl=static_cast<rtl::VeriFunc*>(mod->scope()->value_same_level("call_c"))->func();
      assert(decl->dpi_import()&&decl->dpi_name()=="call_c"&&decl->dpi_property()==2&&decl->is_auto()==rtl::IS_TRUE);
    }
    auto* decl=static_cast<rtl::VeriFunc*>(parser->package("api")->scope()->value_same_level("f"))->func();
    assert(decl->dpi_import()&&decl->dpi_name()=="native"&&decl->dpi_property()==1);
    for(const char* source:{"module top;import \"DPI\" function int f();endmodule",
                            "module top;import \"DPI-C\" task f();endmodule",
                            "module top;class C;import \"DPI-C\" function int f();endclass endmodule",
                            "import \"DPI-C\" function int f();module top;endmodule",
                            "module top;export \"DPI-C\" function ;endmodule"}) {
      rtl::Src_mgr::get_instance()->set_src(std::string(source)+std::string(1,'\0'));
      assert(parser->init()==rtl::OK);parser->set_top_module("top");
      bool rejected=false;try{rejected=parser->parse()!=rtl::OK;}catch(const std::runtime_error&){rejected=true;}
      assert(rejected);analyze(valid);
    }
  }
}

void test_anonymous_enum_cloning_cleanup() {
  auto* parser=rtl::VeriParser::get_instance();
  for(int round=0;round<4;++round) {
    auto* top=analyze(R"SV(module child #(parameter int W=3);
      enum logic[W-1:0] {LOW=1,HIGH=3} a=LOW,b=a,q[$];
      enum {IDLE,RUN} state;
      typedef int optional_t[$];
      function automatic optional_t empty();return '{};endfunction
      const int limit=7;
      endmodule
      module top;child #(3) u();child #(7) v();endmodule)SV");
    rtl::VeriVar* previous=nullptr;
    for(const char* name:{"u","v"}) {
      auto* inst=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(inst->instance())->hive());
      auto var=[&](const char* n){return static_cast<rtl::VeriVar*>(mod->scope()->value_same_level(n));};
      auto* type=var("a")->enum_type();assert(type&&type!=previous);previous=type;
      assert(type->tok_type()==vtTYPE&&type->name().empty());
      assert(var("a")->dlen()==(std::string(name)=="u"?3:7));
      assert(var("b")->enum_type()==type&&var("q")->enum_type()==type);
      assert(var("state")->enum_type()!=type);
      auto* low=static_cast<rtl::VeriParam*>(mod->scope()->value_same_level("LOW"));
      assert(low->enum_type()==type&&low->get_val()->get_first_int()==1);
    }
    auto* clean=analyze("module top;enum {ZERO,ONE} a;endmodule");
    assert(clean&&parser->module("child")==nullptr);
  }
}

void test_time_scope_cloning_cleanup() {
  for(int round=0;round<4;++round) {
    auto* top=analyze("timeunit 10ns/1ps;"
      "package p;timeunit 100ps/10ps;parameter realtime P=950ps;endpackage "
      "module child #(parameter realtime D=250ps)();timeunit 1ns/100ps;"
      "localparam realtime A=1.25ns;endmodule "
      "module top;timeunit 1us/1ps;child a();child #(.D(250ps)) b();endmodule");
    assert(top->time_scale().unit_fs==1000000000ULL&&top->time_scale().precision_fs==1000);
    auto* parser=rtl::VeriParser::get_instance();
    assert(parser->time_precision_fs()==1000);
    auto* package=parser->package("p");assert(package&&package->time_scale().unit_fs==100000);
    assert(static_cast<rtl::VeriParam*>(package->scope()->value_same_level("P"))->get_val()->real_value()==9.5);
    rtl::VeriMod* previous=nullptr;
    for(const auto& name:{"a","b"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      assert(mod!=previous);previous=mod;
      assert(mod->time_scale().unit_fs==1000000&&mod->time_scale().precision_fs==100000);
      const auto value=[&](const char* param){return static_cast<rtl::VeriParam*>(mod->scope()->value_same_level(param))->get_val()->real_value();};
      assert(value("A")==1.25);
      assert(value("D")== (std::string(name)=="a"?0.25:0.00025));
    }
    // No compilation-unit scale, precision minimum or callback survives init.
    top=analyze("module top;parameter realtime D=1ns;endmodule");
    assert(top->time_scale().unit_fs==1000000000000000ULL);
    assert(rtl::VeriParser::get_instance()->time_precision_fs()==1000000000000000ULL);
    assert(static_cast<rtl::VeriParam*>(top->scope()->value_same_level("D"))->get_val()->real_value()==1e-9);
  }
}

void test_clocking_cloning_cleanup() {
  const std::string source=R"SV(
    module endpoint #(parameter int W=65);
      logic clk;logic[W-1:0] data;
      clocking cb @(posedge clk);
        default input #1step output #2;
        input sampled=data, copy=data;
        output driven=data;
      endclocking : cb
      default clocking cb;
      initial begin ##2;cb.driven<=cb.sampled;@(cb);end
    endmodule
    module top;endpoint #(65) a();endpoint #(129) b();endmodule)SV";
  for(int round=0;round<8;++round) {
    auto* top=analyze(source);rtl::VeriClocking* previous=nullptr;
    for(const char* name:{"a","b"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* clock=static_cast<rtl::VeriClocking*>(mod->scope()->value_same_level("cb"));
      assert(clock&&clock->detail_type()==vsDECL_CLOCKING&&clock!=previous);previous=clock;
      assert(clock->ports().size()==5);
      for(auto* port:clock->ports())if(!port->name.empty()) {
        assert(port->children[0]->father()==port);
        assert(rtl::veri_bit_width(port->children[0])==(name[0]=='a'?65:129));
      }
      rtl::VeriNode::NodeVec pending{mod->item()};int members=0;
      while(!pending.empty()) {
        auto* node=pending.back();pending.pop_back();
        if(node->tok_type()==vtEXP&&node->detail_type()==veEXP_MEMBER) {
          auto* member=static_cast<rtl::VeriMemberExp*>(node);
          assert(member->clocking_owner()==clock&&member->clocking_source());++members;
        }
        node->push_for_replacement(pending);
      }
      assert(members==2);
    }
  }
}

void test_coverage_cloning_cleanup() {
  const std::string source=R"SV(
    module endpoint #(parameter int W=3);
      bit clk;bit[W-1:0] value;
      covergroup cg @(posedge clk);
        option.per_instance=1;
        cp:coverpoint value {bins lo={[0:1]};bins hi={[2:3]};}
      endgroup
      cg c;
      class Monitor;
        bit[W-1:0] data;
        covergroup cg;
          option.per_instance=1;cp:coverpoint this.data;
        endgroup
        function new();cg=new();endfunction
      endclass
      Monitor m;
      initial begin c=new();m=new();m.cg.sample();end
    endmodule
    module top;endpoint #(3) a();endpoint #(4) b();endmodule)SV";
  for(int round=0;round<5;++round) {
    auto* top=analyze(source);rtl::VeriSeqBlock* previous=nullptr;
    for(const char* name:{"a","b"}) {
      auto* instance=static_cast<rtl::VeriModInst*>(top->scope()->value_same_level(name));
      auto* mod=static_cast<rtl::VeriMod*>(static_cast<rtl::VeriModInstance*>(instance->instance())->hive());
      auto* type=rtl::veri_class_type(mod->scope()->value_same_level("cg"));
      assert(type&&type->coverage_type()&&type!=previous);previous=type;
      auto* metadata=static_cast<rtl::VeriClocking*>(static_cast<rtl::VeriModuleItemList*>(type->decl_list())->item_list().front());
      assert(metadata->detail_type()==vsDECL_COVERAGE&&metadata->children[0]->father()==metadata);
      auto* items=static_cast<rtl::VeriModuleItemList*>(metadata->children[1]);
      auto* cp=static_cast<rtl::VeriClocking*>(items->item_list().back());
      assert(rtl::veri_bit_width(cp->children[0])==(name[0]=='a'?3:4));
    }
    auto* parser=rtl::VeriParser::get_instance();
    rtl::Src_mgr::get_instance()->set_src(std::string("module top;covergroup cg;cp:coverpoint v {bins b={1};}endgroup:wrong endmodule")+std::string(1,'\0'));
    assert(parser->init()==rtl::OK);parser->set_top_module("top");
    bool rejected=false;try{rejected=parser->parse()!=rtl::OK;}catch(const std::runtime_error&){rejected=true;}assert(rejected);
  }
}

int main(int argc, char** argv) {
  if(argc==3) {
    std::ifstream input(argv[1]);
    assert(input.good());
    const std::string source((std::istreambuf_iterator<char>(input)),{});
    for(int round=0;round<3;++round) analyze(source,rtl::OK,argv[2]);
    std::cout<<"PASS corpus second pass and repeated cleanup: "<<argv[2]<<"\n";
    return 0;
  }
  test_growing_symbol_scopes();
  test_nonexpression_type_queries();
  test_shared_subroutine_cleanup();
  test_dpi_declarations_and_cleanup();
  test_time_scope_cloning_cleanup();
  test_anonymous_enum_cloning_cleanup();
  test_constraint_class_cloning_cleanup();
  test_constraint_foreach_cloning_cleanup();
  test_typed_for_cloning_cleanup();
  test_unsupported_class_recovery();
  test_class_forward_cloning_cleanup();
  test_forward_specialization_cleanup();
  test_signature_initializer_cleanup();
  test_forward_alias_cleanup();
  test_named_container_cloning_cleanup();
  test_selection_eof_recovery();
  test_variable_port_elements_and_cleanup();
  test_enum_methods_and_cleanup();
  test_empty_subroutine_ports_and_syntax_recovery();
  test_subroutine_end_labels_and_recovery();
  test_array_alias_cloning_cleanup();
  test_dynamic_subarray_and_delay_call_cleanup();
  test_level_wait_and_cleanup();
  test_named_events_and_cleanup();
  test_instance_events_and_cleanup();
  test_expression_events_and_cleanup();
  test_conditional_events_and_cleanup();
  test_function_events_and_cleanup();
  test_qualified_named_events_and_cleanup();
  test_intra_event_assignments_and_cleanup();
  test_fork_join_and_cleanup();
  test_named_disable_and_labels_cleanup();
  test_fork_control_cleanup();
  test_explicit_automatic_cleanup();
  test_explicit_static_cleanup();
  test_wait_order_cleanup();
  test_ref_arguments_cleanup();
  test_const_ref_cleanup();
  test_array_arguments_cleanup();
  test_dynamic_declaration_initializers_cleanup();
  test_fixed_declaration_initializers_cleanup();
  test_packed_dimensions_and_keyword_modes_cleanup();
  test_dynamic_array_cleanup();
  test_open_array_cleanup();
  test_pool_reset(false);
  test_pool_reset(true);
  test_word_boundaries();
  test_padded_negative_constants();
  test_relational_constants();
  test_scope_cleanup();
  test_declarations();
  test_integer_block_scopes();
  test_loop_control_cloning();
  test_action_cloning();
  test_increment_expression_cloning();
  test_random_expression_cloning();
  test_file_function_cloning();
  test_scan_function_cloning();
  test_testbench_function_cloning();
  test_integral_type_cloning();
  test_two_state_type_cloning();
  test_reduction_parity();
  test_subroutine_types();
  test_ports();
  test_interface_binding_cleanup();
  test_default_formal_scope_cleanup();
  test_process_type_cleanup();
  test_ipc_type_cleanup();
  test_queue_last_and_unsigned_key_cleanup();
  test_modport_prototype_cleanup();
  test_header_import_cloning_cleanup();
  test_multidimensional_associative_cleanup();
  test_runtime_container_cloning_cleanup();
  test_class_inheritance_cloning_cleanup();
  test_parameterized_class_cloning_cleanup();
  test_class_parameter_lists_cleanup();
  test_class_body_parameters_cleanup();
  test_struct_container_metadata_cleanup();
  test_parameterized_formals_cleanup();
  test_string_associative_cloning_cleanup();
  test_object_key_associative_cloning_cleanup();
  test_integral_key_associative_cloning_cleanup();
  test_packed_key_associative_cleanup();
  test_string_queue_cloning_cleanup();
  test_clocking_cloning_cleanup();
  test_coverage_cloning_cleanup();
  test_foreach_selection_cloning_cleanup();
  test_class_access_cloning_cleanup();
  test_extern_method_cloning_cleanup();
  test_class_static_cloning_cleanup();
  test_abstract_class_cloning_cleanup();
  test_class_object_cloning_cleanup();
  test_compilation_import_cloning_cleanup();
  test_compilation_types_identity_cleanup();
  test_chandle_cloning_cleanup();
  test_struct_string_cloning_cleanup();
  test_package_export_identity_cleanup();
  test_final_bind_cleanup();
  test_array_ports_and_cleanup();
  test_array_copy_and_cleanup();
  test_assignment_patterns_cleanup();
  test_streaming_cleanup();
  test_array_reductions_cleanup();
  test_reduction_with_cleanup();
  test_report_fixes_cleanup();
  test_packages_cleanup();
  test_package_subroutine_lifetimes_cleanup();
  test_design_unit_subroutine_lifetimes_cleanup();
  test_strings_cleanup();
  test_properties_cleanup();
  test_complex_report_cleanup();
  test_parameters();
  test_typed_parameter_cloning();
  test_constant_division_shifts();
  test_reduction_truth_tables();
  test_immediate_assertion_cloning();
  test_explicit_casts();
  test_real_types_and_constants();
  test_string_casts_and_parameters();
  test_named_integral_types();
  test_enum_types();
  test_unsigned_enum_initializers_cleanup();
  test_vector_system_functions();
  test_array_queries();
  test_packed_aggregates();
  test_implicit_named_connections();
  test_four_state_case_equality();
  test_invalid_typedef_bounds();
  test_hierarchical_procedural_loops();
  test_public_entry();
  test_primitive_groups();
  test_dump_targets();
  test_systemverilog_sized_casts();
  std::cout<<"PASS semantic memory, values, widths, ports and repeated cleanup\n";
}
