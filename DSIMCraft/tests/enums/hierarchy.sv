`timescale 1ns/1ps
module lane #(parameter int W=3)(output logic [129:0] q);
typedef logic signed [W-1:0] base_t;
typedef enum base_t {MINUS=-2,ZERO=0,ONE,TWO} state_t;
typedef state_t alias_t;
state_t state;
genvar g;
for(g=0;g<2;g=g+1)begin: gen
 typedef enum logic [W+g-1:0] {A=W+g,B,C} local_t;
 local_t x;
 initial begin x=A;#1 x=B;#1 x=local_t'((W+g)*0-1);end
end
initial begin
 state=MINUS;q=state;
 #1 state=ONE;q=state;
 #1 state=alias_t'(W+1);q=state;
end
endmodule
module top;
wire [129:0] a,b;
lane #(.W(3))u(a);
lane #(.W(7))v(b);
initial begin #3;
 if(a!==130'h3fffffffffffffffffffffffffffffffc||b!==130'd8)$fatal(1,"instance enum");
 $display("TRACE hierarchy %h %h",a,b);
end
endmodule
