#! /usr/bin/env python3

from typing import List
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
            sock = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM
            )  # type: socket.socket
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
