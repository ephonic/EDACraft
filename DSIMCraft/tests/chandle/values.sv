package handles;
 typedef chandle H;
 class Box #(type T=H);
  T value;
  function T copy(input T x); value=x; return value; endfunction
 endclass
endpackage
module top;
 import handles::*;
 import "DPI-C" pure function chandle get_handle(input int i);
 import "DPI-C" pure function int inspect_handle(input chandle p);
 H h,k,arr[2]; int observed=0;
 Box#(H) box;
 function automatic H identity(input H x);return x;endfunction
 task automatic swap(ref H a, ref H b);H tmp;tmp=a;a=b;b=tmp;endtask
 initial begin
  $display("TRACE default %0d %0d",h==null,arr[1]===null);
  if(h)$fatal(1,"default handle condition");
  h=get_handle(0);if(h)observed=1;else $fatal(1,"nonnull handle condition");k=get_handle(1);arr[0]=h;arr[1]=k;
  box=new();
  $display("TRACE values %0d %0d %0d",inspect_handle(identity(h)),inspect_handle(box.copy(k)),h!=k);
  swap(h,k);
  observed=inspect_handle(h);
  $display("TRACE swap %0d %0d",observed,inspect_handle(k));
  h=null;k=H'(arr[0]);
  case(h) null:observed=observed+1;default:$fatal(1,"opaque case");endcase
  h=(observed==74)?k:arr[1];
  $display("TRACE copy %0d %0d %0d",inspect_handle(h),h===arr[0],box.value===arr[1]);
  #1;$finish;
 end
endmodule
