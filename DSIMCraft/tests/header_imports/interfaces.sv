`timescale 1ns/1ps
package payload_types;
 parameter integer WIDTH=6;
 typedef logic[WIDTH-1:0] word_t;
endpackage
interface transport import payload_types::*; #(parameter integer N=WIDTH)(input word_t seed);
 word_t payload;
 logic[N-1:0] data=0;
 assign payload=seed;
 modport writer(input payload,output data);
endinterface
module writer import payload_types::word_t; (transport.writer bus);
 word_t sample;
 initial begin #1;sample=bus.payload;bus.data='1;#1;bus.data<=sample;end
endmodule
module top;
 payload_types::word_t seed=6'h2b;
 transport #(.N(9)) channel(seed);writer u(channel);
 initial begin #1.5;if(channel.data!==9'h1ff)$fatal(1,"header interface width");
 #1;if(channel.data!==9'h02b||channel.payload!==6'h2b)$fatal(1,"header interface alias");
 $display("TRACE header interfaces %h %h",channel.data,channel.payload);end
endmodule
