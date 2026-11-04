`timescale 1ns/1ps
module top;
 integer seed[2],index=0,r,control=0;int unsigned a,b,expected;
 function automatic int unsigned draw(input integer initial_seed);
  return $urandom(initial_seed);
 endfunction
 task automatic legacy(input integer initial_seed,output integer result);
  integer local_seed;
  begin local_seed=initial_seed;result=$random(local_seed);end
 endtask
 initial begin
  seed[0]=1;seed[1]=1;
  r=$random(seed[index++]);
  if(index!=2||r!==32'h80010e00||seed[0]!==1||seed[1]!==69070)$fatal(1,"seed copy-in/copy-out");
  legacy(1,r);if(r!==32'h80010e00)$fatal(1,"task seed");
  a=draw(777);expected=$urandom;
  a=$urandom(777);control=0&&$urandom();b=$urandom();
  if(b!==expected)$fatal(1,"short circuit and");
  a=$urandom(777);control=1||$urandom();b=$urandom();
  if(b!==expected)$fatal(1,"short circuit or");
  a=$urandom(777);b=1?$urandom():$urandom();
  if(b!==expected)$fatal(1,"conditional");
  a=$urandom(777);void'($urandom());b=$urandom();
  a=$urandom(777);void'($urandom());expected=$urandom();
  if(b!==expected)$fatal(1,"discard calls");
  $display("TRACE random effects frames and short circuit pass");
  #1;
 end
endmodule
