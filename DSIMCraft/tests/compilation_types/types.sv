typedef enum bit[1:0] {IDLE=0,RUN=2} Mode;
typedef struct packed {Mode mode;bit[5:0] data;} Packet;
typedef Packet Pair[1:0];
typedef logic[95:0] Wide;
class Holder;
 Packet p;
 Wide w;
 function new();p='{RUN,9};w=96'hf123456789abcdef01234567;endfunction
endclass
module top;
 Pair pairs;Holder h;
 initial begin
 h=new;pairs[0]=h.p;pairs[1]='{IDLE,3};
 if(pairs[0].mode!=RUN||pairs[0].data!=9||$bits(h.w)!=96||pairs[1].data!=3)$fatal(1,"CU aggregates");
 $display("TRACE unit types %0d %0d %024h",pairs[0].mode,pairs[1].data,h.w);
 end
endmodule
