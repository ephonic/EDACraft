`timescale 1ns/1ps
package narrow_types;parameter integer WIDTH=3;typedef logic[WIDTH-1:0] word_t;endpackage
package wide_types;parameter integer WIDTH=11;typedef logic[WIDTH-1:0] word_t;endpackage
module narrow import narrow_types::*; #(parameter integer N=WIDTH)(output logic[N-1:0] value);
 word_t internal_value='1;
 initial begin value=0;#1;value=N+internal_value;end
endmodule
module wide import wide_types::*; #(parameter integer N=WIDTH)(output logic[N-1:0] value);
 word_t internal_value=5;
 initial begin value=0;#1;value=N+internal_value;end
endmodule
module empty import narrow_types::WIDTH; ;
 initial if(WIDTH!=3)$fatal(1,"empty header import");
endmodule
module top;
 localparam integer WIDTH=20;
 wire[4:0] a;wire[10:0] b;wire[3:0] c;
 narrow #(WIDTH-15) first(a);wide second(b);narrow #(.N(4)) third(c);empty none();
 genvar i;
 generate for(i=0;i<3;i++)begin:generated
  wire[7:0] value;narrow #(.N(8)) child(value);
  initial begin #2;if(value!==15)$fatal(1,"header import generate clone");end
 end endgenerate
 initial begin #2;if(a!==12||b!==16||c!==11)$fatal(1,"header import scope isolation");
 $display("TRACE header clones %h %h %h",a,b,c);end
endmodule
