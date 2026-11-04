interface bus_if;logic valid;endinterface
class driver;
 virtual bus_if vif;
 function new(virtual bus_if value);vif=value;endfunction
 task run();vif.valid=1;endtask
endclass
module top;bus_if bus();driver d;initial begin d=new(bus);d.run();if(bus.valid!==1)$fatal(1,"vif");$display("TRACE GAP virtual_interface 1");end endmodule
