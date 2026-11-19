`timescale 1ns / 1ps

module test_priority_encoder8;
    reg [7:0] in;
    wire [2:0] out;
    wire valid;

    priority_encoder8 uut (
        .in(in),
        .out(out),
        .valid(valid)
    );

    initial begin
        in = 8'b00000001; #2; // ???????
        in = 8'b00001000; #2; // ???????
        in = 8'b10000000; #2; // ???????
        in = 8'b01010101; #2; // ??????????????
        in = 8'b00000000; #2; // ????
        $finish;
    end
endmodule