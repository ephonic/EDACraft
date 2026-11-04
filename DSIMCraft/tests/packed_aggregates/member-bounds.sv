`timescale 1ns/1ps
module top;
typedef struct packed {logic[3:0] head;logic[7:4] data;logic[3:0] tail;} word_t;
word_t words[0:1];word_t s;
int wi=0,bi=6,calls=0;
logic[3:0] old;
initial begin
 words[0]=12'h123;words[1]=12'h456;
 words[wi++].data[bi++ -:2] += 2'b01;
 if(wi!=1||bi!=7||words[0]!==12'h143||words[1]!==12'h456)$fatal(1,"address once");
 wi=0;old=words[wi++].data++;calls=wi;
 if(calls!=1||old!==4'h4||words[0]!==12'h153)$fatal(1,"member update");
 bi=3;words[0].data[bi+:3]=3'b111;
 if(words[0]!==12'h173)$fatal(1,"lower clipping");
 bi=7;words[0].data[bi+:3]=3'b111;
 if(words[0]!==12'h1f3)$fatal(1,"upper clipping");
 bi=20;words[0].data[bi]=0;
 if(words[0]!==12'h1f3||words[0].data[bi]!==1'bx)$fatal(1,"out of range");
 wi=99;words[wi].data=0;
 if(words[0]!==12'h1f3||words[wi].data!==4'bxxxx)$fatal(1,"invalid word");
 s=0;s.head=4'ha;s.tail=4'hb;
 bi=6;s.data[bi-:3]<=#2 3'b101;bi=4;
 #1 s.data=#1 4'hc;
 #1 if(s!==12'hadb)$fatal(1,"delay and nba");
 {s.head,s.tail}=8'h34;s.data[7:6]=2'b01;
 if(s!==12'h354)$fatal(1,"concatenation member");
 $display("TRACE wide select %b",s.data[bi+:65]);
 $display("TRACE effects %h %h %h %0d %0d %0d",words[0],words[1],s,wi,bi,calls);
end
endmodule
