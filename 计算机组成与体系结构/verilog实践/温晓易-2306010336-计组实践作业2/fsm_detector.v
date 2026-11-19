module fsm_detector (
    input wire clk,  // ????
    input wire rst,  // ??????
    input wire din,  // ????
    output reg dout
);
    // ????
    parameter S0 = 3'b000;  // ????
    parameter S1 = 3'b001;  // 1
    parameter S2 = 3'b010;  // 11
    parameter S3 = 3'b011;  // 110
    parameter S4 = 3'b100;  // 1101

    reg [2:0] current_state, next_state;  // ????, ????

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            current_state <= S0;  // ????
        end else begin
            current_state <= next_state; // ????
        end
    end

    // ?????
    always @(*) begin
        case (current_state)
            S0: next_state = (din == 1) ? S1 : S0; // ??? "1" ?? S1
            S1: next_state = (din == 1) ? S2 : S0; // ??? "11" ?? S2
            S2: next_state = (din == 0) ? S3 : S2; // ??? "110" ?? S3
            S3: next_state = (din == 1) ? S4 : S0; // ??? "1101" ?? S4
            S4: next_state = (din == 1) ? S2 : S0; // ??? "?1?1" ??? S2
            default: next_state = S0;  // ???? S0
        endcase
    end

    // ??
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            dout <= 1'b0;
        end else begin
            dout <= (current_state == S4) ? 1'b1 : 1'b0;
        end
    end
endmodule
