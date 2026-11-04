`timescale 1ns/1ps
package fine;
 task automatic sample(output integer q);begin #0.125;q=123;end endtask
endpackage
`timescale 1ns/1ns
module top;
 integer sampled=0,observed=0;
 initial begin fine::sample(sampled);observed=sampled;end
 initial begin #1;if(sampled!=123||observed!=123)$fatal(1,"package precision");$display("TRACE package precision %0d %0d",sampled,observed);end
endmodule
