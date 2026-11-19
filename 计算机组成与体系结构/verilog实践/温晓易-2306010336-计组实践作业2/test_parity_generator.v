`timescale 1ns / 1ps

module test_parity_generator;
    reg [7:0] data_in; 
    reg mode;          
    wire parity_bit;        

    parity_generator uut (
        .data_in(data_in),
        .mode(mode),
        .parity_bit(parity_bit)
    );

    initial begin
        data_in = 8'b00000000; mode = 0;  // Even parity -> 0
        #10 data_in = 8'b10101011; mode = 0; // Even parity -> 1
        #10 data_in = 8'b10101010; mode = 1; // Odd parity -> 1
        #10 data_in = 8'b11111110; mode = 1; // Odd parity -> 0
        #10 $stop;
    end
endmodule