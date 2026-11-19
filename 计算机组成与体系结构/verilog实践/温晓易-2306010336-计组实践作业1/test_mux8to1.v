`timescale 1ns / 1ps

module test_mux8to1;
    reg [7:0] data_in;
    reg [2:0] sel;
    wire data_out;

    mux8to1 uut (
        .data_in(data_in),
        .sel(sel),
        .data_out(data_out)
    );

    initial begin
        // ?????
        data_in = 8'b01010101; sel = 3'b000;
        
        #2 sel = 3'b000; // ?? data_in[0]
        #2 sel = 3'b001; // ?? data_in[1]
        #2 sel = 3'b010; // ?? data_in[2]
        #2 sel = 3'b011; // ?? data_in[3]
        #2 sel = 3'b100; // ?? data_in[4]
        #2 sel = 3'b101; // ?? data_in[5]
        #2 sel = 3'b110; // ?? data_in[6]
        #2 sel = 3'b111; // ?? data_in[7]

        #2 $stop;
    end

endmodule