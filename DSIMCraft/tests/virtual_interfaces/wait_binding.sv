interface bus_if;logic clk;endinterface
module top;
 bus_if a(),b();virtual bus_if vif;int hit;
 initial begin
  a.clk=0;b.clk=0;vif=a;
  fork
   begin @(posedge vif.clk);hit=$time;end
   begin #1;vif=b;#1;a.clk=1;#1;b.clk=1;end
  join
  $display("TRACE virtual wait binding %0d",hit);
 end
endmodule
