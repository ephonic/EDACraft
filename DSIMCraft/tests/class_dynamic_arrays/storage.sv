module top;
 class Base;
  logic signed [31:0] data[];
  function new();data=new[2];endfunction
 endclass
 class Derived extends Base;
  bit [7:0] bytes_da[];
  string names[];
 endclass
 Derived a,b;logic signed [31:0] copied[];int observed;
 initial begin
  a=new;b=new;
  if(a.data.size()!=2||a.bytes_da.size()!=0||a.data[0]!==32'bx)$fatal(1,"initial allocation");
  a.data[0]=17;a.data[1]=23;a.data[2]=99;
  if(a.data.size()!=2)$fatal(1,"dynamic write must not append");
  a.data[-1]=10;a.data[32'bx]=11;a.data[2][7:0]=12;
  if(a.data.size()!=2||a.data[0]!=17||a.data[1]!=23)$fatal(1,"invalid index write");
  a.data[64'h100000000]=13;
  if(a.data[0]!=13)$fatal(1,"wide index integral conversion");
  a.data[0]=17;
  a.data=new[4](a.data);
  if(a.data[0]!=17||a.data[1]!=23||a.data[2]!==32'bx)$fatal(1,"resize preserve and default");
  b.data=a.data;b.data[0]=8;
  if(a.data[0]!=17||b.data[0]!=8)$fatal(1,"copy isolation");
  copied=b.data;copied[0]=9;
  if(b.data[0]!=8)$fatal(1,"ordinary array copy isolation");
  a.bytes_da=new[3];if(a.bytes_da[2]!==0)$fatal(1,"two state default");
  a.names=new[2];if(a.names[1]!="")$fatal(1,"string default");
  a.names[0]="alpha";b.names=a.names;b.names[0]="beta";
  if(a.names[0]!="alpha"||b.names[0]!="beta")$fatal(1,"string copy");
  a.data.delete();a.names.delete();
  if(a.data.size()!=0||a.names.size()!=0||b.data.size()!=4)$fatal(1,"delete isolation");
  foreach(b.data[i])if(i<2)observed+=b.data[i];
  if(observed!=31)$fatal(1,"foreach class dynamic");
  $display("TRACE class dynamic allocation copy defaults bounds pass");$finish;
 end
endmodule
