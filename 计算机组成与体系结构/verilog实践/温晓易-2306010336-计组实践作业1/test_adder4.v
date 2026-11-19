`timescale 1ns / 1ps

module test_adder4;
    reg [3:0] A, B; 
    reg Cin;    
    wire [3:0] Sum;
    wire Cout;      

    adder4 uut (
        .A(A),
        .B(B),
        .Cin(Cin),
        .Sum(Sum),
        .Cout(Cout)
    );

    initial begin
        // 0 + 1
        A = 4'b0000; B = 4'b0001; Cin = 0; #2;

        // 1 + 1 ????Cout
        A = 4'b0001; B = 4'b0001; Cin = 0; #2;

        // ????Cin
        A = 4'b1010; B = 4'b0101; Cin = 1; #2;

	A = 4'b1000; B = 4'b1000; Cin = 0; #2;

        $stop;
    end
endmodule