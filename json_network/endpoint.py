#! /usr/bin/env python3

import argparse
import sys
import os
import tempfile
from contextlib import closing
from typing import *
import logging
import socket
import threading
import socketserver
import queue
from . import protocol


# Set up logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class SendPackage:

    @classmethod
    def package(cls, address: str, port: int, *args, **kwargs):
        """Creates a SendPackage with protocol.package() serialization"""
        package = protocol.package(*args, **kwargs)  # type: bytes
        return cls(address, port, package)

    def __init__(self, address: str, port: int, package: bytes):
        """Creates a new instance of SendPackage

        SendPackages are packaged objects that are placed in the send queue,
        and tell the send thread method where to send the serialized data.

        Args:
            address (str): Address of the destination.
            port (int): Port number of the destination.
            package (bytes): Data to be sent serialized with the protocol
                module.
        """
        self.address = address  # type: str
        self.port = port  # type: int
        self.package = package  # type: bytes


class RecvPackage:

    def __init__(
            self, address: str,
            data: dict, data_blocks: List[protocol.DataBlock]):
        """Creates a new instance of RecvPackage

        RecvPackages are packaged objects that are placed in the recv queue,
        containing the final deserialized data and client information.

        Args:
            address (str): Client address data was received from.

        """
        self.address = address  # type: str
        self.data = data  # type: Dict
        self.data_blocks = data_blocks  # type: List[protocol.DataBlock]

    def __str__(self) -> str:
        return_list = [
            str(self.address),
            str(self.data),
            str(self.data_blocks),
        ]
        return '\n'.join(return_list)


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        log.debug('New ThreadedTCPRequestHandler instance')

    def handle(self):
        log.debug('Received connection from: {}'.format(
            self.client_address
        ))
        #print(self.client_address)
        chunk_list = []  # type: List[bytes]
        while True:
            tmp = self.request.recv(
                self.server.parent.buffer_size
            )  # type: bytes
            if not tmp:
                break
            chunk_list.append(tmp)
        data = b''.join(chunk_list)  # type: bytes

        # Have access to the server object with self.server
        self.server.parent.recv_queue.put(
            RecvPackage(self.client_address, *protocol.unpackage(data))
        )


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):

    def __init__(self, *args, **kwargs):
        self.parent = kwargs.pop('parent', None)  # type: Endpoint
        super().__init__(*args, **kwargs)


    def serve_forever(self):
        log.debug('Starting to serve forever...')
        super().serve_forever()
        log.error('Failed to server forever!')


class Endpoint:


    def __init__(
            self, address: str='localhost', port: int=9999,
            server: ThreadedTCPServer=ThreadedTCPServer,
            buffer_size: int=4096):
        self.buffer_size = buffer_size  # type: int

        # Create new send and receive queues
        self.send_queue = queue.Queue()  # type: queue.Queue[SendPackage]
        self.recv_queue = queue.Queue()  # type: queue.Queue[RecvPackage]

        self.address = address  # type: str
        self.port = port  # type: int
        log.debug('Creating listing server on ({}, {})'.format(
            self.address, self.port
        ))
        self.server = server(
            (self.address, self.port),
            ThreadedTCPRequestHandler,
            parent=self
        )  # type: ThreadedTCPServer

        # Create threads
        self.recv_thread = threading.Thread(target=self.server.serve_forever)  # type: threading.Thread
        self.send_thread = threading.Thread(target=self.send_loop)  # type: threading.Thread

        # Set up threads to exit when the main thread exits
        self.recv_thread.daemon = True  # type: bool
        self.send_thread.daemon = True  # type: bool

    def send_loop(self):
        while True:
            # Get the next package in the queue or block while waiting
            send_package = self.send_queue.get()  # type: SendPackage

            # Send the package
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # type: socket.socket
            try:
                log.debug('Attempting to send to ({}, {})'.format(
                    send_package.address, send_package.port
                ))
                sock.connect((send_package.address, send_package.port))
                sock.sendall(send_package.package)
                log.debug('Package sent!')
            except:
                log.warning('Error sending the package!')
            finally:
                sock.close()

    def run(self):
        log.debug('Starting the recv server...')
        self.recv_thread.start()
        log.debug('Starting the send server...')
        self.send_thread.start()

    def close(self):
        self.server.close()
        self.recv_thread.join()


def test_server(send_address, send_port, recv_address, recv_port):
    endpoint = Endpoint(recv_address, recv_port)
    endpoint.run()
    while True:
        text = input('> ')
        while True:
            log.info('looking for incoming: {}'.format(endpoint.recv_queue.qsize()))
            try:
                recv_package = endpoint.recv_queue.get(False)
                log.info(recv_package)
            except queue.Empty:
                break
        if text:
            endpoint.send_queue.put(SendPackage.package(send_address, send_port, {'text': text}))


# def run_server(address: str, port: int, chunksize: int, out_dir: str=None, backlog: int=None):
#     out_dir = os.getcwd() if out_dir is None else out_dir

#     with socket.socket() as sock:  # type: socket.socket
#         sock.bind((address, port))
#         sock.listen() if backlog is None else sock.listen(backlog)

#         while True:
#             conn, _ = sock.accept()  # type: socket.socket, (str, int)

#             fd, in_file_name = tempfile.mkstemp(dir=out_dir)  # type: int, str
#             with closing(os.fdopen(fd, 'wb')) as in_file:  # type: IO[bytes]
#                 # Read incoming information and write to a file
#                 chunk = conn.recv(chunksize)  # type: bytes
#                 while (chunk):
#                     in_file.write(chunk)
#                     chunk = conn.recv(chunksize)  # type: bytes
#             conn.close()


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
        default=59999, type=int,
        help='Port number'
    )
    parser.add_argument('-i', '--input_address',
        default='localhost', type=str,
        help='Listener address'
    )
    parser.add_argument('-r', '--receive_port',
        default=59998, type=int,
        help='Listener port number'
    )
    # parser.add_argument('-c', '--chunksize',
    #     default=1024, type=int,
    #     help='Chunk size to read in from connections'
    # )
    # parser.add_argument('-d', '--directory',
    #     default=os.getcwd(), type=str,
    #     help='Directory where received files should be written to'
    # )
    # parser.add_argument('-b', '--backlog',
    #     default=None, type=int,
    #     help='Number of unaccepted connections to buffer'
    # )
    args = parser.parse_args()

    log.info('To learn how to configure the server, run with -h flag.')
    log.info('Running server on {address}:{port}...'.format(**args.__dict__))
    # run_server(args.address, args.port, args.chunksize, args.directory, args.backlog)
    test_server(args.address, args.receive_port, args.address, args.port)

if __name__ == '__main__':
    main()
