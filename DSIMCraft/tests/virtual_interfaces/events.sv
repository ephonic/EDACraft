interface bus_if;logic clk;logic[7:0] data;endinterface
class driver;
 virtual bus_if vif;
 task send(input bit[7:0] value);
  @(negedge vif.clk);vif.data<=value;
 endtask
endclass
module top;
 bus_if a(),b();driver d;int seen,total;
 initial begin a.clk=0;b.clk=0;repeat(8)begin #1;a.clk=~a.clk;end end
 initial begin a.data=0;b.data=0;d=new();d.vif=a;d.send(8'h25);#1;d.vif=b;d.vif.data<=8'h13;#1;
  if(a.data!==8'h25||b.data!==8'h13||seen!=1||total!=8'h25)$fatal(1,"event/NBA");
  $display("TRACE virtual events %0h %0h %0d %0d",a.data,b.data,seen,total);$finish;
 end
 initial begin wait(a.data!=0);seen++;total+=a.data;end
endmodule
