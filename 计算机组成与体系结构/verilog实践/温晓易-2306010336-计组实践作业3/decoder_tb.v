module decoder_tb;
    reg [7:0] instr;         // ????
    wire [3:0] op;           // ALU ???
    wire [1:0] rs1, rs2;     // ?????

    decoder uut (
        .instr(instr),
        .op(op),
        .rs1(rs1),
        .rs2(rs2)
    );

    initial begin
        // op: 0001, rs1: 00, rs2: 11
        instr = 8'b00010011;#10;  

        // op: 1010, rs1: 11, rs2: 00
        instr = 8'b10101100;#10;  

        // op: 1111, rs1: 00, rs2: 01
        instr = 8'b11110001;#10;  

        // op: 0101, rs1: 10, rs2: 10
        instr = 8'b01011010;#10;  
        $stop;
    end
endmodule