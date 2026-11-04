module top;
 class C;
  rand int a,b;
  constraint ca {a inside {[1:9]};}
  constraint cb {b==a+1;}
 endclass
 C c;int observed;
 initial begin
  c=new;c.a=3;c.b=4;c.a.rand_mode(0);
  if($bits(c.a.rand_mode())!=32||$bits(c.ca.constraint_mode())!=32)$fatal(1,"random mode return type");
  if(c.a.rand_mode()!=0||c.b.rand_mode()!=1)$fatal(1,"individual rand mode");
  if(!c.randomize()||c.a!=3||c.b!=4)$fatal(1,"frozen variable");
  c.ca.constraint_mode(0);c.a=-8;
  if(c.ca.constraint_mode()!=0||c.cb.constraint_mode()!=1)$fatal(1,"individual constraint mode");
  if(!c.randomize()||c.a!=-8||c.b!=-7)$fatal(1,"disabled constraint");
  c.constraint_mode(0);c.rand_mode(0);c.b=-9;
  if(!c.randomize()||c.a!=-8||c.b!=-9)$fatal(1,"all modes disabled");
  c.a.rand_mode(1);c.constraint_mode(1);
  if(c.randomize()||c.a!=-8||c.b!=-9)$fatal(1,"frozen relation contradiction");
  c.b.rand_mode(1);
  if(!c.randomize()||c.a<1||c.a>9||c.b!=c.a+1)$fatal(1,"restored modes");
  observed=c.b-c.a;
  if(observed!=1)$fatal(1,"observed relation");
  $display("TRACE constraints individual and object modes pass");$finish;
 end
endmodule
