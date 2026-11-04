module top;
  parameter real P=-1.5+0.25;
  parameter shortreal S=16777217;
  localparam int N=int'(-1.5);
  localparam logic CONST_X=1.0&&1'bx;
  localparam logic CONST_ZERO=0.0&&1'bx;
  localparam logic SHORT_EQUAL=shortreal'(16777216)==16777217;
  real r, negzero;
  shortreal a,b;
  int i;
  logic unknown;
  initial begin
    if(P!=-1.25 || S!=16777216.0 || N!=-2) $fatal(1,"real parameter");
    if(CONST_X!==1'bx || CONST_ZERO!==1'b0 || !SHORT_EQUAL)$fatal(1,"constant real truth/promotion");
    r=1.5;i=r;if(i!=2)$fatal(1,"positive rounding");
    r=-1.5;i=r;if(i!=-2 || $rtoi(r)!=-1)$fatal(1,"negative rounding");
    i=-1;r=i;if(r!=-1.0)$fatal(1,"signed conversion");
    r=64'hffffffffffffffff;if(r<1.0e19)$fatal(1,"unsigned conversion");
    r=8'b1x01z101;if(r!=149.0)$fatal(1,"unknown conversion");
    a=16777216;b=1;
    if(!(a==16777217) || a>16777217)$fatal(1,"shortreal integral comparison");
    if((a+b)!=16777216.0 || (real'(a)+b)!=16777217.0)$fatal(1,"shortreal promotion");
    r=2.0**3;if(r!=8.0)$fatal(1,"real power");
    negzero=$bitstoreal(64'h8000000000000000);
    if(negzero || $realtobits(negzero)!=64'h8000000000000000)$fatal(1,"negative zero");
    unknown=1'bx;r=unknown?1.5:2.5;if(r!=0.0)$fatal(1,"real unknown mux");
    if((1.0&&unknown)!==1'bx || (0.0||unknown)!==1'bx)$fatal(1,"mixed truth");
    if($bitstoshortreal(32'h3f000000)!=0.5 || $shortrealtobits(shortreal'(0.5))!=32'h3f000000)$fatal(1,"shortreal bits");
    if($bits($realtobits(r))!=64 || $bits($shortrealtobits(a))!=32)$fatal(1,"real bit conversion widths");
    r=P;
    $display("TRACE arithmetic p=%0.3f n=%0d bits=%h",r,N,$realtobits(r));
    $finish;
  end
endmodule
