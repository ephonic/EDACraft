`timescale 1ps/1ps
module top;
 class Base#(type T=int, U=T);T n;virtual function T get();return n;endfunction endclass
 class Item#(type T=int, U=T) extends Base#(T);
 function T read_peer(int bias,Base#(T) peer);return bias+peer.get();endfunction
 function new(T v=0);n=v;endfunction function T get();return n;endfunction endclass
 typedef Base#(logic[64:0]) B;typedef Item#(logic[64:0]) I;
 B q[$],selected;I item=new(3);logic[64:0] observed;
 initial begin
 q.push_back(item);observed=item.read_peer(0,q[0]);#2;item=new(5);q.push_front(item);selected=q.pop_front();observed=selected.get();
 #1;selected.n=7;observed=selected.get();#2;$display("TRACE rollback %0d %0d",observed,q.size());$finish;
 end
endmodule
