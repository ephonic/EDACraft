module top;
 class Values;
  rand bit signed [7:0] a;
  rand bit [7:0] u;
  rand bit [95:0] wide;
  rand bit select;
  bit impossible=0;
  constraint math {
   a inside {[-12:-3]};a%3==0;
   u==8'(a+1);
   (a>>>2)==-2;
   wide==96'hacbd13572468ef9000fffffb;
   wide[7:0]==u;
   if(select) {a==-6;} else {a==-9;}
   select -> int'(a)+int'(u)==245;
   if(impossible) {wide[7:0]!=u;}
  }
 endclass
 Values v;
 bit signed [7:0] observed;
 bit [95:0] observed_wide;
 initial begin
  v=new;
  if(!v.randomize())$fatal(1,"signed wide satisfiable");
  if(v.a!=-6||v.u!=251||v.wide!=96'hacbd13572468ef9000fffffb||v.select!=1)$fatal(1,"signed wide values");
  observed=v.a;observed_wide=v.wide;
  v.impossible=1;
  if(v.randomize())$fatal(1,"wide contradiction");
  if(v.a!=-6||v.u!=251||v.wide!=96'hacbd13572468ef9000fffffb||v.select!=1)$fatal(1,"failure atomicity");
  if(observed!=-6||observed_wide!=v.wide)$fatal(1,"observed values");
  $display("TRACE constraints signed wide unsat atomic pass");$finish;
 end
endmodule
