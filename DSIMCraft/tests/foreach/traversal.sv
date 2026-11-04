`timescale 1ns/1ps
module top;
  logic[3:0] words[2:4];
  logic[4:0] bits=5'b10101;
  logic[2147483647:2147483645] high=0;
  integer sum=0,order=0,i=99,visits=0,last=0;
  initial begin
    foreach(words[i]) begin words[i]=i+1; order=order*10+i; end
    foreach(words[i]) sum+=words[i];
    if(order!=234 || sum!=12 || i!=99)$fatal(1,"ascending or scope");
    order=0;
    foreach(bits[k]) begin order=order*10+k; if(bits[k])visits++; end
    if(order!=43210 || visits!=3)$fatal(1,"packed descending");
    visits=0;
    foreach(high[k]) begin
      if(k!=2147483647-visits)$fatal(1,"large packed index");
      visits++;last=k;
    end
    if(visits!=3 || last!=2147483645)$fatal(1,"large endpoint");
    #1;$display("TRACE traversal %0d %0d",sum,order);
  end
endmodule
