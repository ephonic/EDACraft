module top;
 typedef enum int signed {BACK=-7,IDLE=0,WRITE=19} command_t;
 class Packet;
  rand command_t command;
  bit impossible;
  int pre_calls,post_calls;
  constraint legal {command!=IDLE;if(impossible)int'(command)==123;}
  function void pre_randomize();pre_calls++;endfunction
  function void post_randomize();post_calls++;endfunction
 endclass
 Packet p;command_t saved;int checked;
 initial begin
  p=new;p.srandom(17);
  repeat(16)begin
   if(!p.randomize())$fatal(1,"enum randomization failed");
   if(p.command!=BACK&&p.command!=WRITE)$fatal(1,"enum domain");
   checked++;
  end
  saved=p.command;p.impossible=1;
  if(p.randomize()||p.command!==saved||p.pre_calls!=17||p.post_calls!=16)$fatal(1,"failure atomicity");
  p.impossible=0;p.legal.constraint_mode(0);
  if(p.randomize() with {int'(command)==123;})$fatal(1,"domain survives constraint_mode");
  p.command=command_t'(123);p.command.rand_mode(0);
  if(!p.randomize()||int'(p.command)!=123)$fatal(1,"inactive enum is state");
  if(!p.randomize(null)||int'(p.command)!=123)$fatal(1,"null variable list");
  p.command.rand_mode(1);
  if(!p.randomize() with {command==IDLE;}||p.command!=IDLE)$fatal(1,"inline enum constraint");
  $display("TRACE constraints enum domains callbacks modes atomicity pass");$finish;
 end
endmodule
