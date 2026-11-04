module top;
class Packet;
  int value=7;
  logic [128:0] wide;
  function new(int value=12); this.value=value; endfunction
  function int add(int n); value=value+n; return value; endfunction
endclass
Packet a,b;
int observed;logic [128:0] observed_wide;
initial begin
  observed=(a==null);
 $display("TRACE null=%0d",a==null);
  a=new(5); b=a;
  observed=a.value;
 $display("TRACE a=%0d b=%0d add=%0d",a.value,b.value,a.add(3));
  b.value=19;
  observed=a.value;
 $display("TRACE alias=%0d",a.value);
  a=new();
  observed=a.value;
 $display("TRACE separate=%0d old=%0d",a.value,b.value);
  a.wide=129'h123456789abcdef0;
  a.wide[67:64]=4'hf;
  observed_wide=a.wide;
 $display("TRACE wide=%h",a.wide);
  $finish;
end
endmodule
