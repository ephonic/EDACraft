`timescale 1ns/1ps
module top;
 integer calls=0;
 logic[23:0] result,padded,argument_result;
 logic[15:0] task_result;
 function automatic logic[15:0] next_word(input logic[15:0] word);
  calls=calls+1;return word+1;
 endfunction
 function automatic logic[23:0] convert(input logic[15:0] word);
  logic[23:0] tmp={<<8{word}};
  return {<<8{word}};
 endfunction
 function automatic logic[23:0] argument_copy(input logic[23:0] word);return word;endfunction
 task automatic unpack(input logic[15:0] word,output logic[15:0] out);
  logic[7:0] local_bytes[0:1];
  {>>{local_bytes}}=word;
  #1;out={<<8{local_bytes}};
 endtask
 initial begin
  result={<<8{next_word(16'h1233)}};
  padded=convert(16'habcd);argument_result=argument_copy({<<8{16'h1234}});
  unpack(16'h1357,task_result);
  #1;$display("TRACE automatic %h %h %h %h %0d",result,padded,argument_result,task_result,calls);
 end
endmodule
