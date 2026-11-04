`timescale 1ns/1ps
module top;
  typedef struct packed {bit [3:0] bits; logic [3:0] raw;} packed_t;
  typedef struct {bit [7:0] bits; logic [7:0] raw;} item_t;
  typedef struct {item_t item; packed_t packed_view; bit [129:0] wide;} nested_t;
  item_t s, want, rows[0:1];
  nested_t n, expected_n;
  int index=0, calls=0;
  function automatic logic [3:0] source();
    begin calls++; source=4'bxz10; end
  endfunction
  initial begin
    if(s.bits!==0||s.raw!==8'bx||rows[0].bits!==0||rows[1].raw!==8'bx||n.wide!==0||n.item.bits!==0)$fatal(1,"module aggregate defaults after signal ordering");
    s.bits=0;s.raw=0;want=s;
    s.bits[3:0]=source();want.bits=2;
    if(s!==want||calls!=1)$fatal(1,"selected two-state member");
    {s.bits,s.raw}=16'bxz101zx0_zzxx1100;
    want.bits=8'b00101000;want.raw=8'bzzxx1100;
    if(s!==want)$fatal(1,"concatenated member conversion");
    s.bits+=8'bx;want.bits=0;
    if(s!==want)$fatal(1,"compound member conversion");
    rows[0]=want;rows[1]=want;
    rows[index++].bits[4+:4]=source();want.bits=8'h20;
    if(index!=1||calls!=2||rows[0]!==want||rows[1].bits!==0)$fatal(1,"single-evaluation array member");
    s='{bits:8'bxz0110zx,raw:8'bxz0110zx};
    want.bits=8'h18;want.raw=8'bxz0110zx;
    if(s!==want)$fatal(1,"assignment pattern member state");
    n.item=s;n.packed_view=8'bxz10_zx01;n.wide='1;
    n.wide[63+:67]='x;
    expected_n.item=want;expected_n.packed_view=8'bxz10_zx01;
    expected_n.wide=130'h7fff_ffff_ffff_ffff;
    if(n!==expected_n||n.packed_view.bits!==4'b0010||n.packed_view!==8'bxz10_zx01)$fatal(1,"nested/wide state representation");
    $display("TRACE storage %b %b %h %0d %0d",s.bits,s.raw,n.wide,index,calls);
    #1;$finish;
  end
endmodule
