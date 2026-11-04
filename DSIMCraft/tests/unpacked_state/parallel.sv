`timescale 1ns/1ps
module lane #(parameter int MODE=0,parameter int DELAY=2)(output logic error,output logic [7:0] q);
  typedef struct {bit [7:0] bits;logic [7:0] raw;} item_t;
  item_t state,want;
  int count=0;
  initial begin
    error=0;state.bits=0;state.raw=0;want=state;q=0;
    repeat(3)begin
      #DELAY;
      if(MODE==0)begin
        state.bits+=8'bx;want.bits=0;
        if(state!==want)error=1;
        state.bits[3:0]=4'bxz10;want.bits=2;
      end else begin
        {state.bits,state.raw}=16'bxz10_zx01_zzxx0011;
        want.bits=8'h21;want.raw=8'bzzxx0011;
      end
      if(state!==want)error=1;
      count++;q=state.bits;
    end
  end
endmodule
module top;
  wire ea,eb;
  wire [7:0] a,b;
  lane #(.MODE(0),.DELAY(2)) u(ea,a);
  lane #(.MODE(1),.DELAY(3)) v(eb,b);
endmodule
