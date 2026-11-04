module top;
 class C;
  randc bit [15:0] a;
  rand bit [31:0] b;
  int low=100,high=104;
  constraint ca {a inside {[low:high]};}
  constraint cb {b==32'(a)+1;}
 endclass
 C c;
 bit [15:0] seen;
 int observed;
 initial begin
  c=new;
  for(int round=0;round<3;round++)begin
   seen=0;
   for(int i=0;i<5;i++)begin
    if(!c.randomize()||c.a<100||c.a>104||seen[c.a-100]||c.b!=c.a+1)$fatal(1,"constrained cycle");
    seen[c.a-100]=1;observed=c.a;#1;
   end
   if(seen!=31)$fatal(1,"exhaustion");
  end
  c.low=200;c.high=203;seen=0;
  for(int i=0;i<4;i++)begin
   if(!c.randomize()||c.a<200||c.a>203||seen[c.a-200])$fatal(1,"changed domain");
   seen[c.a-200]=1;
  end
  c.ca.constraint_mode(0);
  if(!c.randomize()||c.b!=c.a+1)$fatal(1,"disabled domain");
  c.ca.constraint_mode(1);seen=0;
  for(int i=0;i<4;i++)begin
   if(!c.randomize()||c.a<200||c.a>203||seen[c.a-200])$fatal(1,"restored domain");
   seen[c.a-200]=1;
  end
  $display("TRACE constraints cyclic constrained domains exhaustion modes pass");$finish;
 end
endmodule
