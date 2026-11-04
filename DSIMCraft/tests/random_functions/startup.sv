`timescale 1ns/1ps
module top;
 int unsigned seeded=$urandom(73),following=$urandom;
 integer global_first=$random,global_second=$random;
 int unsigned first,next;integer third;
 initial begin
  first=$urandom(73);next=$urandom();
  if(first!==seeded||next!==following)$fatal(1,"startup stream");
  if(global_first!==32'h12153524||global_second!==32'hc0895e81)$fatal(1,"startup legacy");
  third=$random;if(third!==32'h8484d609)$fatal(1,"startup continuation");
  $display("TRACE random static initialization pass");
  #1;
 end
endmodule
