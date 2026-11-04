interface bus_if;logic[7:0] data;endinterface
module top;
 bus_if a(),b();virtual bus_if vif;
 task automatic change(ref logic[7:0] value);#2;value=8'h5a;endtask
 initial begin a.data=0;b.data=0;vif=a;fork change(vif.data);begin #1;vif=b;end join
  if(a.data!==8'h5a||b.data!==0)$fatal(1,"live ref receiver identity");
  $display("TRACE virtual ref %0h %0h",a.data,b.data);
 end
endmodule
