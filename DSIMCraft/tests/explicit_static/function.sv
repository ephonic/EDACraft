`timescale 1ns/1ps
module lane #(parameter BASE=0)(output integer q=0,r=0);
function automatic integer tick(input integer n);
 static integer count=BASE;
 integer local_value=n;
 count++;
 begin : nested
  static integer calls=0;
  calls++;
  return count*100+calls*10+local_value;
 end
endfunction
initial begin
 q=tick(1);
 #1;r=tick(3);
 #1;q=tick(5);
end
endmodule
module top;
wire signed [31:0] a,b,c,d;
lane u(a,b);lane #(.BASE(5))v(c,d);
initial begin #4;
 $display("TRACE function %0d %0d %0d %0d",a,b,c,d);
 if(a!=335||b!=223||c!=835||d!=723)$fatal(1,"static call-site sharing or instance isolation");
end
endmodule
