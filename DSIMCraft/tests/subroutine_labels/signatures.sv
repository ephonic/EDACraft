module top;
 typedef logic[7:0] byte_t;
 typedef enum int {ZERO,ONE,TWO} enum_t;
 // All original implicit/ranged, integral, named and lifetime grammar paths.
 function f0;input a;f0=a;endfunction : f0
 function f1(input a);f1=a;endfunction : f1
 function f2(input a);reg t;t=a;f2=t;endfunction : f2
 function[7:0] f3;input[7:0] a;f3=a+1;endfunction : f3
 function[7:0] f4(input[7:0] a);f4=a+1;endfunction : f4
 function[7:0] f5(input[7:0] a);reg[7:0] t;t=a+1;f5=t;endfunction : f5
 function integer f6;input integer a;f6=a+1;endfunction : f6
 function int f7(input int a);return a+1;endfunction : f7
 function int f8(input int a);int t;t=a+1;return t;endfunction : f8
 function logic[7:0] f9;input[7:0] a;f9=a+1;endfunction : f9
 function logic[7:0] f10(input[7:0] a);return a+1;endfunction : f10
 function logic[7:0] f11(input[7:0] a);reg[7:0] t;t=a+1;return t;endfunction : f11
 function automatic f12;input a;f12=a;endfunction : f12
 function automatic f13(input a);f13=a;endfunction : f13
 function automatic f14(input a);reg t;t=a;f14=t;endfunction : f14
 function automatic[7:0] f15;input[7:0] a;f15=a+1;endfunction : f15
 function automatic[7:0] f16(input[7:0] a);return a+1;endfunction : f16
 function automatic[7:0] f17(input[7:0] a);reg[7:0] t;t=a+1;return t;endfunction : f17
 function byte_t f18;input byte_t a;f18=a+1;endfunction : f18
 function byte_t f19(input byte_t a);return a+1;endfunction : f19
 function byte_t f20(input byte_t a);byte_t t;t=a+1;return t;endfunction : f20
 function automatic byte_t f21;input byte_t a;f21=a+1;endfunction : f21
 function automatic byte_t f22(input byte_t a);return a+1;endfunction : f22
 function automatic byte_t f23(input byte_t a);byte_t t;t=a+1;return t;endfunction : f23
 function automatic enum_t enum_fn(input enum_t a);return a;endfunction : enum_fn
 function int \escaped.fn (input int a);return a+1;endfunction : \escaped.fn
 int observed;
 task t0;input int x;observed=x;endtask : t0
 task t1;input int x;int y;y=x+1;observed=y;endtask : t1
 task automatic t2;input int x;observed=x;endtask : t2
 task automatic t3;input int x;int y;y=x+1;observed=y;endtask : t3
 task t4(input int x);observed=x;endtask : t4
 task t5(input int x);int y;y=x+1;observed=y;endtask : t5
 task automatic t6(input int x);observed=x;endtask : t6
 task automatic t7(input int x);int y;y=x+1;observed=y;endtask : t7
 initial begin
  observed=f0(1)+f1(1)+f2(1)+f3(3)+f4(3)+f5(3)+f6(3)+f7(3)+f8(3)+f9(3)+f10(3)+f11(3)
   +f12(1)+f13(1)+f14(1)+f15(3)+f16(3)+f17(3)+f18(3)+f19(3)+f20(3)+f21(3)+f22(3)+f23(3);
  $display("TRACE functions %0d %0d %0d",observed,enum_fn(TWO),\escaped.fn (6));
  #1;t0(0);t1(observed);t2(observed+1);t3(observed);t4(observed+1);t5(observed);t6(observed+1);t7(observed);
  $display("TRACE tasks %0d",observed);#1;$finish;
 end
endmodule
