`timescale 1ns/1ps
interface bus_if;
 integer state;
 task automatic exchange(input integer value,output integer result);#2;state=value;result=state;endtask
endinterface
class driver;
 virtual bus_if vif;
 task send(input integer value,output integer result);vif.exchange(value,result);endtask
endclass
module top;
 bus_if a(),b();driver d;integer first,second;
 initial begin d=new();d.vif=a;
  fork
   d.send(10,first);
   begin #1;d.vif=b;d.send(20,second);end
  join
  if(first!=10||second!=20||a.state!=10||b.state!=20)$fatal(1,"reentry/rebinding");
  $display("TRACE vif reentry %0d %0d %0d %0d",first,second,a.state,b.state);
 end
endmodule
