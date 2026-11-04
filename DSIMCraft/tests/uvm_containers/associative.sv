`timescale 1ns/1ps
module top;
 int aa[int], bb[int], key=12, ok=0, sum=0, count=0;
 integer xa[int];
 initial begin
   ok=aa.first(key);$display("TRACE empty %0d %0d %0d %0d %b",aa.num(),ok,key,aa[7],xa[7]);
   aa[-5]=10;aa[9]=30;aa[2]=20;aa[32'hffff_ffff]=40;
   aa[2]++;aa[2][7:0]+=3;
   bb=aa;aa.delete(-5);aa[-1]=77;
   #2;
   foreach(bb[i]) begin sum+=bb[i];count++;$display("TRACE key %0d %0d",i,bb[i]);end
   $display("TRACE totals %0d %0d %0d %0d %0d %0d",aa.size(),bb.num(),sum,count,aa.exists(-5),bb.exists(-5));
   ok=bb.first(key);$display("TRACE first %0d %0d",ok,key);
   ok=bb.next(key);$display("TRACE next %0d %0d",ok,key);
   ok=bb.last(key);$display("TRACE last %0d %0d",ok,key);
   ok=bb.next(key);$display("TRACE end %0d %0d",ok,key);
   ok=bb.prev(key);$display("TRACE prev %0d %0d",ok,key);
   $display("TRACE reduce %0d %0d",bb.sum(),bb.sum() with (item*2));
   #2;aa.delete();bb.delete(2);xa.delete();
   $display("TRACE delete %0d %0d %0d",aa.size(),bb.size(),xa.num());
 end
endmodule
