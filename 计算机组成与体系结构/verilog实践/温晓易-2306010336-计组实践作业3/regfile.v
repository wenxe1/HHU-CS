module regfile (
    input wire clk,                // ????
    input wire rst,                // ??????
    input wire we,                 // ?????
    input wire [1:0] raddr1,       // ????1??
    input wire [1:0] raddr2,       // ????2??
    input wire [1:0] waddr,        // ??????
    input wire [7:0] wdata,        // ????
    output wire [7:0] rdata1,      // ????1??
    output wire [7:0] rdata2       // ????2??
);
    // 4?8?????????
    reg [7:0] registers [3:0];

    // ????
    assign rdata1 = registers[raddr1];
    assign rdata2 = registers[raddr2];

    // ????
    always @(posedge clk) begin
        if (rst) begin
            // ????
            registers[0] <= 8'b0;
            registers[1] <= 8'b0;
            registers[2] <= 8'b0;
            registers[3] <= 8'b0;
        end else if (we) begin
            // ??????????
            registers[waddr] <= wdata;
        end
    end
endmodule