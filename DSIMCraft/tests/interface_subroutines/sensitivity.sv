`timescale 1ns/1ps
interface bus;
 typedef enum logic[2:0]{IDLE=1,READY=5} status_t;
 typedef struct packed {logic[3:0] high,low;} word_t;
 logic[7:0] value=0;status_t mode=IDLE;
 function automatic logic[7:0] decode(input logic[7:0] mask);return value^mask;endfunction
 function automatic status_t status();return mode;endfunction
 function automatic word_t word();return word_t'(value);endfunction
 task automatic set(input logic[7:0] n);value=n;mode=READY;endtask
 modport client(import decode,status,word,set,input value);
endinterface
module comb(bus.client p,output logic[7:0] q,output logic[2:0] mode,output logic[7:0] packed_word);
 always_comb begin q=p.decode(8'h55);mode=p.status();packed_word=p.word();end
endmodule
module top;
 bus b();wire[7:0] q,packed_word;wire[2:0] mode;comb c(b,q,mode,packed_word);
 initial begin #1;if(q!==8'h55||mode!=1||packed_word!=0)$fatal(1,"FAIL initial sensitivity");
  b.set(8'ha3);#1;if(q!==8'hf6||mode!=5||packed_word!=8'ha3)$fatal(1,"FAIL updated sensitivity");
  if(b.word().high!==4'ha||b.status().name()!="READY")$fatal(1,"FAIL typed method composition");
  $display("TRACE sensitivity %h %0d %h",q,mode,packed_word);#1;$finish;end
endmodule
