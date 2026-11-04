`timescale 1ns/1ps
module top;
 logic[31:0] source=32'h12345678;
 logic[31:0] blocked,scheduled,event_result,array_result,sampled_stream;
 logic[7:0] bytes[0:3];
 wire[31:0] comb;
 event tick;
 assign #1 comb={<<8{source}};
 initial begin
  blocked=0;scheduled=0;event_result=0;
  #1;scheduled<=#3 {<<8{source}};
  {>>{bytes}}<=#3 source;
  sampled_stream={<<4{source}};event_result<=@(tick) sampled_stream;
  #1;source=32'habcdef01;
  #1;->tick;
  #2;array_result={>>{bytes}};
  $display("TRACE scheduled %h %h %h %h %h %h",source,scheduled,event_result,array_result,sampled_stream,comb);
  blocked=#2 {<<8{source}};
  $display("TRACE blocked %h",blocked);
 end
 initial begin #6;source=32'h99887766;end
endmodule
