#! /usr/bin/env python3

import socket
import sys
import os
import tempfile
from contextlib import closing
from typing import *



class SocketClientBase(socket.socket):

    def __init__(self, address: str, port: int, chunksize: int):
        super().__init__()
        self.address = address  # type: str
        self.port = port  # type: int
        self.chunksize = chunksize  # type: int
        super().connect((self.address, self.port))



def send_file(file, connection: SocketClientBase):
    chunk = file.read(connection.chunksize)  # type: bytes
    while (chunk):
        connection.send(chunk)
        chunk = file.read(connection.chunksize)  # type: bytes

def main():
    ADDRESS = 'localhost'
    PORT = 13579
    CHUNKSIZE = 1024

    filename = 'send.txt'  # type: str

    with SocketClientBase(ADDRESS, PORT, CHUNKSIZE) as client_sock:  # type: SocketClientBase
        with open(filename, 'rb') as out_file:  # type: IO[bytes]
            send_file(out_file, client_sock)

if __name__ == '__main__':
    main()
