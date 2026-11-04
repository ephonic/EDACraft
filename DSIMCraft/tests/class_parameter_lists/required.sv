module top;
 class Required #(int W, N=W+1, type T, U=T, parameter logic[W-1:0] MASK, NEXT=MASK-1);
  T value;U alias_value;logic[W-1:0] mask;
  function new(T v);value=v;alias_value=v;mask=NEXT;endfunction
  function T get();return value+alias_value;endfunction
 endclass
 Required#(.W(65),.T(logic[70:0]),.MASK('1)) a;
 Required#(8,9,int,int,8'hff) b;
 logic[70:0] observed;logic[64:0] mask;
 initial begin
  a=new(71'h123456789abcdef);b=new(6);observed=a.get();mask=a.mask;
  $display("TRACE required %h %h %0d",observed,mask,b.get());
 end
endmodule
