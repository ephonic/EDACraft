module top;
 int a,b;
 function automatic int sample(input int wanted);
  int x,y;
  if(!std::randomize(x,y) with {x==wanted;y==x+7;})return -1;
  if(x!=wanted||y!=wanted+7)return -2;
  return x+y;
 endfunction
 initial begin
  a=4;b=9;
  if(std::randomize(a,b) with {a==32'h5acb8291;b==(a^32'h12345678);}!=1)$fatal(1,"scope rare");
  if(a!=32'h5acb8291||b!=(a^32'h12345678))$fatal(1,"scope rare values");
  if(std::randomize(a,b) with {a==2;a==3;b==1;})$fatal(1,"scope unsat accepted");
  if(a!=32'h5acb8291||b!=(a^32'h12345678))$fatal(1,"scope failure wrote variables");
  if(!std::randomize() with {a==32'h5acb8291;})$fatal(1,"empty scope check true");
  if(std::randomize() with {a==0;})$fatal(1,"empty scope check false");
  if(!std::randomize())$fatal(1,"empty scope check no constraint");
  if(sample(123)!=253)$fatal(1,"scope automatic");
  $display("TRACE constraints scope rare unsat automatic pass");$finish;
 end
endmodule
