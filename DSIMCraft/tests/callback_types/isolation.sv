class Payload;endclass
class A extends Payload;endclass
class B extends Payload;endclass
class Family #(type T=Payload);
 static int count=0;int id;
 function new();count++;id=count;endfunction
endclass
class Leaf #(type T=Payload) extends Family#(T);endclass
module top;
 Leaf#(A) a;Leaf#(B) b;Family#(A) first;Family#(B) second;int stage=0;
 initial begin
  a=new();b=new();first=a;second=b;
  $display("TRACE separate %0d %0d %0d %0d",first.id,second.id,Family#(A)::count,Family#(B)::count);
  stage++;#1;a=new();first=a;$display("TRACE counts %0d %0d",Family#(A)::count,Family#(B)::count);$finish;
 end
endmodule
