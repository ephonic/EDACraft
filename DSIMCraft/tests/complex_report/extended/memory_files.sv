`timescale 1ns/1ps
module tb;
  reg [131:0] data[2:5],h[2:5],b[2:5];
  integer i;
  initial begin
    #2;
    data[2]=132'hf01234567_89abcdef_76543210_fedcba98;
    data[3]=132'hxxxxzzzzz_00001111_22223333_44445555;
    data[4]=132'h000012345_67890123_45678901_23456789;
    data[5]=132'hfffffffff_ffffffff_ffffffff_ffffffff;
    $writememh("wide.hex",data);
    $writememb("wide.bin",data);
    $readmemh("wide.hex",h);$readmemb("wide.bin",b);
    for(i=2;i<=5;i++)if(data[i]!==h[i]||data[i]!==b[i])$fatal(1,"file roundtrip %d",i);
    $writememh("partial.hex",data,3,4);
    $readmemh("partial.hex",h,3,4);
    if(h[3]!==data[3]||h[4]!==data[4])$fatal(1,"partial roundtrip");
    $display("TRACE memory files complete");$finish;
  end
endmodule
