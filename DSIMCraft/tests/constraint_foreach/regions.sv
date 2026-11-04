`timescale 1ps/1ps
module top;
 class Region;
  int unsigned first,last;
  function new(int unsigned a,b);first=a;last=b;endfunction
 endclass
 class Policy;
  rand bit [7:0] start;
  int unsigned length=4;
  Region in_use[$];
  int pre_count=0,post_count=0;
  bit add_region=0;
  constraint limits {start inside {[0:31]};start<=32-length;}
  constraint no_overlap {
   foreach(in_use[i]) {
    !(start<=in_use[i].last && start+length-1>=in_use[i].first);
   }
  }
  function void pre_randomize();
   Region r;
   pre_count++;
   if(add_region)begin r=new(0,27);in_use.push_back(r);add_region=0;end
  endfunction
  function void post_randomize();post_count++;endfunction
 endclass
 Policy p,other;
 Region a,b;
 bit [7:0] saved;
 initial begin
  p=new;other=new;
  if(!p.randomize())$fatal(1,"empty foreach must be true");
  a=new(0,11);b=new(16,31);p.in_use.push_back(a);p.in_use.push_back(b);
  repeat(12)if(!p.randomize()||p.start!=12)$fatal(1,"non-overlap constraints");
  if(other.in_use.size()!=0||p.in_use.size()!=2)$fatal(1,"per-object queue");
  saved=p.start;
  a.last=15;
  if(p.randomize()||p.start!==saved)$fatal(1,"unsat must preserve fields");
  p.no_overlap.constraint_mode(0);
  if(!p.randomize() with {start==3;})$fatal(1,"constraint mode");
  p.no_overlap.constraint_mode(1);
  if(p.randomize(null))$fatal(1,"null checker ignores foreach");
  p.in_use.delete();p.add_region=1;
  if(!p.randomize()||p.start!=28||p.in_use.size()!=1)$fatal(1,"pre callback queue mutation");
  if(p.pre_count!=17||p.post_count!=15)$fatal(1,"callback accounting");
  $display("TRACE constraint foreach current object queue overlap callbacks pass");$finish;
 end
endmodule
