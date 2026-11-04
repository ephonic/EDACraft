#pragma once
// Embedded after runtime.hpp, only in models using constrained randomization.
#include <z3++.h>
#include <numeric>
namespace dsim {
class ConstraintSolver {
 public:
  struct Value {z3::expr bits,valid;};
 private:
  z3::context context;
  z3::solver solver{context};
  std::vector<z3::expr> variables;
  struct Cycle {
    unsigned variable;std::string* saved_constraints;std::vector<V>* saved_used;
    std::string constraints;std::vector<V> used;
  };
  std::vector<Cycle> cycles;
  static unsigned width(const Value& v) {return v.bits.get_sort().bv_size();}
  z3::expr truth(const Value& v) {return v.bits!=context.bv_val(0,width(v));}
  Value boolean(z3::expr b,z3::expr valid) {return {z3::ite(b,context.bv_val(1,1),context.bv_val(0,1)),valid};}
  void add_conjuncts(z3::expr e,std::vector<z3::expr>& out) {
    if(e.is_and()){for(unsigned i=0;i<e.num_args();++i)add_conjuncts(e.arg(i),out);}
    else if(!e.is_true())out.push_back(e);
  }
  void dependencies(z3::expr e,std::set<unsigned>& found,std::set<unsigned>& visited) {
    if(!visited.insert(e.id()).second)return;
    for(unsigned i=0;i<variables.size();++i)if(z3::eq(e,variables[i])){found.insert(i);return;}
    for(unsigned i=0;i<e.num_args();++i)dependencies(e.arg(i),found,visited);
  }
  std::string cycle_constraints(unsigned variable) {
    // Only assertions connected to this field invalidate its permutation.
    // Changing an unrelated rand field's constraints must not restart a cycle.
    std::vector<z3::expr> atoms;
    for(auto assertion:solver.assertions())add_conjuncts(assertion.simplify(),atoms);
    std::vector<std::set<unsigned>> uses(atoms.size());
    for(size_t i=0;i<atoms.size();++i){std::set<unsigned> visited;dependencies(atoms[i],uses[i],visited);}
    std::set<unsigned> reached{variable};std::vector<bool> selected(atoms.size(),false);bool changed=true;
    while(changed){changed=false;for(size_t i=0;i<atoms.size();++i)if(!selected[i]){
      for(auto v:uses[i])if(reached.count(v)){selected[i]=true;reached.insert(uses[i].begin(),uses[i].end());changed=true;break;}
    }}
    std::vector<std::string> text;
    for(size_t i=0;i<atoms.size();++i)if(selected[i])text.push_back(atoms[i].to_string());
    std::sort(text.begin(),text.end());std::string result;
    for(const auto& s:text)result+=std::to_string(s.size())+":"+s;
    return result;
  }
 public:
  Value resize(Value v,unsigned w,bool sign=false) {
    auto old=width(v);if(old<w)v.bits=sign?z3::sext(v.bits,w-old):z3::zext(v.bits,w-old);
    else if(old>w)v.bits=v.bits.extract(w-1,0);return v;
  }
  Value constant(const V& v) {
    z3::expr bits=context.bv_val(0,unsigned(v.w));
    for(int i=v.w;i-->0;) {auto bit=v.bit(i);if(bit>1)throw std::runtime_error("X/Z state value in constraint expression");
      if(bit==1)bits=bits|z3::shl(context.bv_val(1,unsigned(v.w)),context.bv_val(unsigned(i),unsigned(v.w)));}
    return {bits.simplify(),context.bool_val(true)};
  }
  Value variable(unsigned w,const char* name=nullptr) {
    auto bits=context.bv_const(name?name:("r"+std::to_string(variables.size())).c_str(),w);
    variables.push_back(bits);return {bits,context.bool_val(true)};
  }
  size_t variable_count() const {return variables.size();}
  Value element(const std::vector<Value>& values,Value index,unsigned element_width) {
    index=resize(index,std::max(32u,width(index)));
    auto fixed=index.bits.simplify();uint64_t offset;
    if(fixed.is_numeral()) {
      if(fixed.is_numeral_u64(offset)&&offset<values.size())return {values[offset].bits,index.valid&&values[offset].valid};
      return {context.bv_val(0,element_width),context.bool_val(false)};
    }
    auto bits=context.bv_val(0,element_width);
    for(size_t i=values.size();i-->0;)bits=z3::ite(index.bits==context.bv_val(uint64_t(i),width(index)),values[i].bits,bits);
    return {bits,index.valid&&z3::ult(index.bits,context.bv_val(uint64_t(values.size()),width(index)))};
  }
  Value state_element(const std::vector<V>& values,Value index,unsigned element_width) {
    auto fixed=index.bits.simplify();uint64_t offset;
    if(fixed.is_numeral()) {
      if(fixed.is_numeral_u64(offset)&&offset<values.size()){auto value=constant(values[offset]);value.valid=value.valid&&index.valid;return value;}
      return {context.bv_val(0,element_width),context.bool_val(false)};
    }
    std::vector<Value> elements;elements.reserve(values.size());
    for(const auto& value:values)elements.push_back(constant(value));
    return element(elements,index,element_width);
  }
  void cyclic(Value v,std::string& constraints,std::vector<V>& used) {
    for(unsigned i=0;i<variables.size();++i)if(z3::eq(v.bits,variables[i])){
      cycles.push_back({i,&constraints,&used,{},{}});return;
    }
    throw std::runtime_error("cyclic randomization requires a solver variable");
  }
  void domain(Value v,std::initializer_list<V> members) {
    z3::expr_vector alternatives(context);
    for(const auto& member:members)alternatives.push_back(v.bits==resize(constant(member),width(v)).bits);
    solver.add(v.valid&&z3::mk_or(alternatives));
  }
  Value unary(const std::string& op,Value a) {
    if(op=="+")return a;if(op=="-")return {-a.bits,a.valid};if(op=="~")return {~a.bits,a.valid};
    if(op=="!")return boolean(!truth(a),a.valid);
    if(op=="&")return boolean(a.bits==~context.bv_val(0,width(a)),a.valid);
    if(op=="|")return boolean(truth(a),a.valid);
    if(op=="^"){auto bit=a.bits.extract(0,0);for(unsigned i=1;i<width(a);++i)bit=bit^a.bits.extract(i,i);return {bit,a.valid};}
    throw std::runtime_error("unsupported constraint unary operator: "+op);
  }
  Value binary(const std::string& op,Value a,Value b,bool sign=false) {
    auto valid=a.valid&&b.valid;
    if(op=="&&")return boolean(truth(a)&&truth(b),a.valid&&( !truth(a)||b.valid));
    if(op=="||")return boolean(truth(a)||truth(b),a.valid&&( truth(a)||b.valid));
    if(op=="+")return {a.bits+b.bits,valid};if(op=="-")return {a.bits-b.bits,valid};
    if(op=="*")return {a.bits*b.bits,valid};
    if(op=="/")return {sign?a.bits/b.bits:z3::udiv(a.bits,b.bits),valid&&truth(b)};
    if(op=="%")return {sign?z3::srem(a.bits,b.bits):z3::urem(a.bits,b.bits),valid&&truth(b)};
    if(op=="&")return {a.bits&b.bits,valid};if(op=="|")return {a.bits|b.bits,valid};if(op=="^")return {a.bits^b.bits,valid};
    if(op=="=="||op=="===")return boolean(a.bits==b.bits,valid);
    if(op=="!="||op=="!==")return boolean(a.bits!=b.bits,valid);
    if(op=="<")return boolean(sign?a.bits<b.bits:z3::ult(a.bits,b.bits),valid);
    if(op==">")return boolean(sign?a.bits>b.bits:z3::ugt(a.bits,b.bits),valid);
    if(op=="<=")return boolean(sign?a.bits<=b.bits:z3::ule(a.bits,b.bits),valid);
    if(op==">=")return boolean(sign?a.bits>=b.bits:z3::uge(a.bits,b.bits),valid);
    if(op=="concat")return {z3::concat(a.bits,b.bits),valid};
    if(op=="<<"||op==">>"||op==">>>") {
      // Preserve oversized shift counts: narrowing them would wrap modulo 2^W.
      auto w=width(a);auto count=resize(b,std::max(w,width(b))).bits;
      auto large=z3::uge(count,context.bv_val(w,count.get_sort().bv_size()));
      auto small=resize(b,w).bits;
      auto shifted=op=="<<"?z3::shl(a.bits,small):op==">>>"&&sign?z3::ashr(a.bits,small):z3::lshr(a.bits,small);
      auto fill=op==">>>"&&sign?z3::ite(a.bits.extract(w-1,w-1)==context.bv_val(1,1),~context.bv_val(0,w),context.bv_val(0,w)):context.bv_val(0,w);
      return {z3::ite(large,fill,shifted),valid};
    }
    throw std::runtime_error("unsupported constraint binary operator: "+op);
  }
  Value choose(Value c,Value a,Value b) {return {z3::ite(truth(c),a.bits,b.bits),c.valid&&z3::ite(truth(c),a.valid,b.valid)};}
  Value slice(Value v,unsigned low,unsigned w) {return {v.bits.extract(low+w-1,low),v.valid};}
  void require(Value v) {solver.add(v.valid&&truth(v));}
  template<class Random> bool solve(Random random,std::vector<V>& output) {
    auto checked=[&](){auto status=solver.check();if(status==z3::unknown)throw std::runtime_error("constraint solver returned unknown: "+solver.reason_unknown());return status==z3::sat;};
    // Failed randomization leaves property values untouched. Discard the
    // active cyclic permutations, matching a fresh cycle on the next call.
    auto failed=[&](){for(auto& cycle:cycles){cycle.saved_constraints->clear();cycle.saved_used->clear();}return false;};
    if(!checked())return failed();
    // Determine exhaustion against the base constraints, independently for
    // each cyclic field. An inconsistent combination of live cycles is UNSAT,
    // not permission to silently discard their histories.
    for(auto& cycle:cycles){
      cycle.constraints=cycle_constraints(cycle.variable);
      cycle.used=cycle.constraints==*cycle.saved_constraints?*cycle.saved_used:std::vector<V>{};
      solver.push();for(const auto& old:cycle.used)solver.add(variables[cycle.variable]!=constant(old).bits);
      bool remaining=checked();solver.pop();if(!remaining)cycle.used.clear();
    }
    for(const auto& cycle:cycles)for(const auto& old:cycle.used)solver.add(variables[cycle.variable]!=constant(old).bits);
    if(!checked())return failed();
    // Random bit preferences never substitute for an actual SAT/UNSAT decision.
    // The complete model is materialized before the caller updates any variable.
    std::vector<unsigned> solve_order;std::set<unsigned> cyclic_indices;
    for(const auto& cycle:cycles){solve_order.push_back(cycle.variable);cyclic_indices.insert(cycle.variable);}
    for(unsigned i=0;i<variables.size();++i)if(!cyclic_indices.count(i))solve_order.push_back(i);
    for(auto index:solve_order) {
      const auto& v=variables[index];
      unsigned w=v.get_sort().bv_size();std::vector<unsigned> order(w);std::iota(order.begin(),order.end(),0);
      for(unsigned i=w;i>1;--i)std::swap(order[i-1],order[uint64_t(random())%i]);
      uint32_t bits=0;unsigned left=0;
      for(auto bit:order) {
        if(!left){bits=random();left=32;}unsigned wanted=bits&1;bits>>=1;--left;
        auto preference=v.extract(bit,bit)==context.bv_val(wanted,1);
        solver.push();solver.add(preference);bool sat=checked();solver.pop();solver.add(sat?preference:!preference);
      }
    }
    if(!checked())throw std::runtime_error("constraint solver lost a satisfiable model");
    auto model=solver.get_model();std::vector<V> solved;
    for(const auto& v:variables) {
      unsigned w=v.get_sort().bv_size();auto value=model.eval(v,true);
#ifdef DSIM_WIDE_VALUES
      if(w>64) {
        std::vector<V::Word> words((w+63)/64);
        for(unsigned i=0;i<words.size();++i)words[i].a=model.eval(value.extract(std::min(w,i*64+64)-1,i*64),true).get_numeral_uint64();
        solved.push_back(V::from_words(std::move(words),int(w)));continue;
      }
#endif
      solved.emplace_back(value.get_numeral_uint64(),0,int(w));
    }
    for(auto& cycle:cycles){cycle.used.push_back(solved.at(cycle.variable));*cycle.saved_constraints=std::move(cycle.constraints);*cycle.saved_used=std::move(cycle.used);}
    output=std::move(solved);return true;
  }
};
}
