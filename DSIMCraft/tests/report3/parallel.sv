`timescale 1ns/1ps
module literal_lane #(parameter int DELAY=2)(output logic [31:0] q,output logic error);
  int count=0;
  initial begin
    q="AB";error=0;
    repeat(3)begin
      #DELAY; q="AB"+count;
      if(q!==32'h4142+count)error=1;
      count++;
    end
  end
endmodule
module top;
  wire[31:0] a,b;wire ea,eb;
  literal_lane #(.DELAY(2)) u(a,ea);
  literal_lane #(.DELAY(3)) v(b,eb);
endmodule
