package constants;
 const int LIMIT=13;const string LABEL="pkg";const real RATIO=1.25;
endpackage
module top;
 import constants::*;
 const int LIMIT2=LIMIT;const string LABEL2=LABEL;const real RATIO2=RATIO;
 int observed;
 initial begin
  if(LIMIT2!=13||LABEL2!="pkg"||RATIO2!=1.25)$fatal(1,"package and module const");
  observed=LIMIT2;#1;$display("TRACE const scopes %0d %s %0.2f",observed,LABEL2,RATIO2);$finish;
 end
endmodule
