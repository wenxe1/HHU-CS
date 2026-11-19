module regfile_tb;
    reg clk;                      // ????
    reg rst;                      // ??????
    reg we;                       // ?????
    reg [1:0] raddr1, raddr2;     // ????
    reg [1:0] waddr;              // ????
    reg [7:0] wdata;              // ????
    wire [7:0] rdata1, rdata2;    // ????

    regfile uut (
        .clk(clk),
        .rst(rst),
        .we(we),
        .raddr1(raddr1),
        .raddr2(raddr2),
        .waddr(waddr),
        .wdata(wdata),
        .rdata1(rdata1),
        .rdata2(rdata2)
    );

    // ????
    initial clk = 0;
    always #5 clk = ~clk;

    // ????
    initial begin
        // ?????
        rst = 1; we = 0; waddr = 0; wdata = 0; raddr1 = 0; raddr2 = 0;
        #10;

        // ?????
        rst = 1; #10;
        rst = 0; #10;

        // ????????
        we = 1; waddr = 2'b00; wdata = 8'hAA; #10; // ?? r0
        we = 1; waddr = 2'b01; wdata = 8'hBB; #10; // ?? r1
        we = 1; waddr = 2'b10; wdata = 8'hCC; #10; // ?? r2
        we = 1; waddr = 2'b11; wdata = 8'hDD; #10; // ?? r3
        we = 0;

        // ????
        raddr1 = 2'b00; raddr2 = 2'b01; #10; // ?? r0 ? r1

        raddr1 = 2'b10; raddr2 = 2'b11; #10; // ?? r2 ? r3

        // ????
        rst = 1; #10;
        rst = 0; #10;

        raddr1 = 2'b00; raddr2 = 2'b01; #10; // ?? r0 ? r1

        $stop;
    end
endmodule
