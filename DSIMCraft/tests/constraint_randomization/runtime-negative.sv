module top;
 class C;
  rand bit [3:0] a;
  logic [3:0] state_value=4'bx;
  constraint c {a==state_value;}
 endclass
 C c;
 initial begin
  c=new;
  if(c.randomize())$fatal(1,"unknown state accepted");
  $fatal(1,"unknown state reported as ordinary unsat");
 end
endmodule
