module top;
 class Box #(type T=int);
  T value;
  function new(T n);value=n;endfunction
 endclass
 typedef int queue_t[$];
 typedef logic[70:0] wide_t;
 Box#(int) object;
 queue_t selected;
 int observed;
 function Box#(int) get_box;return object;endfunction
 function automatic Box#(int) auto_box;return object;endfunction
 function automatic Box#(int) local_box;
  Box#(int) copy;
  copy=object;return copy;
 endfunction
 function queue_t make_queue;return {4,7,9};endfunction
 function automatic queue_t auto_queue;return {3,8};endfunction
 function wide_t wide;return 71'h12_3456789abcdef012;endfunction
 function real real_value;return 1.25;endfunction
 function string label;return "nonansi";endfunction
 initial begin
  object=new(17);
  if(get_box()!=object || auto_box()!=object || local_box()!=object)$fatal(1,"parameterized return");
  selected=make_queue();if(selected.size()!=3 || selected.sum()!=20)$fatal(1,"queue return");
  selected=auto_queue();if(selected.size()!=2 || selected.sum()!=11)$fatal(1,"automatic queue return");
  if(wide()!=71'h12_3456789abcdef012 || real_value()!=1.25 || label()!="nonansi")$fatal(1,"value types");
  observed=selected.sum();#1;$display("TRACE nonansi types value=%0d",observed);$finish;
 end
endmodule
