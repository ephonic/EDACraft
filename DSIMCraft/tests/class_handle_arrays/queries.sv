module top;
 class C;
  logic [7:0] bytes_da[];
  int words[$];
 endclass
 C c;int calls,observed;
 function C get_c();calls++;return c;endfunction
 initial begin
  c=new;
  if($size(c.bytes_da)!=0||$bits(c.bytes_da)!=0||$right(c.bytes_da)!=-1)$fatal(1,"empty queries");
  c.bytes_da=new[3];c.words.push_back(7);c.words.push_back(8);
  if($size(get_c().bytes_da)!=3||calls!=1)$fatal(1,"query receiver once");
  if($bits(c.bytes_da)!=24||$dimensions(c.bytes_da)!=2||$unpacked_dimensions(c.bytes_da)!=1)$fatal(1,"query shape");
  if($size(c.bytes_da,2)!=8||$left(c.bytes_da)!=0||$right(c.bytes_da)!=2||$low(c.bytes_da)!=0||$high(c.bytes_da)!=2||$increment(c.bytes_da)!=-1)$fatal(1,"unpacked queries");
  if($left(c.bytes_da,2)!=7||$right(c.bytes_da,2)!=0||$increment(c.bytes_da,2)!=1)$fatal(1,"packed queries");
  if($size(c.bytes_da,0)!==32'bx||$size(c.bytes_da,3)!==32'bx||$size(c.bytes_da,32'bx)!==32'bx)$fatal(1,"invalid dimension");
  if($size(c.words)!=2||$bits(c.words)!=64)$fatal(1,"queue queries");
  c.bytes_da.delete();observed=calls;
  if($size(c.bytes_da)!=0||$bits(c.bytes_da)!=0)$fatal(1,"delete query");
  $display("TRACE class container system queries dimensions receiver pass");$finish;
 end
endmodule
