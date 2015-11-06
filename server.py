#! /usr/bin/env python3

import argparse
import socket
import sys
import os
import tempfile
from contextlib import closing
from typing import *


def run_server(address: str, port: int, chunksize: int, out_dir: str=None, backlog: int=None):
    out_dir = os.getcwd() if out_dir is None else out_dir

    with socket.socket() as sock:  # type: socket.socket
        sock.bind((address, port))
        sock.listen() if backlog is None else sock.listen(backlog)

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
    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Runs a server that copies received data to a new file.'
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
    parser.add_argument('-d', '--directory',
        default=os.getcwd(), type=str,
        help='Directory where received files should be written to'
    )
    parser.add_argument('-b', '--backlog',
        default=None, type=int,
        help='Number of unaccepted connections to buffer'
    )
    args = parser.parse_args()

    run_server(args.address, args.port, args.chunksize, args.directory, args.backlog)


if __name__ == '__main__':
    main()
