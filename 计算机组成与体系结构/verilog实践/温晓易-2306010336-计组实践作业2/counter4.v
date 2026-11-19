
module counter4 (
    input wire clock,  // ????
    input wire reset,  // ??????
    output reg [3:0] count  // 4????
);
    always @(posedge clock) begin
        if(reset)  // ??
            count <= 4'b0000;
        else
            count <= count + 1; // ??
    end
endmodule