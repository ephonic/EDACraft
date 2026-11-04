`timescale 1ns/1ps
module top;
  typedef logic[7:0] byte_t;
  byte_t input_value=0;
  integer answer=0,pop,steps=0;
  integer k;
  function automatic integer scan(input byte_t value);
    integer local_values[1:3];
    integer total;
    begin
      total=0;
      foreach(local_values[i]) local_values[i]=i+1;
      foreach(local_values[i]) total+=local_values[i];
      foreach(value[k]) begin
        if(k==2)break;
        if(!value[k])continue;
        total+=k;
      end
      return total;
    end
  endfunction
  function automatic integer stop(input logic[4:0] value);
    foreach(value[i]) if(value[i])return i;
    return -1;
  endfunction
  always_comb begin
    pop=0;foreach(input_value[i]) if(input_value[i])pop++;
  end
  initial begin
    for(k=0;k<4;k++)begin
      input_value=8'h88+k;answer=scan(input_value);steps=stop(input_value[2:0]);
      #1;
      if(answer!=19 || pop!=2+(k==1 || k==2?1:k==3?2:0))$fatal(1,"function or comb dependencies");
      if(steps!=(k==0?-1:k==1?0:1))$fatal(1,"foreach return");
    end
    $display("TRACE functions %0d",answer);
  end
endmodule
