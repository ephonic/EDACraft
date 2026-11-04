module top;
 class Base;
  rand int a;
  int pre_calls=0,post_calls=0,minimum=0;
  constraint range_c {a inside {[0:4]};}
  function void pre_randomize();pre_calls++;endfunction
  function void post_randomize();post_calls++;endfunction
 endclass
 class Derived extends Base;
  rand int b;
  constraint range_c {a inside {[10:20]};a>=minimum;}
  constraint relation {b==a+1;}
  function void pre_randomize();super.pre_randomize();minimum=12;endfunction
 endclass
 class Param #(parameter int N=8);
  rand bit [N-1:0] v;
  constraint value_c {v==N+3;}
 endclass
 Base base_h;Derived d;Param #(12) p;
 int i;int limit;
 initial begin
  d=new;base_h=d;p=new;limit=15;
  for(i=0;i<5;i++)begin
   if(!base_h.randomize())$fatal(1,"dynamic randomize");
   if(d.a<12||d.a>20||d.b!=d.a+1)$fatal(1,"inheritance constraints");
  end
  if(d.pre_calls!=5||d.post_calls!=5)$fatal(1,"callbacks");
  if(!d.randomize() with {a==limit;})$fatal(1,"inline constraint");
  if(d.a!=15||d.b!=16)$fatal(1,"inline result");
  if(!p.randomize()||p.v!=15)$fatal(1,"parameter constraint");
  $display("TRACE constraints inheritance callbacks inline parameters pass");$finish;
 end
endmodule
