`timescale 1ps/1ps
typedef bit[7:0] Word;
class Base;
 static int count=0;
 Word value;
 function new(Word n=3);value=n;count++;endfunction
 virtual function int read();return value;endfunction
endclass
class Derived extends Base;
 function new(Word n=5);super.new(n);endfunction
 virtual function int read();return value+1;endfunction
endclass
module lane;
 Base b;
 initial b=new(7);
endmodule
module top;
 lane a(),z();
 Base b;Derived d;
 int observed;
 initial begin
  #1;d=new;b=d;observed=Base::count;
  if(Base::count!=3||b.read()!=6||a.b.read()!=7||z.b.read()!=7)
   $fatal(1,"global class identity, inherited dispatch or static storage");
  $display("TRACE unit shared %0d %0d",Base::count,b.read());
 end
endmodule
