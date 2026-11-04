`timescale 1ps/1ps
module top;
 class C;
  rand bit [7:0] n;
  int entries[$];
  constraint limit {n<10;foreach(entries[i])n>entries[i];}
 endclass
 C c;
 int observed;
 initial begin
  c=new;c.entries={1,2};
  if(!c.randomize() with {n==3;})$fatal(1,"first");
  #2;c.entries.push_back(7);
  if(!c.randomize() with {n==8;})$fatal(1,"second");observed=3;
  #1;c.entries[0]=8;
  if(!c.randomize()||c.n!=9)$fatal(1,"third");observed=9;
  #2;$display("TRACE constraint foreach queue heap checkpoint pass");$finish;
 end
endmodule
