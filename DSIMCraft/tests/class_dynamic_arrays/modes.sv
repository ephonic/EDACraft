module top;
 class Base;
  rand bit [7:0] data[];
  rand logic [7:0] untouched[];
  bit [7:0] other[];
  int requested=3;
  int pre_count,post_count;
  constraint sizes {data.size()==requested;}
  constraint contents {foreach(data[i])data[i]==i+4;}
  function void pre_randomize();pre_count++;endfunction
  function void post_randomize();post_count++;endfunction
 endclass
 class Derived extends Base;rand int tag;constraint ctag {tag==21;}endclass
 Base p;Derived child;int observed;
 initial begin
  child=new;p=child;p.untouched=new[2];p.untouched.rand_mode(0);
  if(!p.randomize()||p.data.size()!=3||child.tag!=21)$fatal(1,"derived randomization");
  p.data.rand_mode(0);
  if(!p.randomize()||p.data[1]!=5)$fatal(1,"disabled array");
  if(!p.randomize(null))$fatal(1,"array checker");
  p.other=new[2];
  if(!p.randomize(other) with {foreach(other[i])other[i]==i+11;}||p.other[1]!=12||p.data[1]!=5)$fatal(1,"named ordinary array");
  p.sizes.constraint_mode(0);p.data.rand_mode(1);p.data=new[4];
  if(!p.randomize()||p.data.size()!=4||p.data[3]!=7)$fatal(1,"unconstrained size retains allocation");
  if(p.pre_count!=5||p.post_count!=5)$fatal(1,"callback counts");
  observed=p.data[3];
  $display("TRACE class dynamic inherited modes callbacks named arrays pass");$finish;
 end
endmodule
