`timescale 1ps/1ps
package config_pkg;parameter W=9;typedef bit[W-1:0] Payload;endpackage
import config_pkg::*;
class Box #(type T=Payload, int OFFSET=2);
 static int count=0;
 T value;
 function new(T n);value=n+OFFSET;count++;endfunction
 function T read();return value;endfunction
endclass
typedef Box#(Payload,3) SharedBox;
module slot #(parameter N=1);
 SharedBox b;
 initial b=new(N);
endmodule
module top;
 slot #(5) a();slot #(9) b();
 Box#(bit[7:0],4) other;
 SharedBox alias_handle;
 int observed;
 initial begin
  #1;other=new(11);alias_handle=a.b;observed=SharedBox::count;
  if(SharedBox::count!=2||alias_handle.read()!=8||b.b.read()!=12||other.read()!=15||other.count!=1)
   $fatal(1,"canonical global specialization or alias");
  if($bits(alias_handle.value)!=9||$bits(other.value)!=8)$fatal(1,"type parameter widths");
  $display("TRACE unit generic %0d %0d %0d",observed,alias_handle.read(),other.read());
 end
endmodule
