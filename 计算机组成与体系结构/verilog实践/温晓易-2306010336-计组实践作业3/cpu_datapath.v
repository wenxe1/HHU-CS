module cpu_datapath (
    input wire clk,                // ????
    input wire rst,                // ??????
    input wire [7:0] instr,        // ????
    output wire [7:0] alu_result   // ????????
);
    // ????
    wire [3:0] op;                 // ALU ???
    wire [1:0] rs1, rs2;           // ??????
    wire [7:0] rdata1, rdata2;     // ???????          

    decoder u_decoder (
        .instr(instr),
        .op(op),
        .rs1(rs1),
        .rs2(rs2)
    );

    regfile u_regfile (
        .clk(clk),
        .rst(rst),
        .we(1'b1),                 // ?????? 1
        .raddr1(rs1),
        .raddr2(rs2),
        .waddr(rs1),               // ??? rs1
        .wdata(alu_result),           // ????? ALU ??
        .rdata1(rdata1),
        .rdata2(rdata2)
    );

    alu u_alu (
        .op(op),
        .a(rdata1),
        .b(rdata2),
        .result(alu_result),
        .zero_flag()               // ?? zero_flag
    );

endmodule