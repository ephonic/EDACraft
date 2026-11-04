module top;
integer a[],observed=0;
initial begin
 $display("TRACE empty %0d %0d %0d %0d %0d %0d %0d %0d %0d",$bits(a),$size(a),$left(a),$right(a),$low(a),$high(a),$increment(a),$dimensions(a),$unpacked_dimensions(a));
 a=new[3];
 $display("TRACE allocated %0d %0d %0d %0d %0d %0d %0d",$bits(a),$size(a),$left(a),$right(a),$low(a),$high(a),$increment(a));
 $display("TRACE packed %0d %0d %0d %0d %0d %0d",$size(a,2),$left(a,2),$right(a,2),$low(a,2),$high(a,2),$increment(a,2));
 foreach(a[i])begin a[i]=i+1;end
 observed=$bits(a)+$size(a);
 $display("TRACE loop %0d %0d %0d",a[0],a[1],a[2]);
end
endmodule
