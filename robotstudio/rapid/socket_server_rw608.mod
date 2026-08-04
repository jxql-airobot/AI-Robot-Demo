MODULE socket_server_rw608

    VAR socketdev server_socket;

    PROC socket_main()
        SocketCreate server_socket;
        TPWrite "SocketCreate OK";
    ENDPROC

ENDMODULE
