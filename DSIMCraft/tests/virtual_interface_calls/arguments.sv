`timescale 1ns/1ps
interface api;
 integer state=10;
 function automatic integer edit(ref integer item,input integer delta=3);item+=delta;state+=item;return state;endfunction
 function automatic string tag(input string prefix="value");return $sformatf("%s:%0d",prefix,state);endfunction
 task automatic exchange(input integer values[0:1],output integer total,inout integer carry);#1;total=values[0]+values[1]+state;carry+=total;state=carry;endtask
 function automatic void bump(ref integer item);item++;endfunction
 modport client(import edit,tag,exchange,bump,input state);
endinterface
class driver;
 virtual api.client vif;
 function new(virtual api.client value);vif=value;endfunction
 task run(ref integer item,input integer values[0:1],output integer got,total,inout integer carry,output string text);
  got=vif.edit(.item(item));vif.bump(item);vif.exchange(values,total,carry);text=vif.tag("sum");
 endtask
endclass
module top;
 api a();driver d;integer item=4,data[0:1],got,total,carry=2;string text;
 initial begin data[0]=7;data[1]=9;d=new(a);d.run(item,data,got,total,carry,text);
  if(item!=8||got!=17||total!=33||carry!=35||text!="sum:35")$fatal(1,"arguments");
  $display("TRACE vif arguments %0d %0d %0d %0d %s",item,got,total,carry,text);
 end
endmodule
