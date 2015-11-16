#! /usr/bin/env python3

import argparse
import socket
import sys
import os
import tempfile
from contextlib import closing
from typing import *
import threading


BUFFER_SIZE = 65536


class Client(threading.Thread):
    """Thread that manages all client interaction with the server.

    Creates a new socket connection for every requested
    """

    def __init__(self, address: str, port: int, buffer_size: int=BUFFER_SIZE):
        self.address = address  # type: str
        self.port = port  # type: int
        self.buffer_size = buffer_size  # type: int

    def close(self):
        pass

class ClientSocket(socket.socket):

    def __init__(self, address: str, port: int, buffer_size: int=BUFFER_SIZE):
        super().__init__()
        self.address = address  # type: str
        self.port = port  # type: int
        self.buffer_size = buffer_size  # type: int
        super().connect((self.address, self.port))



def send_file(file, connection: ClientSocket):
    chunk = file.read(connection.buffer_size)  # type: bytes
    while (chunk):
        connection.send(chunk)
        chunk = file.read(connection.buffer_size)  # type: bytes

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
    parser.add_argument('-b', '--buffer_size',
        default=1024, type=int,
        help='Chunk size to read in from connections'
    )
    args = parser.parse_args()

    with ClientSocket(args.address, args.port, args.buffer_size) as client_sock:  # type: ClientSocket
        with open(args.file, 'rb') as out_file:  # type: IO[bytes]
            send_file(out_file, client_sock)

if __name__ == '__main__':
    main()
