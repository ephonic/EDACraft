`timescale 1ps/1ps
module leaf;
  reg [128:0] mem[0:2];
  reg [128:0] word;
endmodule
module top;
  leaf u(),v();
  integer i;
  initial begin
    u.mem[0]='0;u.mem[1]='0;u.mem[2]='0;v.mem[1]='1;
    u.word='0;v.word='1;
    i=0;u.mem[i++][65+:64]=64'hfedcba9876543210;
    u.mem[1][0+:65]={1'b1,64'h0123456789abcdef};
    u.word={1'b1,64'hf0f0f0f0f0f0f0f0,64'h0123456789abcdef};
    u.word[127:64]^=64'h1111111111111111;
    if(i!=1||u.mem[0][128:65]!=64'hfedcba9876543210||u.mem[1][64:0]!={1'b1,64'h0123456789abcdef}||u.word[127:64]!=64'he1e1e1e1e1e1e1e1)$fatal(1,"wide write");
    i=1;u.mem[i++][128:64]<=#2 65'h123456789abcdef01;
    #1;if(u.mem[1][128:65]!=0)$fatal(1,"wide NBA early");
    #2;if(u.mem[1][128:64]!=65'h123456789abcdef01||u.mem[2]!=0||v.mem[1]!={129{1'b1}}||v.word!={129{1'b1}})$fatal(1,"wide NBA/alias");
    $display("TRACE hierarchy wide %h %h %h",u.mem[0],u.mem[1],u.word);
    $finish;
  end
endmodule
