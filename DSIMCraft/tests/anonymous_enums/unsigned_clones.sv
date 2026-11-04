module lane #(parameter int W=32)(output bit[W-1:0] observed);
 localparam int NEGATIVE=-2;
 typedef bit[W-1:0] base_t;
 typedef enum base_t {PREVIOUS=NEGATIVE,LAST,ZERO=0} state_t;
 state_t state;
 initial begin
  state=PREVIOUS;
  if($bits(state)!=W||state!==({W{1'b1}}-1'b1))$fatal(1,"cloned enum initializer");
  #1;state=LAST;observed=state;
  if(observed!=={W{1'b1}}||state.name()!="LAST")$fatal(1,"cloned enum increment");
 end
endmodule
module top;
 bit[31:0] a;bit[64:0] b;bit[128:0] c;
 lane #(32) u(a);lane #(65) v(b);lane #(129) w(c);
 initial begin
  #2;if(a!=={32{1'b1}}||b!=={65{1'b1}}||c!=={129{1'b1}})$fatal(1,"enum clone isolation");
  $display("TRACE clones %h %h %h",a,b,c);$finish;
 end
endmodule
