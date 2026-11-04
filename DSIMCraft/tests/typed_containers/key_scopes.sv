`timescale 1ps/1ps
package keys;
 class Key;int id;function new(int n=0);id=n;endfunction endclass
 typedef Key Alias;
 typedef int Table[Alias];
 Table shared_values;
 function automatic int calculate(Key k,int n);
   Table local_values;Key key;
   local_values[k]=n;
   if(!local_values.first(key)||key!=k)return -1;
   return local_values[k]+key.id;
 endfunction
endpackage
module leaf #(parameter W=65)(output logic [W-1:0] observed);
 import keys::*;
 typedef Key LocalKey;
 logic [W-1:0] values[LocalKey];
 Key a;
 initial begin
  a=new(W);values[a]='1;observed=values[a];
  if(calculate(a,2)!=W+2)$fatal(1,"automatic local map");
  shared_values[a]=W;
  foreach(values[k])if(k.id!=W||values[k]!=='1)$fatal(1,"cloned class key");
  #1;$display("TRACE scope %0d %0h",W,observed);
 end
endmodule
module top;
 logic [64:0] a;logic [128:0] b;
 leaf #(.W(65)) u(a);leaf #(.W(129)) v(b);
 initial begin #2;if(keys::shared_values.num()!=2)$fatal(1,"package map");$display("TRACE shared %0d",keys::shared_values.num());$finish;end
endmodule
