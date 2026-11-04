`timescale 1ps/1ps
module top;
 typedef enum logic[128:0] {LOW=129'h1,HIGH=129'h100000000000000000000000000000001} Wide;
 Wide selected;
 logic[128:0] wide;
 byte signed narrow_value;
 int ok,signout;string text,source;
 class Base;endclass
 class Derived extends Base;endclass
 class Unrelated;endclass
 Derived d;Base b;Unrelated u;
 initial begin
  ok=$cast(narrow_value,32'h1fc);$display("TRACE narrow_value %0d %0d",ok,narrow_value);
  ok=$cast(signout,narrow_value);$display("TRACE signed %0d %0d",ok,signout);
  ok=$cast(wide,narrow_value);$display("TRACE wide %0d %h",ok,wide);
  selected=LOW;ok=$cast(selected,129'h100000000000000000000000000000001);
  $display("TRACE enumwide %0d %h",ok,selected);
  ok=$cast(selected,129'h100000000000000000000000000000002);
  $display("TRACE enumwidefail %0d %h",ok,selected);
  source="cast string";ok=$cast(text,source);$display("TRACE string %0d %s",ok,text);
  d=new;ok=$cast(b,d);$display("TRACE up %0d %0d",ok,b==d);
  ok=$cast(d,u);$display("TRACE unrelatednull %0d %0d",ok,d==null);
  d=new;b=d;ok=$cast(d,3);$display("TRACE incompatiblehandle %0d %0d",ok,d==b);
  ok=$cast(signout,b);$display("TRACE incompatibleint %0d %0d",ok,signout);
  #1;$finish;
 end
endmodule
