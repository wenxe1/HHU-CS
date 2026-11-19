module cpu_datapath_tb;
    reg clk;                      // ????
    reg rst;                      // ??????
    reg [7:0] instr;              // ????
    wire [7:0] alu_result;        // ALU ????
    
    cpu_datapath uut (
        .clk(clk),
        .rst(rst),
        .instr(instr),
        .alu_result(alu_result)
    );

    // ????
    initial clk = 0;
    always #5 clk = ~clk;

    // ??
    initial begin
        // ???
        rst = 1; instr = 8'h00; #10;  // ??
        rst = 0; #10;
        uut.u_regfile.registers[1] = 8'd5; // r1 = 5
        uut.u_regfile.registers[2] = 8'd3; // r2 = 3
        uut.u_regfile.registers[3] = 8'd7; // r3 = 7
    
        instr = 8'h06; #10; // add r1, r2 (5 + 3 = 8)
        instr = 8'h17; #10; // sub r1, r3 (8 - 7 = 1)
        instr = 8'h46; #10; // xor r1, r2 (1 ^ 3 = 2)
        instr = 8'h54; #10; // sll r1 (2 << 1 = 4)
        instr = 8'h64; #10; // srl r1 (4 >> 1 = 2)
    
        $stop;
    end
endmodule