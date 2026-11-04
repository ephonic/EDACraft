package p;
 typedef logic[128:0] Wide;
 typedef Wide Q[$];typedef Q Alias;
 typedef int AA[string];
endpackage
module leaf #(parameter int W=65)(output logic[W-1:0] observed);
 class C #(type T=logic[W-1:0]);
  typedef T Q[$];
  static function Q make(input T n);Q q;q.push_back(n);return q;endfunction
 endclass
 typedef logic[W-1:0] Bits;
 typedef Bits Values[$];Values values;
 initial begin values=C#(Bits)::make('1);#1;observed=values[0];end
endmodule
module top;
 import p::*;
 Alias a,b;AA aa;
 wire[64:0] narrow;wire[128:0] wide_output;
 leaf #(65) u(narrow);leaf #(129) v(wide_output);
 initial begin
  a={129'h1x,129'h1z};b=a;a[0]=0;aa["name"]=7;
  $display("TRACE aliases %0d %h %h %0d",b.size(),b[0],b[1],aa["name"]);
  #2;$display("TRACE clone %h %h",narrow,wide_output);$finish;
 end
endmodule
