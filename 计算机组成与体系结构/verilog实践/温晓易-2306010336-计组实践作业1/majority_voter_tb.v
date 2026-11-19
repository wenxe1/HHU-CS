// ??????(1ns)?????(1ps)
`timescale 1ns / 1ps

module tb_majority_voter;
    // ????
    reg ta;
    reg tb;
    reg tc;
    // ????
    wire ty;

    // ???????
    majority_voter my_mv (
        .a(ta),
        .b(tb),
        .c(tc),
        .y(ty)
    );

    // ???????
    initial begin
        // ??
        ta = 0; tb = 0; tc = 0;
        #2; // ?? 5*1 ns

        ta = 0; tb = 0; tc = 1;
        #2;

        ta = 0; tb = 1; tc = 0;
        #2;

        ta = 1; tb = 1; tc = 1;
        #2;

        // ????
        $stop;
    end
endmodule