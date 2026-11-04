`timescale 1ns/1ps
module top;
  reg [63:0] source=0;
  reg enable=0;
  wire [63:0] data=source;
  wire [4:0] narrow=source;
  wire [31:0] stable=enable ? source[31:0] : 32'h13579bdf;
  wire [63:0] tail=(data ^ {64{enable}}) + stable;
  integer positives=0, negatives=0, changes=0, s;
  always @(posedge data) positives=positives+1;
  always @(negedge data) negatives=negatives+1;
  always @(data) changes=changes+1;
  initial begin
    #1; positives=0; negatives=0; changes=0;
    for(s=0;s<4;s=s+1) begin
      source=64'hxxxxxxxxxxxxxxxx; #1;
      source=64'hzzzzzzzzzzzzzzzz; #1;
      source=64'h8000000000000000; #1;
      source=64'h8000000000000001; #1;
      enable=~enable; source=source+1; #0;
      source=source+32; #1;
      $display("TRACE %0d %h %h %h %h %0d %0d %0d",s,data,narrow,stable,tail,positives,negatives,changes);
    end
    $finish;
  end
endmodule
