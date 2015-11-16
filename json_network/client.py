#! /usr/bin/env python3

import argparse
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
    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Connects to a server and sends the contents of a file.'
    )
    parser.add_argument('file', type=str,
        help='Path to the file that should be uploaded'
    )
    parser.add_argument('-a', '--address',
        default='localhost', type=str,
        help='Server address'
    )
    parser.add_argument('-p', '--port',
        default=13579, type=int,
        help='Port number'
    )
    parser.add_argument('-c', '--chunksize',
        default=1024, type=int,
        help='Chunk size to read in from connections'
    )
    args = parser.parse_args()

    with SocketClientBase(args.address, args.port, args.chunksize) as client_sock:  # type: SocketClientBase
        with open(args.file, 'rb') as out_file:  # type: IO[bytes]
            send_file(out_file, client_sock)

if __name__ == '__main__':
    main()
