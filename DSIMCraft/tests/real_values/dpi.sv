module top;
  import "DPI-C" pure function real scale_real(input real a,input shortreal b);
  import "DPI-C" function void outputs(input real a,output real b,output shortreal c);
  real result,value;
  shortreal rounded;
  initial begin
    result=scale_real(1.25,0.5);outputs(result,value,rounded);
    if(result!=2.5 || value!=2.75 || rounded!=0.5)$fatal(1,"floating DPI ABI");
    $display("TRACE dpi value=%0.2f rounded=%0.2f",value,rounded);$finish;
  end
endmodule
