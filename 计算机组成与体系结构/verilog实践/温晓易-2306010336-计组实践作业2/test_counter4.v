// ??????(1ns)?????(1ps)
`timescale 1ns / 1ps

module test_counter4;
    reg clock;             
    reg reset;           
    wire [3:0] count;      

    counter4 uut (
        .clock(clock),
        .reset(reset),
        .count(count)
    );

    // ?????????? 4ns
    initial begin
        clock = 0;    
        forever #2 clock = ~clock; // ? 2ns ????
    end

    initial begin
        reset = 1;          // ??????
        #4 reset = 0;      // 10ns ???????
        #8 reset = 1;      // 50ns ?????
        #4 reset = 0;      // 10ns ???????
        #8 $stop;          // ????
    end
endmodule