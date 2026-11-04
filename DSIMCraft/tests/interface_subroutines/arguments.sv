`timescale 1ns/1ps
interface api;
 integer state=10;
 function automatic integer edit(ref integer item,input integer delta=3);item+=delta;state+=item;return state;endfunction
 function automatic string tag(input string prefix="value");return $sformatf("%s:%0d",prefix,state);endfunction
 task automatic exchange(input integer values[0:1],output integer total,inout integer carry);
  #1;total=values[0]+values[1]+state;carry+=total;state=carry;
 endtask
 function automatic void bump(ref integer item);item++;endfunction
 modport client(import edit,tag,exchange,bump,input state);
endinterface
module client(interface p);
 integer item=4,got,total,carry=2;integer data[0:1];string text;
 initial begin data[0]=7;data[1]=9;got=p.edit(.delta(2),.item(item));p.bump(item);
  p.exchange(data,total,carry);text=p.tag("sum");
  if(item!=7||got!=16||total!=32||carry!=34||text!="sum:34")$fatal(1,"FAIL arguments");
  $display("TRACE arguments %0d %0d %0d %0d %s",item,got,total,carry,text);end
endmodule
module top;api b();client c(b.client);initial begin #3;$finish;end endmodule
