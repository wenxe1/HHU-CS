`timescale 1ns / 1ps

module test_fsm_detector;
    reg clk;             
    reg rst;           
    reg din;               
    wire dout;             

    fsm_detector uut (
        .clk(clk),
        .rst(rst),
        .din(din),
        .dout(dout)
    );

    // ?????? ??? 10ns
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end

    // ????
    initial begin
        rst = 1; din = 0;  // ???
        #10 rst = 0;  // ??????
        #10 din = 1;  // 1
        #10 din = 1;  // 11
        #10 din = 0;  // 110
        #10 din = 1;  // 1101 -> 1
        #10 din = 1;  // 11
        #10 din = 0;  // 110
        #10 din = 1;  // 1101 -> 1
        #10 rst = 1;  // ????
        #10 $stop;          
    end
endmodule
