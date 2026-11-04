`timescale 1ns/1ps
module top;
 int unsigned first[2],next[2],saved_first[2],saved_next[2],parent_next[2],discarded;
 integer round=0,k=0;
 initial begin
  for(round=0;round<2;round++)begin
   discarded=$urandom(91);
   fork
    begin
     first[0]=$urandom;#1;next[0]=$urandom;
    end
    begin
     first[1]=$urandom;
     for(k=0;k<30;k++)discarded=$urandom;
     #2;next[1]=$urandom;
    end
   join
   parent_next[round]=$urandom;
   if(round==0)begin
    saved_first[0]=first[0];saved_first[1]=first[1];saved_next[0]=next[0];saved_next[1]=next[1];
   end else if(first[0]!==saved_first[0]||first[1]!==saved_first[1]||next[0]!==saved_next[0]||next[1]!==saved_next[1]||parent_next[1]!==parent_next[0])$fatal(1,"hierarchical repeat");
  end
  if(first[0]===first[1]||next[0]===next[1])$fatal(1,"fork streams identical");
  $display("TRACE random fork hierarchical seeding pass");
 end
endmodule
