interface bus_if;
 logic valid;
 logic [7:0] data;
 modport drive(output valid,data);
 modport observe(input valid,data);
endinterface
class driver;
 virtual interface bus_if vif;
 function new(virtual bus_if value);vif=value;endfunction
 function void drive(input bit[7:0] value);vif.valid=1;vif.data=value;endfunction
endclass
module top;
 bus_if a(),b();
 driver d;
 virtual bus_if alias_value;
 virtual bus_if.drive writer;
 virtual bus_if.observe reader;
 initial begin
  a.valid=0;a.data=0;b.valid=0;b.data=0;
  d=new(a);d.drive(8'h35);alias_value=d.vif;
  d.vif=b;d.drive(8'ha6);
  writer=a;reader=a;
  writer.data[3:0]=4'hc;
  if(alias_value!=a||d.vif!=b||alias_value==d.vif)$fatal(1,"binding identity");
  if(a.data!==8'h3c||b.data!==8'ha6||reader.data!==8'h3c)$fatal(1,"canonical storage");
  alias_value=null;if(alias_value!=null)$fatal(1,"null");
  $display("TRACE virtual binding %0h %0h %0d",a.data,b.data,reader.valid);
 end
endmodule
