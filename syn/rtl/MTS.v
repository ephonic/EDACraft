`timescale 1ns / 1ps

module MTS #(
  parameter Instruction_Width = 'd96,
  parameter Sel_Width = 'd8,
  parameter BP_NUM = 'd256,
  parameter A = 1'd0,//�������λ����-״̬
  parameter B = 1'd1
)
(   input CLK,                               //pc��CLK
    input RST,                              //pc��RST
    input[Instruction_Width-1:0] MOSI_sData,//PC�˷��͵�����96λ
    input [Sel_Width-1:0]CS,               //PC�˷��͵�Ƭѡ�ź�
    input [Sel_Width-1:0]CS_2,
    input flag,
    input MISO,                       //?
    output reg MOSI,//instr_mem�Ľӿ�
    output reg MISO_rData,
    output reg SCK,                         //BP��SCK
    output reg [BP_NUM-1:0]BP_CS,           //256��BP_CSƬѡ�˿�
    output reg [BP_NUM-1:0]BP_CS2
    );


reg Data_State=A;
reg [6:0]m=7'd95;
initial begin
 BP_CS = {256{1'b1}};
 BP_CS2 = {256{1'b1}};
end

always@(posedge CLK or negedge RST) begin
if (RST==0)//�͵�ƽ��λ
begin
    m<=7'd95;
    SCK<=1'b1;
    MOSI<='b0;//��ʼ��ƽΪ��
    MISO_rData<=1'b0;
    Data_State<=A;
end

else
begin//posedge CLK����SPIʱ��
   case(Data_State)
     A://SCK�½����л�����
     begin
      if (flag == 1'b0) begin
          SCK<=1'b0;
          BP_CS2 <= {256{1'b1}};
          BP_CS <= {256{1'b1}};
          BP_CS[{CS}]<=1'b0;       //ѡ�е�ƬѡΪ0
            if(m[6:0]!=7'd127)begin
              MOSI<=MOSI_sData[m];
              m <= m-1;
              Data_State<=B;
            end
            else Data_State<=B;
       end
      else begin
          SCK<=1'b0;
          BP_CS <= {256{1'b1}};
          Data_State <=B;
      end
     end
  
     
     B://SCK�����ؽ�������
     begin
       if (flag == 1'b1) begin
        SCK<=1'b1;
        BP_CS <= {256{1'b1}};
        BP_CS2 <= {256{1'b1}};
        BP_CS2[{CS_2}]<=1'b0;
        MISO_rData <= MISO;
        Data_State<=A;
        end
        else begin
          SCK<=1'b1;
          BP_CS2 <= {256{1'b1}};
          Data_State <=A;
        end
        end
     default:
     Data_State<=A;
     endcase
end
end

endmodule

