module alu (
    input wire [3:0] op,       // ???
    input wire [7:0] a, b,     // ???
    output reg [7:0] result,   // ????
    output reg zero_flag       // ???
);
    always @(*) begin
        case (op)
            4'h0: result = a + b;         
            4'h1: result = a - b;         
            4'h2: result = a & b;         // ???
            4'h3: result = a | b;         // ???
            4'h4: result = a ^ b;         // ????
            4'h5: result = a << 1;        
            4'h6: result = a >> 1;        // ??????
            4'h7: result = $signed(a) >>> 1; // ??????
            default: result = 8'h00;      // ???
        endcase
        zero_flag = (result == 8'h00) ? 1'b1 : 1'b0;  // ?????
    end
endmodule