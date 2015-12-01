"""Implements the underlying network communication for the package

Defines an Endpoint class that is utilized as both a server and client.
"""


import logging
import socket
import threading
import socketserver
import queue
import collections
from . import protocol


# Set up logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# Define a container for a packaged message to be sent
SendPackage = collections.namedtuple(
    'SendPackage', ['address', 'port', 'package']
)
"""collections.namedtuple: Container for an outgoing message.

Provides a single object for easily managing the outgoing queue (send_queue)
"""

# Define a container for received message that needs to be unpacked
RecvPackage = collections.namedtuple(
    'RecvPackage', ['address', 'data', 'data_blocks']
)
"""collections.namedtuple: Container for a received message.

Provides a single object for easily managing the incoming queue (recv_queue)
"""


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):

    def handle(self):
        chunk_list = []
        while True:
            tmp = self.request.recv(
                self.server.parent.buffer_size
            )
            if not tmp:
                break
            chunk_list.append(tmp)
        data = b''.join(chunk_list)

        # Have access to the server object with self.server
        # As it was passed to the server, self.server.parent is our Endpoint
        self.server.parent.recv_queue.put(
            RecvPackage(
                self.client_address,
                *protocol.deserialize(
                    data,
                    self.server.parent.encoding,
                    self.server.parent.errors
                )
            )
        )


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):

    def __init__(self, *args, **kwargs):
        # I popped the parent as I was getting an error if I passed the
        # keyword 'parent' to the super().__init__() method.
        self.parent = kwargs.pop('parent', None)
        super().__init__(*args, **kwargs)


class Endpoint:

    def __init__(
            self, address='localhost', port=9999,
            server=ThreadedTCPServer, buffer_size=4096,
            encoding=protocol.DFLT_ENCODING, errors=protocol.DFLT_ERRORS):
        # Assign instance variables from arguments
        self.buffer_size = buffer_size
        self.encoding = encoding
        self.errors = errors

        # Create new send and receive queues
        self.send_queue = queue.Queue()
        self.recv_queue = queue.Queue()

        self.address = address
        self.port = port
        log.debug('Creating listing server on ({}, {})'.format(
            self.address, self.port
        ))
        self.server = server(
            (self.address, self.port),
            ThreadedTCPRequestHandler,
            parent=self,
        )

        # Create threads
        self.recv_thread = threading.Thread(target=self.server.serve_forever)
        self.send_thread = threading.Thread(target=self.send_loop)

        # Set up threads to exit when the main thread exits
        self.recv_thread.daemon = True
        self.send_thread.daemon = True

    def send_loop(self):
        while True:
            # Get the next package in the queue or block while waiting
            send_package = self.send_queue.get()

            # Send the package
            sock = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM
            )
            try:
                log.debug('Attempting to send to ({}, {})'.format(
                    send_package.address, send_package.port
                ))
                sock.connect((send_package.address, send_package.port))
                sock.sendall(send_package.package)
                log.debug('Package sent!')
            except:
                log.error(
                    'An error occurred while attempting to send a package!'
                )
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


def package(
        address, port, data, data_blocks=None,
        encoding='utf-8', errors='strict'):
    """Creates a SendPackage with protocol.serialize() serialization

    Args:
        address (str): Package destination address.
        port (int): Package destination port number.
        data (Dict): Data to be serialized and packaged into a byte string.
        data_blocks (Optional[List[DataBlock]]): Zero or more DataBlock
            instances to be concatenated to the byte string. (default=None)
        encoding (str): Encoding for the JSON byte string. (default='utf-8')
        errors (str): Response when the JSON cannot be converted with the
            given encoding. (accepts: ['strict', 'replace', 'ignore'],
            default='strict')

    Returns:
        SendPackage: New instance with the given data serialized.
    """
    data_blocks = [] if data_blocks is None else data_blocks

    package = protocol.serialize(
        data, data_blocks, encoding, errors
    )
    return SendPackage(address, port, package)
