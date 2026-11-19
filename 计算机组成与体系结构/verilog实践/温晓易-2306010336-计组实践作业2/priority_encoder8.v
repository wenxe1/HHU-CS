module priority_encoder8 (
    input wire [7:0] in,
    output reg [2:0] out,
    output reg valid
);
    always @(*) begin
        valid = 1'b0; // ????
        out = 3'b000; // ????? 0
        case (1'b1) // ??????????
            in[7]: begin
                out = 3'b111;
                valid = 1'b1;
            end
            in[6]: begin
                out = 3'b110;
                valid = 1'b1;
            end
            in[5]: begin
                out = 3'b101;
                valid = 1'b1;
            end
            in[4]: begin
                out = 3'b100;
                valid = 1'b1;
            end
            in[3]: begin
                out = 3'b011;
                valid = 1'b1;
            end
            in[2]: begin
                out = 3'b010;
                valid = 1'b1;
            end
            in[1]: begin
                out = 3'b001;
                valid = 1'b1;
            end
            in[0]: begin
                out = 3'b000;
                valid = 1'b1;
            end
        endcase
    end
endmodule