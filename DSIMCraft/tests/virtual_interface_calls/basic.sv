`timescale 1ns/1ps
interface bus_if;
 integer state=1;
 function automatic integer read(input integer delta=2);return state+delta;endfunction
 function automatic void bump();state++;endfunction
 task automatic write(input integer value,output integer echoed);#2;state=value;echoed=read(1);endtask
 modport client(import read,bump,write,input state);
endinterface
class driver;
 virtual bus_if.client vif;
 function new(virtual bus_if.client value);vif=value;endfunction
 task run(output integer echoed);integer value;value=vif.read();vif.bump();vif.write(value+3,echoed);endtask
endclass
module top;
 bus_if a(),b();driver d;integer got;
 initial begin d=new(a);d.run(got);if(a.state!=6||b.state!=1||got!=7)$fatal(1,"basic");d.vif=b;d.vif.bump();$display("TRACE vif call %0d %0d %0d",a.state,b.state,got);end
endmodule
