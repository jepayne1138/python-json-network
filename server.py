#! /usr/bin/env python3

import socket
import sys
import os
import tempfile
from contextlib import closing
from typing import *


def run_server(address: str, port: int, chunksize: int, out_dir: str=None):
    out_dir = os.getcwd() if out_dir is None else out_dir

    with socket.socket() as sock:  # type: socket.socket
        sock.bind((address, port))
        sock.listen()

        while True:
            conn, _ = sock.accept()  # type: socket.socket, (str, int)

            fd, in_file_name = tempfile.mkstemp(dir=out_dir)  # type: int, str
            with closing(os.fdopen(fd, 'wb')) as in_file:  # type: IO[bytes]
                # Read incoming information and write to a file
                chunk = conn.recv(chunksize)  # type: bytes
                while (chunk):
                    in_file.write(chunk)
                    chunk = conn.recv(chunksize)  # type: bytes
            conn.close()


def main():
    ADDRESS = 'localhost'
    PORT = 13579
    CHUNKSIZE = 1024
    run_server(ADDRESS, PORT, CHUNKSIZE)

if __name__ == '__main__':
    main()
