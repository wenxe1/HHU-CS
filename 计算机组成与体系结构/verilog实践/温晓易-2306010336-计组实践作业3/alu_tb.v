module alu_tb;
    reg [3:0] op;            // ???
    reg [7:0] a, b;          // ???
    wire [7:0] result;       // ????
    wire zero_flag;          // ???

    alu uut (
        .op(op),
        .a(a),
        .b(b),
        .result(result),
        .zero_flag(zero_flag)
    );

    initial begin
        // ????
        op = 4'h0; a = 8'h05; b = 8'h03; #10;

        // ????
        op = 4'h1; a = 8'h05; b = 8'h05; #10;

        // ?????
        op = 4'h2; a = 8'h0F; b = 8'hF0; #10;

        // ?????
        op = 4'h3; a = 8'h0F; b = 8'hF0; #10;

        // ??????
        op = 4'h4; a = 8'hFF; b = 8'h0F; #10;

        // ????
        op = 4'h5; a = 8'h01; b = 8'h00; #10;
 
        // ??????
        op = 4'h6; a = 8'h80; b = 8'h00; #10;
 
        // ??????
        op = 4'h7; a = 8'h80; b = 8'h00; #10;
   
        $stop;
    end
endmodule
