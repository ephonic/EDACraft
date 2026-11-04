`timescale 1ns/1ps
module string_lane #(parameter integer INTERVAL=2)(output integer score=0);
  string state;
  integer count=0,errors=0;
  function automatic string advance(input string old);
    return {old,"x"};
  endfunction
  task automatic update(input string old,output string next);
    next=advance(old);
  endtask
  initial begin
    repeat(4)begin
      #(INTERVAL);update(state,state);count++;score=state.len();
      if(score!=count)errors++;
    end
  end
endmodule
module top;
  wire[31:0] first,second;
  string_lane #(.INTERVAL(2)) u(first);
  string_lane #(.INTERVAL(3)) v(second);
  initial begin #14;$finish;end
endmodule
