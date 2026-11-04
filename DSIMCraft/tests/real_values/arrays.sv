module storage;
  real values[0:2];
  initial begin values[0]=1.25;values[1]=2.5;values[2]=-0.5;end
endmodule
module top;
  storage u();
  real result;
  logic signed [127:0] signed_wide;
  logic [127:0] unsigned_wide;
  initial begin
    signed_wide=-1;unsigned_wide=128'h10000000000000000000000000;
    #1;
    result=u.values[0]+u.values[1]+u.values[2];
    if(result!=3.25)$fatal(1,"hierarchical real arrays");
    result=signed_wide;if(result!=-1.0)$fatal(1,"wide signed real conversion");
    result=unsigned_wide;if(result!=1267650600228229401496703205376.0)$fatal(1,"wide unsigned real conversion");
    result=u.values[0];$display("TRACE arrays value=%0.2f",result);$finish;
  end
endmodule
