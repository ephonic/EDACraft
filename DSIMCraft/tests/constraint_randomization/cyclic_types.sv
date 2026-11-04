module top;
 class Base #(parameter int W=3);
  randc bit [W-1:0] a;
 endclass
 class C extends Base#(2);
  randc bit [1:0] b;
  randc bit [95:0] wide;
  randc int counter;
  constraint cw {wide inside {[96'h100000000000000000000000:96'h100000000000000000000003]};}
  constraint ci {counter inside {[-2:1]};}
 endclass
 C c;
 Base#(2) alias_handle;
 bit [3:0] sa,sb,sw,si;
 int observed;
 initial begin
  c=new;alias_handle=c;
  for(int round=0;round<2;round++)begin
   sa=0;sb=0;sw=0;si=0;
   repeat(4)begin
    if(!alias_handle.randomize()||sa[c.a]||sb[c.b]||sw[c.wide[1:0]]||c.wide[95:2]!=(96'h100000000000000000000000>>2))$fatal(1,"cyclic inheritance and wide");
    sa[c.a]=1;sb[c.b]=1;sw[c.wide[1:0]]=1;observed=c.a+c.b;#1;
    if(c.counter < -2||c.counter>1||si[c.counter+2])$fatal(1,"signed integer cycle");si[c.counter+2]=1;
   end
   if(sa!=15||sb!=15||sw!=15||si!=15)$fatal(1,"cyclic fields incomplete");
  end
  $display("TRACE constraints cyclic inherited specialized wide fields pass");$finish;
 end
endmodule
