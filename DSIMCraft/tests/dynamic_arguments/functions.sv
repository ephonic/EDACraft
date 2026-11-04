`timescale 1ns/1ps
module top;
integer a[],b[],q=0,k=0,total=0;
int two[];
logic signed [95:0] wide[],wide_copy[];
task automatic wide_transform(ref logic signed [95:0] x[],output logic signed [95:0] y[]);
 x=new[x.size()+1](x);x[x.size()-1]=-1;y=x;
endtask
function automatic integer zero(input int x[]=two);
 return x.size()?$bits(x)+x[0]:0;
endfunction
task automatic classic;
 inout integer x[];
 begin x=new[x.size()+1](x);x[x.size()-1]=17;end
endtask
function automatic integer sum(input integer x[]);
 integer s=0;
 foreach(x[i])s+=x[i];
 x=new[x.size()+1](x);x[x.size()-1]=99;
 return s;
endfunction
function automatic integer change(inout integer x[],output integer y[]);
 x=new[x.size()+1](x);x[x.size()-1]=10;
 y=x;return $bits(x)+$size(y);
endfunction
function automatic integer forward(input integer x[]);
 return sum(x);
endfunction
initial begin
 for(k=0;k<4;k++)begin a=new[k];foreach(a[i])a[i]=i+1;total+=forward(a);end
 q=change(a,b);
 $display("TRACE functions %0d %0d %0d %0d %0d %0d",total,q,a.size(),b.size(),a[3],sum(b));
 a.delete();q=forward(a);$display("TRACE empty %0d %0d",q,a.size());
 wide=new[1];wide[0]=96'h800000000000000000000005;wide_transform(.y(wide_copy),.x(wide));
 two=new[2];two[0]=3;q=zero();classic(a);
 $display("TRACE types %0d %0d %h %h %0d %0d",q,two[1],wide_copy[0],wide_copy[1],a.size(),a[0]);
end
endmodule
