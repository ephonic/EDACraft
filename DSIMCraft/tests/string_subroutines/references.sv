`timescale 1ns/1ps
module top;
  typedef string text_t;
  text_t live="a",snapshot;
  int length=0,done=0;
  task automatic watch(ref text_t target,const ref string source);
    #2;
    if(source!="outside")$fatal(1,"const ref must observe live storage");
    target={source,"/seen"};
    #2;target={target,"/done"};
  endtask
  function automatic string change(ref string target,const ref text_t source);
    target={target,"/",source};return target;
  endfunction
  initial begin
    #1;watch(live,live);done=1;
  end
  initial begin
    #2;live="outside";
    #2;
    if(live!="outside/seen")$fatal(1,"ref write must be immediately visible");
    snapshot=live;
    #2;
    if(done!=1||live!="outside/seen/done")$fatal(1,"ref delayed lifetime");
    live=change(live,snapshot);length=live.len();
    if(live!="outside/seen/done/outside/seen"||snapshot!="outside/seen"||length!=30)$fatal(1,"function ref strings");
    $display("TRACE references [%s] [%s] %0d",live,snapshot,length);
    $finish;
  end
endmodule
