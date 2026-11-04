`timescale 1ns/1ps
module top;
typedef struct packed {bit [3:0] bits;logic [3:0] tail;} mixed_t;
typedef struct packed {mixed_t inner;logic [1:0] tag;} nested_t;
typedef union packed {bit [7:0] bits;logic [7:0] raw;} view_t;
typedef union packed {bit [129:0] bits;logic [129:0] raw;} wide_t;
typedef struct packed {bit [3:0] bits;bit [3:0] tail;} pure_t;
typedef struct {bit [3:0] bits;logic [3:0] tail;} unpacked_t;
mixed_t s, words[0:1];nested_t n;view_t u;wide_t w;
pure_t all_bits;unpacked_t separate;bit [3:0] standalone;
int index=0,calls=0;
function automatic logic [3:0] source();
  begin
    calls++;
    source=4'bx1z0;
  end
endfunction
initial begin
  s='x;u='x;n='x;words[0]='x;words[1]='x;
  standalone=4'bx1z0;all_bits.bits=4'bx1z0;separate.bits=4'bx1z0;
  s.bits=source();n.inner.bits=4'bx1z0;u.bits=8'bxz0011zx;
  words[index++].bits=4'bx1z0;
  if(s!==8'bx1z0xxxx||n.inner!==8'bx1z0xxxx||u.raw!==8'bxz0011zx)
    $fatal(1,"packed storage must retain raw X/Z");
  if(s.bits!==4'b0100||n.inner.bits!==4'b0100||u.bits!==8'b00001100)
    $fatal(1,"bit views must convert on read");
  if(words[0]!==s||words[1]!==8'hxx||index!=1||calls!=1)
    $fatal(1,"member address and RHS evaluated once");
  if(standalone!==4'b0100||all_bits.bits!==4'b0100||separate.bits!==4'b0100)
    $fatal(1,"independent two-state storage conversion");
  $display("TRACE views direct %b %b %b %b",s,n.inner,u.raw,s.bits);
  s.bits<=#2 4'bzx01;u.bits<=#2 8'bz10xx01z;
  #1;
  if(s!==8'bx1z0xxxx||u.raw!==8'bxz0011zx)$fatal(1,"NBA delivered early");
  #2;
  if(s!==8'bzx01xxxx||u.raw!==8'bz10xx01z||s.bits!==4'b0001||u.bits!==8'b01000010)
    $fatal(1,"delayed member NBA storage");
  $display("TRACE views nba %b %b %b %b",s,u.raw,s.bits,u.bits);
  s='x;u='1;
  {s.bits,u.bits[3:0]}=8'bxz011zx0;
  if(s!==8'bxz01xxxx||u.raw!==8'b11111zx0)$fatal(1,"concatenation member storage");
  $display("TRACE views concat %b %b %b %b",s,u.raw,s.bits,u.bits);
  w.raw=0;w.bits={2'bxz,64'h0123456789abcdef,64'hfedcba9876543210};
  if(w.raw!=={2'bxz,64'h0123456789abcdef,64'hfedcba9876543210}||
     w.bits!=={2'b00,64'h0123456789abcdef,64'hfedcba9876543210})
    $fatal(1,"wide member storage");
  $display("TRACE views wide %b %b",w.raw[129:128],w.bits[129:128]);
end
endmodule
