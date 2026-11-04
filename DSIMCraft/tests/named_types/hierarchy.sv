`timescale 1ns/1ps
module lane #(parameter int W=8)(output logic [129:0] q);
typedef logic signed [W-1:0] word_t;
typedef word_t copy_t;
copy_t value;
localparam NEG=copy_t'(-2);
genvar g;
generate for(g=0;g<2;g=g+1)begin: gen
 typedef bit [W+g-1:0] word_t;
 word_t x;
 localparam C=word_t'((W+g)*0-1);
 initial begin x=C;#1;x=word_t'(16'hx5z1);end
end endgenerate
initial begin value=NEG;q=130'(value);#2;value=copy_t'(128);q=130'(value);end
endmodule
module top;
wire [129:0] a,b;
lane #(.W(8))u(a);
lane #(.W(13))v(b);
initial begin #3;$display("TRACE hierarchy %h %h",a,b);$finish;end
endmodule
