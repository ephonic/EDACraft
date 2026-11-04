package types;
 typedef logic signed[64:0] word_t;
 localparam int VALUE=1;
endpackage
module top;
 class C#(types::word_t A=-4,B=A-1);
  extern function types::word_t sum(int x,types::word_t y=-2,types::word_t z=-3);
  task adjust(ref types::word_t x,input types::word_t delta);#1;x+=delta;endtask
 endclass
 function types::word_t C::sum(int x,types::word_t y,types::word_t z);return x+y+z+A+B;endfunction
 C obj;types::word_t observed;
 initial begin
  obj=new;observed=obj.sum(1);obj.adjust(observed,4);
  $display("TRACE scoped %0d %0d %0d",observed,obj.sum(1,2,3),types::VALUE inside {1,2});
 end
endmodule
