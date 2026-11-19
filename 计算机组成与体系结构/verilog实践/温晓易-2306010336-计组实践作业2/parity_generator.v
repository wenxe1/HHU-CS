module parity_generator (
    input wire [7:0] data_in, 
    input wire mode,  // 0: even 1: odd
    output wire parity_bit  
);
    assign parity_bit = ^data_in ^ mode;  //????
endmodule
