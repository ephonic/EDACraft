module top;
 class Base;
  int value;
  randc bit [1:0] a;
  rand int b;
  constraint cv {value inside {[1:20]};}
  constraint cb {b inside {[30:40]};}
  function int draw();return randomize(a);endfunction
 endclass
 class C extends Base;
  local int secret;
  constraint cs {secret inside {[1:5]};}
  function int init_secret();return randomize(secret);endfunction
 endclass
 C c;
 int a=99,b=100,value=101,observed;
 bit [3:0] seen;
 initial begin
  c=new;c.value=1;c.b=30;
  if(!c.init_secret())$fatal(1,"local selected field");
  c.a.rand_mode(0);c.b.rand_mode(0);
  if(!c.randomize(a)||c.a.rand_mode()!=0||c.b!=30)$fatal(1,"list overrides modes");seen[c.a]=1;
  if(!c.randomize(value,a)||seen[c.a]||c.value<1||c.value>20||c.b!=30)$fatal(1,"nonrand selection");seen[c.a]=1;
  if(!c.draw()||seen[c.a])$fatal(1,"inherited implicit call");seen[c.a]=1;
  if(!c.randomize(a)||seen[c.a])$fatal(1,"stable cycle field identity");seen[c.a]=1;
  if(seen!=15||a!=99||b!=100||value!=101)$fatal(1,"object scope selection");
  if(!c.randomize(b) with {b==37;}||c.b!=37||c.b.rand_mode()!=0)$fatal(1,"with list binding");
  observed=c.a;
  if(!c.randomize(null)||c.a!=observed||c.b!=37)$fatal(1,"null checker");
  c.value=0;
  if(c.randomize(null)||c.a!=observed)$fatal(1,"unsatisfied checker");
  if(!c.randomize(value)||c.value<1||c.value>20||c.a!=observed)$fatal(1,"repair state variable");
  $display("TRACE constraints class variable lists nonrand local modes checker pass");$finish;
 end
endmodule
