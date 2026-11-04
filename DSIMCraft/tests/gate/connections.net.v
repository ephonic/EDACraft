module sub(input a,output y,inout p,output cx,output cz);
  assign p=a;
  assign y=p;
  assign cx=1'bx;
  assign cz=1'bz;
endmodule
module dut(input a,b,output y,tied,missing,cx,cz,output [4:4] one);
  HALF shared(.A(a),.B(b),.SUM(tied),.CARRY(tied));
  sub u(.a(a),.y(y),.p(),.cx(cx),.cz(cz));
  AND2 omitted(.A(a),.Y(missing));
  wire \internal/path.with.dot ;
  INV \g/first (.A(b),.Y(\internal/path.with.dot ));
  assign one[4]=\internal/path.with.dot ;
endmodule
