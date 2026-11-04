`timescale 1ns/1ps
module top;
 logic[129:0]value;logic[7:0]words[0:1];integer index,stage,never,immediate;
 wire[15:0]observe_words={words[1],words[0]};
 initial begin value='x;words[0]=0;words[1]=0;index=0;stage=0;
   wait(1);wait(130'h200000000000000000000000000000000);immediate=$time;
   wait(value[129]);stage=1;
   wait(words[index]===8'ha5);stage=2;
   wait(value[128:64]==65'h123456789abcdef01);stage=3;
 end
 initial begin never=0;wait(0);never=1;end
 initial begin #1;value='z;#1;if(stage!==0)$fatal(1,"XZ condition");value[129]=1;
   #1;if(stage!==1)$fatal(1,"wide true");index=1;
   #1;if(stage!==1)$fatal(1,"index recheck");words[1]=8'ha5;
   #1;if(stage!==2)$fatal(1,"memory wake");value[128:64]=65'h123456789abcdef01;
   #1;if(stage!==3||never!==0||immediate!==0)$fatal(1,"level conditions");
   $display("TRACE conditions %0d %0d %0d",stage,never,immediate);$finish;
 end
endmodule
